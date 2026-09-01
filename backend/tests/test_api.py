from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_overview_and_map_share_pilot_state() -> None:
    client.post("/api/v1/simulation/reset")
    overview = client.get("/api/v1/overview").json()
    snapshot = client.get("/api/v1/map/snapshot").json()
    assert overview["data_mode"] == "SIMULATED"
    assert overview["metrics"]["active_vehicles"] == 2
    assert len(snapshot["road_segments"]) == 7
    assert any(item["destination_name"] == "Tawang District Hospital" for item in overview["priority_deliveries"])


def test_heavy_rain_event_raises_risk() -> None:
    client.post("/api/v1/simulation/reset")
    response = client.post("/api/v1/simulation/events/heavy-rain")
    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["metrics"]["high_risk_segments"] == 2
    assert payload["overview"]["priority_deliveries"][0]["status"] == "AT_RISK"

