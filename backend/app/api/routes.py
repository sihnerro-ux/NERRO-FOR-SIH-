from datetime import UTC, datetime
import logging
import os
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response, WebSocket, WebSocketDisconnect

from app.auth.security import create_access_token, current_user, decode_access_token, require_roles
from app.auth.service import auth_service
from app.domain.models import AlertAcknowledgementRequest, AnalyticsResponse, AuthUser, DeliveryCreateRequest, DeliveryCreateResponse, DeliveryVehicleAssignmentRequest, DriverJourneyActionRequest, DriverJourneyResponse, FieldIncidentReportRequest, IncidentVerificationRequest, LocationContextResponse, LocationSearchResult, LoginRequest, RoutePlanRequest, RoutePlanResponse, SimulationResponse, SystemStatus, TokenResponse, UserRole, VehiclePositionRequest, VehiclePositionResponse, VehicleRegistrationRequest, VehicleRegistrationResponse, WeatherRefreshResponse
from app.domain.models import OperationalDataImportRequest, OperationalDataImportResponse
from app.db.repository import operational_repository
from app.evidence import evidence_storage
from app.intelligence.model_adapter import model_adapter
from app.intelligence.location_context import location_context_service
from app.intelligence.data_import import parse_operational_import
from app.routing.service import route_planning_service
from app.routing.geocoding import geocoding_service
from app.seed.store import store
from app.weather.open_meteo import weather_service
from app.realtime import operations_hub

router = APIRouter()
logger = logging.getLogger(__name__)


def require_worker_token(x_worker_token: str = Header(default="")) -> None:
    expected = os.getenv("WORKER_TOKEN", "")
    if not expected or not secrets.compare_digest(x_worker_token, expected):
        raise HTTPException(status_code=401, detail={"code": "INVALID_WORKER_TOKEN", "message": "Worker authentication failed."})


@router.websocket("/ws/operations")
async def operations_stream(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "")
    try:
        payload = decode_access_token(token)
        user = auth_service.get_user(payload.get("sub", ""))
        if user is None:
            await websocket.close(code=4401, reason="Authenticated user not found")
            return
    except HTTPException:
        await websocket.close(code=4401, reason="Invalid or expired access token")
        return
    await operations_hub.connect(websocket, user)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        operations_hub.disconnect(websocket)


@router.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    user = auth_service.authenticate(request.username, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Username or password is incorrect."})
    token, expires = create_access_token(user)
    return TokenResponse(access_token=token, expires_in_seconds=expires, user=user)


@router.get("/auth/me", response_model=AuthUser)
def auth_me(user: AuthUser = Depends(current_user)) -> AuthUser:
    return user


@router.get("/system/status", response_model=SystemStatus)
def system_status(_user: AuthUser = Depends(current_user)) -> SystemStatus:
    return SystemStatus(
        status="operational",
        service="NER Logistics API",
        data_mode="SIMULATED",
        generated_at=datetime.now(UTC),
        sources=[
            {"name": "Pilot road network", "status": "available", "mode": "SIMULATED"},
            {"name": "GPS ingestion gateway", "status": "available", "mode": "LIVE_ON_DEMAND"},
            {"name": "Open-Meteo weather adapter", "status": "available", "mode": "LIVE_ON_DEMAND"},
            {"name": "OSRM road-network adapter", "status": "available", "mode": "EXTERNAL_ON_DEMAND"},
            {"name": "NER place-search adapter", "status": "available", "mode": "USER_TRIGGERED_CACHED"},
            {"name": "Operational database", "status": "available", "mode": operational_repository.backend.upper()},
            {"name": "Real-time event transport", "status": "available", "mode": operations_hub.mode},
            {"name": f"ML model {model_adapter.version}", "status": model_adapter.status.lower(), "mode": f"{model_adapter.data_mode}_ADVISORY"},
        ],
    )


@router.get("/overview")
def overview(_user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.FIELD_OFFICER, UserRole.LOGISTICS_OPERATOR, UserRole.DISTRICT_AUTHORITY, UserRole.VIEWER))):
    return store.overview()


@router.get("/map/snapshot")
def map_snapshot(_user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.FIELD_OFFICER, UserRole.LOGISTICS_OPERATOR, UserRole.DISTRICT_AUTHORITY, UserRole.VIEWER))):
    return store.map_snapshot()


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(_user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.LOGISTICS_OPERATOR, UserRole.DISTRICT_AUTHORITY, UserRole.VIEWER))) -> AnalyticsResponse:
    return store.analytics()


