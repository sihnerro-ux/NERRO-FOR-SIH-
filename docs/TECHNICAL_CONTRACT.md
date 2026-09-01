# NER Logistics Control Tower

## Technical Contract for Implementation

This document locks the data language, API surface, realtime events, state transitions, and repository conventions used by the MVP. Changes to these contracts should be deliberate and reflected here.

---

## 1. System boundaries

```text
React PWA
|- REST client
|- WebSocket client
|- IndexedDB offline queue
`- Map renderer
        |
        v
FastAPI application
|- API layer
|- Application services
|- Accessibility policy
|- Risk service
|- Routing service
|- Alert service
|- Simulation service
`- Repository interfaces
        |
        +-- Seed/in-memory adapter (first runnable milestone)
        `-- PostgreSQL/PostGIS adapter (target persistence)
```

The frontend never reads the database directly. Business decisions stay in backend services rather than React components.

---

## 2. API conventions

- Base path: `/api/v1`
- JSON keys: `snake_case`
- IDs: stable prefixed strings such as `DEL-1001`, `VEH-001`, `SEG-001`
- Coordinates: GeoJSON order `[longitude, latitude]`
- Datetimes: ISO 8601 UTC strings
- Percentages in APIs: numbers from `0` to `100`
- Probabilities in model internals: numbers from `0` to `1`
- Pagination: `page`, `page_size`, `total`
- List filtering: query parameters
- Mutations return the updated resource and generated events where relevant
- Errors use a stable `code`, readable `message`, and optional `details`

Example error:

```json
{
  "error": {
    "code": "NO_FEASIBLE_ROUTE",
    "message": "No currently accessible road route was found.",
    "details": {
      "blocked_segments": ["SEG-006", "SEG-009"]
    }
  }
}
```

---

## 3. Core enumerations

```text
RoadAccessibility = OPEN | CAUTION | HIGH_RISK | PARTIAL | BLOCKED | UNKNOWN
RiskBand          = LOW | MODERATE | HIGH | CRITICAL | UNKNOWN
DataMode          = LIVE | SIMULATED | CACHED | UNAVAILABLE
Verification      = UNVERIFIED | OFFICER_VERIFIED | CONTROL_CONFIRMED | RESOLVED | EXPIRED
DeliveryStatus    = PLANNED | ASSIGNED | IN_TRANSIT | AT_RISK | DELAYED | REROUTING | ARRIVED | CANCELLED
VehicleStatus     = AVAILABLE | ASSIGNED | IN_TRANSIT | HOLDING | OFFLINE | MAINTENANCE
GpsFreshness      = LIVE | DELAYED | STALE | OFFLINE
AlertSeverity     = INFO | WARNING | CRITICAL
CargoPriority     = NORMAL | HIGH | CRITICAL
RoutePreference   = BALANCED | SAFETY_FIRST | FASTEST_FEASIBLE
```

---

## 4. Core resource shapes

### Road segment

```json
{
  "id": "SEG-006",
  "road_name": "Dirang-Sela Road",
  "from_node": "DIRANG",
  "to_node": "SELA",
  "geometry": { "type": "LineString", "coordinates": [] },
  "distance_km": 63.4,
  "accessibility": "HIGH_RISK",
  "risk_score": 78,
  "risk_band": "HIGH",
  "road_condition": "FAIR",
  "rainfall_mm_24h": 91,
  "slope_degrees": 31,
  "source": "Risk engine",
  "data_mode": "SIMULATED",
  "observed_at": "2026-09-01T14:32:00Z",
  "updated_at": "2026-09-01T14:36:00Z",
  "confidence": 82
}
```

### Vehicle

```json
{
  "id": "VEH-001",
  "registration": "AS-01-ER-2048",
  "vehicle_class": "REFRIGERATED_TRUCK",
  "status": "IN_TRANSIT",
  "latitude": 26.6528,
  "longitude": 92.7926,
  "speed_kph": 42,
  "heading": 34,
  "gps_freshness": "LIVE",
  "last_position_at": "2026-09-01T14:36:00Z",
  "active_delivery_id": "DEL-1001"
}
```

### Delivery

```json
{
  "id": "DEL-1001",
  "cargo_type": "EMERGENCY_MEDICINES",
  "cargo_description": "Vaccines and critical medicines",
  "quantity": 3.4,
  "quantity_unit": "tonnes",
  "priority": "CRITICAL",
  "source_facility_id": "FAC-GHY-MED",
  "destination_facility_id": "FAC-TAW-HOSP",
  "vehicle_id": "VEH-001",
  "status": "IN_TRANSIT",
  "progress_percent": 38,
  "planned_eta": "2026-09-01T18:40:00Z",
  "current_eta": "2026-09-01T18:40:00Z",
  "delay_minutes": 0,
  "route_id": "ROUTE-1001"
}
```

### Incident

```json
{
  "id": "INC-1001",
  "incident_type": "LANDSLIDE",
  "severity": "CRITICAL",
  "reported_accessibility": "BLOCKED",
  "verification": "UNVERIFIED",
  "location": { "type": "Point", "coordinates": [92.108, 27.267] },
  "matched_segment_id": "SEG-006",
  "description": "Debris across both lanes",
  "photo_url": null,
  "reported_by": "USR-OFFICER-01",
  "source": "Field report",
  "data_mode": "SIMULATED",
  "observed_at": "2026-09-01T14:32:00Z",
  "received_at": "2026-09-01T14:36:00Z"
}
```

### Alert

```json
{
  "id": "ALT-1001",
  "severity": "CRITICAL",
  "alert_type": "ROUTE_DISRUPTION",
  "title": "Medicine delivery route affected",
  "message": "A confirmed landslide blocks SEG-006.",
  "related_entity_type": "DELIVERY",
  "related_entity_id": "DEL-1001",
  "acknowledged": false,
  "created_at": "2026-09-01T14:36:05Z"
}
```

---

## 5. MVP REST endpoints

### System and overview

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Process health |
| GET | `/api/v1/system/status` | Mode, sources, freshness, WebSocket status |
| GET | `/api/v1/overview` | KPI cards, critical alerts, priority deliveries, connectivity |

### Roads, map, and facilities

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/map/snapshot` | GeoJSON roads plus incidents, vehicles, facilities, weather zones |
| GET | `/api/v1/road-segments` | Filterable road-segment list |
| GET | `/api/v1/road-segments/{id}` | Segment detail and risk factors |
| POST | `/api/v1/road-segments/{id}/override` | Audited administrator status override |
| GET | `/api/v1/facilities` | Warehouses, hospitals, and supply centres |

