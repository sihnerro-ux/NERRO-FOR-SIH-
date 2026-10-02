from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.domain.models import VehicleRegistrationRequest, VehiclePositionRequest, RoadAccessibility
from app.seed.store import store, now_utc
from app.db.repository import operational_repository
from app.routing.engine import RoutingEngine


def test_driver_pause_hold_revision_and_report_flow(monkeypatch):
    subject = deepcopy(store)
    subject.reset(persist=False)
    saved = []
    monkeypatch.setattr(operational_repository, 'save_state', lambda payload, **kwargs: saved.append(deepcopy(payload)))
    vehicle = subject.register_vehicle(VehicleRegistrationRequest(
        registration='DEMO-TRANSITIONS', vehicle_class='RELIEF_TRUCK',
        latitude=26.1445, longitude=91.7362, source='DEMO_GPS_OVERRIDE',
    ), 'Driver', 'test-driver', 'Driver')
    assigned = subject.assign_delivery_vehicle('DEL-1001', vehicle.id, 'Dispatcher')
    delivery = next(item for item in subject.deliveries if item.id == assigned.id)
    with pytest.raises(RuntimeError):
        subject.apply_driver_journey_action('test-driver', 'START_JOURNEY', 'Driver')
    with pytest.raises(RuntimeError):
        subject.apply_driver_journey_action('test-driver', 'ACKNOWLEDGE_ROUTE', 'Driver', now_utc() - timedelta(days=1))
    subject.apply_driver_journey_action('test-driver', 'ACKNOWLEDGE_ROUTE', 'Driver', delivery.instruction_updated_at)
    subject.apply_driver_journey_action('test-driver', 'START_JOURNEY', 'Driver')
    subject.apply_driver_journey_action('test-driver', 'PAUSE_JOURNEY', 'Driver')
    subject.apply_vehicle_position(vehicle.id, VehiclePositionRequest(latitude=26.15, longitude=91.74, source='DEMO_GPS_OVERRIDE', recorded_at=now_utc()), 'Driver')
    assert delivery.status == 'PAUSED'
    assert delivery.journey_paused
    subject.apply_driver_journey_action('test-driver', 'RESUME_JOURNEY', 'Driver')
    subject.apply_driver_journey_action('test-driver', 'REPORT_OBSTRUCTION', 'Driver', description='Fallen trees block both lanes.')
    assert subject.incidents[0].verification == 'UNVERIFIED'
    assert subject.incidents[0].data_mode == 'SIMULATED'
    assert subject.incidents[0].context_snapshot['delivery_id'] == delivery.id
    assert any(event['event'] == 'DRIVER_REPORT_OBSTRUCTION' for event in saved[-1]['deliveries'][0]['journey_timeline'])
    original_plan = RoutingEngine.plan
    monkeypatch.setattr(RoutingEngine, 'plan', lambda *args: SimpleNamespace(routes=[], recommended_route_id=None))
    road = next(item for item in subject.roads if item.id in delivery.route_segment_ids)
    _, impacts = subject._reassess_deliveries_for_road(road, now_utc())
    assert any(item['outcome'] == 'NO_FEASIBLE_ROUTE' for item in impacts)
    assert delivery.status == 'HELD'
    subject.apply_driver_journey_action('test-driver', 'ACKNOWLEDGE_ROUTE', 'Driver', delivery.instruction_updated_at)
    subject.apply_vehicle_position(vehicle.id, VehiclePositionRequest(latitude=26.16, longitude=91.75, source='DEMO_GPS_OVERRIDE', recorded_at=now_utc()), 'Driver')
    assert delivery.status == 'HELD'
    for action in ['START_JOURNEY', 'RESUME_JOURNEY', 'COMPLETE_DELIVERY']:
        with pytest.raises(RuntimeError):
            subject.apply_driver_journey_action('test-driver', action, 'Driver')
    hold_version = delivery.instruction_updated_at
    monkeypatch.setattr(RoutingEngine, 'plan', original_plan)
    road = next(item for item in subject.roads if item.id == 'SEG-004')
    road.accessibility = RoadAccessibility.BLOCKED
    _, impacts = subject._reassess_deliveries_for_road(road, now_utc())
    assert delivery.instruction_type == 'REROUTE'
    assert delivery.instruction_status == 'PENDING'
    assert 'SEG-004' not in delivery.route_segment_ids
    with pytest.raises(RuntimeError):
        subject.apply_driver_journey_action('test-driver', 'ACKNOWLEDGE_ROUTE', 'Driver', hold_version)
    subject.apply_driver_journey_action('test-driver', 'ACKNOWLEDGE_ROUTE', 'Driver', delivery.instruction_updated_at)
    assert delivery.instruction_status == 'ACKNOWLEDGED'
    destination = delivery.route_geometry.coordinates[-1]
    subject.apply_vehicle_position(vehicle.id, VehiclePositionRequest(
        latitude=destination[1], longitude=destination[0], source='DEMO_GPS_OVERRIDE',
        recorded_at=now_utc() + timedelta(seconds=1), accuracy_m=10,
    ), 'Driver')
    assert delivery.tracking_status == 'AT_DESTINATION'
    assert delivery.status != 'ARRIVED'
    active_vehicle = next(item for item in subject.vehicles if item.id == vehicle.id)
    assert active_vehicle.active_delivery_id == delivery.id
    subject.apply_driver_journey_action('test-driver', 'COMPLETE_DELIVERY', 'Driver')
    assert delivery.status == 'ARRIVED'
    assert active_vehicle.active_delivery_id is None
    assert any(event['event'] == 'DRIVER_COMPLETE_DELIVERY' for event in delivery.journey_timeline)
