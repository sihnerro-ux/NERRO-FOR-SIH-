"""Add secure field evidence metadata.

Revision ID: 20260904_0004
Revises: 20260903_0003
"""

from alembic import op
import sqlalchemy as sa


revision = "20260904_0004"
down_revision = "20260903_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_objects",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("client_report_id", sa.String(100), nullable=True),
        sa.Column("object_key", sa.String(300), nullable=False),
        sa.Column("content_type", sa.String(80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_backend", sa.String(30), nullable=False),
        sa.Column("uploaded_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_report_id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_evidence_objects_client_report_id", "evidence_objects", ["client_report_id"], unique=True)
    op.create_index("ix_evidence_objects_sha256", "evidence_objects", ["sha256"])
    op.create_index("ix_evidence_objects_created_at", "evidence_objects", ["created_at"])


def downgrade() -> None:
    op.drop_table("evidence_objects")
