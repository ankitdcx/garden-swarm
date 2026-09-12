from fastapi.testclient import TestClient

from server.app import app

client = TestClient(app)


def test_health():
    r = client.get('/healthz')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_summary_status_boundary():
    r = client.get('/v1/summary')
    assert r.status_code == 200
    data = r.json()
    assert data['release'] == 'v15.5'
    assert data['status']['machine_certification'] == 'PENDING'
    assert data['status']['deployment_certification'] == 'PENDING'
    assert data['mcp']['implementation'] == 'OFFICIAL_PYTHON_SDK_V2'
    assert data['mcp']['public_conformance'] == 'PENDING_LIVE_ENDPOINT_VERIFICATION'


def test_source_manifest_available():
    r = client.get('/v1/source-manifest')
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_issue_payload_does_not_post():
    r = client.post('/v1/issue-payload', json={
        'claim': 'example',
        'coverage': 'public source',
        'source_anchors': ['H-05'],
        'evidence_or_failure': 'example failure',
        'severity': 'LOW',
        'affected_invariant': 'example',
        'existing_mitigation_checked': 'none',
        'better_alternative': 'example alternative',
        'test': 'example test',
        'uncertainty': 'example uncertainty',
        'publishable_issue_title': 'Example finding'
    })
    assert r.status_code == 200
    assert 'does not post to GitHub' in r.json()['note']


def test_discovery_protocol_status_is_bounded():
    r = client.get('/.well-known/garden-discovery.json')
    assert r.status_code == 200
    data = r.json()
    assert data['a2a_status'] == 'NOT_YET_A2A_CONFORMANT'
    assert data['mcp_status'] == 'OFFICIAL_SDK_IMPLEMENTED_LOCAL_TEST_PENDING_PUBLIC_ENDPOINT_VERIFICATION'
    assert data['mcp'].endswith('/mcp/')
