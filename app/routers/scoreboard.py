import asyncio
from datetime import datetime
import time
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..crud.dashboard import build_location_scoreboard, get_location_scoreboard_version
from ..database import SessionLocal, get_db
from .. import models

router = APIRouter(prefix="/api/v1/public", tags=["public"])


@router.get("/locations/{location_id}/scoreboard", response_model=schemas.LocationScoreboard)
def get_location_scoreboard(location_id: int, db: Session = Depends(get_db)):
    data = build_location_scoreboard(db, location_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return data


async def _location_scoreboard_stream(
    location_id: int, request: Request, poll_interval: float
) -> AsyncIterator[str]:
    last_version: Optional[str] = None
    last_heartbeat = time.monotonic()
    heartbeat_interval = max(15.0, poll_interval * 4)

    def query_version() -> Optional[datetime]:
        with SessionLocal() as session:
            return get_location_scoreboard_version(session, location_id)

    while True:
        if await request.is_disconnected():
            break

        version = await asyncio.to_thread(query_version)

        now = time.monotonic()

        if version is not None:
            iso_value = version.isoformat()
            if iso_value != last_version:
                last_version = iso_value
                last_heartbeat = now
                yield f"data: {iso_value}\n\n"
            elif now - last_heartbeat >= heartbeat_interval:
                last_heartbeat = now
                yield ": keep-alive\n\n"
        elif now - last_heartbeat >= heartbeat_interval:
            last_heartbeat = now
            yield ": keep-alive\n\n"

        await asyncio.sleep(poll_interval)


@router.get("/locations/{location_id}/scoreboard/stream")
async def stream_location_scoreboard(
    location_id: int,
    request: Request,
    poll_interval: float = 2.0,
):
    poll_interval = max(0.5, min(poll_interval, 10.0))

    with SessionLocal() as session:
        location_exists = (
            session.query(models.Location.id)
            .filter(models.Location.id == location_id)
            .first()
        )
        if location_exists is None:
            raise HTTPException(status_code=404, detail="Location not found")

    generator = _location_scoreboard_stream(location_id, request, poll_interval)
    return StreamingResponse(generator, media_type="text/event-stream")
