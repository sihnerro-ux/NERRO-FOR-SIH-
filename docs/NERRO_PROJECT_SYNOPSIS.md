# NERRO — Smart Logistics and Accessibility Intelligence Platform

## A simple project synopsis for the team and SIH presentation

**Problem statement:** 26002  
**Organization:** Ministry of Development of North Eastern Region (MDoNER)  
**Category:** Software  
**Theme:** Transportation and Logistics  
**Project stage:** Working, integrated prototype  
**Scope:** The eight North Eastern states of India

**Document guide:** This synopsis is arranged into ten page-sized sections. When exported to a document, use A4 paper, 11–12-point text, normal margins and page breaks between sections. Actual page count depends on formatting. Descriptions distinguish implemented prototype functions from future production requirements.

---

## Page 1 — Project introduction and summary

### What is NERRO?

NERRO is a shared digital platform that helps authorities and logistics teams move essential supplies through North-East India. It brings maps, road reports, weather forecasts, vehicle locations and delivery information into one place.

In simple words, it helps a control room answer: “Which route can we use, what could go wrong, where is our vehicle, and what should we do if the road becomes blocked?”

The platform is designed around Assam, Arunachal Pradesh, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim and Tripura. Users can select an origin and destination in the NER operating area rather than being limited to one demonstration journey. A routable road connection and adequate provider data are still necessary; selecting two points does not guarantee that a usable road exists between them.

### Why this project matters

Medicines, food, agricultural produce, construction materials and emergency supplies depend on reliable transport. The problem statement describes a region where steep terrain, heavy rainfall, floods, landslides and infrastructure gaps can interrupt that transport.

A delayed ordinary parcel is inconvenient. A delayed medicine shipment can interrupt an essential service. NERRO therefore focuses on operational decisions, not only on drawing directions on a map.

### The central idea

An ordinary route calculation considers where a road goes and how long a journey might take. NERRO adds operational context: recent field reports, verified closures, rainfall forecasts, available terrain information and machine-learning risk estimates. It connects the selected route to a delivery, a vehicle and a responsible driver.

If conditions change, the control room can review the impact and communicate an updated instruction. If a feasible alternative cannot be found, the system should hold the journey instead of presenting a misleading route.

### One sentence for explaining the project

> NERRO helps logistics teams plan and monitor essential-supply journeys across North-East India by combining road maps, weather, field reports, GPS tracking and AI-assisted risk estimates.

The current application is a prototype of this workflow. It is not a certified navigation service, an official road-closure authority or a validated disaster-prediction system.

---

## Page 2 — The problem and the proposed solution

### What makes the problem difficult?

The challenge is not simply finding the shortest route. A road that appears short may be affected by rainfall, damage or a reported obstruction. In remote areas, information can arrive late because connectivity is weak. A driver, field officer and administrator may each know a different part of the situation.

Consider a medicine shipment travelling towards a remote hospital. The dispatcher knows the delivery priority. The driver knows the vehicle's position. A field officer has seen a landslide further ahead. A weather service predicts additional rain. Unless these pieces of information are connected, the dispatcher may continue using an outdated plan.

The problem statement calls for an integrated system to reduce this information gap. NERRO implements a prototype of that shared operational view.

### How NERRO responds

| Operational problem | NERRO's response |
|---|---|
| Road information is scattered | Display road segments, reports and their sources on a common map |
| Conditions change after planning | Refresh weather inputs and process newly reviewed incidents |
| The shortest road may be risky | Compare available candidates using time, predicted risk and delay |
| Dispatch cannot see the vehicle | Accept GPS positions for registered vehicles |
| A report arrives without context | Attach coordinates, description, evidence and verification state |
| A remote officer loses internet | Queue reports locally and synchronize when connectivity returns |
| Teams miss changed instructions | Generate alerts and require driver acknowledgement |
| The destination is cut off | Communicate a hold when no feasible candidate is found |

### What improvement do we expect?

The expected benefits are earlier awareness of disruptions, better coordination, more informed dispatch decisions and clearer accountability. These could help reduce avoidable detours and supply delays.

However, these are intended benefits, not measured results from a deployed regional service. We must not claim a particular percentage reduction in travel time, cost or disruption without a controlled pilot and supporting measurements.

### What NERRO cannot do by itself