### Routing

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/routes/plan` | Return recommended/fastest/lowest-risk routes |
| POST | `/api/v1/routes/recalculate` | Replan from current vehicle position |
| GET | `/api/v1/routes/{id}` | Route geometry, segments, risk, and reasoning |

### Deliveries and fleet

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/deliveries` | Filterable delivery list |
| POST | `/api/v1/deliveries` | Create and optionally assign a delivery |
| GET | `/api/v1/deliveries/{id}` | Delivery detail and timeline |
| POST | `/api/v1/deliveries/{id}/dispatch-route` | Approve and send a proposed route |
| POST | `/api/v1/deliveries/{id}/cancel` | Cancel with reason |
| GET | `/api/v1/vehicles` | Fleet list |
| GET | `/api/v1/vehicles/{id}` | Vehicle, telemetry, and assignment |
| POST | `/api/v1/vehicles/{id}/positions` | Receive GPS position |

### Incidents

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/incidents` | Filterable incident list |
| POST | `/api/v1/incidents` | Submit online or synchronized field report |
| GET | `/api/v1/incidents/{id}` | Incident detail and timeline |
| POST | `/api/v1/incidents/{id}/verify` | Verify/reject and confirm matched segment |
| POST | `/api/v1/incidents/{id}/resolve` | Resolve with resulting road status |
| POST | `/api/v1/incidents/{id}/observations` | Add follow-up field evidence |

### Alerts and simulation

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/alerts` | Filterable alert list |
| POST | `/api/v1/alerts/{id}/acknowledge` | Record acknowledgement |
| POST | `/api/v1/simulation/reset` | Reset deterministic demo state |
| POST | `/api/v1/simulation/events/{event}` | Apply a named demo event |

---

## 6. Route planning request and response

