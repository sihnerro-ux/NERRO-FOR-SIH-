from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.db.database import Base


class PostGISGeometry(UserDefinedType):
    """Native PostGIS geometry with a JSON fallback for local SQLite."""

    cache_ok = True

    def __init__(self, geometry_type: str, srid: int = 4326) -> None:
        self.geometry_type = geometry_type
        self.srid = srid

    def get_col_spec(self, **_kw) -> str:
        return f"geometry({self.geometry_type},{self.srid})"


POINT_GEOMETRY = PostGISGeometry("Point").with_variant(JSON(), "sqlite")
LINE_GEOMETRY = PostGISGeometry("LineString").with_variant(JSON(), "sqlite")


class OperationalStateRow(Base):
    __tablename__ = "operational_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(100), default="SYSTEM", nullable=False)
    changed_entities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True, nullable=False)


class RoadSegmentRow(Base):
    __tablename__ = "road_segments"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    road_name: Mapped[str] = mapped_column(String(160), index=True)
    from_node: Mapped[str] = mapped_column(String(100), index=True)
    to_node: Mapped[str] = mapped_column(String(100), index=True)
    accessibility: Mapped[str] = mapped_column(String(30), index=True)
    risk_score: Mapped[int] = mapped_column(Integer, index=True)
    distance_km: Mapped[float] = mapped_column(Float)
    geometry_geojson: Mapped[Any] = mapped_column(LINE_GEOMETRY)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (Index("ix_road_segments_geometry_geojson_gist", "geometry_geojson", postgresql_using="gist"),)


class VehicleRow(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    registration: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    active_delivery_id: Mapped[str | None] = mapped_column(String(40), index=True)
    position: Mapped[Any] = mapped_column(POINT_GEOMETRY)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (Index("ix_vehicles_position_gist", "position", postgresql_using="gist"),)


class FacilityRow(Base):
    __tablename__ = "facilities"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    facility_type: Mapped[str] = mapped_column(String(50), index=True)
    district: Mapped[str] = mapped_column(String(120), index=True)
    location_geojson: Mapped[Any] = mapped_column(POINT_GEOMETRY)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (Index("ix_facilities_location_geojson_gist", "location_geojson", postgresql_using="gist"),)


class IncidentRow(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    incident_type: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(30), index=True)
    verification: Mapped[str] = mapped_column(String(40), index=True)
    matched_segment_id: Mapped[str | None] = mapped_column(String(40), index=True)
    location_geojson: Mapped[Any] = mapped_column(POINT_GEOMETRY)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (Index("ix_incidents_location_geojson_gist", "location_geojson", postgresql_using="gist"),)


class DeliveryRow(Base):
    __tablename__ = "deliveries"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    priority: Mapped[str] = mapped_column(String(30), index=True)
    vehicle_id: Mapped[str] = mapped_column(String(40), index=True)
    route_id: Mapped[str] = mapped_column(String(80), index=True)
    current_eta: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class AlertRow(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    severity: Mapped[str] = mapped_column(String(30), index=True)
    alert_type: Mapped[str] = mapped_column(String(60), index=True)
    related_entity_type: Mapped[str] = mapped_column(String(50), index=True)
    related_entity_id: Mapped[str] = mapped_column(String(60), index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    username: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(50), index=True)
    district: Mapped[str | None] = mapped_column(String(120), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class EvidenceRow(Base):
    __tablename__ = "evidence_objects"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    client_report_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    object_key: Mapped[str] = mapped_column(String(300), unique=True)
    content_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_backend: Mapped[str] = mapped_column(String(30))
    uploaded_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True, nullable=False)