@router.get("/intelligence/status")
def intelligence_status(_user: AuthUser = Depends(current_user)) -> dict[str, object]:
    return {
        "status": model_adapter.status,
        "detail": model_adapter.detail,
        "mode": "ADVISORY_ONLY",
        "version": model_adapter.version,
        "data_mode": model_adapter.data_mode,
        "can_block_roads": False,
    }


@router.post("/weather/refresh", response_model=WeatherRefreshResponse)
def refresh_weather(background_tasks: BackgroundTasks, user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.DISTRICT_AUTHORITY))) -> WeatherRefreshResponse:
    refreshed_at = datetime.now(UTC)
    try:
        readings = weather_service.fetch_for_segments(store.roads)
        changed = store.apply_weather_readings(readings, actor=user.display_name)
        status = "LIVE"
        message = f"Live 24-hour precipitation forecast refreshed for {len(changed)} road segments."
    except Exception as exc:
        logger.warning("Live weather refresh failed; persisted values retained: %s", exc)
        changed = []
        status = "CACHED"
        message = "Weather provider is unavailable. Persisted road weather remains in use."
    background_tasks.add_task(operations_hub.publish, "WEATHER_REFRESHED", changed, user.display_name, user.district)
    return WeatherRefreshResponse(
        status=status,
        provider=weather_service.provider,
        message=message,
        changed_entities=changed,
        overview=store.overview(),
        map_snapshot=store.map_snapshot(),
        refreshed_at=refreshed_at,
    )


@router.post("/internal/jobs/weather-intelligence", include_in_schema=False)
async def scheduled_weather_intelligence(_authorization: None = Depends(require_worker_token)) -> dict[str, object]:
    refreshed_at = datetime.now(UTC)
    try:
        readings = weather_service.fetch_for_segments(store.roads)
        changed = store.apply_weather_readings(readings, actor="Automated intelligence worker")
    except Exception as exc:
        logger.warning("Scheduled weather intelligence failed: %s", exc)
        return {"status": "CACHED", "changed_entities": [], "refreshed_at": refreshed_at.isoformat()}
    await operations_hub.publish("WEATHER_INTELLIGENCE_REFRESHED", changed, "Automated intelligence worker", None)
    return {"status": "LIVE", "changed_entities": changed, "refreshed_at": refreshed_at.isoformat()}


@router.get("/persistence/status")
def persistence_status(_user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN))) -> dict:
    spatial = operational_repository.spatial_capabilities()
    return {
        "status": "AVAILABLE",
        "backend": operational_repository.backend.upper(),
        "mode": "PERSISTENT",
        "entity_counts": operational_repository.entity_counts(),
        "spatial": spatial,
    }


@router.get("/audit/events")
def audit_events(limit: int = 50, _user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN))) -> dict:
    safe_limit = max(1, min(limit, 200))
    return {"events": operational_repository.recent_audit_events(safe_limit)}


@router.get("/alerts")
def alerts(language: str = "en", _user: AuthUser = Depends(current_user)) -> dict:
    hindi = {
        "WEATHER_RISK": ("मौसम जोखिम चेतावनी", "मौसम के कारण मार्ग जोखिम बढ़ा है। नवीनतम सड़क और फील्ड अपडेट देखें।"),
        "FIELD_REPORT": ("फील्ड रिपोर्ट सत्यापन की प्रतीक्षा में", "नई भू-स्थानांकित रिपोर्ट प्राप्त हुई है और अधिकृत सत्यापन की प्रतीक्षा में है।"),
        "INCIDENT_REVIEW": ("फील्ड रिपोर्ट समीक्षा अपडेट", "अधिकृत अधिकारी ने घटना रिपोर्ट की समीक्षा पूरी की है।"),
        "DELIVERY_ROUTE_REASSESSMENT": ("डिलीवरी मार्ग का पुनर्मूल्यांकन", "सड़क, मौसम, घटना और एमएल जोखिम के आधार पर डिलीवरी मार्ग दोबारा जांचा गया है।"),
        "DELIVERY_TRACKING": ("लाइव डिलीवरी ट्रैकिंग चेतावनी", "जीपीएस टेलीमेट्री के आधार पर डिलीवरी की स्थिति बदली है।"),
        "ROUTE_DISRUPTION": ("मार्ग बाधा चेतावनी", "सत्यापित बाधा के कारण प्रभावित डिलीवरी मार्ग अपडेट किया गया है।"),
        "PREDICTED_DISRUPTION": ("संभावित मार्ग बाधा", "मौसम और एमएल संकेतों ने बढ़ा हुआ मार्ग जोखिम दिखाया है।"),
    }
    requested = "hi" if language.casefold() == "hi" else "en"
    items = []
    for alert in store.alerts:
        item = alert.model_dump(mode="json")
        if requested == "hi":
            item["display_title"], item["display_message"] = hindi.get(alert.alert_type, ("संचालन चेतावनी", "नई संचालन जानकारी उपलब्ध है। विवरण के लिए संबंधित रिकॉर्ड देखें।"))
        else:
            item["display_title"], item["display_message"] = alert.title, alert.message
        item["language"] = requested
        item["channel"] = "IN_APP_REALTIME"
        items.append(item)
    return {"language": requested, "channel": "IN_APP_REALTIME", "items": items}


