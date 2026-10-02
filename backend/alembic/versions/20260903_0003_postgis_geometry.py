"""Enable PostGIS and convert operational GeoJSON columns to geometry.

Revision ID: 20260903_0003
Revises: 20260902_0002
"""

from alembic import op


revision = "20260903_0003"
down_revision = "20260902_0002"
branch_labels = None
depends_on = None


GEOMETRY_COLUMNS = (
    ("road_segments", "geometry_geojson", "LineString"),
    ("vehicles", "position", "Point"),
    ("facilities", "location_geojson", "Point"),
    ("incidents", "location_geojson", "Point"),
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    for table, column, geometry_type in GEOMETRY_COLUMNS:
        op.execute(f"""
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = '{table}'
              AND column_name = '{column}'
              AND udt_name <> 'geometry'
          ) THEN
            ALTER TABLE {table}
              ALTER COLUMN {column} TYPE geometry({geometry_type},4326)
              USING ST_SetSRID(ST_GeomFromGeoJSON({column}::text),4326);
          END IF;
        END $$;
        """)
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_{column}_gist "
            f"ON {table} USING GIST ({column})"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, column, _geometry_type in reversed(GEOMETRY_COLUMNS):
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_{column}_gist")
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE json "
            f"USING ST_AsGeoJSON({column})::json"
        )

