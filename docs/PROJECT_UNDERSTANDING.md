# NER Smart Logistics and Accessibility Intelligence Platform

## Team Understanding and MVP Blueprint

**Problem Statement ID:** 26002  
**Organization:** Ministry of Development of North Eastern Region (MDoNER)  
**Category:** Software  
**Theme:** Transportation and Logistics

---

## 1. Problem in simple terms

The North Eastern Region of India has difficult terrain, extreme weather, limited transport connectivity, and frequent road disruptions. Landslides, floods, damaged roads, bridge problems, and traffic can delay medicines, food, agricultural produce, construction material, and emergency supplies.

Information about roads, weather, vehicles, and field incidents currently comes from different sources. Without a unified system, authorities cannot easily answer:

1. Can a vehicle travel from its current location to its destination now?
2. Which road segments are safe, risky, blocked, or unverified?
3. Which available route is safest for the cargo and current conditions?
4. Where are essential-goods vehicles, and will they arrive on time?
5. Which deliveries and communities will be affected by a disruption?

The project must solve this through a real-time GIS logistics control tower.

---

## 2. What we are building

We are building a **real-time, GIS-based logistics intelligence and accessibility control tower** for essential-goods transportation in North-East India.

The system combines:

- Road-network and bridge information
- Weather and rainfall observations
- Terrain and historical disruption data
- Live GPS vehicle positions
- Geo-tagged field reports and photographs
- Delivery, cargo, destination, and priority information

It uses these inputs to:

- Determine road accessibility
- Predict disruption risk for individual road segments
- Calculate safer routes
- Track active deliveries
- Detect affected vehicles
- Recalculate ETAs
- Generate alerts
- Reroute vehicles when possible
- Report when no feasible route exists

### One-sentence description

> An AI-powered GIS logistics control tower that predicts transport disruptions, monitors road accessibility, tracks essential-goods vehicles, and dynamically recommends safer routes across the North Eastern Region.

---

## 3. What we are not building

The MVP is not:

- A consumer navigation application
- A Google Maps replacement
- A static map containing decorative markers
- Only an AI/ML model
- A complete production platform for all eight NER states
- A system that invents alternative roads when none exist

AI is one component inside a larger operational logistics platform.

---

## 4. MVP geography and demonstration corridor

The MVP will focus on a representative Assam-Arunachal corridor:

> **Guwahati -> Tezpur -> Bhalukpong -> Bomdila -> Dirang -> Tawang**

The main demonstration delivery will be emergency medicines moving from a medical warehouse in Guwahati to a hospital in Tawang.

This corridor lets us demonstrate:

- Plains and mountainous terrain
- Long-distance essential-supply movement
- Remote destinations
- Weather-sensitive roads
- Landslide-prone road segments
- Limited alternative connectivity
- Emergency logistics decisions

The architecture will be designed to scale across NER, but the hackathon prototype will contain detailed data for the selected pilot corridor.

### Important routing principle

If the road graph contains a genuine alternative, the system recommends it. If every feasible road is blocked, the system must display **No road route currently available**. It must never fabricate a route.

---

## 5. Users and responsibilities

### 5.1 Control-room administrator

The administrator can:

- View the complete GIS dashboard
- Monitor roads, bridges, vehicles, deliveries, weather, and incidents
- Plan and compare routes
- View district/corridor connectivity
- Receive critical alerts
- Review and confirm field reports
- Apply audited manual overrides
- Monitor delays and supply-chain gaps

### 5.2 Field officer

The field officer can:

- Capture the current GPS location
- Report a landslide, flood, bridge issue, road damage, or traffic block
- Add severity, road status, description, and photograph
- Save a report without internet connectivity
- Synchronize pending reports when connectivity returns
- View nearby alerts and recently reported incidents

### 5.3 Driver

The driver can:

- View the assigned delivery
- View the approved route and next stop
- See the next high-risk segment
- Receive road-disruption alerts
- Receive and acknowledge an updated route
- View the updated ETA

For the MVP, these roles can be provided through one responsive role-based Progressive Web Application rather than three independently installed applications.

---

## 6. The road segment is the core operational object

A complete highway cannot have one risk or accessibility value. Roads must be divided into smaller segments.

Example:

