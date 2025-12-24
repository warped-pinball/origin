import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import database, models, schemas, udp

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBasic()
logger = logging.getLogger(__name__)

UPDATE_CHECK_COOLDOWN_SECONDS = 5 * 60
_update_check_cache: dict[str, tuple[datetime, dict | None]] = {}


def _verify_admin(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin password not configured.",
        )

    if not secrets.compare_digest(credentials.password, password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )


async def _get_game_with_machine(game_id: int, db: AsyncSession) -> models.Game:
    result = await db.execute(
        select(models.Game).where(models.Game.id == game_id).options(selectinload(models.Game.machine))
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    if game.machine is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game has no machine attached")
    return game


async def _refresh_machine_version(db: AsyncSession, machine: models.Machine) -> models.Machine:
    now = datetime.now(timezone.utc)
    last_checked = machine.version_checked_at
    if last_checked and last_checked.tzinfo is None:
        last_checked = last_checked.replace(tzinfo=timezone.utc)

    if last_checked:
        age = (now - last_checked).total_seconds()
        if age < udp.VERSION_FETCH_COOLDOWN_SECONDS:
            logger.info(
                "Using cached machine version for uid=%s checked %.1fs ago", machine.uid, age
            )
            return machine

    logger.info("Refreshing machine version for uid=%s ip=%s", machine.uid, machine.ip_address)
    version = await udp._fetch_machine_version(machine.ip_address)
    machine.version_checked_at = datetime.now(timezone.utc)
    machine.version = version
    db.add(machine)
    await db.commit()
    await db.refresh(machine)
    return machine


async def _fetch_update_check(machine: models.Machine) -> dict | None:
    key = machine.uid or str(machine.id)
    now = datetime.now(timezone.utc)
    cached = _update_check_cache.get(key)
    if cached:
        cached_at, payload = cached
        if (now - cached_at).total_seconds() < UPDATE_CHECK_COOLDOWN_SECONDS:
            return payload

    if not machine.ip_address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Machine IP unavailable")

    url = f"http://{machine.ip_address}/api/update/check"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        if response.status_code >= 500:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Machine update check failed")
        if not response.is_success:
            detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else None
            raise HTTPException(status_code=response.status_code, detail=detail or "Unable to check updates")
        payload = response.json()
        _update_check_cache[key] = (now, payload)
        return payload


async def _apply_machine_update(game: models.Game, url: str) -> dict:
    machine = game.machine
    if not machine.ip_address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Machine IP unavailable")
    if not game.admin_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Set a machine password before applying updates")

    body = schemas.UpdateApplyRequest(url=url).model_dump_json()
    base_url = f"http://{machine.ip_address}" if not machine.ip_address.startswith("http") else machine.ip_address
    async with httpx.AsyncClient(timeout=10) as client:
        challenge_resp = await client.get(f"{base_url}/api/auth/challenge")
    if not challenge_resp.is_success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to request authentication challenge")

    challenge = challenge_resp.json().get("challenge")
    if not challenge:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid authentication challenge")

    message = f"{challenge}/api/update/apply{body}"
    signature = hmac.new(
        game.admin_password.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "x-auth-challenge": challenge,
        "x-auth-hmac": signature,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(f"{base_url}/api/update/apply", content=body, headers=headers)
        if not response.is_success:
            detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else None
            raise HTTPException(status_code=response.status_code, detail=detail or "Unable to apply update")
        try:
            return response.json()
        except Exception:
            return {"status": "ok"}


@router.get("/players", response_model=List[schemas.Player])
async def list_players_for_admin(
    search: str | None = None,
    db: AsyncSession = Depends(database.get_db),
    _: None = Depends(_verify_admin),
):
    query = select(models.Player)
    if search:
        from .players import _build_search_filter  # local import to avoid cycle

        query = query.where(_build_search_filter(search))

    result = await db.execute(query)
    return result.scalars().all()


@router.put("/games/{game_id}/password", response_model=schemas.GamePasswordStatus)
async def set_game_password(
    game_id: int,
    payload: schemas.GamePasswordUpdate,
    db: AsyncSession = Depends(database.get_db),
    _: None = Depends(_verify_admin),
):
    game = await db.get(models.Game, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    game.admin_password = payload.password
    db.add(game)
    await db.commit()

    return schemas.GamePasswordStatus(id=game.id, has_password=bool(game.admin_password))


@router.get("/games/{game_id}/version", response_model=schemas.MachineVersionStatus)
async def refresh_machine_version(
    game_id: int, db: AsyncSession = Depends(database.get_db), _: None = Depends(_verify_admin)
):
    game = await _get_game_with_machine(game_id, db)
    machine = await _refresh_machine_version(db, game.machine)
    return schemas.MachineVersionStatus(
        machine_version=machine.version, machine_version_checked_at=machine.version_checked_at
    )


@router.get("/games/{game_id}/updates/check")
async def check_machine_updates(
    game_id: int, db: AsyncSession = Depends(database.get_db), _: None = Depends(_verify_admin)
):
    game = await _get_game_with_machine(game_id, db)
    payload = await _fetch_update_check(game.machine)
    return payload or {}


@router.post("/games/{game_id}/updates/apply")
async def apply_machine_updates(
    game_id: int,
    payload: schemas.UpdateApplyRequest,
    db: AsyncSession = Depends(database.get_db),
    _: None = Depends(_verify_admin),
):
    game = await _get_game_with_machine(game_id, db)
    return await _apply_machine_update(game, payload.url)
