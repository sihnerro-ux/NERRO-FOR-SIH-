# NER Logistics Control Tower

Working prototype for Smart India Hackathon Problem Statement 26002: an AI-assisted GIS logistics and accessibility platform for the North Eastern Region.

## Start everything with Docker and PostGIS

Docker Desktop must be running and `docker --version` must work in the current
terminal.

```powershell
Copy-Item .env.docker.example .env
# Replace the example database password and JWT secret in .env.
docker compose up --build -d
```

Open `http://localhost:8080`. This starts the production frontend, FastAPI,
Alembic migrations, PostgreSQL 16/PostGIS 3.4, private MinIO evidence storage,
Redis and the event-relay worker. Database and evidence data are retained in
named volumes when the containers are stopped normally. Redis is private to the
container network and is used for cross-instance real-time delivery.

## Current milestone

The repository currently contains the first full-stack vertical slice:

- React/TypeScript/Vite control-tower dashboard
- Leaflet pilot-corridor map
- FastAPI operational API
- Deterministic Guwahati-Tawang pilot data
- Roads, facilities, incidents, vehicles, deliveries, and alerts
- Road-segment detail and data provenance
- Live-on-demand Open-Meteo rainfall forecasts with persisted fallback
- External OSRM/OpenStreetMap road geometry with curated-corridor fallback
- User-triggered NER place search for arbitrary route origins and destinations
- Heavy-rain risk simulation and reset

Weather can be refreshed from a real external forecast feed, and authenticated GPS telemetry can be ingested for registered vehicles. Seeded GPS positions, road geometry, facilities, deliveries, and demonstration incidents remain clearly marked as simulated until replaced by a live source. Application state is persisted locally.

## Start the backend

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation is available at `http://127.0.0.1:8000/docs`.

## Demo login

Control-room administrator:

- Username: `admin@ner.gov.in`
- Password: `NerDemo@2026`

Field officer:

- Username: `field@ner.gov.in`
- Password: `FieldDemo@2026`

Vehicle driver:

- Username: `driver@ner.gov.in`
- Password: `DriverDemo@2026`

These accounts are only for local prototype evaluation. Set a strong `JWT_SECRET` and replace demo users before deployment.

## Database

The backend uses SQLAlchemy and persists operational state plus audit events. Without configuration it creates a local SQLite database at `backend/data/ner_logistics.db`.

To use PostgreSQL, set the connection before starting the API:

