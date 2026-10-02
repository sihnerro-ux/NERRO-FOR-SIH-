from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "ner_logistics.db"
DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _database_url() -> str | URL:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    database_host = os.getenv("DB_HOST")
    if database_host:
        return URL.create(
            drivername="postgresql+psycopg",
            username=os.getenv("DB_USER", "ner_app"),
            password=os.getenv("DB_PASSWORD", ""),
            host=database_host,
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "ner_logistics"),
        )

    return f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"


DATABASE_URL = _database_url()
engine_options = (
    {"connect_args": {"check_same_thread": False}}
    if str(DATABASE_URL).startswith("sqlite")
    else {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20, "pool_recycle": 1800}
)
engine = create_engine(DATABASE_URL, future=True, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def database_backend() -> str:
    return engine.dialect.name