Software cannot reopen a damaged bridge or create a road where none exists. It also cannot determine every local condition from rainfall alone. Its role is to organize evidence, estimate risk and support people making transport decisions. The quality of the result depends on the freshness, coverage and reliability of the available information.

---

## Page 3 — Users, separate panels and responsibilities

NERRO uses one application with role-based workspaces. Different users receive the screens and actions relevant to their responsibilities. Backend permission checks are important: hiding a button is not sufficient access control.

### Control-room administrator

The administrator sees the broad operational picture. This includes the map, deliveries, vehicles, incidents, alerts and analytics. Administrators review incoming reports and coordinate responses to disruptions. The administration area also supports controlled operational-data imports and inspection of source information and audit activity.

### Logistics operator

The logistics operator manages movement of supplies. The main tasks are choosing journey locations, comparing available routes, creating a delivery and assigning an available registered vehicle. The operator monitors journey progress and changing instructions. This role concentrates on dispatch rather than field-data collection.

### Field officer

The field officer's workspace focuses on reporting conditions. An officer can identify a location, describe an incident, provide its severity and reported accessibility, and attach photographic evidence through the reporting workflow. Reports can be associated with a monitored road where relevant, but reporting is not limited to the original pilot corridor.

If connectivity is unavailable, the officer can save a report locally for synchronization. A submitted report is evidence awaiting the appropriate review; it is not automatically a confirmed closure.

### Driver

The driver registers a vehicle and works with its assigned delivery. The driver can review and acknowledge instructions, start or pause the journey, share location, report an obstruction and confirm delivery handover.

The driver does not receive unrestricted control over everyone else's fleet. Driver API operations check vehicle ownership. A driver cannot release a safety hold simply by sending another GPS position.

### District authority and viewer

District-authority access supports district-related oversight and authorized review operations. A viewer receives read-oriented operational visibility. Not every dashboard should be assumed to provide complete district isolation: production deployment still requires a full permission and data-scope audit.

### Why separate workspaces matter

An officer working beside a damaged road needs a quick report form, not a large administration console. A driver needs a clear route instruction, not dataset-import tools. The administrator needs the combined picture. These focused workspaces reduce confusion while keeping everyone connected to the same underlying records.

---

## Page 4 — Main modules and the operational map

### Map and geographic information

The map is the main visual workspace. It can display monitored roads, incidents, facilities, bridge or crossing assets, vehicles and planned journey geometry. Layers let users control what is visible instead of placing every marker on top of every other marker.

The application uses geographic coordinates to connect these objects. Roads are represented as lines; vehicles and facilities usually appear as points; regional boundaries are represented as geographic areas. This is what GIS—Geographic Information System—means in this project: information linked to physical locations.

An important distinction is that a visible marker does not automatically represent a verified real asset. The prototype includes representative facilities and monitored-road records for demonstrations. Their source and simulated status must remain visible.

### Route planner

The planner lets an authorized user choose origin and destination locations through supported search and map-selection flows. It requests available road routes and evaluates the candidates using operational inputs. Users can select a preference such as safety first, balanced or fastest.

The system may return multiple candidates, but it must not promise two or three routes for every request. Some locations have only one suitable road connection. Sometimes the provider cannot return a route or all assessed candidates are unsuitable.

### Deliveries and fleet

The deliveries view connects cargo and priority with a destination, selected route, assigned vehicle and journey status. The fleet view shows registered vehicles and available telemetry, including position freshness and route-deviation information where applicable.

Fake vehicle movement is not required to demonstrate the interface. A separately labelled demo GPS mode exists for controlled testing, including when a tester is physically outside NER.

### Incidents, alerts and analytics

Incident review turns a field observation into a reviewed operational record. Alerts draw attention to changes that need action. Acknowledging an alert means someone has seen it; it does not necessarily mean the underlying problem is resolved.

Analytics summarizes the records available to the platform, such as monitored connectivity, district activity and higher-risk corridors. These summaries describe the platform's coverage—not a complete, official measurement of every road, hospital or supply shortage across North-East India.

---

## Page 5 — How route calculation and machine learning work

### Step 1: identify the journey locations

The user selects an origin and destination. A location-search service can translate a place name into coordinates. Map-selected coordinates provide another way to describe the requested journey. The application checks the operating area and sends the request to the backend.

### Step 2: obtain possible road routes