```powershell
$env:DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:5432/ner_logistics"
$env:JWT_SECRET="replace-with-a-long-random-secret"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

PostgreSQL deployments use native PostGIS SRID 4326 geometry columns and GiST spatial indexes for roads, vehicles, facilities and incidents. SQLite keeps JSON geometry as the zero-configuration fallback. See `docs/POSTGIS_SETUP.md` for the local container and migration procedure.

Schema migrations are versioned with Alembic:

```powershell
cd backend
python -m alembic upgrade head
```

## Start the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## NER-wide synthetic dataset

The reproducible prototype dataset is generated under `SIH Model/nerro_ml/data/generated`. It contains 16,000 balanced observations across all eight NER states and 29 representative corridors. See `docs/NER_SYNTHETIC_DATASET.md` for its schema, provenance and safety limitations.

```powershell
cd "SIH Model/nerro_ml"
python -m scripts.generate_ner_dataset
```

The generated rows are explicitly simulated and must not be presented as historical government observations.

The operational map seed catalog currently provides 64 representative monitored road segments and 80 prototype assets across all eight NER states. The asset catalog includes hospitals, relief depots, warehouses, cold-chain nodes, maintenance bases, cargo/border nodes, fuel depots, and a separate bridge/crossing-monitor layer. Names and coordinates added for coverage are clearly SIMULATED and are designed to be replaced through the future government/department data-import pipeline.

## Verification

Backend tests:

```powershell
cd backend
python -m pytest -q
```

Frontend typecheck and production build:

```powershell
cd frontend
npm run build
```

## Project documents

- `docs/PROJECT_UNDERSTANDING.md` — problem, product scope, architecture, safety, and MVP plan
- `docs/USER_JOURNEYS_AND_SCREENS.md` — role journeys, navigation, screens, actions, and UI states
- `docs/TECHNICAL_CONTRACT.md` — data language, APIs, events, transitions, and repository conventions

## Current implemented capabilities

- Risk-aware emergency routing and blocked-road exclusion
- Live GPS ingestion plus simulated fleet and critical-delivery visibility
- Heavy-rain and confirmed-landslide operational scenarios
- ML risk/delay advisory with human verification boundaries
- Geo-tagged field reporting, review, and offline synchronization
- IndexedDB field-report queue with reconnect synchronization and duplicate-safe client report IDs
- Installable field-officer PWA with an offline application shell, per-user last-known operational snapshots, restart-safe report recovery and explicit reconnect synchronization
- Private MinIO/S3 photographic-evidence storage with authenticated retrieval and integrity hashes
- Redis Streams event queue, worker relay and multi-instance WebSocket fan-out
- Scheduled live-weather ingestion with automatic ML road reassessment and advisory alert generation
- Alert acknowledgement and multilingual notification proof of concept
- Persistent operational state and audit events
- JWT authentication, Argon2 password hashing, and role-based permissions
- Live 24-hour precipitation ingestion with timestamps and segment-level provenance
- Cached weather fallback when the external provider is unavailable
- Timestamp-ordered vehicle telemetry with NER boundary validation, provenance, accuracy, freshness, and position history
- External road-network routing, alternative geometry and local closure/risk overlays
- Anywhere-to-anywhere routing across the eight NER states using selected map coordinates
- Expanded eight-state operational catalog with separate bridge/crossing and essential-facility map layers
- Admin-only GeoJSON/CSV operational-data import with preview validation, atomic upsert, source classification, boundary checks and audit history
- Per-route live weather and terrain sampling with ML risk/delay assessment and visible data confidence
- Functional Overview, Deliveries and Fleet modules sharing one operational state
- Delivery assignment/ETA/progress views and fleet telemetry/provenance views
- Driver-only journey workspace with phone-GPS vehicle onboarding, scoped route visibility, dispatch acknowledgement, live position updates and delivery completion
- Opt-in foreground driver GPS sharing with 10-second uploads, accuracy/staleness checks, latest-fix reconnect recovery and explicit stop control
- Driver-managed destination arrival requires explicit handover confirmation; pause, hold and pending instructions cannot be released by GPS

Weather is advisory input only. A forecast may change risk and delay predictions, but it cannot mark a road blocked without a verified field or control-room event.

The field PWA caches its public application shell and stores the latest operational map/overview snapshot in IndexedDB for the signed-in officer. Authenticated API responses are never placed in the shared service-worker cache, and the per-user snapshot is removed on sign-out. Public basemap tiles remain online-only; production offline mapping requires an approved or self-hosted NER tile package.

The GPS endpoint is `POST /api/v1/vehicles/{vehicle_id}/positions`. For the prototype it uses the existing administrator/logistics-operator JWT. Production device integration should use per-device credentials at an AIS-140/vendor gateway.

Route planning queries OSRM/OpenStreetMap on demand and falls back to the deterministic pilot graph on timeout, provider failure, or unsafe external candidates. OSRM provides road-network geometry and profile-based ETA, not live traffic. Set `OSRM_BASE_URL` to a self-hosted OSRM deployment for production; the public demonstration server should only be used for prototype evaluation.

For an arbitrary NER route, the service samples up to eight points on every candidate route, obtains a 24-hour precipitation forecast and elevation, adds nearby field incidents and monitored road information where available, then invokes the submitted ML risk and delay models. The displayed ML score is a disruption advisory, not a closure decision. The current supplied model was trained on synthetic data and should be retrained and validated on historical NER observations before operational deployment.

Location search uses explicit user-triggered Nominatim queries—never autocomplete—restricted to India and the eight NER states. Results are cached and requests are rate-limited. Set `NOMINATIM_BASE_URL` and `NER_GEOCODER_USER_AGENT` for deployment; production should use a self-hosted or contracted geocoder rather than the public demonstration service.

Future official road, bridge, and facility datasets can be loaded from the Administration panel using the controlled two-stage importer. The accepted schemas and samples are documented in `docs/OPERATIONAL_DATA_IMPORT.md`.
