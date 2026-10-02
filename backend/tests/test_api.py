from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
admin_login = client.post(
    "/api/v1/auth/login",
    json={"username": "admin@ner.gov.in", "password": "NerDemo@2026"},
)
assert admin_login.status_code == 200
client.headers.update({"Authorization": f"Bearer {admin_login.json()['access_token']}"})


def register_test_vehicle(active_delivery_id: str | None = "DEL-1001") -> dict:
    response = client.post(
        "/api/v1/vehicles",
        json={
            "registration": "AS-01-TEST-140",
            "vehicle_class": "REFRIGERATED_TRUCK",
            "latitude": 26.6528,
            "longitude": 92.7926,
            "active_delivery_id": active_delivery_id,
            "accuracy_m": 6.5,
            "source": "AIS-140-TEST-DEVICE",
        },
    )
    assert response.status_code == 201
    return response.json()["vehicle"]


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_and_role_authorization() -> None:
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "CONTROL_ROOM_ADMIN"

    field_login = TestClient(app).post(
        "/api/v1/auth/login",
        json={"username": "field@ner.gov.in", "password": "FieldDemo@2026"},
    )
    assert field_login.status_code == 200
    field_headers = {"Authorization": f"Bearer {field_login.json()['access_token']}"}
    forbidden = TestClient(app).post(
        "/api/v1/simulation/reset",
        headers=field_headers,
    )
    assert forbidden.status_code == 403

    unauthenticated = TestClient(app).post("/api/v1/simulation/reset")
    assert unauthenticated.status_code == 401

    assert TestClient(app).get("/api/v1/overview").status_code == 401
    assert TestClient(app).get("/api/v1/map/snapshot").status_code == 401

    role_accounts = [
        ("logistics@ner.gov.in", "LogisticsDemo@2026", "LOGISTICS_OPERATOR"),
        ("district@ner.gov.in", "DistrictDemo@2026", "DISTRICT_AUTHORITY"),
        ("viewer@ner.gov.in", "ViewerDemo@2026", "VIEWER"),
        ("driver@ner.gov.in", "DriverDemo@2026", "DRIVER"),
    ]
    for username, password, role in role_accounts:
        login_response = TestClient(app).post("/api/v1/auth/login", json={"username": username, "password": password})
        assert login_response.status_code == 200
        assert login_response.json()["user"]["role"] == role

    viewer_login = TestClient(app).post("/api/v1/auth/login", json={"username": "viewer@ner.gov.in", "password": "ViewerDemo@2026"}).json()
    viewer_headers = {"Authorization": f"Bearer {viewer_login['access_token']}"}
    viewer_route = TestClient(app).post(
        "/api/v1/routes/plan",
        headers=viewer_headers,
        json={"source_location": {"label": "Shillong", "latitude": 25.5788, "longitude": 91.8933}, "destination_location": {"label": "Silchar", "latitude": 24.8333, "longitude": 92.7789}},
    )
    assert viewer_route.status_code == 403

    client.post("/api/v1/simulation/reset")
    district_login = TestClient(app).post("/api/v1/auth/login", json={"username": "district@ner.gov.in", "password": "DistrictDemo@2026"}).json()
    district_headers = {"Authorization": f"Bearer {district_login['access_token']}"}
    outside_district = TestClient(app).post(
        "/api/v1/incidents/INC-1001/verification",
        headers=district_headers,
        json={"decision": "CONFIRM"},
    )
    assert outside_district.status_code == 403