The backend requests road-network geometry from an external routing provider. The current integration uses OSRM with OpenStreetMap-based road data. OSRM supplies road paths and profile-based travel estimates; this is not the same as a live traffic-navigation feed.

The application also has a curated pilot-graph fallback. That fallback does not create complete offline routing coverage across all eight states.

### Step 3: collect route context

For each candidate, the assessment process samples locations along the route. The current design uses up to eight sample points per candidate to request weather and terrain information. It also considers nearby incident records and monitored road information where available.

Sampling makes the prototype practical, but it cannot observe every bend, bridge or hillside. A narrow local hazard may fall between sample points. This is one reason that field reports and coverage indicators matter.

### Step 4: obtain ML advisory outputs

Two models support the assessment. A risk classifier estimates disruption risk; a delay regressor estimates additional delay. The risk model receives features such as rainfall, slope, elevation, incident count, season, weather severity, road condition and traffic density. The delay model uses distance, rainfall, traffic, road condition, a baseline journey-time input and active incidents.

Some inputs may be estimated or defaulted when observed data is unavailable. They must not be described as direct sensor readings.

### Step 5: exclude and rank candidates

Known confirmed closures are used to exclude affected candidates according to the application's spatial matching and routing rules. The remaining candidates are compared using the selected preference. A recommended route means the highest-ranked available candidate under those rules and inputs—not a mathematically guaranteed safest route across every possible road.

### Current model status

The active version is `ner-synthetic-v2-all-state`, with XGBoost selected for risk and delay. It was trained using a 16,000-row synthetic dataset covering eight states and 29 representative corridors. Evaluation held out whole corridors. Reported risk accuracy is approximately 80.82%, and delay mean absolute error is approximately 23.98 minutes on that synthetic evaluation.

These figures do not establish real-world accuracy. `VALIDATED_PROTOTYPE` means the model passed prototype quality checks. Weather forecasts and ML predictions can raise warnings, but **they cannot independently declare a verified road closure**.

---

## Page 6 — Complete delivery example

The following is an illustrative workflow, not a claim about a real shipment or incident.

### 1. Register the vehicle

A driver signs in and registers the vehicle. In the live workflow, the phone supplies its location with permission. For a demonstration outside NER, the driver explicitly selects demo GPS. The vehicle then becomes available to the dispatch workflow without disguising a simulated position as real telemetry.

### 2. Plan and assign the delivery

A logistics operator selects a supply origin and a hospital destination. The planner assesses available candidates using weather, incidents, monitored road context and ML advisory outputs. The operator selects a route, creates the delivery and assigns the registered vehicle.

### 3. Acknowledge and begin

The driver receives an instruction and reviews the route. The driver must acknowledge the current instruction before departure. The system records the instruction version so that an acknowledgement for an older route cannot accidentally approve a newer one.

### 4. Track the journey

The driver starts the journey and opts into GPS sharing. While the driver workspace is open, acceptable phone positions are submitted at approximately ten-second intervals. The control room can see accepted positions and their freshness. GPS sharing itself does not authorize a paused or held vehicle to move.

### 5. Receive a disruption report

A field officer reports a blocked road, or the driver submits an obstruction at the last recorded vehicle position. The report enters the verification process. A driver obstruction report should be preceded by a fresh GPS update because its location is based on the last accepted position, not an assumed current location.

### 6. Review and reassess

An authorized reviewer checks the report and evidence. If the closure is confirmed, the system reassesses affected deliveries. If an acceptable alternative is found, a new instruction is issued. If no feasible candidate is found, the delivery enters a hold state.

### 7. Follow the latest instruction

The driver acknowledges the reroute or hold. A hold acknowledgement confirms receipt only; it does not permit departure. Pause, pending-instruction and hold protections remain in effect even when more GPS updates arrive.

### 8. Complete handover

When a driver-managed vehicle reaches the destination area, the platform marks it as `AT_DESTINATION`. The driver then confirms shipment handover using the completion action. This distinction matters: being near a hospital does not prove that its medicines have been delivered. Completion releases the vehicle and records the event in the shared timeline.

---

## Page 7 — Technology stack and system architecture

NERRO separates the user interface, operational logic, storage and background processing. Each part has a specific job.

