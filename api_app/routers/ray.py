import os
import secrets
from typing import List, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .. import database, udp

router = APIRouter(prefix="/ray", tags=["ray"])


async def _verify_ray_password(x_ray_password: str | None = Header(default=None)) -> None:
    configured = os.getenv("RAY_PASSWORD")
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ray password not configured.",
        )
    if not x_ray_password or not secrets.compare_digest(x_ray_password, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "X-Ray"},
        )


class RayDiscoveryPeer(BaseModel):
    ip: str
    name: str | None = None


class RayDiscoveryRequest(BaseModel):
    ip: str
    type: Literal["hello", "full"]
    name: str | None = None
    peers: List[RayDiscoveryPeer] = Field(default_factory=list)


class RayGameStateRequest(BaseModel):
    ip: str
    data: dict


@router.post("/discovery")
async def ingest_discovery(
    payload: RayDiscoveryRequest,
    db: AsyncSession = Depends(database.get_db),
    _: None = Depends(_verify_ray_password),
):
    if payload.type == "hello" and not payload.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discovery hello messages require a name.",
        )

    peers = [(peer.ip, peer.name or "") for peer in payload.peers]
    name = payload.name if payload.type == "hello" else None
    await udp.ingest_discovery(db, payload.ip, name=name, peers=peers)
    return {"status": "ok"}


@router.post("/game-state")
async def ingest_game_state(
    payload: RayGameStateRequest,
    db: AsyncSession = Depends(database.get_db),
    _: None = Depends(_verify_ray_password),
):
    await udp.ingest_game_state(db, payload.data, payload.ip)
    return {"status": "ok"}


@router.post("/ping")
async def ping(_: None = Depends(_verify_ray_password)):
    return {"status": "ok"}
