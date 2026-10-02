from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from sqlalchemy import delete, func, select, text

from app.db.database import Base, SessionLocal, database_backend, engine
from app.db.tables import (
    AlertRow,
    AuditEventRow,
    DeliveryRow,
    EvidenceRow,
    FacilityRow,
    IncidentRow,
    OperationalStateRow,
    RoadSegmentRow,
    VehicleRow,
)


class OperationalRepository:
    def __init__(self) -> None:
        Base.metadata.create_all(engine)

    def load_state(self) -> dict[str, Any] | None:
        with SessionLocal() as session:
            row = session.get(OperationalStateRow, 1)
            return row.payload if row else None

    def save_state(
        self,
        payload: dict[str, Any],
        event_type: str,
        changed_entities: list[str] | None = None,
        actor: str = "SYSTEM",
        details: dict[str, Any] | None = None,
    ) -> None:
        timestamp = datetime.now(UTC)
        with SessionLocal.begin() as session:
            row = session.get(OperationalStateRow, 1)
            if row is None:
                row = OperationalStateRow(id=1, payload=payload, updated_at=timestamp)
                session.add(row)
            else:
                row.payload = payload
                row.updated_at = timestamp
            self._replace_materialized_entities(session, payload)
            session.add(AuditEventRow(
                event_type=event_type,
                actor=actor,
                changed_entities=changed_entities or [],
                details=details or {},
                created_at=timestamp,
            ))

    @staticmethod
    def _as_datetime(value: str | datetime) -> datetime:
        return value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _replace_materialized_entities(self, session, payload: dict[str, Any]) -> None:
        for table in (RoadSegmentRow, VehicleRow, FacilityRow, IncidentRow, DeliveryRow, AlertRow):
            session.execute(delete(table))

        session.add_all([
            RoadSegmentRow(
                id=item["id"], road_name=item["road_name"], from_node=item["from_node"], to_node=item["to_node"],
                accessibility=item["accessibility"], risk_score=item["risk_score"], distance_km=item["distance_km"],
                geometry_geojson=self._spatial_value(item["geometry"]), payload=item, updated_at=self._as_datetime(item["updated_at"]),
            ) for item in payload.get("roads", [])
        ])
        session.add_all([
            VehicleRow(
                id=item["id"], registration=item["registration"], status=item["status"],
                active_delivery_id=item.get("active_delivery_id"),
                position=self._spatial_value({"type": "Point", "coordinates": [item["longitude"], item["latitude"]]}),
                payload=item, updated_at=self._as_datetime(item["last_position_at"]),
            ) for item in payload.get("vehicles", [])
        ])
        session.add_all([
            FacilityRow(
                id=item["id"], name=item["name"], facility_type=item["facility_type"], district=item["district"],
                location_geojson=self._spatial_value(item["location"]), payload=item,
            ) for item in payload.get("facilities", [])
        ])
        session.add_all([
            IncidentRow(
                id=item["id"], incident_type=item["incident_type"], severity=item["severity"],
                verification=item["verification"], matched_segment_id=item.get("matched_segment_id"),
                location_geojson=self._spatial_value(item["location"]), payload=item, received_at=self._as_datetime(item["received_at"]),
            ) for item in payload.get("incidents", [])
        ])
        session.add_all([
            DeliveryRow(
                id=item["id"], status=item["status"], priority=item["priority"], vehicle_id=item["vehicle_id"],
                route_id=item["route_id"], current_eta=self._as_datetime(item["current_eta"]), payload=item,
            ) for item in payload.get("deliveries", [])
        ])
        session.add_all([
            AlertRow(
                id=item["id"], severity=item["severity"], alert_type=item["alert_type"],
                related_entity_type=item["related_entity_type"], related_entity_id=item["related_entity_id"],
                acknowledged=item["acknowledged"], created_at=self._as_datetime(item["created_at"]), payload=item,
            ) for item in payload.get("alerts", [])
        ])

    @staticmethod
    def _spatial_value(geojson: dict[str, Any]):
        if database_backend() == "postgresql":
            return func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(geojson)), 4326)
        return geojson

    def recent_audit_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            rows = session.scalars(select(AuditEventRow).order_by(AuditEventRow.id.desc()).limit(limit)).all()
            return [
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "actor": row.actor,
                    "changed_entities": row.changed_entities,
                    "details": row.details,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def vehicle_position_history(self, vehicle_id: str, limit: int = 100) -> list[dict[str, Any]]:
        scan_limit = max(limit * 10, 200)
        with SessionLocal() as session:
            latest_reset_id = session.scalar(
                select(func.max(AuditEventRow.id)).where(AuditEventRow.event_type == "DEMO_RESET")
            ) or 0
            rows = session.scalars(
                select(AuditEventRow)
                .where(
                    AuditEventRow.event_type == "GPS_POSITION_RECEIVED",
                    AuditEventRow.id > latest_reset_id,
                )
                .order_by(AuditEventRow.id.desc())
                .limit(scan_limit)
            ).all()
            return [
                {"id": row.id, **row.details, "received_at": row.created_at}
                for row in rows
                if row.details.get("vehicle_id") == vehicle_id
            ][:limit]

    def entity_counts(self) -> dict[str, int]:
        tables = {
            "road_segments": RoadSegmentRow,
            "vehicles": VehicleRow,
            "facilities": FacilityRow,
            "incidents": IncidentRow,
            "deliveries": DeliveryRow,
            "alerts": AlertRow,
            "audit_events": AuditEventRow,
            "evidence_objects": EvidenceRow,
        }
        with SessionLocal() as session:
            return {name: session.scalar(select(func.count()).select_from(table)) or 0 for name, table in tables.items()}

    def spatial_capabilities(self) -> dict[str, Any]:
        if database_backend() != "postgresql":
            return {"postgis": False, "version": None, "geometry_storage": "GEOJSON_FALLBACK"}
        try:
            with SessionLocal() as session:
                version = session.scalar(text("SELECT PostGIS_Version()"))
            return {"postgis": True, "version": str(version), "geometry_storage": "POSTGIS_GEOMETRY_4326"}
        except Exception:
            return {"postgis": False, "version": None, "geometry_storage": "POSTGRESQL_WITHOUT_POSTGIS"}

    @property
    def backend(self) -> str:
        return database_backend()


operational_repository = OperationalRepository()