@router.get("/admin/overview")
def administration(_user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN))) -> dict:
    status = system_status(_user)
    spatial = operational_repository.spatial_capabilities()
    return {
        "generated_at": datetime.now(UTC),
        "users": auth_service.list_users(),
        "sources": status.sources,
        "persistence": {
            "backend": operational_repository.backend.upper(), "entity_counts": operational_repository.entity_counts(),
            "spatial": spatial,
        },
        "ml": intelligence_status(_user),
        "audit_events": operational_repository.recent_audit_events(40),
    }


@router.post('/admin/data/import', response_model=OperationalDataImportResponse)
def import_operational_data(
    request: OperationalDataImportRequest,
    background_tasks: BackgroundTasks,
    user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN)),
) -> OperationalDataImportResponse:
    try:
        roads, facilities, warnings = parse_operational_import(request)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail={'code': 'INVALID_OPERATIONAL_DATASET', 'message': str(exc)}) from exc
    result = store.import_operational_data(roads, facilities, actor=user.display_name, dry_run=request.dry_run)
    if not request.dry_run:
        background_tasks.add_task(operations_hub.publish, 'OPERATIONAL_DATA_IMPORTED', result['changed_entities'], user.display_name, user.district)
    return OperationalDataImportResponse(
        status='PREVIEW_VALID' if request.dry_run else 'APPLIED',
        filename=request.filename,
        source_name=request.source_name,
        dry_run=request.dry_run,
        warnings=warnings,
        processed_at=datetime.now(UTC),
        **result,
    )


@router.post("/vehicles/{vehicle_id}/positions", response_model=VehiclePositionResponse)
def ingest_vehicle_position(
    vehicle_id: str,
    position: VehiclePositionRequest,
    background_tasks: BackgroundTasks,
    user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.LOGISTICS_OPERATOR, UserRole.DRIVER)),
) -> VehiclePositionResponse:
    if user.role == UserRole.DRIVER:
        owned_vehicle = next((item for item in store.vehicles if item.id == vehicle_id and item.driver_user_id == user.id), None)
        if owned_vehicle is None:
            raise HTTPException(status_code=403, detail={"code": "DRIVER_VEHICLE_FORBIDDEN", "message": "This vehicle is not assigned to the authenticated driver."})
    try:
        vehicle, delivery, changed = store.apply_vehicle_position(vehicle_id, position, actor=user.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "VEHICLE_NOT_FOUND", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "STALE_POSITION", "message": str(exc)}) from exc
    except OverflowError as exc:
        raise HTTPException(status_code=422, detail={"code": "OUTSIDE_OPERATIONAL_BOUNDARY", "message": str(exc)}) from exc
    background_tasks.add_task(operations_hub.publish, "GPS_POSITION_RECEIVED", changed, user.display_name, None)
    return VehiclePositionResponse(vehicle=vehicle, telemetry=store.vehicle_telemetry(vehicle.id), delivery=delivery, changed_entities=changed, received_at=datetime.now(UTC))


