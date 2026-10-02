from copy import deepcopy
from datetime import UTC, datetime, timedelta
from math import cos, hypot, radians
from uuid import uuid4

from app.domain.models import (
    Alert,
    AlertAcknowledgementRequest,
    ConnectivityItem,
    DataMode,
    Delivery,
    DeliveryCreateRequest,
    FieldIncidentReportRequest,
    IncidentVerificationRequest,
    Facility,
    GeoJsonLineString,
    GeoJsonMultiPolygon,
    GeoJsonPoint,
    Incident,
    MapSnapshotResponse,
    OverviewResponse,
    RiskBand,
    RoadAccessibility,
    RoadSegment,
    RouteLocation,
    Vehicle,
    VehiclePositionRequest,
    VehicleRegistrationRequest,
    VehicleTelemetry,
    AnalyticsResponse,
    DistrictAnalytics,
    RiskCorridorAnalytics,
    StateConnectivityAnalytics,
)
from app.domain.models import RoutePlanRequest
from app.db.repository import operational_repository
from app.intelligence.model_adapter import model_adapter
from app.routing.engine import RoutingEngine
from app.routing.service import route_planning_service
from app.weather.open_meteo import WeatherReading
from app.seed.ner_assets import ADDITIONAL_FACILITY_BLUEPRINTS, ADDITIONAL_NODE_STATES, ADDITIONAL_ROAD_BLUEPRINTS


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
    ("SEG-008", "NH 15", "GUWAHATI", "MANGALDAI", 68.0, [[91.7362, 26.1445], [91.91, 26.3], [92.032, 26.442]]),
    ("SEG-009", "NH 15", "MANGALDAI", "ORANG", 56.0, [[92.032, 26.442], [92.17, 26.5], [92.31, 26.551]]),
    ("SEG-010", "Orang-Kalaktang Road", "ORANG", "KALAKTANG", 96.0, [[92.31, 26.551], [92.21, 26.78], [92.123, 27.106]]),
    ("SEG-011", "OKSRT Road", "KALAKTANG", "SHERGAON", 68.0, [[92.123, 27.106], [92.18, 27.16], [92.277, 27.133]]),
    ("SEG-012", "Shergaon-Rupa Road", "SHERGAON", "RUPA", 34.0, [[92.277, 27.133], [92.34, 27.18], [92.399, 27.203]]),
    ("SEG-013", "Rupa-Bomdila Road", "RUPA", "BOMDILA", 49.0, [[92.399, 27.203], [92.42, 27.23], [92.412, 27.264]]),
]

# NER-wide prototype monitoring mesh. These are operational sampling corridors;
# arbitrary route geometry still comes from the external OpenStreetMap road graph.
ROAD_BLUEPRINTS += [
    ("SEG-014", "NH 6", "GUWAHATI", "SHILLONG", 99.0, [[91.7362, 26.1445], [91.64, 25.91], [91.8933, 25.5788]]),
    ("SEG-015", "NH 6", "SHILLONG", "SILCHAR", 214.0, [[91.8933, 25.5788], [92.47, 25.45], [92.79, 24.83]]),
    ("SEG-016", "NH 6", "SILCHAR", "AIZAWL", 172.0, [[92.7789, 24.8333], [92.73, 24.25], [92.7176, 23.7271]]),
    ("SEG-017", "NH 54", "AIZAWL", "LUNGLEI", 168.0, [[92.7176, 23.7271], [92.75, 23.31], [92.7477, 22.887]]),
    ("SEG-018", "NH 37", "SILCHAR", "IMPHAL", 248.0, [[92.7789, 24.8333], [93.38, 24.75], [93.9368, 24.817]]),
    ("SEG-019", "NH 2", "IMPHAL", "KOHIMA", 136.0, [[93.9368, 24.817], [94.05, 25.22], [94.1086, 25.6751]]),
    ("SEG-020", "NH 29", "KOHIMA", "DIMAPUR", 74.0, [[94.1086, 25.6751], [93.98, 25.78], [93.7266, 25.9091]]),
    ("SEG-021", "NH 2", "DIMAPUR", "JORHAT", 136.0, [[93.7266, 25.9091], [93.95, 26.35], [94.2037, 26.7509]]),
    ("SEG-022", "NH 2", "JORHAT", "DIBRUGARH", 138.0, [[94.2037, 26.7509], [94.62, 27.04], [94.912, 27.4728]]),
    ("SEG-023", "NH 15", "DIBRUGARH", "PASIGHAT", 154.0, [[94.912, 27.4728], [95.18, 27.68], [95.326, 28.0661]]),
    ("SEG-024", "NH 2", "IMPHAL", "CHURACHANDPUR", 64.0, [[93.9368, 24.817], [93.79, 24.56], [93.6833, 24.3333]]),
    ("SEG-025", "NH 102B", "IMPHAL", "MOREH", 110.0, [[93.9368, 24.817], [94.12, 24.48], [94.31, 24.25]]),
    ("SEG-026", "NH 6", "AIZAWL", "CHAMPHAI", 188.0, [[92.7176, 23.7271], [93.02, 23.62], [93.33, 23.47]]),
    ("SEG-027", "NH 8", "SILCHAR", "DHARMANAGAR", 111.0, [[92.7789, 24.8333], [92.48, 24.63], [92.1783, 24.3786]]),
    ("SEG-028", "NH 8", "DHARMANAGAR", "AGARTALA", 173.0, [[92.1783, 24.3786], [91.71, 24.06], [91.2868, 23.8315]]),
    ("SEG-029", "NH 8", "AGARTALA", "UDAIPUR", 53.0, [[91.2868, 23.8315], [91.31, 23.65], [91.48, 23.53]]),
    ("SEG-030", "NH 17", "GUWAHATI", "TURA", 216.0, [[91.7362, 26.1445], [90.96, 25.85], [90.2024, 25.5142]]),
    ("SEG-031", "NH 217", "SHILLONG", "TURA", 305.0, [[91.8933, 25.5788], [91.08, 25.55], [90.2024, 25.5142]]),
    ("SEG-032", "NH 27", "GUWAHATI", "KOKRAJHAR", 226.0, [[91.7362, 26.1445], [90.72, 26.38], [90.27, 26.4]]),
    ("SEG-033", "NH 10", "KOKRAJHAR", "GANGTOK", 338.0, [[90.27, 26.4], [89.52, 26.72], [88.6065, 27.3389]]),
    ("SEG-034", "NH 710", "GANGTOK", "NAMCHI", 78.0, [[88.6065, 27.3389], [88.48, 27.25], [88.35, 27.1667]]),
    ("SEG-035", "NH 13", "PASIGHAT", "ALONG", 105.0, [[95.326, 28.0661], [94.95, 28.1], [94.8, 28.17]]),
    ("SEG-036", "NH 13", "ALONG", "ZIRO", 285.0, [[94.8, 28.17], [94.25, 27.87], [93.83, 27.59]]),
    ("SEG-037", "NH 13", "ZIRO", "ITANAGAR", 111.0, [[93.83, 27.59], [93.72, 27.31], [93.6053, 27.0844]]),
    ("SEG-038", "NH 702", "KOHIMA", "MOKOKCHUNG", 145.0, [[94.1086, 25.6751], [94.34, 26.05], [94.52, 26.32]]),
    ("SEG-039", "NH 2", "MOKOKCHUNG", "JORHAT", 110.0, [[94.52, 26.32], [94.37, 26.52], [94.2037, 26.7509]]),
    ("SEG-040", "NH 106", "SHILLONG", "NONGSTOIN", 95.0, [[91.8933, 25.5788], [91.55, 25.52], [91.27, 25.52]]),
]

ROAD_BLUEPRINTS += ADDITIONAL_ROAD_BLUEPRINTS

NODE_STATES = {
    "GUWAHATI": "Assam", "NAGAON": "Assam", "TEZPUR": "Assam", "BHALUKPONG": "Arunachal Pradesh",
    "BOMDILA": "Arunachal Pradesh", "DIRANG": "Arunachal Pradesh", "SELA": "Arunachal Pradesh", "TAWANG": "Arunachal Pradesh",
    "MANGALDAI": "Assam", "ORANG": "Assam", "KALAKTANG": "Arunachal Pradesh", "SHERGAON": "Arunachal Pradesh", "RUPA": "Arunachal Pradesh",
    "SHILLONG": "Meghalaya", "SILCHAR": "Assam", "AIZAWL": "Mizoram", "LUNGLEI": "Mizoram", "IMPHAL": "Manipur",
    "KOHIMA": "Nagaland", "DIMAPUR": "Nagaland", "JORHAT": "Assam", "DIBRUGARH": "Assam", "PASIGHAT": "Arunachal Pradesh",
    "CHURACHANDPUR": "Manipur", "MOREH": "Manipur", "CHAMPHAI": "Mizoram", "DHARMANAGAR": "Tripura", "AGARTALA": "Tripura",
    "UDAIPUR": "Tripura", "TURA": "Meghalaya", "KOKRAJHAR": "Assam", "GANGTOK": "Sikkim", "NAMCHI": "Sikkim",
    "ALONG": "Arunachal Pradesh", "ZIRO": "Arunachal Pradesh", "ITANAGAR": "Arunachal Pradesh", "MOKOKCHUNG": "Nagaland", "NONGSTOIN": "Meghalaya",
}

NODE_STATES.update(ADDITIONAL_NODE_STATES)