def test_overview_and_map_share_pilot_state() -> None:
    client.post("/api/v1/simulation/reset")
    overview = client.get("/api/v1/overview").json()
    snapshot = client.get("/api/v1/map/snapshot").json()
    assert overview["data_mode"] == "SIMULATED"
    assert overview["metrics"]["active_vehicles"] == 0
    assert snapshot["vehicles"] == []
    assert len(snapshot["road_segments"]) == 64
    assert len(snapshot["facilities"]) == 80
    assert sum(item["facility_type"] == "BRIDGE_MONITOR" for item in snapshot["facilities"]) >= 10
    covered_states = {item["district"].split(", ")[-1] for item in snapshot["facilities"]}
    assert covered_states == {"Assam", "Arunachal Pradesh", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura"}
    assert snapshot["operational_boundary"]["type"] == "MultiPolygon"
    assert any(item["destination_name"] == "Tawang District Hospital" for item in overview["priority_deliveries"])


def test_heavy_rain_event_raises_risk() -> None:
    client.post("/api/v1/simulation/reset")
    response = client.post("/api/v1/simulation/events/heavy-rain")
    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["metrics"]["high_risk_segments"] == 2
    assert payload["overview"]["priority_deliveries"][0]["status"] == "AT_RISK"


def test_ml_advisory_is_exposed_without_changing_road_accessibility() -> None:
    client.post("/api/v1/simulation/reset")
    status = client.get("/api/v1/intelligence/status")
    snapshot = client.get("/api/v1/map/snapshot").json()
    road = next(item for item in snapshot["road_segments"] if item["id"] == "SEG-004")
    assert status.status_code == 200
    assert status.json()["mode"] == "ADVISORY_ONLY"
    assert road["accessibility"] == "CAUTION"
    assert road["ml_advisory_status"] in {"AVAILABLE", "DEGRADED", "UNAVAILABLE"}
    if road["ml_advisory_status"] == "AVAILABLE":
        assert 0 <= road["ml_risk_probability"] <= 1
        assert road["ml_predicted_delay_minutes"] >= 0


def test_field_report_is_geotagged_and_awaits_verification() -> None:
    client.post("/api/v1/simulation/reset")
    response = client.post(
        "/api/v1/field-reports",
        json={
            "incident_type": "LANDSLIDE",
            "severity": "WARNING",
            "reported_accessibility": "CAUTION",
            "matched_segment_id": "SEG-010",
            "description": "Loose debris and small stones reported along the road shoulder.",
            "reporter_name": "West Kameng field team",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    incident = payload["map_snapshot"]["incidents"][0]
    road = next(item for item in payload["map_snapshot"]["road_segments"] if item["id"] == "SEG-010")
    assert incident["matched_segment_id"] == "SEG-010"
    assert incident["verification"] == "UNVERIFIED"
    assert road["accessibility"] == "OPEN"
    assert payload["overview"]["critical_alerts"][0]["title"] == "Field report awaiting verification"


def test_ner_wide_gps_report_blocks_only_nearby_routes_after_confirmation(monkeypatch) -> None:
    from app.routing.osrm_adapter import OsrmRoute
    from app.routing.service import route_planning_service
    from app.weather.open_meteo import RouteWeatherPoint

    client.post("/api/v1/simulation/reset")
    created = client.post(
        "/api/v1/field-reports",
        json={
            "incident_type": "LANDSLIDE",
            "severity": "CRITICAL",
            "reported_accessibility": "BLOCKED",
            "latitude": 25.4,
            "longitude": 92.35,
            "description": "GPS confirmed debris field blocks the road at this remote location.",
        },
    )
    assert created.status_code == 200
    incident = created.json()["map_snapshot"]["incidents"][0]
    assert incident["matched_segment_id"] is None
    assert incident["data_mode"] == "LIVE"
    assert incident["location"]["coordinates"] == [92.35, 25.4]
    confirmed = client.post(
        f"/api/v1/incidents/{incident['id']}/verification",
        json={"decision": "CONFIRM"},
    )
    assert confirmed.status_code == 200

    source = [91.8933, 25.5788]
    destination = [92.7789, 24.8333]
    monkeypatch.setattr(route_planning_service.external, "fetch_routes", lambda _source, _destination: [
        OsrmRoute(190000, 15000, [source, [92.35, 25.4], destination], ["Blocked approach"]),
        OsrmRoute(260000, 21000, [source, [93.5, 26.2], destination], ["Safe detour"]),
    ])
    monkeypatch.setattr(route_planning_service.weather, "fetch_for_coordinates", lambda coordinates: [
        RouteWeatherPoint(12, 40, 700, datetime.now(UTC)) for _ in coordinates
    ])
    planned = client.post("/api/v1/routes/plan", json={
        "source_location": {"label": "Shillong", "latitude": source[1], "longitude": source[0]},
        "destination_location": {"label": "Silchar", "latitude": destination[1], "longitude": destination[0]},
        "preference": "SAFETY_FIRST",
    })
    assert planned.status_code == 200
    payload = planned.json()
    assert len(payload["routes"]) == 1
    assert incident["id"] in payload["excluded_blocked_segments"]
    assert payload["routes"][0]["path"][1] == "Safe detour"
    client.post("/api/v1/simulation/reset")


def test_verified_field_report_can_close_road_and_reroute_delivery() -> None:
    client.post("/api/v1/simulation/reset")
    created = client.post(
        "/api/v1/field-reports",
        json={
            "incident_type": "LANDSLIDE",
            "severity": "CRITICAL",
            "reported_accessibility": "BLOCKED",
            "matched_segment_id": "SEG-004",
            "description": "Major debris flow blocks both lanes on the Bhalukpong-Bomdila approach.",
            "reporter_name": "West Kameng field team",
        },
    ).json()
    incident_id = created["map_snapshot"]["incidents"][0]["id"]
    response = client.post(
        f"/api/v1/incidents/{incident_id}/verification",
        json={"decision": "CONFIRM", "reviewer_name": "Control room officer"},
    )
    assert response.status_code == 200
    payload = response.json()
    incident = next(item for item in payload["map_snapshot"]["incidents"] if item["id"] == incident_id)
    road = next(item for item in payload["map_snapshot"]["road_segments"] if item["id"] == "SEG-004")
    assert incident["verification"] == "CONTROL_CONFIRMED"
    assert road["accessibility"] == "BLOCKED"
    assert payload["disruption_summary"]["outcome"] == "REROUTED"
    assert "KALAKTANG" in payload["disruption_summary"]["route_path"]
    assert {impact["delivery_id"] for impact in payload["delivery_impacts"]} == {"DEL-1001", "DEL-1002"}
    assert all("SEG-004" not in impact.get("route_segment_ids", []) for impact in payload["delivery_impacts"])


def test_verified_unrelated_road_does_not_modify_deliveries() -> None:
    client.post("/api/v1/simulation/reset")
    before = {item["id"]: item for item in client.get("/api/v1/overview").json()["priority_deliveries"]}
    created = client.post("/api/v1/field-reports", json={
        "incident_type": "ROAD_DAMAGE", "severity": "CRITICAL", "reported_accessibility": "BLOCKED",
        "matched_segment_id": "SEG-014", "description": "Bridge approach damage blocks the monitored Shillong corridor.",
        "reporter_name": "Meghalaya field team",
    }).json()
    incident_id = created["map_snapshot"]["incidents"][0]["id"]
    response = client.post(f"/api/v1/incidents/{incident_id}/verification", json={"decision": "CONFIRM"})
    assert response.status_code == 200
    payload = response.json()
    after = {item["id"]: item for item in payload["overview"]["priority_deliveries"]}
    assert payload["delivery_impacts"] == []
    assert payload["disruption_summary"] is None
    assert {key: value["route_id"] for key, value in after.items()} == {key: value["route_id"] for key, value in before.items()}
    client.post("/api/v1/simulation/reset")


def test_alert_acknowledgement_removes_item_from_active_queue() -> None:
    client.post("/api/v1/simulation/reset")
    overview = client.get("/api/v1/overview").json()
    alert_id = overview["critical_alerts"][0]["id"]
    response = client.post(f"/api/v1/alerts/{alert_id}/acknowledgement", json={"acknowledged_by": "Control room officer"})
    assert response.status_code == 200
    assert response.json()["overview"]["critical_alerts"] == []


def test_operational_state_is_persistent_and_audited() -> None:
    client.post("/api/v1/simulation/reset")
    status = client.get("/api/v1/persistence/status")
    audit = client.get("/api/v1/audit/events?limit=5")
    assert status.status_code == 200
    assert status.json()["mode"] == "PERSISTENT"
    assert status.json()["backend"] in {"SQLITE", "POSTGRESQL"}
    assert status.json()["entity_counts"]["road_segments"] == 64
    assert status.json()["entity_counts"]["vehicles"] == 0
    assert status.json()["entity_counts"]["deliveries"] == 2
    assert status.json()["spatial"]["geometry_storage"] in {"GEOJSON_FALLBACK", "POSTGIS_GEOMETRY_4326"}
    assert audit.status_code == 200
    assert any(event["event_type"] == "DEMO_RESET" for event in audit.json()["events"])


def test_persisted_state_is_restored_by_new_store_instance() -> None:
    from app.seed.store import SeedStore

    client.post("/api/v1/simulation/reset")
    created = client.post(
        "/api/v1/field-reports",
        json={
            "incident_type": "ROAD_DAMAGE",
            "severity": "WARNING",
            "reported_accessibility": "CAUTION",
            "matched_segment_id": "SEG-010",
            "description": "Road shoulder damage reported near the Kalaktang approach road.",
            "reporter_name": "Persistence test team",
        },
    ).json()
    incident_id = created["map_snapshot"]["incidents"][0]["id"]
    restored = SeedStore()
    assert any(incident.id == incident_id for incident in restored.incidents)
    client.post("/api/v1/simulation/reset")


def test_analytics_are_derived_from_operational_state() -> None:
    client.post("/api/v1/simulation/reset")
    response = client.get("/api/v1/analytics")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["state_connectivity"]) == 8
    assert {item["state"] for item in payload["state_connectivity"]} == {
        "Assam", "Arunachal Pradesh", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura",
    }
    assert payload["summary"]["monitored_road_km"] > 0
    assert payload["summary"]["active_deliveries"] == 2
    assert len(payload["risk_corridors"]) == 10
    assert payload["data_quality"]["ml_model_version"]
    assert 0 <= payload["data_quality"]["ml_coverage_percent"] <= 100


def test_multilingual_alert_feed_and_admin_scope() -> None:
    client.post("/api/v1/simulation/reset")
    hindi = client.get("/api/v1/alerts?language=hi")
    assert hindi.status_code == 200
    assert hindi.json()["language"] == "hi"
    assert hindi.json()["items"][0]["display_title"] != hindi.json()["items"][0]["title"]
    assert hindi.json()["items"][0]["channel"] == "IN_APP_REALTIME"

    admin = client.get("/api/v1/admin/overview")
    assert admin.status_code == 200
    assert len(admin.json()["users"]) == 6
    assert all("password" not in key for user in admin.json()["users"] for key in user)
    assert admin.json()["persistence"]["backend"] in {"SQLITE", "POSTGRESQL"}

    viewer_session = TestClient(app).post("/api/v1/auth/login", json={"username": "viewer@ner.gov.in", "password": "ViewerDemo@2026"}).json()
    viewer_headers = {"Authorization": f"Bearer {viewer_session['access_token']}"}
    assert TestClient(app).get("/api/v1/admin/overview", headers=viewer_headers).status_code == 403
    assert TestClient(app).get("/api/v1/alerts?language=en", headers=viewer_headers).status_code == 200


def test_driver_demo_gps_is_labelled_and_supports_assigned_journey() -> None:
    client.post("/api/v1/simulation/reset")
    driver_login = TestClient(app).post(
        "/api/v1/auth/login",
        json={"username": "driver@ner.gov.in", "password": "DriverDemo@2026"},
    )
    assert driver_login.status_code == 200
    driver_headers = {"Authorization": f"Bearer {driver_login.json()['access_token']}"}
    driver_client = TestClient(app)

    assert driver_client.get("/api/v1/overview", headers=driver_headers).status_code == 403
    empty = driver_client.get("/api/v1/driver/journey", headers=driver_headers)
    assert empty.status_code == 200
    assert empty.json()["vehicle"] is None

    registered = driver_client.post(
        "/api/v1/vehicles",
        headers=driver_headers,
        json={
            "registration": "AS-01-DRIVER-1",
            "vehicle_class": "RELIEF_TRUCK",
            "latitude": 26.1445,
            "longitude": 91.7362,
            "active_delivery_id": "DEL-1001",
            "accuracy_m": 8,
            "source": "DEMO_GPS_OVERRIDE:GUWAHATI",
        },
    )
    assert registered.status_code == 201
    vehicle = registered.json()["vehicle"]
    assert vehicle["driver_user_id"] == "USR-DRIVER-001"
    assert vehicle["active_delivery_id"] is None
    assert vehicle["data_mode"] == "SIMULATED"
    assert vehicle["gps_freshness"] == "SIMULATED"

    assigned = client.post(f"/api/v1/deliveries/DEL-1001/vehicle", json={"vehicle_id": vehicle["id"]})
    assert assigned.status_code == 200
    journey = driver_client.get("/api/v1/driver/journey", headers=driver_headers).json()
    assert journey["delivery"]["id"] == "DEL-1001"
    assert journey["delivery"]["instruction_status"] == "PENDING"
    assert len(journey["map_snapshot"]["vehicles"]) == 1

    acknowledged = driver_client.post(
        "/api/v1/driver/journey/actions",
        headers=driver_headers,
        json={"action": "ACKNOWLEDGE_ROUTE", "instruction_updated_at": journey["delivery"]["instruction_updated_at"]},
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["delivery"]["instruction_status"] == "ACKNOWLEDGED"

    started = driver_client.post(
        "/api/v1/driver/journey/actions",
        headers=driver_headers,
        json={"action": "START_JOURNEY"},
    )
    assert started.status_code == 200
    assert started.json()["delivery"]["status"] == "IN_TRANSIT"

    completed = driver_client.post(
        "/api/v1/driver/journey/actions",
        headers=driver_headers,
        json={"action": "COMPLETE_DELIVERY"},
    )
    assert completed.status_code == 200
    assert completed.json()["delivery"] is None
    assert completed.json()["vehicle"]["active_delivery_id"] is None


def test_internal_diagnostics_require_authentication() -> None:
    anonymous = TestClient(app)
    assert anonymous.get("/api/v1/system/status").status_code == 401
    assert anonymous.get("/api/v1/intelligence/status").status_code == 401
    assert anonymous.get("/api/v1/persistence/status").status_code == 401
    assert anonymous.get("/api/v1/audit/events").status_code == 401
def test_route_plan_returns_real_pilot_alternatives() -> None:
    client.post("/api/v1/simulation/reset")
    response = client.post(
        "/api/v1/routes/plan",
        json={
            "source_facility_id": "FAC-GHY-MED",
            "destination_facility_id": "FAC-TAW-HOSP",
            "cargo_type": "EMERGENCY_MEDICINES",
            "priority": "CRITICAL",
            "vehicle_class": "REFRIGERATED_TRUCK",
            "preference": "SAFETY_FIRST",
            "routing_mode": "CURATED_ONLY",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ROUTES_AVAILABLE"
    assert len(payload["routes"]) >= 2
    assert all("GANGTOK" not in route["path"] for route in payload["routes"])
    assert payload["recommended_route_id"] is not None


def test_confirmed_shared_block_returns_no_feasible_route() -> None:
    from app.domain.models import RoadAccessibility
    from app.routing.engine import RoutingEngine
    from app.seed.store import store

    client.post("/api/v1/simulation/reset")
    shared_segment = next(segment for segment in store.roads if segment.id == "SEG-006")
    shared_segment.accessibility = RoadAccessibility.BLOCKED
    request = {
        "source_facility_id": "FAC-GHY-MED",
        "destination_facility_id": "FAC-TAW-HOSP",
        "preference": "SAFETY_FIRST",
    }
    from app.domain.models import RoutePlanRequest

    result = RoutingEngine(store.roads).plan(RoutePlanRequest(**request))
    assert result.status == "NO_FEASIBLE_ROUTE"
    assert result.routes == []
    assert "SEG-006" in result.excluded_blocked_segments
    store.reset()


def test_logistics_operator_can_dispatch_a_calculated_route() -> None:
    client.post("/api/v1/simulation/reset")
    planned = client.post("/api/v1/routes/plan", json={
        "source_facility_id": "FAC-GHY-MED", "destination_facility_id": "FAC-TAW-HOSP",
        "source_location": {"label": "Guwahati, Assam", "latitude": 26.1445, "longitude": 91.7362},
        "destination_location": {"label": "Tawang, Arunachal Pradesh", "latitude": 27.5861, "longitude": 91.8594},
        "preference": "SAFETY_FIRST", "routing_mode": "CURATED_ONLY",
    })
    assert planned.status_code == 200
    plan = planned.json()
    selected = next(route for route in plan["routes"] if route["id"] == plan["recommended_route_id"])
    response = client.post("/api/v1/deliveries", json={
        "cargo_type": "EMERGENCY_MEDICINES", "cargo_description": "Insulin and emergency antibiotics",
        "priority": "CRITICAL", "source": {"label": "Guwahati, Assam", "latitude": 26.1445, "longitude": 91.7362},
        "destination": {"label": "Tawang, Arunachal Pradesh", "latitude": 27.5861, "longitude": 91.8594},
        "selected_route": selected, "vehicle_id": None,
    })
    assert response.status_code == 201
    payload = response.json()
    delivery = payload["delivery"]
    assert delivery["status"] == "AWAITING_VEHICLE"
    assert delivery["vehicle_id"] == "UNASSIGNED"
    assert delivery["route_geometry"]["coordinates"] == selected["geometry"]["coordinates"]
    assert delivery["route_risk_score"] == selected["risk_score"]
    assert any(item["id"] == delivery["id"] for item in payload["overview"]["priority_deliveries"])
    vehicle = register_test_vehicle(None)
    assigned = client.post(f"/api/v1/deliveries/{delivery['id']}/vehicle", json={"vehicle_id": vehicle["id"]})
    assert assigned.status_code == 200
    assigned_payload = assigned.json()
    assert assigned_payload["delivery"]["vehicle_id"] == vehicle["id"]
    assert assigned_payload["delivery"]["status"] == "DISPATCHED"
    assigned_vehicle = next(item for item in assigned_payload["map_snapshot"]["vehicles"] if item["id"] == vehicle["id"])
    assert assigned_vehicle["active_delivery_id"] == delivery["id"]
    route_coordinates = selected["geometry"]["coordinates"]
    midpoint = route_coordinates[len(route_coordinates) // 2]
    first_ping_at = datetime.fromisoformat(assigned_vehicle["last_position_at"]) + timedelta(minutes=1)
    moving = client.post(f"/api/v1/vehicles/{vehicle['id']}/positions", json={
        "latitude": midpoint[1], "longitude": midpoint[0], "speed_kph": 35, "heading": 25,
        "accuracy_m": 8, "recorded_at": first_ping_at.isoformat(), "source": "AIS-140-TEST-DEVICE",
    })
    assert moving.status_code == 200
    assert moving.json()["delivery"]["progress_percent"] > 0
    assert moving.json()["delivery"]["tracking_status"] == "ON_ROUTE"

    destination = route_coordinates[-1]
    arrived = client.post(f"/api/v1/vehicles/{vehicle['id']}/positions", json={
        "latitude": destination[1], "longitude": destination[0], "speed_kph": 0, "heading": 25,
        "accuracy_m": 8, "recorded_at": (first_ping_at + timedelta(minutes=1)).isoformat(), "source": "AIS-140-TEST-DEVICE",
    })
    assert arrived.status_code == 200
    assert arrived.json()["delivery"]["progress_percent"] == 100
    assert arrived.json()["delivery"]["status"] == "ARRIVED"
    assert arrived.json()["vehicle"]["active_delivery_id"] is None
    client.post("/api/v1/simulation/reset")


def test_confirmed_landslide_blocks_road_and_reroutes_medicine_delivery() -> None:
    client.post("/api/v1/simulation/reset")
    response = client.post("/api/v1/simulation/events/confirmed-landslide")
    assert response.status_code == 200
    payload = response.json()
    assert payload["disruption_summary"]["outcome"] == "REROUTED"
    assert payload["disruption_summary"]["blocked_segment_id"] == "SEG-004"
    assert "KALAKTANG" in payload["disruption_summary"]["route_path"]
    road = next(item for item in payload["map_snapshot"]["road_segments"] if item["id"] == "SEG-004")
    delivery = next(item for item in payload["overview"]["priority_deliveries"] if item["id"] == "DEL-1001")
    assert road["accessibility"] == "BLOCKED"
    assert delivery["status"] == "REROUTING"


def test_live_weather_refresh_updates_forecast_inputs_without_closing_roads(monkeypatch) -> None:
    from app.weather.open_meteo import WeatherReading, weather_service

    client.post("/api/v1/simulation/reset")

    def fake_fetch(roads):
        observed_at = datetime.now(UTC)
        return [
            WeatherReading(
                segment_id=road.id,
                precipitation_mm_24h=12.5 + index,
                current_precipitation_mm=0.4,
                precipitation_probability_max=78,
                weather_code=61,
                observed_at=observed_at,
            )
            for index, road in enumerate(roads)
        ]

    monkeypatch.setattr(weather_service, "fetch_for_segments", fake_fetch)
    response = client.post("/api/v1/weather/refresh")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "LIVE"
    assert len(payload["changed_entities"]) == 64
    road = next(item for item in payload["map_snapshot"]["road_segments"] if item["id"] == "SEG-004")
    assert road["data_mode"] == "LIVE"
    assert road["source"] == "Open-Meteo 24-hour forecast"
    assert road["rainfall_mm_24h"] > 0
    assert road["accessibility"] == "CAUTION"
    client.post("/api/v1/simulation/reset")


def test_weather_refresh_uses_persisted_values_when_provider_is_unavailable(monkeypatch) -> None:
    from app.weather.open_meteo import weather_service

    client.post("/api/v1/simulation/reset")

    def unavailable(_roads):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(weather_service, "fetch_for_segments", unavailable)
    response = client.post("/api/v1/weather/refresh")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "CACHED"
    assert payload["changed_entities"] == []
    assert "remains in use" in payload["message"]


def test_scheduled_weather_intelligence_is_private_and_generates_advisory_alerts(monkeypatch) -> None:
    from app.weather.open_meteo import WeatherReading, weather_service

    client.post("/api/v1/simulation/reset")
    monkeypatch.setenv("WORKER_TOKEN", "test-worker-token")
    unauthorized = client.post("/api/v1/internal/jobs/weather-intelligence")
    assert unauthorized.status_code == 401

    def severe_forecast(roads):
        observed_at = datetime.now(UTC)
        return [
            WeatherReading(
                segment_id=road.id,
                precipitation_mm_24h=110,
                current_precipitation_mm=8,
                precipitation_probability_max=95,
                weather_code=65,
                observed_at=observed_at,
            )
            for road in roads
        ]

    monkeypatch.setattr(weather_service, "fetch_for_segments", severe_forecast)
    refreshed = client.post(
        "/api/v1/internal/jobs/weather-intelligence",
        headers={"X-Worker-Token": "test-worker-token"},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] == "LIVE"
    snapshot = client.get("/api/v1/map/snapshot").json()
    alerts = client.get("/api/v1/alerts?language=en").json()["items"]
    automated_alerts = [alert for alert in alerts if alert["alert_type"] == "AUTOMATED_WEATHER_RISK"]
    assert automated_alerts
    assert all(road["accessibility"] != "BLOCKED" for road in snapshot["road_segments"])
    client.post("/api/v1/simulation/reset")


def test_field_location_context_combines_live_and_prototype_inputs(monkeypatch) -> None:
    from app.intelligence.location_context import location_context_service
    from app.weather.open_meteo import RouteWeatherPoint

    client.post("/api/v1/simulation/reset")
    monkeypatch.setattr(
        location_context_service,
        "assess",
        lambda latitude, longitude, store: __import__("app.domain.models", fromlist=["LocationContextResponse"]).LocationContextResponse(
            latitude=latitude,
            longitude=longitude,
            location_label="Shillong, Meghalaya, India",
            state="Meghalaya",
            district="East Khasi Hills",
            nearest_road={"id": "SEG-014", "name": "NH 6", "distance_km": 1.2, "accessibility": "OPEN", "condition": "GOOD", "data_mode": "SIMULATED"},
            nearest_facility={"id": "FAC-ML-SHL-HOSP", "name": "Shillong Regional Hospital", "type": "HOSPITAL", "distance_km": 2.1, "data_mode": "SIMULATED"},
            weather={"rainfall_mm_24h": 54, "precipitation_probability_max": 88, "elevation_m": 1496, "mode": "LIVE", "provider": "Open-Meteo"},
            predefined_context={"slope_degrees": 18, "road_condition": "GOOD", "landslide_susceptibility": 57, "flood_susceptibility": 35, "source": "NER prototype monitoring dataset", "mode": "SIMULATED"},
            incident_context={"nearby_count": 0, "radius_km": 25, "incident_ids": [], "mode": "LIVE_OPERATIONAL_STATE"},
            ml_assessment={"status": "AVAILABLE", "model_version": "test", "risk_probability": .42, "risk_band": "MODERATE", "predicted_delay_minutes": 36, "data_mode": "SYNTHETIC"},
            assessed_at=datetime.now(UTC),
        ),
    )
    response = client.get("/api/v1/locations/context?latitude=25.5788&longitude=91.8933")
    assert response.status_code == 200
    context = response.json()
    assert context["state"] == "Meghalaya"
    assert context["weather"]["mode"] == "LIVE"
    assert context["predefined_context"]["mode"] == "SIMULATED"
    assert context["ml_assessment"]["risk_probability"] == .42

    report = client.post("/api/v1/field-reports", json={
        "incident_type": "LANDSLIDE",
        "severity": "WARNING",
        "reported_accessibility": "CAUTION",
        "latitude": 25.5788,
        "longitude": 91.8933,
        "description": "Loose soil and falling stones observed beside the uphill carriageway.",
        "reporter_name": "Field Officer",
        "context_snapshot": context,
    })
    assert report.status_code == 200
    incident = report.json()["map_snapshot"]["incidents"][0]
    assert incident["context_snapshot"]["state"] == "Meghalaya"
    district_login = TestClient(app).post("/api/v1/auth/login", json={"username": "district@ner.gov.in", "password": "DistrictDemo@2026"}).json()
    district_review = TestClient(app).post(
        f"/api/v1/incidents/{incident['id']}/verification",
        headers={"Authorization": f"Bearer {district_login['access_token']}"},
        json={"decision": "DOWNGRADE"},
    )
    assert district_review.status_code == 200
    client.post("/api/v1/simulation/reset")


def test_authenticated_operations_websocket_receives_field_report_event() -> None:
    client.post("/api/v1/simulation/reset")
    token = admin_login.json()["access_token"]
    with client.websocket_connect(f"/api/v1/ws/operations?token={token}") as websocket:
        connected = websocket.receive_json()
        assert connected["type"] == "CONNECTED"
        response = client.post("/api/v1/field-reports", json={
            "incident_type": "ROAD_DAMAGE",
            "severity": "WARNING",
            "reported_accessibility": "PARTIAL",
            "latitude": 25.5788,
            "longitude": 91.8933,
            "description": "Road shoulder failure has reduced the usable carriageway to one lane.",
            "reporter_name": "Field Officer",
            "context_snapshot": {"district": "East Khasi Hills", "state": "Meghalaya"},
        })
        assert response.status_code == 200
        event = websocket.receive_json()
        assert event["type"] == "FIELD_REPORT_SUBMITTED"
        assert event["district"] == "East Khasi Hills"
        assert response.json()["changed_entities"][0] in event["changed_entities"]
    client.post("/api/v1/simulation/reset")


def test_offline_field_report_sync_is_idempotent() -> None:
    client.post("/api/v1/simulation/reset")
    payload = {
        "client_report_id": "OFFLINE-test-report-0001",
        "incident_type": "ROAD_DAMAGE",
        "severity": "WARNING",
        "reported_accessibility": "PARTIAL",
        "latitude": 25.5788,
        "longitude": 91.8933,
        "description": "Road shoulder failure has reduced the usable carriageway to one lane.",
        "context_snapshot": {"district": "East Khasi Hills", "state": "Meghalaya"},
    }

    first = client.post("/api/v1/field-reports", json=payload)
    second = client.post("/api/v1/field-reports", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["event"] == "field-report-already-synchronized"
    incident_id = first.json()["changed_entities"][0]
    matching = [item for item in second.json()["map_snapshot"]["incidents"] if item["id"] == incident_id]
    assert len(matching) == 1
    client.post("/api/v1/simulation/reset")


def test_field_evidence_is_stored_and_requires_authentication() -> None:
    client.post("/api/v1/simulation/reset")
    report_id = f"OFFLINE-evidence-{uuid4()}"
    tiny_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
    submitted = client.post("/api/v1/field-reports", json={
        "client_report_id": report_id,
        "incident_type": "FLOODING",
        "severity": "WARNING",
        "reported_accessibility": "CAUTION",
        "latitude": 25.5788,
        "longitude": 91.8933,
        "description": "Standing water is covering part of the uphill carriageway near the bridge.",
        "context_snapshot": {"district": "East Khasi Hills", "state": "Meghalaya"},
        "photo_data_url": tiny_png,
    })
    assert submitted.status_code == 200
    incident = submitted.json()["map_snapshot"]["incidents"][0]
    evidence_path = incident["photo_data_url"]
    assert evidence_path.startswith("/api/v1/evidence/EVD-")

    unauthenticated = TestClient(app).get(evidence_path)
    assert unauthenticated.status_code == 401
    evidence = client.get(evidence_path)
    assert evidence.status_code == 200
    assert evidence.headers["content-type"] == "image/png"
    assert evidence.content.startswith(b"\x89PNG")
    client.post("/api/v1/simulation/reset")


def test_gps_position_ingestion_updates_vehicle_and_records_history() -> None:
    client.post("/api/v1/simulation/reset")
    registered = register_test_vehicle()
    vehicle_id = registered["id"]
    recorded_at = datetime.now(UTC) + timedelta(seconds=1)
    response = client.post(
        f"/api/v1/vehicles/{vehicle_id}/positions",
        json={
            "latitude": 26.7104,
            "longitude": 92.8012,
            "speed_kph": 38.5,
            "heading": 28,
            "accuracy_m": 7.2,
            "recorded_at": recorded_at.isoformat(),
            "source": "AIS-140-TEST-DEVICE",
        },
    )
    assert response.status_code == 200
    vehicle = response.json()["vehicle"]
    telemetry = response.json()["telemetry"]
    assert vehicle["data_mode"] == "LIVE"
    assert vehicle["source"] == "AIS-140-TEST-DEVICE"
    assert vehicle["latitude"] == 26.7104
    assert vehicle["position_accuracy_m"] == 7.2
    assert telemetry["vehicle_id"] == vehicle_id
    assert telemetry["motion_state"] == "MOVING"
    assert telemetry["position_count"] >= 1
    assert telemetry["route_deviation_km"] is not None
    assert telemetry["on_planned_route"] is True

    history = client.get(f"/api/v1/vehicles/{vehicle_id}/positions").json()["positions"]
    assert history[0]["vehicle_id"] == vehicle_id
    assert history[0]["latitude"] == 26.7104
    client.post("/api/v1/simulation/reset")


def test_fleet_telemetry_detects_route_deviation() -> None:
    client.post("/api/v1/simulation/reset")
    registered = register_test_vehicle()
    vehicle_id = registered["id"]
    response = client.post(
        f"/api/v1/vehicles/{vehicle_id}/positions",
        json={
            "latitude": 24.817,
            "longitude": 93.9368,
            "speed_kph": 41,
            "recorded_at": (datetime.now(UTC) + timedelta(seconds=2)).isoformat(),
            "source": "AIS-140-TEST-DEVICE",
        },
    )
    assert response.status_code == 200
    telemetry = response.json()["telemetry"]
    assert telemetry["on_planned_route"] is False
    assert telemetry["route_deviation_km"] > 8
    assert telemetry["estimated_delivery_delay_minutes"] > 0
    snapshot = client.get("/api/v1/map/snapshot").json()
    tracked = next(item for item in snapshot["vehicle_telemetry"] if item["vehicle_id"] == vehicle_id)
    assert tracked["motion_state"] == "MOVING"
    assert tracked["track"]["coordinates"]
    client.post("/api/v1/simulation/reset")


def test_gps_ingestion_rejects_stale_and_out_of_region_positions() -> None:
    client.post("/api/v1/simulation/reset")
    registered = register_test_vehicle()
    vehicle_id = registered["id"]
    snapshot = client.get("/api/v1/map/snapshot").json()
    latest = next(vehicle for vehicle in snapshot["vehicles"] if vehicle["id"] == vehicle_id)["last_position_at"]
    stale = client.post(
        f"/api/v1/vehicles/{vehicle_id}/positions",
        json={"latitude": 26.7, "longitude": 92.8, "recorded_at": latest},
    )
    assert stale.status_code == 409

    outside = client.post(
        f"/api/v1/vehicles/{vehicle_id}/positions",
        json={"latitude": 19.0, "longitude": 92.8, "recorded_at": (datetime.now(UTC) + timedelta(seconds=2)).isoformat()},
    )
    assert outside.status_code == 422


def test_live_routing_uses_provider_geometry_and_rejects_confirmed_closure(monkeypatch) -> None:
    from app.domain.models import RoadAccessibility
    from app.routing.osrm_adapter import OsrmRoute
    from app.routing.service import route_planning_service
    from app.seed.store import store
    from app.weather.open_meteo import RouteWeatherPoint

    client.post("/api/v1/simulation/reset")

    def geometry(segment_ids):
        points = []
        for segment_id in segment_ids:
            segment = next(item for item in store.roads if item.id == segment_id)
            points.extend(segment.geometry.coordinates)
        return points

    monkeypatch.setattr(route_planning_service.external, "fetch_routes", lambda _source, _destination: [
        OsrmRoute(425700, 21960, geometry(["SEG-001", "SEG-002", "SEG-003", "SEG-004", "SEG-005", "SEG-006", "SEG-007"]), ["NH 27", "NH 15", "NH 13", "Sela Road"]),
        OsrmRoute(508700, 23400, geometry(["SEG-008", "SEG-009", "SEG-010", "SEG-011", "SEG-012", "SEG-013", "SEG-005", "SEG-006", "SEG-007"]), ["NH 15", "Kalaktang Road", "Rupa Road", "Sela Road"]),
    ])
    monkeypatch.setattr(route_planning_service.weather, "fetch_for_coordinates", lambda coordinates: [
        RouteWeatherPoint(precipitation_mm_24h=36, precipitation_probability_max=82, elevation_m=900, observed_at=datetime.now(UTC)) for _ in coordinates
    ])

    blocked = next(item for item in store.roads if item.id == "SEG-004")
    blocked.accessibility = RoadAccessibility.BLOCKED
    response = client.post("/api/v1/routes/plan", json={
        "source_facility_id": "FAC-GHY-MED",
        "destination_facility_id": "FAC-TAW-HOSP",
        "preference": "SAFETY_FIRST",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["routing_status"] == "LIVE"
    assert payload["routing_source"] == "OSRM / OpenStreetMap"
    assert len(payload["routes"]) == 1
    assert "SEG-004" not in payload["routes"][0]["segment_ids"]
    assert "SEG-010" in payload["routes"][0]["segment_ids"]
    assert payload["routes"][0]["geometry"]["coordinates"]
    assert payload["routes"][0]["intelligence_segments"]
    assert all(section["accessibility"] != "BLOCKED" for section in payload["routes"][0]["intelligence_segments"])
    client.post("/api/v1/simulation/reset")


def test_location_search_and_arbitrary_ner_route(monkeypatch) -> None:
    from app.domain.models import LocationSearchResult
    from app.routing.geocoding import geocoding_service
    from app.routing.osrm_adapter import OsrmRoute
    from app.routing.service import route_planning_service
    from app.weather.open_meteo import RouteWeatherPoint

    monkeypatch.setattr(geocoding_service, "search", lambda query: [
        LocationSearchResult(id="node-1", label=f"{query}, Meghalaya, India", latitude=25.5788, longitude=91.8933, state="Meghalaya", district="East Khasi Hills")
    ])
    search = client.get("/api/v1/locations/search?q=Shillong")
    assert search.status_code == 200
    assert search.json()[0]["state"] == "Meghalaya"

    monkeypatch.setattr(route_planning_service.external, "fetch_routes", lambda source, destination: [
        OsrmRoute(193000, 16200, [source, [92.4, 25.9], destination], ["NH 6", "NH 27"])
    ])
    monkeypatch.setattr(route_planning_service.weather, "fetch_for_coordinates", lambda coordinates: [
        RouteWeatherPoint(precipitation_mm_24h=58, precipitation_probability_max=91, elevation_m=1200 + index * 80, observed_at=datetime.now(UTC))
        for index, _ in enumerate(coordinates)
    ])
    response = client.post("/api/v1/routes/plan", json={
        "source_location": {"label": "Shillong, Meghalaya", "latitude": 25.5788, "longitude": 91.8933},
        "destination_location": {"label": "Silchar, Assam", "latitude": 24.8333, "longitude": 92.7789},
        "preference": "BALANCED",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["routing_status"] == "LIVE"
    assert payload["routes"][0]["path"][0] == "Shillong, Meghalaya"
    assert payload["routes"][0]["path"][-1] == "Silchar, Assam"
    assert payload["routes"][0]["distance_km"] == 193
    assert payload["routes"][0]["risk_coverage_percent"] == 100
    assert payload["routes"][0]["ml_risk_probability"] is not None
    assert payload["routes"][0]["live_rainfall_mm_24h"] == 58
    sections = payload["routes"][0]["intelligence_segments"]
    assert len(sections) == 2
    assert all(section["ml_risk_probability"] is not None for section in sections)
    assert all(section["rainfall_mm_24h"] == 58 for section in sections)
    assert all(section["geometry"]["coordinates"] for section in sections)