@router.post("/vehicles", response_model=VehicleRegistrationResponse, status_code=201)
def register_vehicle(
    request: VehicleRegistrationRequest,
    background_tasks: BackgroundTasks,
    user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.LOGISTICS_OPERATOR, UserRole.DRIVER)),
) -> VehicleRegistrationResponse:
    try:
        if user.role == UserRole.DRIVER:
            request = request.model_copy(update={"active_delivery_id": None})
        vehicle = store.register_vehicle(
            request,
            actor=user.display_name,
            driver_user_id=user.id if user.role == UserRole.DRIVER else None,
            driver_name=user.display_name if user.role == UserRole.DRIVER else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "DELIVERY_NOT_FOUND", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "REGISTRATION_CONFLICT", "message": str(exc)}) from exc
    except OverflowError as exc:
        raise HTTPException(status_code=422, detail={"code": "OUTSIDE_OPERATIONAL_BOUNDARY", "message": str(exc)}) from exc
    background_tasks.add_task(operations_hub.publish, "VEHICLE_REGISTERED", [vehicle.id], user.display_name, None)
    return VehicleRegistrationResponse(vehicle=vehicle, telemetry=store.vehicle_telemetry(vehicle.id), registered_at=datetime.now(UTC))


@router.get("/driver/journey", response_model=DriverJourneyResponse)
def driver_journey(user: AuthUser = Depends(require_roles(UserRole.DRIVER))) -> DriverJourneyResponse:
    vehicle, delivery, telemetry, snapshot = store.driver_journey(user.id)
    if vehicle is None:
        message = "Register this device with a live GPS position to enter the dispatch pool."
    elif delivery is None:
        message = "Vehicle connected. Waiting for the logistics control room to assign a delivery."
    else:
        message = "A new route instruction requires acknowledgement." if delivery.instruction_status == "PENDING" else "Journey telemetry is connected to the control room."
    completed = next((item for item in store.deliveries if vehicle and item.vehicle_id == vehicle.id and item.status == 'ARRIVED'), None)
    return DriverJourneyResponse(vehicle=vehicle, delivery=delivery, completed_delivery=completed, telemetry=telemetry, map_snapshot=snapshot, message=message, generated_at=datetime.now(UTC))


@router.post("/driver/journey/actions", response_model=DriverJourneyResponse)
def driver_journey_action(
    request: DriverJourneyActionRequest,
    background_tasks: BackgroundTasks,
    user: AuthUser = Depends(require_roles(UserRole.DRIVER)),
) -> DriverJourneyResponse:
    try:
        vehicle, delivery = store.apply_driver_journey_action(user.id, request.action, user.display_name, request.instruction_updated_at, request.description)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "DRIVER_VEHICLE_NOT_FOUND", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "DRIVER_ACTION_CONFLICT", "message": str(exc)}) from exc
    background_tasks.add_task(operations_hub.publish, f"DRIVER_{request.action}", [vehicle.id, delivery.id], user.display_name, None)
    current_vehicle, current_delivery, telemetry, snapshot = store.driver_journey(user.id)
    return DriverJourneyResponse(
        vehicle=current_vehicle, delivery=current_delivery, completed_delivery=delivery if request.action == 'COMPLETE_DELIVERY' else None, telemetry=telemetry, map_snapshot=snapshot,
        message={"START_JOURNEY": "Journey started.", "ACKNOWLEDGE_ROUTE": "Instruction acknowledged.", "COMPLETE_DELIVERY": "Delivery completed.", "PAUSE_JOURNEY": "Journey paused.", "RESUME_JOURNEY": "Journey resumed.", "REPORT_OBSTRUCTION": "Obstruction submitted at the last vehicle position for officer verification."}[request.action],
        generated_at=datetime.now(UTC),
    )


@router.get("/vehicles/{vehicle_id}/positions")
def vehicle_position_history(
    vehicle_id: str,
    limit: int = 100,
    _user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.LOGISTICS_OPERATOR, UserRole.DISTRICT_AUTHORITY)),
) -> dict:
    if not any(vehicle.id == vehicle_id for vehicle in store.vehicles):
        raise HTTPException(status_code=404, detail={"code": "VEHICLE_NOT_FOUND", "message": "Vehicle not found"})
    return {"vehicle_id": vehicle_id, "positions": operational_repository.vehicle_position_history(vehicle_id, max(1, min(limit, 500)))}


@router.post("/routes/plan", response_model=RoutePlanResponse)
def plan_route(request: RoutePlanRequest, _user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.LOGISTICS_OPERATOR, UserRole.DISTRICT_AUTHORITY))) -> RoutePlanResponse:
    """Return unique fastest, balanced and safety-first candidates."""
    return route_planning_service.plan(request, store.roads, store.incidents)