FACILITY_BLUEPRINTS = [
    ("FAC-GHY-MED", "Guwahati Medical Logistics Hub", "MEDICAL_WAREHOUSE", "Kamrup Metropolitan, Assam", [91.7362, 26.1445]),
    ("FAC-TEZ-HUB", "Tezpur Regional Supply Hub", "SUPPLY_CENTRE", "Sonitpur, Assam", [92.7926, 26.6528]),
    ("FAC-AS-SIL-HOSP", "Silchar District Hospital", "HOSPITAL", "Cachar, Assam", [92.7789, 24.8333]),
    ("FAC-AS-JOR-WH", "Jorhat Agricultural Warehouse", "AGRI_WAREHOUSE", "Jorhat, Assam", [94.2037, 26.7509]),
    ("FAC-AS-DIB-HOSP", "Dibrugarh Medical Supply Centre", "MEDICAL_WAREHOUSE", "Dibrugarh, Assam", [94.912, 27.4728]),
    ("FAC-AR-ITA-HOSP", "Itanagar Emergency Hospital", "HOSPITAL", "Papum Pare, Arunachal Pradesh", [93.6053, 27.0844]),
    ("FAC-TAW-HOSP", "Tawang District Hospital", "HOSPITAL", "Tawang, Arunachal Pradesh", [91.865, 27.586]),
    ("FAC-BOM-RELIEF", "Bomdila Relief Depot", "RELIEF_DEPOT", "West Kameng, Arunachal Pradesh", [92.412, 27.264]),
    ("FAC-AR-PAS-HUB", "Pasighat Supply Hub", "SUPPLY_CENTRE", "East Siang, Arunachal Pradesh", [95.326, 28.0661]),
    ("FAC-AR-ZIR-DEPOT", "Ziro Emergency Depot", "RELIEF_DEPOT", "Lower Subansiri, Arunachal Pradesh", [93.83, 27.59]),
    ("FAC-ML-SHL-HOSP", "Shillong Regional Hospital", "HOSPITAL", "East Khasi Hills, Meghalaya", [91.8933, 25.5788]),
    ("FAC-ML-SHL-WH", "Shillong Essential Goods Warehouse", "WAREHOUSE", "East Khasi Hills, Meghalaya", [91.87, 25.59]),
    ("FAC-ML-TUR-HOSP", "Tura District Hospital", "HOSPITAL", "West Garo Hills, Meghalaya", [90.2024, 25.5142]),
    ("FAC-ML-NON-DEPOT", "Nongstoin Relief Depot", "RELIEF_DEPOT", "West Khasi Hills, Meghalaya", [91.27, 25.52]),
    ("FAC-MN-IMP-HOSP", "Imphal Medical Logistics Centre", "MEDICAL_WAREHOUSE", "Imphal West, Manipur", [93.9368, 24.817]),
    ("FAC-MN-IMP-WH", "Imphal Central Warehouse", "WAREHOUSE", "Imphal East, Manipur", [94.01, 24.82]),
    ("FAC-MN-CCP-HOSP", "Churachandpur District Hospital", "HOSPITAL", "Churachandpur, Manipur", [93.6833, 24.3333]),
    ("FAC-MN-MOR-DEPOT", "Moreh Border Relief Depot", "RELIEF_DEPOT", "Tengnoupal, Manipur", [94.31, 24.25]),
    ("FAC-MZ-AIZ-HOSP", "Aizawl Civil Hospital", "HOSPITAL", "Aizawl, Mizoram", [92.7176, 23.7271]),
    ("FAC-MZ-AIZ-WH", "Aizawl State Warehouse", "WAREHOUSE", "Aizawl, Mizoram", [92.74, 23.75]),
    ("FAC-MZ-LUN-HOSP", "Lunglei District Hospital", "HOSPITAL", "Lunglei, Mizoram", [92.7477, 22.887]),
    ("FAC-MZ-CHA-DEPOT", "Champhai Relief Depot", "RELIEF_DEPOT", "Champhai, Mizoram", [93.33, 23.47]),
    ("FAC-NL-KOH-HOSP", "Kohima Regional Hospital", "HOSPITAL", "Kohima, Nagaland", [94.1086, 25.6751]),
    ("FAC-NL-DIM-WH", "Dimapur Logistics Warehouse", "WAREHOUSE", "Dimapur, Nagaland", [93.7266, 25.9091]),
    ("FAC-NL-MOK-HOSP", "Mokokchung District Hospital", "HOSPITAL", "Mokokchung, Nagaland", [94.52, 26.32]),
    ("FAC-SK-GAN-HOSP", "Gangtok Referral Hospital", "HOSPITAL", "Gangtok, Sikkim", [88.6065, 27.3389]),
    ("FAC-SK-RAN-WH", "Rangpo Transit Warehouse", "WAREHOUSE", "Pakyong, Sikkim", [88.53, 27.18]),
    ("FAC-SK-NAM-HOSP", "Namchi District Hospital", "HOSPITAL", "Namchi, Sikkim", [88.35, 27.1667]),
    ("FAC-TR-AGA-HOSP", "Agartala Medical Logistics Centre", "MEDICAL_WAREHOUSE", "West Tripura, Tripura", [91.2868, 23.8315]),
    ("FAC-TR-AGA-WH", "Agartala Central Warehouse", "WAREHOUSE", "West Tripura, Tripura", [91.31, 23.85]),
    ("FAC-TR-DHA-HOSP", "Dharmanagar District Hospital", "HOSPITAL", "North Tripura, Tripura", [92.1783, 24.3786]),
    ("FAC-TR-UDA-DEPOT", "Udaipur Relief Depot", "RELIEF_DEPOT", "Gomati, Tripura", [91.48, 23.53]),
]

FACILITY_BLUEPRINTS += ADDITIONAL_FACILITY_BLUEPRINTS

NER_OPERATIONAL_BOUNDARY = GeoJsonMultiPolygon(coordinates=[
    [[[88.02, 26.75], [88.96, 26.75], [88.98, 28.18], [88.02, 28.18], [88.02, 26.75]]],
    [[[89.65, 25.05], [90.75, 22.85], [91.15, 21.85], [93.55, 21.85], [94.35, 23.35], [95.4, 24.0], [97.55, 27.0], [97.45, 29.55], [94.25, 29.55], [92.05, 28.35], [90.45, 26.55], [89.65, 25.05]]],
])