| Technology | Simple explanation of its role |
|---|---|
| React and TypeScript | Build the screens and make data structures more consistent across the interface |
| Vite | Runs frontend development and produces the deployable website files |
| Leaflet and React-Leaflet | Display maps, markers, layers and route lines |
| TanStack Query | Fetches backend data and refreshes cached interface results |
| Python and FastAPI | Provide APIs and run operational business logic |
| Pydantic | Validates the shape and allowed values of incoming and outgoing data |
| NetworkX | Supports graph-based routing logic in the curated network |
| scikit-learn, XGBoost and joblib | Support model training, loading and prediction |
| SQLAlchemy and Alembic | Access relational data and manage database schema changes |
| PostgreSQL and PostGIS | Store operational records and geographic geometry in the Docker setup |
| Redis Streams and worker | Relay events and support background operational updates |
| MinIO/S3-compatible storage | Store photographic evidence separately from ordinary database records |
| IndexedDB and a service worker | Support local report queues and the field application's offline shell |
| JWT and Argon2 | Support authenticated sessions and password hashing |
| Docker Compose and Nginx | Run the services together and forward website/API traffic |

SQLite remains a development fallback when PostgreSQL is not configured. It should not be confused with the PostGIS-enabled Docker deployment.

### How the components connect

```text
Driver / field officer / logistics team / administrator
                          |
                 React web application
                          |
                    FastAPI backend
                   /       |        \
          Route services  ML models  Operational rules
                   \       |        /
           PostgreSQL/PostGIS + evidence storage
                          |
                  Redis event relay
                          |
            Updated maps, alerts and workspaces
```

External weather, geocoding, routing and terrain services provide inputs to the backend. The frontend does not independently decide whether a verified road should reopen. Centralizing those rules helps different users see consistent operational decisions.

Model training is a separate activity from serving predictions. Calculating a route runs the saved model; it does not retrain the model on every request. No GPU is inherently required for serving this prototype's tree-based models.

---

## Page 8 — Data flow, freshness and offline operation

### Field-report data flow

An officer enters the incident information and location. When online, the application submits it to the API. The backend validates the request, stores the incident and associates available geographic context. Evidence is handled through private storage and authenticated retrieval.

The control room receives an update and reviews the report. A reviewed change can update operational accessibility and trigger reassessment of affected deliveries. The updated records are then visible in the relevant workspaces.

When offline, reports are queued in IndexedDB on the device. Client report identifiers support duplicate-safe synchronization. Repeated synchronization should not create a second copy of the same report. Local storage can still be lost if browser data is cleared, so it is not a substitute for server-side backups.

### Weather data flow

Weather can be refreshed on demand and through the scheduled worker. The current Compose configuration schedules refreshes at a default interval of 900 seconds. Forecast values are associated with their source and update time. Cached fallback data may be used when a provider fails, but it should be identified as older information.

### GPS data flow

The browser requests location permission, receives a device fix and checks its age and accuracy. The foreground-sharing feature waits for fixes within 100 metres of reported accuracy and rejects stale or malformed input. The backend then checks authorization and validates the position before accepting it.

Accepted positions update telemetry and can influence progress, deviation and delay information. Events and periodic queries refresh the interface. During connectivity loss, automatic sharing keeps only the latest fix in memory and attempts recovery; it does not upload a complete offline travel history.

### What “real time” means here

NERRO combines different update schedules. GPS is periodically submitted; weather is a periodically refreshed forecast; incidents arrive when people report and review them. WebSocket events and polling help distribute changes. It is not a continuously observed digital copy of every road in the region.

### Offline limitations

The field PWA can retain its application shell, queued reports and appropriate last-known snapshots. Public basemap tiles remain online-only. Full offline NER maps require an approved or self-hosted map package. Phone GPS sharing is foreground-only: a browser cannot be assumed to keep tracking reliably after the screen locks or the application closes.

---

## Page 9 — Security, deployment and testing

### Access and accountability

NERRO uses authenticated accounts and role checks. Passwords are stored as hashes rather than plain text in user records. Driver operations are scoped to the associated vehicle, and sensitive operational actions require authorized roles.

Audit records and journey timelines help explain what happened: who submitted a report, when an instruction changed and when a driver acknowledged or completed an action. These records improve traceability; they do not eliminate the need to review permission coverage and protect the deployed system.

### Safety rules

The platform separates observations from predictions. An unverified report must not silently become an authoritative closure. A high ML risk score is not proof of a landslide. An old GPS fix must not appear to be a newly observed position.

