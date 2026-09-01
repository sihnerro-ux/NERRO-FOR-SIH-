from copy import deepcopy
from datetime import UTC, datetime, timedelta

from app.domain.models import (
    Alert,
    ConnectivityItem,
    DataMode,
    Delivery,
    Facility,
    GeoJsonLineString,
    GeoJsonPoint,
    Incident,
    MapSnapshotResponse,
    OverviewResponse,
    RiskBand,
    RoadAccessibility,
    RoadSegment,
    Vehicle,
)


def now_utc() -> datetime:
    return datetime.now(UTC)


ROAD_BLUEPRINTS = [
    ("SEG-001", "NH 27", "GUWAHATI", "NAGAON", 121.0, [[91.7362, 26.1445], [92.15, 26.28], [92.68, 26.35]]),
    ("SEG-002", "NH 715", "NAGAON", "TEZPUR", 78.0, [[92.68, 26.35], [92.78, 26.52], [92.7926, 26.6528]]),
    ("SEG-003", "NH 15", "TEZPUR", "BHALUKPONG", 58.0, [[92.7926, 26.6528], [92.91, 26.82], [92.995, 27.011]]),
    ("SEG-004", "NH 13", "BHALUKPONG", "BOMDILA", 97.0, [[92.995, 27.011], [92.63, 27.15], [92.412, 27.264]]),
    ("SEG-005", "NH 13", "BOMDILA", "DIRANG", 42.0, [[92.412, 27.264], [92.28, 27.31], [92.267, 27.358]]),
    ("SEG-006", "Dirang-Sela Road", "DIRANG", "SELA", 63.0, [[92.267, 27.358], [92.18, 27.42], [92.105, 27.503]]),
    ("SEG-007", "Sela-Tawang Road", "SELA", "TAWANG", 78.0, [[92.105, 27.503], [91.99, 27.54], [91.865, 27.586]]),
]


