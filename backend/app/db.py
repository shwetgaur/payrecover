from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATA_DIR, get_settings


class Base(DeclarativeBase):
    pass


def _engine_url() -> str:
    settings = get_settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return settings.database_url_resolved


_engine_url = _engine_url()
engine = create_engine(
    _engine_url,
    connect_args={"check_same_thread": False} if _engine_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