Similarly, acknowledging a warning does not resolve the event. GPS cannot release a safety hold, and proximity cannot automatically prove handover for driver-managed deliveries. These rules make the workflow more understandable and reduce misleading automation.

### Current deployment approach

Docker Compose runs the frontend, backend, PostgreSQL/PostGIS, Redis, worker and MinIO locally. Persistent database and evidence volumes retain data across ordinary container restarts.

For team demonstrations, a temporary Cloudflare Tunnel forwards HTTPS traffic to a password-protected gateway. After passing that gateway, testers use the application's normal role login. The tunnel is temporary access to the laptop, not an independently hosted cloud installation. The laptop must remain awake, connected and running Docker. The address can change after a restart.

Temporary access details are deliberately excluded from this synopsis. They should be shared privately, not included in an SIH report or public repository.

### What has been checked?

The latest workflow change passed 35 backend tests, four frontend GPS-policy tests and a frontend production build. Checks cover important transitions such as acknowledgement, pause/hold protection, rerouting and driver-confirmed completion.

Passing those checks is not proof of production readiness. Real-phone trials, interrupted-network testing, multi-user browser tests, load testing, backup restoration and independent model validation are still needed. Before public production deployment, demo credentials must be replaced, secrets secured and database/storage ports kept private.

---

## Page 10 — Current achievement, remaining work and conclusion

### What we have built

NERRO is more than a map or an isolated ML experiment. The prototype connects role-based workspaces, route planning, weather inputs, ML advisory, field reporting, review, dispatch, vehicle telemetry and delivery completion.

It has moved beyond the original Guwahati–Tawang demonstration into NER-wide location selection and representative regional map data. However, regional selection does not mean complete verified regional coverage. Some roads and facilities are simulated, some features are estimated and some external information may be missing.

### What remains before real operational use?

1. **Verified datasets:** Import authoritative roads, bridge restrictions and facilities, with source ownership and update procedures. Replace demonstration records rather than presenting them as official assets.
2. **Real outcome-based ML validation:** Obtain observed disruptions and actual travel records, evaluate on independent data and measure missed serious events—not just overall accuracy.
3. **More reliable tracking:** Test actual phones and integrate a suitable mobile or per-device GPS gateway if dependable background tracking is required.
4. **Stronger accessibility analysis:** Develop deeper district-level reachability and essential-supply gap analysis. Counting incidents alone does not measure whether communities can receive supplies.
5. **Operational resilience:** Add production-grade backups, monitoring, recovery procedures and capacity testing. Evaluate behavior when a routing, weather or storage provider is unavailable.
6. **Language and offline coverage:** Expand beyond the multilingual notification proof of concept and provide a suitable offline mapping strategy.
7. **Pilot evaluation:** Work with a small set of operators, officers and drivers to test the complete flow before expanding geographic or operational responsibility.

### How we should measure success

Useful measures include report-to-review time, time required to notify an affected driver, stale GPS frequency, synchronization success, delivery completion time and the number of incorrect or missed disruption warnings. Baselines and real observations are needed to demonstrate improvement.

### Final explanation for the team

> We are building a shared decision-support platform for essential-goods transport in North-East India. A logistics operator plans a journey, a driver follows it, field officers report problems, and the control room verifies changes. Weather and machine learning help assess risk. If a verified disruption affects a delivery, the platform supports a new route or a safety hold. Everyone works from connected records instead of separate pieces of information.

NERRO's main value is this connected flow. Its current achievement is an integrated, testable prototype—not a guarantee of safe travel or a proven reduction in regional disruption. The next stage is to strengthen data quality, reliability and field validation while keeping that distinction clear.

### Repository references

- `docs/PROJECT_UNDERSTANDING.md`: original problem understanding and pilot blueprint; some early scope descriptions are historical.
- `docs/USER_JOURNEYS_AND_SCREENS.md`: planned role journeys and screens.
- `docs/TECHNICAL_CONTRACT.md`: interfaces, data concepts and operational rules.
- `docs/DRIVER_JOURNEY_TEST.md`: current driver-disruption and foreground GPS test flow.
- `docs/NER_MODEL_TRAINING.md`: training method and prototype validation limitations.
- `README.md` and `compose.yml`: implemented capabilities and local deployment structure.

This synopsis describes the repository's prototype design and inspected implementation. Live service availability and external data coverage can change and must be checked during demonstrations.
