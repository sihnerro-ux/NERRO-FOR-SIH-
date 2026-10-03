"""Create the initial operational persistence schema.

Revision ID: 20260902_0001
Revises: None
"""

from alembic import op

from app.db.database import Base
from app.db import tables  # noqa: F401


revision = "20260902_0001"
down_revision = None
branch_labels = None
depends_on = None


INITIAL_TABLE_NAMES = (
    "operational_state",
    "audit_events",
    "road_segments",
    "vehicles",
    "facilities",
    "incidents",
    "deliveries",
    "alerts",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    operational_tables = [
        Base.metadata.tables[name] for name in INITIAL_TABLE_NAMES
    ]
    Base.metadata.create_all(bind=bind, tables=operational_tables)


def downgrade() -> None:
    operational_tables = [
        Base.metadata.tables[name] for name in INITIAL_TABLE_NAMES
    ]
    Base.metadata.drop_all(bind=op.get_bind(), tables=operational_tables)