Request:

```json
{
  "source_facility_id": "FAC-GHY-MED",
  "destination_facility_id": "FAC-TAW-HOSP",
  "cargo_type": "EMERGENCY_MEDICINES",
  "priority": "CRITICAL",
  "vehicle_class": "REFRIGERATED_TRUCK",
  "preference": "SAFETY_FIRST",
  "departure_at": null
}
```

Response:

```json
{
  "calculated_at": "2026-09-01T14:30:00Z",
  "data_mode": "SIMULATED",
  "recommended_route_id": "CANDIDATE-SAFE",
  "routes": [
    {
      "id": "CANDIDATE-SAFE",
      "label": "Recommended",
      "distance_km": 487,
      "eta_minutes": 840,
      "risk_score": 24,
      "blocked_segments": [],
      "high_risk_segments": [],
      "reason": "Lower weather and landslide exposure with an acceptable ETA.",
      "geometry": { "type": "LineString", "coordinates": [] }
    }
  ],
  "warnings": []
}
```

---

## 7. Realtime event envelope

WebSocket path: `/api/v1/ws/operations`

Every message uses:

```json
{
  "event_id": "EVT-1001",
  "event_type": "road_segment.updated",
  "occurred_at": "2026-09-01T14:36:05Z",
  "data_mode": "SIMULATED",
  "entity_id": "SEG-006",
  "payload": {}
}
```

Initial event types:

```text
vehicle.position_updated
vehicle.gps_freshness_changed
incident.created
incident.verified
incident.resolved
road_segment.risk_changed
road_segment.accessibility_changed
delivery.status_changed
delivery.eta_changed
route.proposed
route.dispatched
alert.created
alert.acknowledged
simulation.reset
```

Events update client caches; they do not require the frontend to duplicate business logic.

---

## 8. State transitions

### Incident

```text
UNVERIFIED
    |
    +--> OFFICER_VERIFIED --> CONTROL_CONFIRMED --> RESOLVED
    |                              |
    +------------------------------+
    |
    `--> EXPIRED
```

Invalid transitions return `409 CONFLICT`.

### Delivery

```text
PLANNED -> ASSIGNED -> IN_TRANSIT -> ARRIVED
                         |   |
                         |   +-> AT_RISK -> REROUTING -> IN_TRANSIT
                         |   `-> DELAYED -> IN_TRANSIT/ARRIVED
                         `------> CANCELLED (authorized exceptional action)
```

### Road accessibility policy

Precedence from strongest to weakest:

1. Active control-room confirmed closure/override
2. Recent officer-verified observation
3. Recent trusted external operational feed
4. Risk-engine prediction
5. Historical/default state

A verified `BLOCKED` state cannot be changed by an ML prediction.

---

## 9. Idempotency and offline synchronization

Field mutations accept `Idempotency-Key`.

The backend stores:

- Key
- User/device
- Request fingerprint
- Processing result
- Creation/expiry time

Repeating the same synchronized operation returns its original result instead of creating a duplicate. Reusing a key with different content returns `409 IDEMPOTENCY_CONFLICT`.

---

## 10. Repository layout

```text
frontend/
|- src/
|  |- app/
|  |- components/
|  |- features/
|  |- pages/
|  |- services/
|  |- stores/
|  |- types/
|  `- styles/
`- tests/

backend/
|- app/
|  |- api/
|  |- core/
|  |- domain/
|  |- repositories/
|  |- services/
|  |- routing/
|  |- risk/
|  |- realtime/
|  `- seed/
`- tests/

data/
|- geojson/
|- seed/
`- model/
```

Frontend features group UI and hooks by domain. Backend domain models do not import FastAPI or database implementations.

---

## 11. First implementation milestone

The first runnable slice must provide:

1. FastAPI health, overview, and map-snapshot endpoints.
2. Seeded pilot corridor, one medicine delivery, vehicles, incidents, alerts, and facilities.
3. React control-tower shell with overview KPIs.
4. GIS map displaying road states and vehicle/facility/incident markers.
5. Visible simulated-data and freshness indicators.
6. One deterministic simulation event that raises road risk.

Database persistence, authentication, full routing, and offline synchronization follow after this vertical slice is stable.