@router.post("/deliveries", response_model=DeliveryCreateResponse, status_code=201)
def create_delivery(request: DeliveryCreateRequest, background_tasks: BackgroundTasks, user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.LOGISTICS_OPERATOR))) -> DeliveryCreateResponse:
    try:
        delivery = store.create_delivery(request, user.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "DISPATCH_REFERENCE_NOT_FOUND", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "DISPATCH_CONFLICT", "message": str(exc)}) from exc
    changed = [delivery.id] + ([delivery.vehicle_id] if delivery.vehicle_id != "UNASSIGNED" else [])
    background_tasks.add_task(operations_hub.publish, "DELIVERY_DISPATCHED", changed, user.display_name, None)
    return DeliveryCreateResponse(delivery=delivery, changed_entities=changed, overview=store.overview(), map_snapshot=store.map_snapshot(), created_at=datetime.now(UTC))


@router.post("/deliveries/{delivery_id}/vehicle", response_model=DeliveryCreateResponse)
def assign_delivery_vehicle(delivery_id: str, request: DeliveryVehicleAssignmentRequest, background_tasks: BackgroundTasks, user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.LOGISTICS_OPERATOR))) -> DeliveryCreateResponse:
    try:
        delivery = store.assign_delivery_vehicle(delivery_id, request.vehicle_id, user.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "ASSIGNMENT_REFERENCE_NOT_FOUND", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "ASSIGNMENT_CONFLICT", "message": str(exc)}) from exc
    changed = [delivery.id, delivery.vehicle_id]
    background_tasks.add_task(operations_hub.publish, "DELIVERY_VEHICLE_ASSIGNED", changed, user.display_name, None)
    return DeliveryCreateResponse(delivery=delivery, changed_entities=changed, overview=store.overview(), map_snapshot=store.map_snapshot(), created_at=datetime.now(UTC))


@router.get("/locations/search", response_model=list[LocationSearchResult])
def search_ner_locations(
    q: str,
    _user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.LOGISTICS_OPERATOR, UserRole.DISTRICT_AUTHORITY)),
) -> list[LocationSearchResult]:
    if len(q.strip()) < 2:
        raise HTTPException(status_code=422, detail={"code": "QUERY_TOO_SHORT", "message": "Enter at least two characters."})
    try:
        return geocoding_service.search(q)
    except Exception as exc:
        logger.warning("NER location search failed: %s", exc)
        raise HTTPException(status_code=503, detail={"code": "GEOCODER_UNAVAILABLE", "message": "Location search is temporarily unavailable."}) from exc


@router.get("/locations/context", response_model=LocationContextResponse)
def location_context(
    latitude: float,
    longitude: float,
    _user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.FIELD_OFFICER, UserRole.DISTRICT_AUTHORITY)),
) -> LocationContextResponse:
    try:
        return location_context_service.assess(latitude, longitude, store)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "OUTSIDE_NER", "message": str(exc)}) from exc


@router.post("/field-reports", response_model=SimulationResponse)
def submit_field_report(report: FieldIncidentReportRequest, background_tasks: BackgroundTasks, user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.FIELD_OFFICER))) -> SimulationResponse:
    report = report.model_copy(update={"reporter_name": user.display_name})
    if report.photo_data_url and report.photo_data_url.startswith("data:"):
        try:
            evidence_id = evidence_storage.save(report.photo_data_url, user.display_name, report.client_report_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_EVIDENCE", "message": str(exc)}) from exc
        except Exception as exc:
            logger.exception("Evidence storage failed")
            raise HTTPException(status_code=503, detail={"code": "EVIDENCE_STORAGE_UNAVAILABLE", "message": "Photographic evidence could not be stored safely. The report was not submitted."}) from exc
        context_snapshot = dict(report.context_snapshot)
        context_snapshot["evidence_id"] = evidence_id
        report = report.model_copy(update={
            "photo_data_url": f"/api/v1/evidence/{evidence_id}",
            "context_snapshot": context_snapshot,
        })
    try:
        changed, created = store.submit_field_report(report)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "ROAD_NOT_FOUND", "message": str(exc)}) from exc
    district = str(report.context_snapshot.get("district") or "") or None
    if created:
        background_tasks.add_task(operations_hub.publish, "FIELD_REPORT_SUBMITTED", changed, user.display_name, district)
    return SimulationResponse(
        event="field-report-submitted" if created else "field-report-already-synchronized",
        message="Geo-tagged field report saved for control-room verification." if created else "This offline field report was already synchronized.",
        changed_entities=changed,
        overview=store.overview(),
        map_snapshot=store.map_snapshot(),
        disruption_summary=None,
    )