class SeedStore:
    """Mutable deterministic state used until the PostGIS adapter is introduced."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        timestamp = now_utc()
        self.roads = [
            RoadSegment(
                id=item[0],
                road_name=item[1],
                from_node=item[2],
                to_node=item[3],
                distance_km=item[4],
                geometry=GeoJsonLineString(coordinates=item[5]),
                accessibility=RoadAccessibility.CAUTION if item[0] == "SEG-004" else RoadAccessibility.OPEN,
                risk_score=46 if item[0] == "SEG-004" else (34 if item[0] in {"SEG-005", "SEG-006"} else 16),
                risk_band=RiskBand.MODERATE if item[0] == "SEG-004" else (RiskBand.MODERATE if item[0] in {"SEG-005", "SEG-006"} else RiskBand.LOW),
                road_condition="FAIR" if item[0] in {"SEG-004", "SEG-005", "SEG-006"} else "GOOD",
                rainfall_mm_24h=42 if item[0] == "SEG-004" else 18,
                slope_degrees=31 if item[0] == "SEG-006" else (24 if item[0] in {"SEG-004", "SEG-005", "SEG-007"} else 6),
                source="Prototype corridor baseline",
                observed_at=timestamp - timedelta(minutes=8),
                updated_at=timestamp,
                confidence=84,
            )
            for item in ROAD_BLUEPRINTS
        ]
        self.vehicles = [
            Vehicle(
                id="VEH-001",
                registration="AS-01-ER-2048",
                vehicle_class="REFRIGERATED_TRUCK",
                status="IN_TRANSIT",
                latitude=26.6528,
                longitude=92.7926,
                speed_kph=42,
                heading=34,
                gps_freshness="LIVE",
                last_position_at=timestamp,
                active_delivery_id="DEL-1001",
            ),
            Vehicle(
                id="VEH-002",
                registration="AR-04-SF-1182",
                vehicle_class="RELIEF_TRUCK",
                status="IN_TRANSIT",
                latitude=27.264,
                longitude=92.412,
                speed_kph=31,
                heading=320,
                gps_freshness="LIVE",
                last_position_at=timestamp - timedelta(seconds=18),
                active_delivery_id="DEL-1002",
            ),
        ]
        self.facilities = [
            Facility(id="FAC-GHY-MED", name="Guwahati Medical Warehouse", facility_type="WAREHOUSE", district="Kamrup Metropolitan", location=GeoJsonPoint(coordinates=[91.7362, 26.1445])),
            Facility(id="FAC-TEZ-HUB", name="Tezpur Regional Supply Hub", facility_type="SUPPLY_CENTRE", district="Sonitpur", location=GeoJsonPoint(coordinates=[92.7926, 26.6528])),
            Facility(id="FAC-BOM-RELIEF", name="Bomdila Relief Depot", facility_type="WAREHOUSE", district="West Kameng", location=GeoJsonPoint(coordinates=[92.412, 27.264])),
            Facility(id="FAC-TAW-HOSP", name="Tawang District Hospital", facility_type="HOSPITAL", district="Tawang", location=GeoJsonPoint(coordinates=[91.865, 27.586])),
        ]
        self.incidents = [
            Incident(
                id="INC-1001",
                incident_type="HEAVY_RAIN",
                severity="WARNING",
                reported_accessibility=RoadAccessibility.CAUTION,
                verification="OFFICER_VERIFIED",
                location=GeoJsonPoint(coordinates=[92.64, 27.15]),
                matched_segment_id="SEG-004",
                description="Persistent rainfall and loose debris reported near the corridor.",
                source="Field officer report",
                data_mode=DataMode.SIMULATED,
                observed_at=timestamp - timedelta(minutes=26),
                received_at=timestamp - timedelta(minutes=21),
            )
        ]
        self.deliveries = [
            Delivery(
                id="DEL-1001",
                cargo_type="EMERGENCY_MEDICINES",
                cargo_description="Vaccines and critical medicines",
                priority="CRITICAL",
                source_name="Guwahati Medical Warehouse",
                destination_name="Tawang District Hospital",
                vehicle_id="VEH-001",
                status="IN_TRANSIT",
                progress_percent=38,
                planned_eta=timestamp + timedelta(hours=8, minutes=20),
                current_eta=timestamp + timedelta(hours=8, minutes=20),
                delay_minutes=0,
                route_id="ROUTE-1001",
            ),
            Delivery(
                id="DEL-1002",
                cargo_type="RELIEF_SUPPLIES",
                cargo_description="Food and emergency shelter kits",
                priority="HIGH",
                source_name="Tezpur Regional Supply Hub",
                destination_name="Bomdila Relief Depot",
                vehicle_id="VEH-002",
                status="IN_TRANSIT",
                progress_percent=72,
                planned_eta=timestamp + timedelta(hours=2, minutes=10),
                current_eta=timestamp + timedelta(hours=2, minutes=34),
                delay_minutes=24,
                route_id="ROUTE-1002",
            ),
        ]
        self.alerts = [
            Alert(
                id="ALT-1001",
                severity="WARNING",
                alert_type="WEATHER_RISK",
                title="Rainfall risk increasing",
                message="NH 13 near Bhalukpong is under caution. Monitor incoming field reports.",
                related_entity_type="ROAD_SEGMENT",
                related_entity_id="SEG-004",
                acknowledged=False,
                created_at=timestamp - timedelta(minutes=19),
            )
        ]

    def overview(self) -> OverviewResponse:
        generated_at = now_utc()
        return OverviewResponse(
            data_mode=DataMode.SIMULATED,
            generated_at=generated_at,
            metrics={
                "active_vehicles": sum(v.status == "IN_TRANSIT" for v in self.vehicles),
                "critical_deliveries": sum(d.priority == "CRITICAL" and d.status != "ARRIVED" for d in self.deliveries),
                "blocked_segments": sum(r.accessibility == RoadAccessibility.BLOCKED for r in self.roads),
                "high_risk_segments": sum(r.risk_band in {RiskBand.HIGH, RiskBand.CRITICAL} for r in self.roads),
                "delayed_deliveries": sum(d.delay_minutes > 0 for d in self.deliveries),
                "unverified_incidents": sum(i.verification == "UNVERIFIED" for i in self.incidents),
            },
            priority_deliveries=deepcopy(self.deliveries),
            critical_alerts=deepcopy(self.alerts),
            connectivity=[
                ConnectivityItem(name="Guwahati-Tezpur", score=94, status="OPEN"),
                ConnectivityItem(name="Tezpur-Bomdila", score=76, status="CAUTION"),
                ConnectivityItem(name="Bomdila-Tawang", score=81, status="OPEN"),
            ],
        )

    def map_snapshot(self) -> MapSnapshotResponse:
        return MapSnapshotResponse(
            data_mode=DataMode.SIMULATED,
            generated_at=now_utc(),
            road_segments=deepcopy(self.roads),
            vehicles=deepcopy(self.vehicles),
            facilities=deepcopy(self.facilities),
            incidents=deepcopy(self.incidents),
        )

    def apply_heavy_rain(self) -> list[str]:
        timestamp = now_utc()
        changed = []
        for road in self.roads:
            if road.id in {"SEG-005", "SEG-006"}:
                road.rainfall_mm_24h = 96
                road.risk_score = 78 if road.id == "SEG-005" else 86
                road.risk_band = RiskBand.HIGH if road.id == "SEG-005" else RiskBand.CRITICAL
                road.accessibility = RoadAccessibility.HIGH_RISK
                road.source = "Simulated heavy-rain event"
                road.observed_at = timestamp
                road.updated_at = timestamp
                changed.append(road.id)
        self.alerts.insert(
            0,
            Alert(
                id="ALT-RAIN-01",
                severity="CRITICAL",
                alert_type="PREDICTED_DISRUPTION",
                title="Critical landslide risk near Sela",
                message="Heavy rainfall raised disruption risk on two upcoming medicine-route segments.",
                related_entity_type="DELIVERY",
                related_entity_id="DEL-1001",
                acknowledged=False,
                created_at=timestamp,
            ),
        )
        self.deliveries[0].status = "AT_RISK"
        return changed + ["DEL-1001", "ALT-RAIN-01"]


store = SeedStore()

