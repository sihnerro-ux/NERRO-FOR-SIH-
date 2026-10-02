# Controlled operational data import

Administrators can open **Administration → Import operational GeoJSON or CSV**. Every upload follows two steps:

1. **Validate preview** parses and validates the entire file without changing data.
2. **Apply validated import** atomically upserts records, recalculates ML advisories, persists PostGIS state, records an audit event, and broadcasts a real-time update.

Files are limited to 5 MB. IDs make imports idempotent: a new ID creates an entity and an existing ID updates it. Any invalid row or feature rejects the whole file.

## GeoJSON schema

The root must be a `FeatureCollection`. Each feature needs an `entity_type` property.

### ROAD_SEGMENT

Required properties:

- `entity_type`: `ROAD_SEGMENT`
- `id`: stable 3–50 character identifier
- `road_name`
- `state`, or `states` as an array for a cross-state road
- `geometry`: GeoJSON `LineString` containing at least two NER coordinates

Optional properties include `from_node`, `to_node`, `distance_km`, `accessibility`, `risk_score`, `risk_band`, `road_condition`, `rainfall_mm_24h`, `slope_degrees`, and `confidence`.

### FACILITY

Required properties:

- `entity_type`: `FACILITY`
- `id`, `name`, `facility_type`, and `district`
- `geometry`: GeoJSON `Point` inside the configured NER boundary

See [operational-import.geojson](../samples/operational-import.geojson).

## CSV schema

Every row requires `entity_type`, `id`, and the corresponding properties above. Facility rows use `longitude` and `latitude`. Road rows use `geometry_json`, containing a JSON array of longitude/latitude pairs. Multiple road states are separated with `|` in the `states` column.

See [operational-facilities.csv](../samples/operational-facilities.csv).

## Trust and safety rules

- Only control-room administrators can preview or apply imports.
- The source name and `CACHED`/`SIMULATED` classification are stored on every entity.
- Coordinates outside the configured NER operating boundary are rejected.
- Imported datasets never become `LIVE`; live status is reserved for timestamped feeds.
- Import application is atomic and produces an `OPERATIONAL_DATA_IMPORTED` audit event.
- Imported roads participate in routing overlays, nearby incident matching, weather/ML reassessment, and state analytics.