@router.get("/evidence/{evidence_id}")
def field_evidence(evidence_id: str, _user: AuthUser = Depends(current_user)) -> Response:
    evidence = evidence_storage.read(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail={"code": "EVIDENCE_NOT_FOUND", "message": "Evidence image was not found."})
    return Response(
        content=evidence.content,
        media_type=evidence.content_type,
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'inline; filename="{evidence.id}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/incidents/{incident_id}/verification", response_model=SimulationResponse)
def verify_field_report(incident_id: str, review: IncidentVerificationRequest, background_tasks: BackgroundTasks, user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.DISTRICT_AUTHORITY))) -> SimulationResponse:
    review = review.model_copy(update={"reviewer_name": user.display_name})
    if user.role == UserRole.DISTRICT_AUTHORITY:
        incident = next((item for item in store.incidents if item.id == incident_id), None)
        incident_district = str(incident.context_snapshot.get("district") or "") if incident else ""
        if not incident or not user.district or incident_district.casefold() != user.district.casefold():
            raise HTTPException(status_code=403, detail={"code": "DISTRICT_SCOPE_FORBIDDEN", "message": "This report is outside your assigned district."})
    incident_before_review = next((item for item in store.incidents if item.id == incident_id), None)
    incident_district = str(incident_before_review.context_snapshot.get("district") or "") if incident_before_review else ""
    try:
        changed, impacts = store.verify_field_report(incident_id, review)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "INCIDENT_NOT_FOUND", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "INCIDENT_ALREADY_REVIEWED", "message": str(exc)}) from exc
    background_tasks.add_task(operations_hub.publish, "FIELD_REPORT_REVIEWED", changed, user.display_name, incident_district or None)
    return SimulationResponse(
        event="field-report-reviewed",
        message="Field report review recorded.",
        changed_entities=changed,
        overview=store.overview(),
        map_snapshot=store.map_snapshot(),
        disruption_summary=({**impacts[0], "blocked_segment_id": impacts[0]["triggering_segment_id"]} if impacts else None),
        delivery_impacts=impacts,
    )


@router.post("/alerts/{alert_id}/acknowledgement", response_model=SimulationResponse)
def acknowledge_alert(alert_id: str, acknowledgement: AlertAcknowledgementRequest, user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN, UserRole.LOGISTICS_OPERATOR, UserRole.DISTRICT_AUTHORITY))) -> SimulationResponse:
    acknowledgement = acknowledgement.model_copy(update={"acknowledged_by": user.display_name})
    try:
        changed = store.acknowledge_alert(alert_id, acknowledgement)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "ALERT_ALREADY_ACKNOWLEDGED", "message": str(exc)}) from exc
    return SimulationResponse(
        event="alert-acknowledged",
        message="Alert acknowledged by control room.",
        changed_entities=changed,
        overview=store.overview(),
        map_snapshot=store.map_snapshot(),
        disruption_summary=None,
    )


@router.post("/simulation/reset", response_model=SimulationResponse)
def reset_simulation(_user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN))) -> SimulationResponse:
    store.reset()
    return SimulationResponse(
        event="reset",
        message="Demo state restored to the baseline scenario.",
        changed_entities=[],
        overview=store.overview(),
        map_snapshot=store.map_snapshot(),
        disruption_summary=None,
    )


@router.post("/simulation/events/{event_name}", response_model=SimulationResponse)
def simulation_event(event_name: str, _user: AuthUser = Depends(require_roles(UserRole.CONTROL_ROOM_ADMIN))) -> SimulationResponse:
    if event_name == "confirmed-landslide":
        changed, summary = store.apply_confirmed_landslide()
        return SimulationResponse(
            event=event_name,
            message="Confirmed Bhalukpong-Bomdila landslide applied and affected delivery evaluated.",
            changed_entities=changed,
            overview=store.overview(),
            map_snapshot=store.map_snapshot(),
            disruption_summary=summary,
        )
    if event_name != "heavy-rain":
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_SIMULATION_EVENT", "message": "Unknown simulation event."})
    changed = store.apply_heavy_rain()
    return SimulationResponse(
        event=event_name,
        message="Heavy rainfall applied to the Bhalukpong-Bomdila approach.",
        changed_entities=changed,
        overview=store.overview(),
        map_snapshot=store.map_snapshot(),
        disruption_summary=None,
    )