```text
Guwahati-Tawang corridor
|- Segment 01: Guwahati -> Nagaon
|- Segment 02: Nagaon -> Tezpur
|- Segment 03: Tezpur -> Bhalukpong
|- Segment 04: Bhalukpong -> Bomdila
|- Segment 05: Bomdila -> Dirang
|- Segment 06: Dirang -> Sela
`- Segment 07: Sela -> Tawang
```

Each segment will contain:

- ID and road name
- GeoJSON/PostGIS line geometry
- Start and end node
- Direction and distance
- Road type and road condition
- Current accessibility state
- Traffic condition
- Rainfall and weather conditions
- Terrain slope and elevation
- Historical disruption count
- Landslide and flood probabilities
- Overall risk score
- Last verification time
- Source of the latest information
- Data-quality/confidence indicator

### Accessibility states

| State | Meaning |
|---|---|
| Open | Confirmed passable under normal operation |
| Caution | Passable, but care or reduced speed is required |
| High risk | Technically open but currently dangerous |
| Partially open | Restricted or controlled movement |
| Blocked | Cannot be used |
| Unknown | Information is missing or stale |

`Unknown` must not be treated as `Open`.

---

## 7. Major system modules

### 7.1 GIS control-tower dashboard

The main operational screen displays:

- Pilot-region map
- Colour-coded road segments
- Active and alternative routes
- Vehicle locations
- Incidents and weather warnings
- Hospitals, warehouses, and supply centres
- Active, delayed, and critical deliveries
- Live alerts
- Connectivity and accessibility indicators

Suggested road colours:

- Green: open/low risk
- Yellow: caution/moderate risk
- Orange: high risk
- Red: blocked
- Grey: unknown or stale information

### 7.2 Road-accessibility engine

The accessibility engine combines:

- Verified operational road status
- Recent field reports
- Weather observations
- Predicted disruption risk
- Traffic and road condition
- Age and reliability of the available data

It determines whether each segment is accessible, restricted, dangerous, blocked, or unverified.

### 7.3 Disruption-risk model

The ML component estimates the probability that a road segment will be disrupted.

Potential inputs:

- Current rainfall
- Rainfall in the previous 24 and 72 hours
- Terrain slope
- Elevation
- Soil moisture
- Road type and condition
- Historical landslides/floods
- Flood-zone indicator
- Traffic
- Recent field reports

Example output:

```text
Landslide probability:    78%
Flood probability:        12%
Road-damage probability:  31%
Overall disruption risk:  72%
Risk band:                HIGH
```

The first ML model will be a Random Forest classifier. Before reliable training data is available, the prototype can use an explainable deterministic risk formula with clearly labelled simulated inputs.

Every prediction must show its time, data freshness, main contributing factors, and model/rule version.

### 7.4 Risk-aware routing engine

The routing engine represents the road network as a directed weighted graph:

- Node: intersection, settlement, or facility connection
- Edge: road segment

Blocked segments are removed. Risky segments receive additional cost.

```text
Generalized route cost =
    travel time
  + disruption-risk penalty
  + traffic penalty
  + road-condition penalty
  + weather penalty
```

Cargo priority changes the weighting. Emergency medicine will prioritize safety and reliability more heavily than ordinary construction material.

The engine should return:

- Recommended route
- Fastest route
- Lowest-risk route
- Distance, ETA, and risk for each option
- Reasons for the recommendation
- No feasible route when appropriate

### 7.5 GPS vehicle tracking

For each active vehicle, the system tracks:

- Registration/vehicle ID
- Current coordinates
- Speed and direction
- Last GPS update
- Assigned delivery
- Selected route
- Route progress
- Current and predicted ETA
- Schedule status

The MVP will use a GPS simulator that moves vehicles along route geometry every few seconds.

### 7.6 Field incident reporting

A field report contains:

- Incident type
- GPS coordinates
- Timestamp
- Severity
- Reported road status
- Description
- Photograph
- Reporter
- Verification state
- Offline/synchronization state

The backend finds the nearest road segment and attaches the report to it.

### 7.7 Alert and rerouting engine

One confirmed incident should trigger several connected actions:

```text
Incident received
        |
        v
Match nearest road segment
        |
        v
Update accessibility state
        |
        v
Find active routes using that segment
        |
        v
Identify affected vehicles/deliveries
        |
        v
Recalculate route and ETA
        |
        v
Notify control room and driver
```

### 7.8 Delivery management

A delivery connects:

- Cargo and quantity
- Priority
- Source and destination
- Assigned vehicle and driver
- Selected route
- Planned and current ETA
- Current status
- Disruption and rerouting history

Initial cargo priority:

1. Emergency medicines and blood
2. Food and disaster-relief supplies
3. Agricultural produce
4. Construction materials

---

## 8. End-to-end data flow

```text
Weather API          GPS simulator          Field officer PWA
     |                    |                        |
     +--------------------+------------------------+
                          |
                          v
                    FastAPI backend
                          |
       +------------------+------------------+
       |                  |                  |
       v                  v                  v
 PostgreSQL/PostGIS   Risk engine       Routing engine
       |                  |                  |
       +------------------+------------------+
                          |
                          v
               Logistics/alert engine
                          |
                          v
                      WebSocket
                          |
             +------------+------------+
             v                         v
       Control dashboard          Driver view
