import json

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
admin_session = client.post('/api/v1/auth/login', json={'username': 'admin@ner.gov.in', 'password': 'NerDemo@2026'}).json()
admin_token = admin_session['access_token']
admin_headers = {'Authorization': f'Bearer {admin_token}'}


def import_request(*, dry_run: bool, longitude: float = 91.9) -> dict:
    feature_collection = {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'properties': {
                    'entity_type': 'FACILITY', 'id': 'FAC-IMPORT-001', 'name': 'Imported test relief node',
                    'facility_type': 'RELIEF_DEPOT', 'district': 'East Khasi Hills, Meghalaya',
                },
                'geometry': {'type': 'Point', 'coordinates': [longitude, 25.58]},
            },
            {
                'type': 'Feature',
                'properties': {
                    'entity_type': 'ROAD_SEGMENT', 'id': 'ROAD-IMPORT-001', 'road_name': 'Imported test road',
                    'from_node': 'TEST_A', 'to_node': 'TEST_B', 'state': 'Meghalaya',
                },
                'geometry': {'type': 'LineString', 'coordinates': [[91.88, 25.56], [91.92, 25.6]]},
            },
        ],
    }
    return {
        'filename': 'test-assets.geojson', 'source_name': 'Authorized test dataset',
        'content': json.dumps(feature_collection), 'data_mode': 'CACHED', 'dry_run': dry_run,
    }


def test_admin_import_preview_apply_upsert_and_boundary_validation() -> None:
    client.post('/api/v1/simulation/reset', headers=admin_headers)
    initial = client.get('/api/v1/map/snapshot', headers=admin_headers).json()

    preview = client.post('/api/v1/admin/data/import', headers=admin_headers, json=import_request(dry_run=True))
    assert preview.status_code == 200
    assert preview.json()['status'] == 'PREVIEW_VALID'
    assert preview.json()['facilities_created'] == 1
    assert preview.json()['roads_created'] == 1
    assert len(client.get('/api/v1/map/snapshot', headers=admin_headers).json()['facilities']) == len(initial['facilities'])

    applied = client.post('/api/v1/admin/data/import', headers=admin_headers, json=import_request(dry_run=False))
    assert applied.status_code == 200
    assert applied.json()['status'] == 'APPLIED'
    snapshot = client.get('/api/v1/map/snapshot', headers=admin_headers).json()
    imported = next(item for item in snapshot['facilities'] if item['id'] == 'FAC-IMPORT-001')
    assert imported['source'] == 'Authorized test dataset'
    assert imported['data_mode'] == 'CACHED'
    imported_road = next(item for item in snapshot['road_segments'] if item['id'] == 'ROAD-IMPORT-001')
    assert imported_road['states'] == ['Meghalaya']

    repeated = client.post('/api/v1/admin/data/import', headers=admin_headers, json=import_request(dry_run=False))
    assert repeated.json()['facilities_updated'] == 1

    invalid = client.post('/api/v1/admin/data/import', headers=admin_headers, json=import_request(dry_run=False, longitude=80.0))
    assert invalid.status_code == 422
    assert len(client.get('/api/v1/map/snapshot', headers=admin_headers).json()['facilities']) == len(snapshot['facilities'])
    client.post('/api/v1/simulation/reset', headers=admin_headers)


def test_operational_import_is_admin_only() -> None:
    viewer = client.post('/api/v1/auth/login', json={'username': 'viewer@ner.gov.in', 'password': 'ViewerDemo@2026'}).json()
    viewer_token = viewer['access_token']
    response = client.post('/api/v1/admin/data/import', headers={'Authorization': f'Bearer {viewer_token}'}, json=import_request(dry_run=True))
    assert response.status_code == 403
