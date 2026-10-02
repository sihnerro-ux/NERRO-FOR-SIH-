import csv
import io
import json
import re
from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt

from app.domain.models import (
    DataMode,
    Facility,
    GeoJsonLineString,
    GeoJsonPoint,
    OperationalDataImportRequest,
    RiskBand,
    RoadAccessibility,
    RoadSegment,
)


SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{2,49}$')
NER_STATES = {'Assam', 'Arunachal Pradesh', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Sikkim', 'Tripura'}
NER_RINGS = [
    [[88.02, 26.75], [88.96, 26.75], [88.98, 28.18], [88.02, 28.18]],
    [[89.65, 25.05], [90.75, 22.85], [91.15, 21.85], [93.55, 21.85], [94.35, 23.35], [95.4, 24.0], [97.55, 27.0], [97.45, 29.55], [94.25, 29.55], [92.05, 28.35], [90.45, 26.55]],
]


def _inside_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous
        x2, y2 = current
        crosses = (y1 > latitude) != (y2 > latitude)
        if crosses and longitude < (x2 - x1) * (latitude - y1) / (y2 - y1) + x1:
            inside = not inside
        previous = current
    return inside


def _inside_ner(coordinate: list[float]) -> bool:
    if len(coordinate) != 2:
        return False
    longitude, latitude = coordinate
    return any(_inside_ring(float(longitude), float(latitude), ring) for ring in NER_RINGS)


def _distance_km(coordinates: list[list[float]]) -> float:
    total = 0.0
    for start, end in zip(coordinates, coordinates[1:]):
        lon1, lat1, lon2, lat2 = map(radians, [start[0], start[1], end[0], end[1]])
        delta_lon, delta_lat = lon2 - lon1, lat2 - lat1
        value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        total += 6371.0 * 2 * asin(sqrt(value))
    return round(total, 2)


def _identifier(properties: dict, index: int) -> str:
    value = str(properties.get('id', '')).strip()
    if not SAFE_ID.fullmatch(value):
        raise ValueError(f'feature {index}: id must be 3-50 letters, numbers, hyphens or underscores')
    return value


def _road(feature: dict, request: OperationalDataImportRequest, index: int) -> RoadSegment:
    properties = feature.get('properties') or {}
    geometry = feature.get('geometry') or {}
    coordinates = geometry.get('coordinates')
    if geometry.get('type') != 'LineString' or not isinstance(coordinates, list) or len(coordinates) < 2:
        raise ValueError(f'feature {index}: ROAD_SEGMENT requires a LineString with at least two points')
    if not all(isinstance(point, list) and _inside_ner(point) for point in coordinates):
        raise ValueError(f'feature {index}: every road coordinate must fall inside the configured NER boundary')
    timestamp = datetime.now(UTC)
    accessibility = RoadAccessibility(str(properties.get('accessibility', 'UNKNOWN')).upper())
    risk_score = int(properties.get('risk_score', 0))
    risk_band = RiskBand(str(properties.get('risk_band', 'UNKNOWN')).upper())
    raw_states = properties.get('states') or properties.get('state') or []
    states = [str(item).strip() for item in raw_states] if isinstance(raw_states, list) else [item.strip() for item in str(raw_states).split('|')]
    if not states or any(state not in NER_STATES for state in states):
        raise ValueError(f'feature {index}: road state/states must name one or more of the eight NER states')
    road_name = str(properties.get('road_name') or properties.get('name') or '').strip()
    if not road_name:
        raise ValueError(f'feature {index}: road_name is required')
    return RoadSegment(
        id=_identifier(properties, index),
        road_name=road_name,
        from_node=str(properties.get('from_node') or 'IMPORTED_START').strip(),
        to_node=str(properties.get('to_node') or 'IMPORTED_END').strip(),
        states=states,
        geometry=GeoJsonLineString(coordinates=coordinates),
        distance_km=float(properties.get('distance_km') or _distance_km(coordinates)),
        accessibility=accessibility,
        risk_score=risk_score,
        risk_band=risk_band,
        road_condition=str(properties.get('road_condition', 'UNKNOWN')).upper(),
        rainfall_mm_24h=float(properties.get('rainfall_mm_24h', 0)),
        slope_degrees=float(properties.get('slope_degrees', 0)),
        source=request.source_name,
        data_mode=DataMode(request.data_mode),
        observed_at=timestamp,
        updated_at=timestamp,
        confidence=int(properties.get('confidence', 70)),
    )


def _facility(feature: dict, request: OperationalDataImportRequest, index: int) -> Facility:
    properties = feature.get('properties') or {}
    geometry = feature.get('geometry') or {}
    coordinate = geometry.get('coordinates')
    if geometry.get('type') != 'Point' or not isinstance(coordinate, list) or not _inside_ner(coordinate):
        raise ValueError(f'feature {index}: FACILITY requires a Point inside the configured NER boundary')
    name = str(properties.get('name', '')).strip()
    facility_type = str(properties.get('facility_type', '')).strip().upper()
    district = str(properties.get('district', '')).strip()
    if not name or not facility_type or not district:
        raise ValueError(f'feature {index}: facility name, facility_type and district are required')
    return Facility(
        id=_identifier(properties, index), name=name, facility_type=facility_type, district=district,
        location=GeoJsonPoint(coordinates=coordinate), source=request.source_name, data_mode=DataMode(request.data_mode),
    )


def _csv_features(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError('CSV header row is missing')
    features: list[dict] = []
    for row_number, row in enumerate(reader, start=2):
        entity_type = str(row.get('entity_type', '')).strip().upper()
        properties = {key: value for key, value in row.items() if value not in (None, '')}
        if entity_type == 'ROAD_SEGMENT':
            try:
                coordinates = json.loads(row.get('geometry_json', ''))
            except json.JSONDecodeError as exc:
                raise ValueError(f'CSV row {row_number}: geometry_json is not valid JSON') from exc
            geometry = {'type': 'LineString', 'coordinates': coordinates}
        elif entity_type == 'FACILITY':
            try:
                geometry = {'type': 'Point', 'coordinates': [float(row.get('longitude', '')), float(row.get('latitude', ''))]}
            except ValueError as exc:
                raise ValueError(f'CSV row {row_number}: longitude and latitude are required numbers') from exc
        else:
            raise ValueError(f'CSV row {row_number}: entity_type must be ROAD_SEGMENT or FACILITY')
        features.append({'type': 'Feature', 'properties': properties, 'geometry': geometry})
    return features


def parse_operational_import(request: OperationalDataImportRequest) -> tuple[list[RoadSegment], list[Facility], list[str]]:
    filename = request.filename.casefold()
    if filename.endswith('.csv'):
        features = _csv_features(request.content)
    elif filename.endswith(('.json', '.geojson')):
        try:
            document = json.loads(request.content)
        except json.JSONDecodeError as exc:
            raise ValueError(f'Invalid JSON at line {exc.lineno}, column {exc.colno}') from exc
        if document.get('type') != 'FeatureCollection' or not isinstance(document.get('features'), list):
            raise ValueError('GeoJSON must be a FeatureCollection')
        features = document['features']
    else:
        raise ValueError('Only .csv, .json and .geojson files are accepted')

    roads: list[RoadSegment] = []
    facilities: list[Facility] = []
    seen_ids: set[str] = set()
    for index, feature in enumerate(features, start=1):
        if not isinstance(feature, dict):
            raise ValueError(f'feature {index}: expected a GeoJSON Feature object')
        properties = feature.get('properties') or {}
        entity_type = str(properties.get('entity_type', '')).strip().upper()
        item = _road(feature, request, index) if entity_type == 'ROAD_SEGMENT' else _facility(feature, request, index) if entity_type == 'FACILITY' else None
        if item is None:
            raise ValueError(f'feature {index}: entity_type must be ROAD_SEGMENT or FACILITY')
        if item.id in seen_ids:
            raise ValueError(f'feature {index}: duplicate id {item.id} in import file')
        seen_ids.add(item.id)
        (roads if entity_type == 'ROAD_SEGMENT' else facilities).append(item)
    if not roads and not facilities:
        raise ValueError('Import file contains no operational features')
    warnings = ['Imported data remains source-attributed and cannot close a road unless accessibility is explicitly supplied by an authorized dataset.']
    return roads, facilities, warnings
