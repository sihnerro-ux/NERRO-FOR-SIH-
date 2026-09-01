from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.domain.models import SimulationResponse, SystemStatus
from app.seed.store import store

router = APIRouter()


@router.get("/system/status", response_model=SystemStatus)
def system_status() -> SystemStatus:
    return SystemStatus(
        status="operational",
        service="NER Logistics API",
        data_mode="SIMULATED",
        generated_at=datetime.now(UTC),
        sources=[
            {"name": "Pilot road network", "status": "available", "mode": "SIMULATED"},
            {"name": "GPS simulator", "status": "available", "mode": "SIMULATED"},
            {"name": "Weather adapter", "status": "available", "mode": "SIMULATED"},
        ],
    )


@router.get("/overview")
def overview():
    return store.overview()


@router.get("/map/snapshot")
def map_snapshot():
    return store.map_snapshot()


@router.post("/simulation/reset", response_model=SimulationResponse)
def reset_simulation() -> SimulationResponse:
    store.reset()
    return SimulationResponse(
        event="reset",
        message="Demo state restored to the baseline scenario.",
        changed_entities=[],
        overview=store.overview(),
        map_snapshot=store.map_snapshot(),
    )


@router.post("/simulation/events/{event_name}", response_model=SimulationResponse)
def simulation_event(event_name: str) -> SimulationResponse:
    if event_name != "heavy-rain":
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_SIMULATION_EVENT", "message": "Unknown simulation event."})
    changed = store.apply_heavy_rain()
    return SimulationResponse(
        event=event_name,
        message="Heavy rainfall applied to the Dirang-Sela corridor.",
        changed_entities=changed,
        overview=store.overview(),
        map_snapshot=store.map_snapshot(),
    )

