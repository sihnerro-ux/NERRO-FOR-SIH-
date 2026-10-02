# PostgreSQL and PostGIS Setup

SQLite remains the zero-configuration local fallback. Use this setup when the
prototype needs native spatial storage and indexes.

## Start the complete container stack

From the repository root:

```powershell
Copy-Item .env.docker.example .env
# Edit .env and replace POSTGRES_PASSWORD and JWT_SECRET first.
docker compose up --build -d
```

Open `http://localhost:8080`. The frontend reverse-proxies HTTP and WebSocket
traffic to the private backend container. The backend waits for PostGIS,
runs `alembic upgrade head`, and then starts the API. PostGIS data persists in
the named `ner_postgis_data` volume. Field photographs are stored privately in
MinIO using the `ner_evidence_data` volume and are only returned through an
authenticated API. The backend receives separate `DB_*`
variables, so a strong database password does not need URL escaping.

Redis Streams and the worker container relay operational events to every
FastAPI instance, which then delivers district-filtered WebSocket updates to
connected dashboards. If Redis is absent during direct local development, the
API safely falls back to its single-process in-memory event transport. Redis is
not published to the host by the Docker stack.

The same worker requests a fresh Open-Meteo forecast every 15 minutes by
default, after an initial 20-second startup delay. FastAPI recomputes the ML
advisory for all monitored roads, persists the result, creates deduplicated
high-risk alerts and sends a live dashboard event. Configure
`WEATHER_REFRESH_INTERVAL_SECONDS` to change the interval; the minimum is 60
seconds. Weather/ML alerts remain advisory and never close a road without an
authorized field verification.

Check the stack:

```powershell
docker compose ps
docker compose logs -f backend
```

Stop containers without deleting the database:

```powershell
docker compose down
```

Do not add `-v` unless you intentionally want to delete the PostGIS volume.

The older database-only command remains available for developers who want to
run Python and Vite directly on Windows:

```powershell
docker compose -f docker-compose.postgis.yml up -d
```

## Migrate the schema

```powershell
cd backend
$env:DATABASE_URL="postgresql+psycopg://ner_app:ner_local_password@127.0.0.1:5432/ner_logistics"
$env:JWT_SECRET="replace-with-a-long-random-secret"
python -m alembic upgrade head
```

## Run the API

Use the same terminal so `DATABASE_URL` remains set:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check `GET /api/v1/persistence/status`. A successful PostGIS runtime reports:

```json
{
  "backend": "POSTGRESQL",
  "spatial": {
    "postgis": true,
    "geometry_storage": "POSTGIS_GEOMETRY_4326"
  }
}
```

Roads use `geometry(LineString,4326)`. Vehicles, facilities and incidents use
`geometry(Point,4326)`. GiST indexes are created for all four geometry columns.
The full JSON payload remains stored alongside each spatial column for API
serialization and audit reproducibility.

## Return to SQLite

Open a new terminal without `DATABASE_URL`, or remove it from the environment.
The API returns to `backend/data/ner_logistics.db`; PostGIS data is not deleted.

## Docker Desktop not visible in PowerShell

If Docker was just installed and `docker` is not recognized, start Docker
Desktop and open a new terminal/IDE window. Verify both commands before trying
the stack:

```powershell
docker --version
docker compose version
```
