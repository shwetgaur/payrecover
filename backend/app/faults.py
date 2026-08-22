from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import FaultConfig
from app.schemas import FaultState


def get_faults(db: Session) -> FaultState:
    row = db.get(FaultConfig, 1)
    if row is None:
        row = FaultConfig(id=1, llm="up", whatsapp="ok")
        db.add(row)
        db.commit()
        db.refresh(row)
    return FaultState(llm=row.llm, whatsapp=row.whatsapp)  # type: ignore[arg-type]


def set_faults(db: Session, llm: str | None = None, whatsapp: str | None = None) -> FaultState:
    state = get_faults(db)
    row = db.get(FaultConfig, 1)
    assert row is not None
    if llm:
        row.llm = llm
    if whatsapp:
        row.whatsapp = whatsapp
    db.commit()
    return FaultState(llm=row.llm, whatsapp=row.whatsapp)  # type: ignore[arg-type]