```

REST APIs will handle queries and commands. WebSockets will push new GPS positions, incidents, alerts, road-state changes, ETA changes, and rerouting events.

---

## 9. Primary demonstration story

The complete demo will follow one medicine truck:

1. An administrator creates an emergency medicine delivery from Guwahati to Tawang.
2. The routing engine evaluates available routes.
3. The platform recommends a safe route and explains why.
4. A simulated truck begins moving and appears on the map.
5. Heavy rainfall develops on an upcoming mountainous segment.
6. The risk engine increases its predicted landslide probability.
7. The road changes from green to orange and an early-warning alert appears.
8. A field officer submits a geo-tagged landslide report.
9. The report is matched to the nearest road segment and confirmed.
10. The road becomes blocked and turns red.
11. The backend detects that the medicine delivery uses this segment.
12. If another route exists, the engine recommends it and recalculates the ETA.
13. If no route exists, the destination is marked temporarily inaccessible.
14. The control room and driver receive alerts.
15. The dashboard preserves a decision and event history.

This story demonstrates GIS, weather, prediction, routing, GPS, field reporting, alerts, delivery monitoring, and rerouting as one integrated system.

---

## 10. Selected technology stack

### Frontend

| Requirement | Technology |
|---|---|
| Application | React + TypeScript |
| Build system | Vite |
| Styling | Tailwind CSS |
| GIS | Leaflet + React-Leaflet |
| API state | TanStack Query |
| Local UI state | Zustand |
| Forms | React Hook Form + Zod |
| Charts | Recharts |
| Icons | Lucide React |
| Offline database | IndexedDB through Dexie |
| Installable application | PWA/service worker |

React/Vite is selected instead of Next.js because this is an authenticated, map-heavy operational SPA with a separate Python backend. It does not need SEO or server-rendered public pages.

### Backend

| Requirement | Technology |
|---|---|
| API | Python FastAPI |
| Validation | Pydantic |
| ORM | SQLAlchemy |
| Spatial ORM | GeoAlchemy2 |
| Migrations | Alembic |
| Realtime | Native WebSockets |
| Authentication | JWT with role claims |
| Image storage | Local for MVP, S3-compatible later |

### Data, AI, and routing

| Requirement | Technology |
|---|---|
| Database | PostgreSQL + PostGIS |
| Routing | NetworkX using Dijkstra/A* |
| Initial risk model | Scikit-learn Random Forest |
| Data exchange | REST JSON, GeoJSON, WebSocket events |
| Development environment | Docker Compose |

### Scale-up path

The MVP will use one FastAPI instance and an in-process WebSocket manager. A production deployment can add Redis/message streaming, worker processes, object storage, a dedicated routing server, and self-hosted regional map tiles.

---

## 11. Initial database entities

```text
users
vehicles
vehicle_positions
facilities
deliveries
routes
route_segments
road_segments
weather_observations
incidents
risk_predictions
alerts
offline_sync_operations
audit_events
```

### Spatial fields

| Entity | Geometry type |
|---|---|
| Vehicle position | Point |
| Facility | Point |
| Incident | Point |
| Road segment | LineString |
| Route | LineString |
| District/risk zone | Polygon |

WGS84/EPSG:4326 will be used for coordinates exchanged through the API.

---

## 12. Data-source and honesty rules

The MVP may use a mixture of curated, simulated, and user-generated data. The source must always be visible.

| Data | MVP source |
|---|---|
| Road geometry | Curated OpenStreetMap-derived GeoJSON |
| Facilities | Curated prototype locations |
| Weather | Simulated or live weather adapter |
| Terrain attributes | Seeded segment attributes initially |
| Historical incidents | Labelled prototype dataset |
| GPS | Backend simulator |
| Field incidents | Actual user submissions |
| Accessibility | Derived operational state |

Synthetic information must be labelled **Simulated**. It must not be presented as live government data.

Every important observation should include:

- Source
- Observation timestamp
- Server receipt timestamp
- Verification status
- Freshness/expiry threshold

---

## 13. Offline operation

The PWA will cache the application shell, field-report form, assigned delivery, recent alerts, and essential reference data.

When a field officer submits a report without connectivity:

```text
Create report
    |
    v
Store in IndexedDB with unique operation ID
    |
    v
Show Pending synchronization
    |
    v
Connectivity returns
    |
    v
Upload and validate on server
    |
    v