class SeedStore:
    """Mutable deterministic state used until the PostGIS adapter is introduced."""

    def __init__(self) -> None:
        self.reset(persist=False)
        persisted = operational_repository.load_state()
        if persisted:
            self._restore_state(persisted)
            removed = self._remove_legacy_simulated_vehicles()
            expanded = self._ensure_ner_coverage()
            delivery_metadata = self._ensure_delivery_route_metadata()
            if removed or expanded or delivery_metadata:
                self.persist("NER_COVERAGE_DATASET_UPGRADED", removed + expanded + delivery_metadata, details={"roads": len(self.roads), "facilities": len(self.facilities)})
        else:
            self.persist("INITIAL_STATE", [])

    def reset(self, persist: bool = True) -> None:
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
                road_condition="FAIR" if item[0] in {"SEG-004", "SEG-005", "SEG-006", "SEG-010", "SEG-011", "SEG-012", "SEG-013"} else "GOOD",
                rainfall_mm_24h=42 if item[0] == "SEG-004" else 18,
                slope_degrees=31 if item[0] == "SEG-006" else (24 if item[0] in {"SEG-004", "SEG-005", "SEG-007", "SEG-010", "SEG-011", "SEG-012", "SEG-013"} else 6),
                source="NER-wide prototype monitoring dataset",
                observed_at=timestamp - timedelta(minutes=8),
                updated_at=timestamp,
                confidence=84,
            )
            for item in ROAD_BLUEPRINTS
        ]
        # Vehicles are deliberately not seeded. A marker exists only after a real
        # device/browser is registered and submits a GPS position.
        self.vehicles: list[Vehicle] = []
        self.facilities = [
            Facility(id=item[0], name=item[1], facility_type=item[2], district=item[3], location=GeoJsonPoint(coordinates=item[4]))
            for item in FACILITY_BLUEPRINTS
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
                vehicle_id="UNASSIGNED",
                status="IN_TRANSIT",
                progress_percent=38,
                planned_eta=timestamp + timedelta(hours=8, minutes=20),
                current_eta=timestamp + timedelta(hours=8, minutes=20),
                delay_minutes=0,
                route_id="ROUTE-1001",
                source_facility_id="FAC-GHY-MED",
                destination_facility_id="FAC-TAW-HOSP",
                route_segment_ids=["SEG-001", "SEG-002", "SEG-003", "SEG-004", "SEG-005", "SEG-006", "SEG-007"],
            ),
            Delivery(
                id="DEL-1002",
                cargo_type="RELIEF_SUPPLIES",
                cargo_description="Food and emergency shelter kits",
                priority="HIGH",
                source_name="Tezpur Regional Supply Hub",
                destination_name="Bomdila Relief Depot",
                vehicle_id="UNASSIGNED",
                status="IN_TRANSIT",
                progress_percent=72,
                planned_eta=timestamp + timedelta(hours=2, minutes=10),
                current_eta=timestamp + timedelta(hours=2, minutes=34),
                delay_minutes=24,
                route_id="ROUTE-1002",
                source_facility_id="FAC-TEZ-HUB",
                destination_facility_id="FAC-BOM-RELIEF",
                route_segment_ids=["SEG-003", "SEG-004"],
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
        self.refresh_ml_advisories()
        if persist:
            self.persist("DEMO_RESET", [])

    def _state_payload(self) -> dict:
        return {
            "roads": [item.model_dump(mode="json") for item in self.roads],
            "vehicles": [item.model_dump(mode="json") for item in self.vehicles],
            "facilities": [item.model_dump(mode="json") for item in self.facilities],
            "incidents": [item.model_dump(mode="json") for item in self.incidents],
            "deliveries": [item.model_dump(mode="json") for item in self.deliveries],
            "alerts": [item.model_dump(mode="json") for item in self.alerts],
        }

    def _restore_state(self, payload: dict) -> None:
        self.roads = [RoadSegment.model_validate(item) for item in payload.get("roads", [])]
        self.vehicles = [
            Vehicle.model_validate({
                **item,
                "gps_freshness": item.get("gps_freshness", "SIMULATED") if "data_mode" in item else "SIMULATED",
            })
            for item in payload.get("vehicles", [])
        ]
        self.facilities = [Facility.model_validate(item) for item in payload.get("facilities", [])]
        self.incidents = [Incident.model_validate(item) for item in payload.get("incidents", [])]
        self.deliveries = [Delivery.model_validate(item) for item in payload.get("deliveries", [])]
        self.alerts = [Alert.model_validate(item) for item in payload.get("alerts", [])]
        self.refresh_ml_advisories()

    def _remove_legacy_simulated_vehicles(self) -> list[str]:
        legacy_ids = {
            vehicle.id
            for vehicle in self.vehicles
            if vehicle.id in {"VEH-001", "VEH-002"} and vehicle.data_mode == DataMode.SIMULATED
        }
        if not legacy_ids:
            return []
        self.vehicles = [vehicle for vehicle in self.vehicles if vehicle.id not in legacy_ids]
        for delivery in self.deliveries:
            if delivery.vehicle_id in legacy_ids:
                delivery.vehicle_id = "UNASSIGNED"
        return sorted(legacy_ids)

    def _ensure_delivery_route_metadata(self) -> list[str]:
        """Backfill route membership for state saved before delivery-impact automation existed."""
        metadata = {
            "DEL-1001": ("FAC-GHY-MED", "FAC-TAW-HOSP", ["SEG-001", "SEG-002", "SEG-003", "SEG-004", "SEG-005", "SEG-006", "SEG-007"]),
            "DEL-1002": ("FAC-TEZ-HUB", "FAC-BOM-RELIEF", ["SEG-003", "SEG-004"]),
        }
        changed: list[str] = []
        for delivery in self.deliveries:
            values = metadata.get(delivery.id)
            if values is None or (delivery.source_facility_id and delivery.destination_facility_id and delivery.route_segment_ids):
                continue
            delivery.source_facility_id, delivery.destination_facility_id, default_segments = values
            if not delivery.route_segment_ids:
                delivery.route_segment_ids = (
                    ["SEG-008", "SEG-009", "SEG-010", "SEG-011", "SEG-012", "SEG-013", "SEG-005", "SEG-006", "SEG-007"]
                    if delivery.id == "DEL-1001" and delivery.route_id != "ROUTE-1001"
                    else default_segments
                )
            changed.append(delivery.id)
        return changed

    def _ensure_ner_coverage(self) -> list[str]:
        timestamp = now_utc()
        changed: list[str] = []
        existing_roads = {road.id for road in self.roads}
        for item in ROAD_BLUEPRINTS:
            if item[0] in existing_roads:
                continue
            self.roads.append(RoadSegment(
                id=item[0], road_name=item[1], from_node=item[2], to_node=item[3], distance_km=item[4],
                geometry=GeoJsonLineString(coordinates=item[5]), accessibility=RoadAccessibility.OPEN,
                risk_score=16, risk_band=RiskBand.LOW, road_condition="GOOD", rainfall_mm_24h=18,
                slope_degrees=10, source="NER-wide prototype monitoring dataset", data_mode=DataMode.SIMULATED,
                observed_at=timestamp, updated_at=timestamp, confidence=75,
            ))
            changed.append(item[0])
        existing_facilities = {facility.id for facility in self.facilities}
        for item in FACILITY_BLUEPRINTS:
            if item[0] in existing_facilities:
                continue
            self.facilities.append(Facility(
                id=item[0], name=item[1], facility_type=item[2], district=item[3],
                location=GeoJsonPoint(coordinates=item[4]),
            ))
            changed.append(item[0])
        if changed:
            self.refresh_ml_advisories()
        return changed

    def import_operational_data(self, roads: list[RoadSegment], facilities: list[Facility], actor: str, dry_run: bool) -> dict[str, object]:
        existing_road_ids = {item.id for item in self.roads}
        existing_facility_ids = {item.id for item in self.facilities}
        result: dict[str, object] = {
            'roads_received': len(roads),
            'facilities_received': len(facilities),
            'roads_created': sum(item.id not in existing_road_ids for item in roads),
            'roads_updated': sum(item.id in existing_road_ids for item in roads),
            'facilities_created': sum(item.id not in existing_facility_ids for item in facilities),
            'facilities_updated': sum(item.id in existing_facility_ids for item in facilities),
            'changed_entities': [item.id for item in roads] + [item.id for item in facilities],
        }
        if dry_run:
            return result

        previous_roads, previous_facilities = self.roads, self.facilities
        road_updates = {item.id: item for item in roads}
        facility_updates = {item.id: item for item in facilities}
        self.roads = [deepcopy(road_updates.pop(item.id, item)) for item in previous_roads] + [deepcopy(item) for item in road_updates.values()]
        self.facilities = [deepcopy(facility_updates.pop(item.id, item)) for item in previous_facilities] + [deepcopy(item) for item in facility_updates.values()]
        try:
            self.refresh_ml_advisories()
            self.persist(
                'OPERATIONAL_DATA_IMPORTED', result['changed_entities'], actor=actor,
                details={key: value for key, value in result.items() if key != 'changed_entities'},
            )
        except Exception:
            self.roads, self.facilities = previous_roads, previous_facilities
            raise
        return result

    def persist(self, event_type: str, changed_entities: list[str], actor: str = "SYSTEM", details: dict | None = None) -> None:
        for delivery in self.deliveries:
            if delivery.id in changed_entities and event_type != "GPS_POSITION_RECEIVED":
                delivery.journey_timeline.append({
                    "id": uuid4().hex, "event": event_type, "actor": actor,
                    "at": now_utc().isoformat(), "status": delivery.status,
                    "instruction": delivery.instruction_type,
                })
        operational_repository.save_state(
            self._state_payload(),
            event_type=event_type,
            changed_entities=changed_entities,
            actor=actor,
            details=details,
        )

    def refresh_ml_advisories(self) -> None:
        """Attach advisory predictions without changing authoritative road status."""
        incident_counts: dict[str, int] = {}
        for incident in self.incidents:
            if incident.matched_segment_id:
                incident_counts[incident.matched_segment_id] = incident_counts.get(incident.matched_segment_id, 0) + 1
        for road in self.roads:
            advisory = model_adapter.assess(road, incident_counts.get(road.id, 0))
            road.ml_advisory_status = model_adapter.status
            if advisory is not None:
                road.ml_risk_probability = round(advisory.probability, 4)
                road.ml_risk_band = RiskBand(advisory.band)
                road.ml_predicted_delay_minutes = round(advisory.delay_minutes, 1)
            else:
                road.ml_risk_probability = None
                road.ml_risk_band = None
                road.ml_predicted_delay_minutes = None

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
            critical_alerts=deepcopy([alert for alert in self.alerts if not alert.acknowledged]),
            connectivity=[
                ConnectivityItem(name="Guwahati-Tezpur", score=94, status="OPEN"),
                ConnectivityItem(name="Tezpur-Bomdila", score=76, status="CAUTION"),
                ConnectivityItem(name="Bomdila-Tawang", score=81, status="OPEN"),
            ],
        )

    def analytics(self) -> AnalyticsResponse:
        state_names = ["Assam", "Arunachal Pradesh", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura"]
        accessibility_score = {
            RoadAccessibility.OPEN: 100, RoadAccessibility.CAUTION: 72, RoadAccessibility.PARTIAL: 52,
            RoadAccessibility.HIGH_RISK: 30, RoadAccessibility.BLOCKED: 0, RoadAccessibility.UNKNOWN: 40,
        }
        state_rows: list[StateConnectivityAnalytics] = []
        for state in state_names:
            roads = [road for road in self.roads if state in road.states or state in {NODE_STATES.get(road.from_node), NODE_STATES.get(road.to_node)}]
            road_ids = {road.id for road in roads}
            incidents = [incident for incident in self.incidents if incident.matched_segment_id in road_ids]
            facilities = [facility for facility in self.facilities if state.casefold() in facility.district.casefold()]
            weighted_score = round(sum(accessibility_score[road.accessibility] * road.distance_km for road in roads) / max(1, sum(road.distance_km for road in roads)))
            state_rows.append(StateConnectivityAnalytics(
                state=state, monitored_segments=len(roads),
                open_segments=sum(road.accessibility == RoadAccessibility.OPEN for road in roads),
                caution_segments=sum(road.accessibility in {RoadAccessibility.CAUTION, RoadAccessibility.PARTIAL} for road in roads),
                high_risk_segments=sum(road.accessibility == RoadAccessibility.HIGH_RISK for road in roads),
                blocked_segments=sum(road.accessibility == RoadAccessibility.BLOCKED for road in roads),
                connectivity_score=weighted_score, incidents=len(incidents), facilities=len(facilities),
            ))

        districts: dict[str, dict[str, int]] = {}
        for facility in self.facilities:
            district = facility.district.split(",")[0].strip()
            districts.setdefault(district, {"incidents": 0, "unverified": 0, "critical": 0, "facilities": 0})["facilities"] += 1
        for incident in self.incidents:
            road = next((item for item in self.roads if item.id == incident.matched_segment_id), None)
            district = str(incident.context_snapshot.get("district") or (road.to_node.replace("_", " ").title() if road else "Unassigned location"))
            row = districts.setdefault(district, {"incidents": 0, "unverified": 0, "critical": 0, "facilities": 0})
            row["incidents"] += 1
            row["unverified"] += incident.verification == "UNVERIFIED"
            row["critical"] += incident.severity == "CRITICAL"
        district_rows = [DistrictAnalytics(
            district=name, incidents=values["incidents"], unverified_incidents=values["unverified"],
            critical_incidents=values["critical"], facilities=values["facilities"],
        ) for name, values in sorted(districts.items(), key=lambda item: (-(item[1]["critical"] + item[1]["unverified"]), item[0]))]

        risk_rows = sorted(self.roads, key=lambda road: max(road.risk_score, round((road.ml_risk_probability or 0) * 100)), reverse=True)[:10]
        risk_corridors = [RiskCorridorAnalytics(
            segment_id=road.id, road_name=road.road_name, corridor=f"{road.from_node.replace('_', ' ').title()} → {road.to_node.replace('_', ' ').title()}",
            accessibility=road.accessibility, operational_risk=road.risk_score,
            ml_risk_probability=road.ml_risk_probability, rainfall_mm_24h=road.rainfall_mm_24h, confidence=road.confidence,
        ) for road in risk_rows]

        event_groups: dict[str, dict[str, int | str]] = {}
        for event in reversed(operational_repository.recent_audit_events(200)):
            occurred = event["created_at"]
            day = occurred.date().isoformat() if isinstance(occurred, datetime) else str(occurred)[:10]
            row = event_groups.setdefault(day, {"date": day, "field_reports": 0, "verification_actions": 0, "gps_updates": 0, "dispatches": 0})
            event_type = event["event_type"]
            if event_type == "FIELD_REPORT_SUBMITTED": row["field_reports"] += 1
            elif event_type == "FIELD_REPORT_REVIEWED": row["verification_actions"] += 1
            elif event_type == "GPS_POSITION_RECEIVED": row["gps_updates"] += 1
            elif event_type in {"DELIVERY_DISPATCHED", "DELIVERY_VEHICLE_ASSIGNED"}: row["dispatches"] += 1

        incident_breakdown: dict[str, int] = {}
        for incident in self.incidents:
            incident_breakdown[incident.incident_type] = incident_breakdown.get(incident.incident_type, 0) + 1
        total_deliveries = len(self.deliveries)
        active_deliveries = [delivery for delivery in self.deliveries if delivery.status != "ARRIVED"]
        ml_available = sum(road.ml_advisory_status == "AVAILABLE" for road in self.roads)
        live_weather = sum(road.data_mode == DataMode.LIVE for road in self.roads)
        verified_incidents = sum(incident.verification != "UNVERIFIED" for incident in self.incidents)
        return AnalyticsResponse(
            generated_at=now_utc(), data_mode=DataMode.SIMULATED,
            summary={
                "monitored_road_km": round(sum(road.distance_km for road in self.roads), 1),
                "active_deliveries": len(active_deliveries), "arrived_deliveries": total_deliveries - len(active_deliveries),
                "average_delivery_progress": round(sum(delivery.progress_percent for delivery in self.deliveries) / max(1, total_deliveries)),
                "delayed_deliveries": sum(delivery.delay_minutes > 0 for delivery in active_deliveries),
                "unassigned_deliveries": sum(delivery.vehicle_id == "UNASSIGNED" for delivery in active_deliveries),
                "live_gps_vehicles": sum(vehicle.data_mode == DataMode.LIVE for vehicle in self.vehicles),
            },
            state_connectivity=state_rows, district_activity=district_rows[:12], risk_corridors=risk_corridors,
            incident_breakdown=incident_breakdown, event_trend=list(event_groups.values())[-7:],
            data_quality={
                "ml_coverage_percent": round(ml_available / max(1, len(self.roads)) * 100),
                "live_weather_coverage_percent": round(live_weather / max(1, len(self.roads)) * 100),
                "verified_incident_percent": round(verified_incidents / max(1, len(self.incidents)) * 100),
                "gps_live_percent": round(sum(vehicle.data_mode == DataMode.LIVE for vehicle in self.vehicles) / max(1, len(self.vehicles)) * 100),
                "road_data_confidence_percent": round(sum(road.confidence for road in self.roads) / max(1, len(self.roads))),
                "ml_model_version": model_adapter.version, "ml_status": model_adapter.status,
            },
        )

    def map_snapshot(self) -> MapSnapshotResponse:
        vehicles = deepcopy(self.vehicles)
        timestamp = now_utc()
        for vehicle in vehicles:
            if vehicle.data_mode != DataMode.LIVE:
                vehicle.gps_freshness = "SIMULATED"
                continue
            position_at = vehicle.last_position_at
            if position_at.tzinfo is None:
                position_at = position_at.replace(tzinfo=UTC)
            age_seconds = max(0, (timestamp - position_at.astimezone(UTC)).total_seconds())
            vehicle.gps_freshness = "LIVE" if age_seconds <= 120 else ("DELAYED" if age_seconds <= 600 else "STALE")
        return MapSnapshotResponse(
            data_mode=DataMode.SIMULATED,
            generated_at=now_utc(),
            road_segments=deepcopy(self.roads),
            vehicles=vehicles,
            vehicle_telemetry=[self.vehicle_telemetry(vehicle.id) for vehicle in vehicles],
            facilities=deepcopy(self.facilities),
            incidents=deepcopy(self.incidents),
            operational_boundary=NER_OPERATIONAL_BOUNDARY,
        )

    @staticmethod
    def _point_to_segment_distance_km(point: list[float], start: list[float], end: list[float]) -> float:
        """Approximate shortest surface distance to a short route line section."""
        reference_latitude = radians((point[1] + start[1] + end[1]) / 3)
        longitude_scale = 111.32 * cos(reference_latitude)
        latitude_scale = 110.57
        px, py = point[0] * longitude_scale, point[1] * latitude_scale
        sx, sy = start[0] * longitude_scale, start[1] * latitude_scale
        ex, ey = end[0] * longitude_scale, end[1] * latitude_scale
        dx, dy = ex - sx, ey - sy
        length_squared = dx * dx + dy * dy
        if length_squared == 0:
            return hypot(px - sx, py - sy)
        fraction = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_squared))
        closest_x, closest_y = sx + fraction * dx, sy + fraction * dy
        return hypot(px - closest_x, py - closest_y)

    @staticmethod
    def _route_position(point: list[float], coordinates: list[list[float]]) -> tuple[float, float]:
        """Return distance from route and fractional progress at the closest projection."""
        if len(coordinates) < 2:
            return float("inf"), 0.0
        reference_latitude = radians(point[1])
        longitude_scale, latitude_scale = 111.32 * cos(reference_latitude), 110.57
        projected = [(item[0] * longitude_scale, item[1] * latitude_scale) for item in coordinates]
        px, py = point[0] * longitude_scale, point[1] * latitude_scale
        lengths = [hypot(projected[index][0] - projected[index - 1][0], projected[index][1] - projected[index - 1][1]) for index in range(1, len(projected))]
        total_length = sum(lengths)
        closest_distance, closest_progress, travelled = float("inf"), 0.0, 0.0
        for index, length in enumerate(lengths, start=1):
            sx, sy = projected[index - 1]
            ex, ey = projected[index]
            dx, dy = ex - sx, ey - sy
            fraction = 0.0 if length == 0 else max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / (length * length)))
            distance = hypot(px - (sx + fraction * dx), py - (sy + fraction * dy))
            if distance < closest_distance:
                closest_distance = distance
                closest_progress = (travelled + fraction * length) / max(total_length, 0.001)
            travelled += length
        return closest_distance, max(0.0, min(1.0, closest_progress))

    def _expected_vehicle_route(self, vehicle: Vehicle) -> tuple[str | None, list[list[float]]]:
        delivery = next((item for item in self.deliveries if item.id == vehicle.active_delivery_id), None)
        if delivery is None:
            return None, []
        if delivery.route_geometry and len(delivery.route_geometry.coordinates) >= 2:
            return delivery.route_id, delivery.route_geometry.coordinates
        if delivery.route_segment_ids:
            segment_ids = delivery.route_segment_ids
        elif delivery.id == "DEL-1002":
            segment_ids = ["SEG-003", "SEG-004"]
        elif delivery.id == "DEL-1001" and delivery.route_id != "ROUTE-1001":
            segment_ids = ["SEG-008", "SEG-009", "SEG-010", "SEG-011", "SEG-012", "SEG-013", "SEG-005", "SEG-006", "SEG-007"]
        elif delivery.id == "DEL-1001":
            segment_ids = ["SEG-001", "SEG-002", "SEG-003", "SEG-004", "SEG-005", "SEG-006", "SEG-007"]
        else:
            return delivery.route_id, []
        coordinates = [
            coordinate
            for segment_id in segment_ids
            for road in self.roads if road.id == segment_id
            for coordinate in road.geometry.coordinates
        ]
        return delivery.route_id, coordinates

    def _reassess_deliveries_for_road(self, road: RoadSegment, timestamp: datetime) -> tuple[list[str], list[dict]]:
        """Re-plan only active deliveries whose current route contains the changed road."""
        changed: list[str] = []
        impacts: list[dict] = []
        active_statuses = {"AWAITING_VEHICLE", "DISPATCHED", "IN_TRANSIT", "AT_RISK", "REROUTING", "DELAYED", "PAUSED", "HELD"}
        for delivery in self.deliveries:
            intersects = road.id in delivery.route_segment_ids or bool(delivery.route_geometry and any(self._route_position(point, delivery.route_geometry.coordinates)[0] <= 1 for point in road.geometry.coordinates))
            if delivery.status not in active_statuses or not intersects:
                continue

            previous_route_id = delivery.route_id
            plan = None
            if delivery.source_facility_id and delivery.destination_facility_id:
                plan = RoutingEngine(self.roads).plan(RoutePlanRequest(
                    source_facility_id=delivery.source_facility_id,
                    destination_facility_id=delivery.destination_facility_id,
                    preference="SAFETY_FIRST",
                ))
            elif delivery.source_location and delivery.destination_location:
                plan = route_planning_service.plan(RoutePlanRequest(
                    source_location=RouteLocation(
                        label=delivery.source_name,
                        longitude=delivery.source_location.coordinates[0],
                        latitude=delivery.source_location.coordinates[1],
                    ),
                    destination_location=RouteLocation(
                        label=delivery.destination_name,
                        longitude=delivery.destination_location.coordinates[0],
                        latitude=delivery.destination_location.coordinates[1],
                    ),
                    cargo_type=delivery.cargo_type,
                    priority=delivery.priority,
                    preference="SAFETY_FIRST",
                    routing_mode="LIVE_WITH_FALLBACK",
                ), self.roads, self.incidents)

            if plan is None:
                delivery.status = "AT_RISK"
                if road.accessibility == RoadAccessibility.BLOCKED:
                    delivery.status = "HELD"
                    delivery.instruction_type = "HOLD"
                    delivery.instruction_status = "PENDING"
                    delivery.instruction_updated_at = timestamp
                    delivery.instruction_acknowledged_at = None
                message = f"{delivery.id} uses {road.road_name}, but its endpoints are not mapped to the routing graph. Manual dispatch review is required."
                impact = {
                    "outcome": "AT_RISK", "delivery_id": delivery.id, "triggering_segment_id": road.id,
                    "previous_route_id": previous_route_id, "route_id": previous_route_id,
                    "route_segment_ids": delivery.route_segment_ids, "delay_minutes": delivery.delay_minutes,
                    "message": message,
                }
            else:
                route = next((item for item in plan.routes if item.id == plan.recommended_route_id), None)
                if route is None:
                    delivery.status = "HELD"
                    delivery.instruction_type = "HOLD"
                    delivery.instruction_status = "PENDING"
                    delivery.instruction_updated_at = timestamp
                    delivery.instruction_acknowledged_at = None
                    message = f"No feasible road route remains for {delivery.id} after the verified change on {road.road_name}. Dispatch intervention is required."
                    impact = {
                        "outcome": "NO_FEASIBLE_ROUTE", "delivery_id": delivery.id,
                        "triggering_segment_id": road.id, "previous_route_id": previous_route_id,
                        "delay_minutes": delivery.delay_minutes, "message": message,
                    }
                else:
                    matched_road_ids = {
                        road_id
                        for section in route.intelligence_segments
                        for road_id in section.matched_road_ids
                    }
                    if not matched_road_ids:
                        matched_road_ids = {segment_id for segment_id in route.segment_ids if any(item.id == segment_id for item in self.roads)}
                    route_changed = route.geometry.coordinates != (delivery.route_geometry.coordinates if delivery.route_geometry else [])
                    delivery.route_id = route.id
                    delivery.route_segment_ids = sorted(matched_road_ids)
                    delivery.route_geometry = route.geometry
                    delivery.route_distance_km = route.distance_km
                    delivery.route_eta_minutes = route.eta_minutes
                    delivery.route_risk_score = route.risk_score
                    delivery.route_risk_band = route.risk_band
                    delivery.delay_minutes = max(delivery.delay_minutes, route.predicted_delay_minutes)
                    delivery.current_eta = timestamp + timedelta(minutes=route.eta_minutes)
                    delivery.status = "REROUTING" if route_changed else "AT_RISK"
                    if route_changed or delivery.instruction_type == "HOLD":
                        delivery.instruction_status = "PENDING"
                        delivery.instruction_type = "REROUTE"
                        delivery.instruction_updated_at = timestamp
                        delivery.instruction_acknowledged_at = None
                        message = f"{delivery.id} was automatically rerouted via {' → '.join(route.path[1:-1])}; verified field, road, weather and ML-risk inputs were applied."
                        outcome = "REROUTED"
                    else:
                        message = f"{delivery.id} remains on its current feasible route, with ETA and risk recalculated from the verified road update."
                        outcome = "AT_RISK"
                    impact = {
                        "outcome": outcome, "delivery_id": delivery.id, "triggering_segment_id": road.id,
                        "previous_route_id": previous_route_id, "route_id": route.id,
                        "route_path": route.path, "route_segment_ids": delivery.route_segment_ids,
                        "eta_minutes": route.eta_minutes, "delay_minutes": delivery.delay_minutes,
                        "message": message,
                    }

            alert_id = f"ALT-DELIVERY-IMPACT-{len(self.alerts) + 1:04d}"
            self.alerts.insert(0, Alert(
                id=alert_id,
                severity="CRITICAL" if impact["outcome"] == "NO_FEASIBLE_ROUTE" else "WARNING",
                alert_type="DELIVERY_ROUTE_REASSESSMENT",
                title={"REROUTED": "Delivery automatically rerouted", "AT_RISK": "Delivery route reassessed", "NO_FEASIBLE_ROUTE": "Delivery requires dispatch action"}[impact["outcome"]],
                message=impact["message"], related_entity_type="DELIVERY", related_entity_id=delivery.id,
                acknowledged=False, created_at=timestamp,
            ))
            changed.extend([delivery.id, alert_id])
            impacts.append(impact)
        return changed, impacts

    def vehicle_telemetry(self, vehicle_id: str) -> VehicleTelemetry:
        vehicle = next((item for item in self.vehicles if item.id == vehicle_id), None)
        if vehicle is None:
            raise ValueError("Vehicle not found")
        assessed_at = now_utc()
        position_at = vehicle.last_position_at
        if position_at.tzinfo is None:
            position_at = position_at.replace(tzinfo=UTC)
        gps_age = max(0, round((assessed_at - position_at.astimezone(UTC)).total_seconds()))
        history = operational_repository.vehicle_position_history(vehicle.id, 100)
        chronological = list(reversed(history))
        track_coordinates = [[float(item["longitude"]), float(item["latitude"])] for item in chronological]
        current_coordinate = [vehicle.longitude, vehicle.latitude]
        if not track_coordinates or track_coordinates[-1] != current_coordinate:
            track_coordinates.append(current_coordinate)

        if vehicle.data_mode != DataMode.LIVE:
            motion_state = "SIMULATED"
        elif gps_age > 600:
            motion_state = "STALE"
        elif gps_age > 120:
            motion_state = "DELAYED"
        elif vehicle.speed_kph <= 3:
            motion_state = "STOPPED"
        else:
            motion_state = "MOVING"

        stationary_minutes = 0
        if motion_state == "STOPPED":
            stationary_since = position_at
            for item in history:
                if float(item.get("speed_kph", 0)) > 3:
                    break
                recorded = item.get("recorded_at") or item.get("received_at")
                if isinstance(recorded, str):
                    recorded = datetime.fromisoformat(recorded.replace("Z", "+00:00"))
                if recorded.tzinfo is None:
                    recorded = recorded.replace(tzinfo=UTC)
                stationary_since = recorded.astimezone(UTC)
            stationary_minutes = max(0, round((assessed_at - stationary_since).total_seconds() / 60))

        expected_route_id, expected_coordinates = self._expected_vehicle_route(vehicle)
        deviation = (
            min(
                self._point_to_segment_distance_km(
                    current_coordinate,
                    expected_coordinates[index - 1],
                    expected_coordinates[index],
                )
                for index in range(1, len(expected_coordinates))
            )
            if len(expected_coordinates) >= 2 else None
        )
        deviation_delay = round(max(0.0, (deviation or 0) - 8.0) * 2.0)
        estimated_delivery_delay = stationary_minutes + deviation_delay
        return VehicleTelemetry(
            vehicle_id=vehicle.id,
            active_delivery_id=vehicle.active_delivery_id,
            expected_route_id=expected_route_id,
            motion_state=motion_state,
            gps_age_seconds=gps_age,
            stationary_minutes=stationary_minutes,
            route_deviation_km=round(deviation, 2) if deviation is not None else None,
            on_planned_route=deviation <= 8 if deviation is not None else None,
            estimated_delivery_delay_minutes=estimated_delivery_delay,
            position_count=len(track_coordinates),
            track=GeoJsonLineString(coordinates=track_coordinates),
            assessed_at=assessed_at,
        )

    def apply_heavy_rain(self) -> list[str]:
        timestamp = now_utc()
        changed = []
        for road in self.roads:
            if road.id in {"SEG-004", "SEG-005"}:
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
                title="Critical landslide risk near Bhalukpong",
                message="Heavy rainfall raised disruption risk on two upcoming medicine-route segments.",
                related_entity_type="DELIVERY",
                related_entity_id="DEL-1001",
                acknowledged=False,
                created_at=timestamp,
            ),
        )
        self.deliveries[0].status = "AT_RISK"
        self.refresh_ml_advisories()
        changed_entities = changed + ["DEL-1001", "ALT-RAIN-01"]
        self.persist("HEAVY_RAIN_SIMULATED", changed_entities)
        return changed_entities

    def apply_confirmed_landslide(self) -> tuple[list[str], dict]:
        """Demo event: confirmed closure triggers a delivery impact and reroute."""
        timestamp = now_utc()
        blocked = next(road for road in self.roads if road.id == "SEG-004")
        blocked.accessibility = RoadAccessibility.BLOCKED
        blocked.risk_score = 96
        blocked.risk_band = RiskBand.CRITICAL
        blocked.rainfall_mm_24h = max(blocked.rainfall_mm_24h, 110)
        blocked.source = "Control-room confirmed field report"
        blocked.observed_at = timestamp
        blocked.updated_at = timestamp

        incident = Incident(
            id="INC-1002",
            incident_type="LANDSLIDE",
            severity="CRITICAL",
            reported_accessibility=RoadAccessibility.BLOCKED,
            verification="CONTROL_CONFIRMED",
            location=GeoJsonPoint(coordinates=[92.63, 27.15]),
            matched_segment_id="SEG-004",
            description="Confirmed debris flow blocks both lanes near the Bhalukpong-Bomdila approach.",
            source="Simulated field officer report",
            data_mode=DataMode.SIMULATED,
            observed_at=timestamp - timedelta(minutes=3),
            received_at=timestamp,
        )
        self.incidents.insert(0, incident)
        self.refresh_ml_advisories()

        delivery = next(item for item in self.deliveries if item.id == "DEL-1001")
        delivery.status = "REROUTING"
        plan = RoutingEngine(self.roads).plan(RoutePlanRequest(
            source_facility_id="FAC-GHY-MED",
            destination_facility_id="FAC-TAW-HOSP",
            preference="SAFETY_FIRST",
        ))
        route = next((item for item in plan.routes if item.id == plan.recommended_route_id), None)
        if route is None:
            delivery.status = "HELD"
            delivery.instruction_type = "HOLD"
            message = "No accessible road route is available after the confirmed Bhalukpong-Bomdila landslide."
            summary = {"outcome": "NO_FEASIBLE_ROUTE", "delivery_id": delivery.id, "blocked_segment_id": blocked.id, "message": message}
        else:
            delivery.route_id = route.id
            delivery.route_geometry = route.geometry
            delivery.route_risk_score = route.risk_score
            delivery.route_risk_band = route.risk_band
            delivery.route_eta_minutes = route.eta_minutes
            delivery.instruction_type = "REROUTE"
            delivery.route_segment_ids = route.segment_ids
            delivery.delay_minutes = max(0, route.eta_minutes - 872)
            delivery.current_eta = timestamp + timedelta(minutes=route.eta_minutes)
            message = f"Alternative route selected via {' → '.join(route.path[1:-1])}. ETA updated by {delivery.delay_minutes} minutes."
            summary = {
                "outcome": "REROUTED",
                "delivery_id": delivery.id,
                "blocked_segment_id": blocked.id,
                "route_id": route.id,
                "route_path": route.path,
                "eta_minutes": route.eta_minutes,
                "delay_minutes": delivery.delay_minutes,
                "message": message,
            }
        delivery.instruction_status = "PENDING"
        delivery.instruction_updated_at = timestamp
        delivery.instruction_acknowledged_at = None
        self.alerts.insert(0, Alert(
            id="ALT-LANDSLIDE-01",
            severity="CRITICAL",
            alert_type="ROUTE_DISRUPTION",
            title="Medicine delivery rerouted" if route else "Medicine delivery held",
            message=message,
            related_entity_type="DELIVERY",
            related_entity_id=delivery.id,
            acknowledged=False,
            created_at=timestamp,
        ))
        changed = [blocked.id, incident.id, delivery.id, "ALT-LANDSLIDE-01"]
        self.persist("LANDSLIDE_CONFIRMED", changed, actor="Control room officer")
        return changed, summary

    def submit_field_report(self, report: FieldIncidentReportRequest) -> tuple[list[str], bool]:
        """Save a geo-tagged field report as unverified evidence, not a closure."""
        if report.client_report_id:
            existing = next(
                (item for item in self.incidents if item.context_snapshot.get("client_report_id") == report.client_report_id),
                None,
            )
            if existing:
                related_alert = next(
                    (item for item in self.alerts if item.related_entity_type == "INCIDENT" and item.related_entity_id == existing.id),
                    None,
                )
                return [existing.id] + ([related_alert.id] if related_alert else []), False
        road = next((item for item in self.roads if item.id == report.matched_segment_id), None) if report.matched_segment_id else None
        if report.matched_segment_id and road is None:
            raise ValueError("Unknown road segment")
        timestamp = now_utc()
        coordinates = (
            [report.longitude, report.latitude]
            if report.latitude is not None and report.longitude is not None
            else road.geometry.coordinates[len(road.geometry.coordinates) // 2]
        )
        location_label = road.road_name if road else f"{report.latitude:.4f}, {report.longitude:.4f}"
        incident_id = f"INC-FIELD-{len(self.incidents) + 1:04d}"
        alert_id = f"ALT-FIELD-{len(self.alerts) + 1:04d}"
        context_snapshot = dict(report.context_snapshot)
        if report.client_report_id:
            context_snapshot["client_report_id"] = report.client_report_id
        self.incidents.insert(0, Incident(
            id=incident_id,
            incident_type=report.incident_type.upper().replace(" ", "_"),
            severity=report.severity,
            reported_accessibility=report.reported_accessibility,
            verification="UNVERIFIED",
            location=GeoJsonPoint(coordinates=coordinates),
            matched_segment_id=road.id if road else None,
            description=report.description,
            source=f"{report.reporter_name} · field report",
            data_mode=DataMode.SIMULATED if context_snapshot.get("telemetry_mode") == "SIMULATED" else DataMode.LIVE,
            observed_at=timestamp,
            received_at=timestamp,
            context_snapshot=context_snapshot,
            photo_data_url=report.photo_data_url,
        ))
        self.alerts.insert(0, Alert(
            id=alert_id,
            severity="WARNING",
            alert_type="FIELD_REPORT",
            title="Field report awaiting verification",
            message=f"{report.incident_type.replace('_', ' ').title()} reported at {location_label}. Accessibility is unchanged until verified.",
            related_entity_type="INCIDENT",
            related_entity_id=incident_id,
            acknowledged=False,
            created_at=timestamp,
        ))
        self.refresh_ml_advisories()
        changed = [incident_id, alert_id]
        self.persist("FIELD_REPORT_SUBMITTED", changed, actor=report.reporter_name, details={
            "segment_id": road.id if road else None,
            "latitude": coordinates[1],
            "longitude": coordinates[0],
            "context_snapshot": report.context_snapshot,
        })
        return changed, True

    def verify_field_report(self, incident_id: str, review: IncidentVerificationRequest) -> tuple[list[str], list[dict]]:
        incident = next((item for item in self.incidents if item.id == incident_id), None)
        if incident is None:
            raise ValueError("Incident not found")
        if incident.verification != "UNVERIFIED":
            raise RuntimeError("This incident has already been reviewed")

        timestamp = now_utc()
        road = next((item for item in self.roads if item.id == incident.matched_segment_id), None)
        changed = [incident.id]
        impacts: list[dict] = []
        if review.decision == "REJECT":
            incident.verification = "REJECTED"
            title = "Field report rejected"
            message = f"{incident.incident_type.replace('_', ' ').title()} report rejected by {review.reviewer_name}."
        elif review.decision == "DOWNGRADE":
            incident.verification = "CONTROL_REVIEWED"
            incident.reported_accessibility = RoadAccessibility.CAUTION
            if road is not None and road.accessibility != RoadAccessibility.BLOCKED:
                road.accessibility = RoadAccessibility.CAUTION
                road.risk_band = RiskBand.MODERATE
                road.risk_score = min(road.risk_score, 54)
                road.source = f"Control-room review · {review.reviewer_name}"
                road.updated_at = timestamp
                changed.append(road.id)
            title = "Field report downgraded"
            message = f"Report reviewed as caution; no closure applied on {road.road_name if road else 'the selected road'} ."
        else:
            incident.verification = "CONTROL_CONFIRMED"
            if road is not None:
                road.accessibility = incident.reported_accessibility
                road.risk_band = RiskBand.CRITICAL if road.accessibility == RoadAccessibility.BLOCKED else RiskBand.HIGH
                road.risk_score = 96 if road.accessibility == RoadAccessibility.BLOCKED else max(70, road.risk_score)
                road.source = f"Control-room verified · {review.reviewer_name}"
                road.updated_at = timestamp
                changed.append(road.id)
            title = "Field report confirmed"
            confirmed_location = road.road_name if road else f"{incident.location.coordinates[1]:.4f}, {incident.location.coordinates[0]:.4f}"
            message = f"{incident.incident_type.replace('_', ' ').title()} confirmed at {confirmed_location}."

        if review.decision != "REJECT" and road is not None:
            self.refresh_ml_advisories()
            delivery_changes, impacts = self._reassess_deliveries_for_road(road, timestamp)
            changed.extend(delivery_changes)

        if review.decision == "CONFIRM" and road is None and self.roads:
            point = incident.location.coordinates
            virtual_road = self.roads[0].model_copy(update={
                "id": incident.id, "road_name": "Reported obstruction",
                "geometry": GeoJsonLineString(coordinates=[point, point]),
                "accessibility": incident.reported_accessibility,
            })
            delivery_changes, impacts = self._reassess_deliveries_for_road(virtual_road, timestamp)
            changed.extend(delivery_changes)

        alert_id = f"ALT-REVIEW-{len(self.alerts) + 1:04d}"
        self.alerts.insert(0, Alert(
            id=alert_id,
            severity="CRITICAL" if review.decision == "CONFIRM" and road and road.accessibility == RoadAccessibility.BLOCKED else "WARNING",
            alert_type="INCIDENT_REVIEW",
            title=title,
            message=f"{message} {review.note}".strip(),
            related_entity_type="INCIDENT",
            related_entity_id=incident.id,
            acknowledged=False,
            created_at=timestamp,
        ))
        self.refresh_ml_advisories()
        changed_entities = changed + [alert_id]
        self.persist("FIELD_REPORT_REVIEWED", changed_entities, actor=review.reviewer_name, details={"decision": review.decision, "incident_id": incident.id})
        return changed_entities, impacts

    def acknowledge_alert(self, alert_id: str, acknowledgement: AlertAcknowledgementRequest) -> list[str]:
        alert = next((item for item in self.alerts if item.id == alert_id), None)
        if alert is None:
            raise ValueError("Alert not found")
        if alert.acknowledged:
            raise RuntimeError("This alert is already acknowledged")
        alert.acknowledged = True
        changed = [alert.id]
        self.persist("ALERT_ACKNOWLEDGED", changed, actor=acknowledgement.acknowledged_by)
        return changed

    def apply_weather_readings(self, readings: list[WeatherReading], actor: str) -> list[str]:
        by_segment = {reading.segment_id: reading for reading in readings}
        changed: list[str] = []
        for road in self.roads:
            reading = by_segment.get(road.id)
            if reading is None:
                continue
            road.rainfall_mm_24h = reading.precipitation_mm_24h
            road.source = "Open-Meteo 24-hour forecast"
            road.data_mode = DataMode.LIVE
            road.observed_at = reading.observed_at
            road.updated_at = reading.observed_at
            changed.append(road.id)
        self.refresh_ml_advisories()
        for road in self.roads:
            predicted_risk = round((road.ml_risk_probability or 0) * 100)
            should_alert = predicted_risk >= 70 or road.rainfall_mm_24h >= 100
            already_active = any(
                alert.alert_type == "AUTOMATED_WEATHER_RISK"
                and alert.related_entity_type == "ROAD_SEGMENT"
                and alert.related_entity_id == road.id
                and not alert.acknowledged
                for alert in self.alerts
            )
            if not should_alert or already_active:
                continue
            severity = "CRITICAL" if predicted_risk >= 85 or road.rainfall_mm_24h >= 150 else "WARNING"
            alert_id = f"ALT-AUTO-{uuid4()}"
            self.alerts.insert(0, Alert(
                id=alert_id,
                severity=severity,
                alert_type="AUTOMATED_WEATHER_RISK",
                title=f"Predicted disruption risk on {road.road_name}",
                message=f"Live weather and ML assessment indicate {predicted_risk}% disruption risk with {road.rainfall_mm_24h:.0f} mm forecast rainfall. Verify field conditions before changing accessibility.",
                related_entity_type="ROAD_SEGMENT",
                related_entity_id=road.id,
                acknowledged=False,
                created_at=now_utc(),
            ))
            changed.append(alert_id)
        self.persist("WEATHER_REFRESHED", changed, actor=actor, details={"provider": "Open-Meteo", "segments": len(readings)})
        return changed

    def apply_vehicle_position(self, vehicle_id: str, position: VehiclePositionRequest, actor: str) -> tuple[Vehicle, Delivery | None, list[str]]:
        vehicle = next((item for item in self.vehicles if item.id == vehicle_id), None)
        if vehicle is None:
            raise ValueError("Vehicle not found")

        recorded_at = position.recorded_at or now_utc()
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=UTC)
        recorded_at = recorded_at.astimezone(UTC)
        previous_at = vehicle.last_position_at
        if previous_at.tzinfo is None:
            previous_at = previous_at.replace(tzinfo=UTC)
        if recorded_at <= previous_at.astimezone(UTC):
            raise RuntimeError("Position is older than or equal to the latest accepted vehicle position")

        if not (21 <= position.latitude <= 30 and 88 <= position.longitude <= 98):
            raise OverflowError("Position is outside the North Eastern Region operational boundary")

        vehicle.latitude = position.latitude
        vehicle.longitude = position.longitude
        vehicle.speed_kph = position.speed_kph
        vehicle.heading = position.heading
        vehicle.position_accuracy_m = position.accuracy_m
        vehicle.last_position_at = recorded_at
        is_demo_position = position.source.upper().startswith("DEMO_")
        vehicle.gps_freshness = "SIMULATED" if is_demo_position else "LIVE"
        vehicle.data_mode = DataMode.SIMULATED if is_demo_position else DataMode.LIVE
        vehicle.source = position.source
        changed = [vehicle.id]
        delivery = next((item for item in self.deliveries if item.id == vehicle.active_delivery_id), None)
        if delivery and not delivery.journey_paused and delivery.instruction_type != "HOLD" and not (vehicle.driver_user_id and (delivery.status == "DISPATCHED" or delivery.instruction_status == "PENDING")) and delivery.route_geometry and len(delivery.route_geometry.coordinates) >= 2:
            previous_tracking = delivery.tracking_status
            deviation_km, progress = self._route_position([vehicle.longitude, vehicle.latitude], delivery.route_geometry.coordinates)
            route_destination = delivery.route_geometry.coordinates[-1]
            requested_destination = delivery.destination_location.coordinates if delivery.destination_location else route_destination
            destination_km = min(
                self._point_to_segment_distance_km([vehicle.longitude, vehicle.latitude], route_destination, route_destination),
                self._point_to_segment_distance_km([vehicle.longitude, vehicle.latitude], requested_destination, requested_destination),
            )
            geofence_km = max(0.5, ((position.accuracy_m or 0) / 1000) + 0.15)
            telemetry = self.vehicle_telemetry(vehicle.id)

            delivery.progress_percent = max(delivery.progress_percent, min(99, round(progress * 100)))
            if destination_km <= geofence_km and vehicle.driver_user_id:
                # GPS proves proximity, not successful shipment handover.
                delivery.progress_percent = 99
                delivery.status = "IN_TRANSIT"
                delivery.tracking_status = "AT_DESTINATION"
            elif destination_km <= geofence_km:
                delivery.progress_percent = 100
                delivery.status = "ARRIVED"
                delivery.tracking_status = "ARRIVED"
                delivery.current_eta = recorded_at
                delivery.delay_minutes = max(0, round((recorded_at - delivery.planned_eta).total_seconds() / 60))
                vehicle.active_delivery_id = None
                vehicle.status = "AVAILABLE"
            elif deviation_km > 2.0:
                delivery.status = "DELAYED"
                delivery.tracking_status = "OFF_ROUTE"
            elif telemetry.stationary_minutes >= 15:
                delivery.status = "DELAYED"
                delivery.tracking_status = "STOPPED"
            else:
                delivery.status = "IN_TRANSIT"
                delivery.tracking_status = "ON_ROUTE"

            if delivery.tracking_status != "ARRIVED":
                remaining_fraction = max(0.0, 1.0 - delivery.progress_percent / 100)
                remaining_minutes = round((delivery.route_eta_minutes or max(1, round((delivery.current_eta - recorded_at).total_seconds() / 60))) * remaining_fraction)
                tracking_delay = telemetry.estimated_delivery_delay_minutes
                delivery.delay_minutes = max(delivery.delay_minutes, tracking_delay)
                delivery.current_eta = recorded_at + timedelta(minutes=max(1, remaining_minutes) + tracking_delay)
            delivery.last_tracking_update = recorded_at
            changed.append(delivery.id)

            alert_details = {
                "AT_DESTINATION": ("INFO", "Vehicle at destination", f"{delivery.id} reached its destination area. Driver handover confirmation is still required."),
                "OFF_ROUTE": ("WARNING", "Vehicle route deviation detected", f"{vehicle.registration} is {deviation_km:.1f} km outside the assigned route for {delivery.id}."),
                "STOPPED": ("WARNING", "Prolonged vehicle stoppage", f"{vehicle.registration} has remained stopped for {telemetry.stationary_minutes} minutes on {delivery.id}."),
                "ARRIVED": ("INFO", "Delivery arrived", f"{delivery.id} entered its destination geofence and was marked arrived."),
            }.get(delivery.tracking_status)
            if alert_details and delivery.tracking_status != previous_tracking:
                severity, title, message = alert_details
                alert_id = f"ALT-TRACKING-{len(self.alerts) + 1:04d}"
                self.alerts.insert(0, Alert(
                    id=alert_id, severity=severity, alert_type="DELIVERY_TRACKING", title=title, message=message,
                    related_entity_type="DELIVERY", related_entity_id=delivery.id,
                    acknowledged=delivery.tracking_status == "ARRIVED", created_at=recorded_at,
                ))
                changed.append(alert_id)
        self.persist(
            "GPS_POSITION_RECEIVED",
            changed,
            actor=actor,
            details={
                "vehicle_id": vehicle.id,
                "latitude": vehicle.latitude,
                "longitude": vehicle.longitude,
                "speed_kph": vehicle.speed_kph,
                "heading": vehicle.heading,
                "accuracy_m": vehicle.position_accuracy_m,
                "recorded_at": recorded_at.isoformat(),
                "source": vehicle.source,
                "delivery_id": delivery.id if delivery else None,
                "delivery_progress_percent": delivery.progress_percent if delivery else None,
                "delivery_tracking_status": delivery.tracking_status if delivery else None,
            },
        )
        return deepcopy(vehicle), deepcopy(delivery), changed

    def register_vehicle(
        self,
        request: VehicleRegistrationRequest,
        actor: str,
        driver_user_id: str | None = None,
        driver_name: str | None = None,
    ) -> Vehicle:
        if not (21 <= request.latitude <= 30 and 88 <= request.longitude <= 98):
            raise OverflowError("Initial position is outside the North Eastern Region operational boundary")
        registration = request.registration.strip().upper()
        if any(vehicle.registration.upper() == registration for vehicle in self.vehicles):
            raise RuntimeError("A vehicle with this registration is already registered")
        if driver_user_id and any(vehicle.driver_user_id == driver_user_id for vehicle in self.vehicles):
            raise RuntimeError("This driver already has a registered vehicle")

        delivery = None
        if request.active_delivery_id:
            delivery = next((item for item in self.deliveries if item.id == request.active_delivery_id), None)
            if delivery is None:
                raise ValueError("Delivery not found")
            if any(vehicle.active_delivery_id == delivery.id for vehicle in self.vehicles):
                raise RuntimeError("The selected delivery is already assigned to another vehicle")

        recorded_at = request.recorded_at or now_utc()
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=UTC)
        recorded_at = recorded_at.astimezone(UTC)
        is_demo_position = request.source.upper().startswith("DEMO_")
        vehicle = Vehicle(
            id=f"VEH-{uuid4().hex[:8].upper()}",
            registration=registration,
            vehicle_class=request.vehicle_class.strip().upper().replace(" ", "_"),
            status="IN_TRANSIT" if delivery else "AVAILABLE",
            latitude=request.latitude,
            longitude=request.longitude,
            speed_kph=0,
            heading=0,
            gps_freshness="SIMULATED" if is_demo_position else "LIVE",
            last_position_at=recorded_at,
            active_delivery_id=delivery.id if delivery else None,
            data_mode=DataMode.SIMULATED if is_demo_position else DataMode.LIVE,
            source=request.source,
            position_accuracy_m=request.accuracy_m,
            driver_user_id=driver_user_id,
            driver_name=driver_name,
        )
        self.vehicles.append(vehicle)
        if delivery:
            delivery.vehicle_id = vehicle.id
        self.persist(
            "VEHICLE_REGISTERED",
            [vehicle.id] + ([delivery.id] if delivery else []),
            actor=actor,
            details={
                "vehicle_id": vehicle.id,
                "registration": registration,
                "latitude": vehicle.latitude,
                "longitude": vehicle.longitude,
                "accuracy_m": vehicle.position_accuracy_m,
                "recorded_at": recorded_at.isoformat(),
                "source": vehicle.source,
            },
        )
        return deepcopy(vehicle)

    def create_delivery(self, request: DeliveryCreateRequest, actor: str) -> Delivery:
        route = request.selected_route
        if len(route.geometry.coordinates) < 2 or route.distance_km <= 0 or route.eta_minutes <= 0:
            raise ValueError("The selected route does not contain usable road geometry")

        matched_road_ids = {
            road_id
            for section in route.intelligence_segments
            for road_id in section.matched_road_ids
        }
        matched_road_ids.update(segment_id for segment_id in route.segment_ids if any(road.id == segment_id for road in self.roads))
        blocked = [road.id for road in self.roads if road.id in matched_road_ids and road.accessibility == RoadAccessibility.BLOCKED]
        if blocked:
            raise RuntimeError(f"The selected route now intersects blocked monitored roads: {', '.join(blocked)}. Calculate routes again.")

        vehicle = None
        if request.vehicle_id:
            vehicle = next((item for item in self.vehicles if item.id == request.vehicle_id), None)
            if vehicle is None:
                raise ValueError("Vehicle not found")
            if vehicle.active_delivery_id:
                raise RuntimeError("The selected vehicle is already assigned to an active delivery")

        timestamp = now_utc()
        delivery = Delivery(
            id=f"DEL-{uuid4().hex[:8].upper()}",
            cargo_type=request.cargo_type.strip().upper().replace(" ", "_"),
            cargo_description=request.cargo_description.strip(),
            priority=request.priority,
            source_name=request.source.label,
            destination_name=request.destination.label,
            vehicle_id=vehicle.id if vehicle else "UNASSIGNED",
            status="DISPATCHED" if vehicle else "AWAITING_VEHICLE",
            progress_percent=0,
            planned_eta=timestamp + timedelta(minutes=route.eta_minutes),
            current_eta=timestamp + timedelta(minutes=route.eta_minutes),
            delay_minutes=route.predicted_delay_minutes,
            route_id=route.id,
            route_segment_ids=sorted(matched_road_ids),
            route_geometry=route.geometry,
            route_risk_score=route.risk_score,
            route_risk_band=route.risk_band,
            route_distance_km=route.distance_km,
            route_eta_minutes=route.eta_minutes,
            source_location=GeoJsonPoint(coordinates=[request.source.longitude, request.source.latitude]),
            destination_location=GeoJsonPoint(coordinates=[request.destination.longitude, request.destination.latitude]),
        )
        self.deliveries.insert(0, delivery)
        changed = [delivery.id]
        if vehicle:
            vehicle.active_delivery_id = delivery.id
            vehicle.status = "IN_TRANSIT"
            delivery.instruction_status = "PENDING"
            delivery.instruction_type = "INITIAL_ROUTE"
            delivery.instruction_updated_at = timestamp
            changed.append(vehicle.id)
        self.persist("DELIVERY_DISPATCHED", changed, actor=actor, details={
            "delivery_id": delivery.id,
            "route_id": delivery.route_id,
            "vehicle_id": delivery.vehicle_id,
            "route_risk_score": delivery.route_risk_score,
            "monitored_road_ids": delivery.route_segment_ids,
        })
        return deepcopy(delivery)

    def assign_delivery_vehicle(self, delivery_id: str, vehicle_id: str, actor: str) -> Delivery:
        delivery = next((item for item in self.deliveries if item.id == delivery_id), None)
        if delivery is None:
            raise ValueError("Delivery not found")
        if delivery.status == "ARRIVED":
            raise RuntimeError("An arrived delivery cannot be assigned")
        if delivery.vehicle_id != "UNASSIGNED":
            raise RuntimeError("The delivery is already assigned to a vehicle")
        vehicle = next((item for item in self.vehicles if item.id == vehicle_id), None)
        if vehicle is None:
            raise ValueError("Vehicle not found")
        if vehicle.active_delivery_id:
            raise RuntimeError("The selected vehicle is already assigned to an active delivery")

        delivery.vehicle_id = vehicle.id
        delivery.status = "DISPATCHED"
        delivery.instruction_status = "PENDING"
        delivery.instruction_type = "INITIAL_ROUTE"
        delivery.instruction_updated_at = now_utc()
        delivery.instruction_acknowledged_at = None
        vehicle.active_delivery_id = delivery.id
        vehicle.status = "IN_TRANSIT"
        self.persist("DELIVERY_VEHICLE_ASSIGNED", [delivery.id, vehicle.id], actor=actor, details={
            "delivery_id": delivery.id, "vehicle_id": vehicle.id, "registration": vehicle.registration,
        })
        return deepcopy(delivery)

    def driver_journey(self, driver_user_id: str) -> tuple[Vehicle | None, Delivery | None, VehicleTelemetry | None, MapSnapshotResponse]:
        vehicle = next((item for item in self.vehicles if item.driver_user_id == driver_user_id), None)
        delivery = next((item for item in self.deliveries if vehicle and item.id == vehicle.active_delivery_id), None)
        snapshot = self.map_snapshot()
        snapshot.vehicles = [item for item in snapshot.vehicles if vehicle and item.id == vehicle.id]
        snapshot.vehicle_telemetry = [item for item in snapshot.vehicle_telemetry if vehicle and item.vehicle_id == vehicle.id]
        if delivery:
            route_ids = set(delivery.route_segment_ids)
            snapshot.road_segments = [item for item in snapshot.road_segments if item.id in route_ids]
            snapshot.incidents = [item for item in snapshot.incidents if item.matched_segment_id in route_ids or item.context_snapshot.get("delivery_id") == delivery.id or (delivery.route_geometry and self._route_position(item.location.coordinates, delivery.route_geometry.coordinates)[0] <= 1)]
        else:
            snapshot.road_segments = []
            snapshot.incidents = []
        snapshot.facilities = []
        telemetry = self.vehicle_telemetry(vehicle.id) if vehicle else None
        return deepcopy(vehicle), deepcopy(delivery), telemetry, snapshot

    def apply_driver_journey_action(self, driver_user_id: str, action: str, actor: str, instruction_updated_at: datetime | None = None, description: str = "") -> tuple[Vehicle, Delivery]:
        vehicle = next((item for item in self.vehicles if item.driver_user_id == driver_user_id), None)
        if vehicle is None:
            raise ValueError("No vehicle is registered to this driver")
        delivery = next((item for item in self.deliveries if item.id == vehicle.active_delivery_id), None)
        if delivery is None:
            raise RuntimeError("No active delivery is assigned to this driver")
        timestamp = now_utc()
        if action in {"START_JOURNEY", "RESUME_JOURNEY", "COMPLETE_DELIVERY"}:
            if delivery.instruction_type == "HOLD" or delivery.instruction_status == "PENDING":
                raise RuntimeError("Journey is held or the latest route instruction needs acknowledgement")
        if action == "START_JOURNEY":
            if delivery.status not in {"DISPATCHED", "REROUTING"}:
                raise RuntimeError("This journey cannot be started in its current state")
            delivery.status = "IN_TRANSIT"
            vehicle.status = "IN_TRANSIT"
        elif action == "ACKNOWLEDGE_ROUTE":
            if delivery.instruction_status != "PENDING":
                raise RuntimeError("There is no pending route instruction")
            if instruction_updated_at is None or instruction_updated_at != delivery.instruction_updated_at:
                raise RuntimeError("Route instruction changed. Refresh and review the latest instruction")
            delivery.instruction_status = "ACKNOWLEDGED"
            delivery.instruction_acknowledged_at = timestamp
            if delivery.status == "REROUTING" and not delivery.journey_paused:
                delivery.status = "IN_TRANSIT"
        elif action == "PAUSE_JOURNEY":
            if delivery.journey_paused or delivery.status not in {"IN_TRANSIT", "DELAYED", "AT_RISK", "REROUTING"}:
                raise RuntimeError("Only an active journey can be paused")
            delivery.journey_paused = True
            delivery.status = "PAUSED"
        elif action == "RESUME_JOURNEY":
            if not delivery.journey_paused:
                raise RuntimeError("Journey is not paused")
            delivery.journey_paused = False
            delivery.status = "IN_TRANSIT"
        elif action == "REPORT_OBSTRUCTION":
            if len(description.strip()) < 10:
                raise RuntimeError("Describe the obstruction in at least 10 characters")
            road = min(self.roads, key=lambda item: self._route_position([vehicle.longitude, vehicle.latitude], item.geometry.coordinates)[0], default=None)
            matched_id = road.id if road and self._route_position([vehicle.longitude, vehicle.latitude], road.geometry.coordinates)[0] <= 1 else None
            self.submit_field_report(FieldIncidentReportRequest(
                incident_type="OTHER", severity="WARNING", reported_accessibility="BLOCKED",
                latitude=vehicle.latitude, longitude=vehicle.longitude, matched_segment_id=matched_id,
                description=description.strip(), reporter_name=actor,
                context_snapshot={"delivery_id": delivery.id, "driver_user_id": driver_user_id, "telemetry_mode": vehicle.data_mode, "recorded_at": vehicle.last_position_at.isoformat()},
            ))
            if vehicle.data_mode == DataMode.SIMULATED:
                self.incidents[0].data_mode = DataMode.SIMULATED
        elif action == "COMPLETE_DELIVERY":
            if delivery.journey_paused:
                raise RuntimeError("Resume the journey before completing delivery")
            if delivery.status not in {"IN_TRANSIT", "DELAYED", "AT_RISK"}:
                raise RuntimeError("Start the journey before completing the delivery")
            delivery.status = "ARRIVED"
            delivery.tracking_status = "ARRIVED"
            delivery.progress_percent = 100
            delivery.current_eta = timestamp
            delivery.last_tracking_update = timestamp
            vehicle.status = "AVAILABLE"
            vehicle.active_delivery_id = None
        else:
            raise ValueError("Unsupported driver action")
        self.persist(
            f"DRIVER_{action}", [vehicle.id, delivery.id], actor=actor,
            details={"driver_user_id": driver_user_id, "vehicle_id": vehicle.id, "delivery_id": delivery.id, "action": action},
        )
        return deepcopy(vehicle), deepcopy(delivery)


store = SeedStore()
