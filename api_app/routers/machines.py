from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import database, models, schemas

router = APIRouter(prefix="/machines", tags=["machines"])


@router.post("/", response_model=schemas.Machine)
async def create_machine(machine: schemas.MachineCreate, db: AsyncSession = Depends(database.get_db)):
    db_machine = models.Machine(**machine.model_dump())
    db.add(db_machine)
    await db.commit()
    await db.refresh(db_machine)
    return db_machine


@router.get("/", response_model=List[schemas.Machine])
async def read_machines(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(
        select(models.Machine)
        .order_by(models.Machine.last_seen.desc(), models.Machine.id.desc())
        .offset(skip)
        .limit(limit)
    )

    seen_uids = set()
    unique_machines = []

    for machine in result.scalars().all():
        if machine.uid in seen_uids:
            continue
        seen_uids.add(machine.uid)
        unique_machines.append(machine)

    return unique_machines