Mark synchronized locally
```

Unique idempotency keys will prevent duplicate reports after reconnection.

Offline application support does not automatically mean offline basemap tiles. Public OpenStreetMap tiles must not be bulk-downloaded. Production offline maps require an approved provider or self-hosted regional tile package.

---

## 14. Safety and decision rules

These rules are non-negotiable:

1. A verified blocked status overrides a low ML risk score.
2. Fresh, confirmed data overrides older observations.
3. Unknown or stale information is not considered safe.
4. The system must not fabricate an alternative route.
5. Predictions are advisory and must display probability and reasons.
6. Every operational state must include a source and timestamp.
7. Manual status overrides require a reason and audit record.
8. Emergency cargo changes route weighting but cannot use a confirmed blocked road.
9. The system must continue safely if weather or other external APIs fail.
10. Field reports must pass through verification states instead of silently replacing official status.

Suggested verification states:

- Unverified
- Officer verified
- Control-room confirmed
- Resolved
- Expired

---

## 15. MVP feature boundary

### Must work

- Interactive GIS map
- Modelled Assam-Arunachal corridor
- Colour-coded road accessibility
- Segment risk details and data freshness
- Route planning and comparison
- Simulated GPS vehicle movement
- Delivery monitoring
- Weather and incident layers
- Field incident submission
- Automatic road-state update
- Affected-vehicle detection
- Rerouting or no-route decision
- Updated ETA and delay
- Dashboard and driver alerts
- Basic offline report queue
- Initial multilingual framework

### Not part of the first MVP

- Complete NER road coverage
- Real vehicle GPS hardware
- Production government integrations
- Real SMS or WhatsApp alerts
- Satellite-image analysis
- Drone integration
- Turn-by-turn consumer navigation
- Production-scale historical datasets
- Fully validated models for every NER district
- Production cloud and disaster-recovery infrastructure

These may be proposed as future integrations, but must not be presented as already implemented.

---

## 16. Recommended implementation order

### Phase 1: Product and interface definition

- Confirm MVP scope
- Define users and permissions
- Define user journeys
- Define screens and navigation
- Finalize road and event data models

### Phase 2: Project foundation

- Create frontend and backend projects
- Configure database and migrations
- Add shared API conventions
- Seed pilot facilities and road graph

### Phase 3: GIS control tower

- Display the map and corridor
- Render road states
- Show facilities and incidents
- Add segment detail panels

### Phase 4: Routing

- Build the directed road graph
- Implement fastest and risk-aware routes
- Return alternatives and no-route decisions

### Phase 5: Deliveries and GPS

- Create deliveries
- Assign vehicles
- Simulate GPS movement
- Display live progress and ETA

### Phase 6: Incidents and realtime updates

- Submit field incidents
- Match nearest road segment
- Push updates through WebSockets
- Detect affected routes

### Phase 7: Risk intelligence

- Implement explainable baseline scoring
- Prepare training dataset
- Train/evaluate Random Forest
- Store prediction factors and model version

### Phase 8: Automatic rerouting and alerts

- Trigger rerouting after state changes
- Update ETAs
- Notify administrators and drivers
- Preserve the event timeline

### Phase 9: Offline and multilingual support

- Add IndexedDB queue
- Add synchronization and duplicate protection
- Add translation structure and priority languages

### Phase 10: Testing and presentation

- Verify the end-to-end demo
- Test no-route and stale-data cases
- Add failure handling
- Prepare deployment and presentation

---

## 17. Team workstreams

Suggested ownership for a four-person team:

| Workstream | Responsibility |
|---|---|
| Frontend/GIS | Dashboard, map layers, route visualization, responsive UI |
| Backend/data | FastAPI, authentication, PostGIS, APIs, WebSockets |
| Risk intelligence | Feature engineering, scoring, model training and evaluation |
| Routing/field app | Graph engine, GPS simulator, offline reporting, driver flow |

All team members share responsibility for integration, tests, documentation, demo data, and presentation accuracy.

---

## 18. Definition of MVP success

The prototype is successful when a reviewer can watch:

> An essential medicine vehicle moving on a GIS interface; road risks changing based on weather and field information; an upcoming disruption affecting the delivery; and the platform producing a defensible rerouting or accessibility decision with a revised ETA and alerts.

The strength of the project is the connected decision flow, not the number of screens.

---

## 19. Core innovation

Traditional route planning primarily optimizes distance and travel time. This platform treats road accessibility and disruption risk as dynamic variables. Routes can change based on weather, terrain, verified field reports, current road state, and predicted landslide or flood probability.

The platform combines three different kinds of intelligence:

- **Machine learning:** predicts disruption probability.
- **Graph algorithms:** calculate feasible risk-aware routes.
- **Rules and operational policy:** trigger alerts, prioritization, and verification workflows.

The system is therefore a logistics platform that uses AI responsibly, rather than claiming that AI performs every task.

