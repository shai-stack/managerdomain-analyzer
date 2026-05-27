import pytest
from unittest.mock import patch, AsyncMock
from app import app, clean_domain


# ── clean_domain ─────────────────────────────────────────────────────────────

def test_clean_domain_strips_https():
    assert clean_domain('https://example.com') == 'example.com'


def test_clean_domain_strips_http():
    assert clean_domain('http://example.com') == 'example.com'


def test_clean_domain_strips_trailing_slash():
    assert clean_domain('example.com/') == 'example.com'


def test_clean_domain_strips_whitespace():
    assert clean_domain('  example.com  ') == 'example.com'


def test_clean_domain_passthrough():
    assert clean_domain('example.com') == 'example.com'


# ── Flask routes ─────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_index_returns_200(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'MANAGERDOMAIN' in resp.data


def test_analyze_returns_results(client):
    mock_results = [
        {'domain': 'example.com', 'manager_domains': ['openx.com'], 'status': 'ok'}
    ]
    with patch('app.analyze_domains', new_callable=AsyncMock, return_value=mock_results):
        resp = client.post('/analyze', json={'domains': ['example.com']})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data[0]['domain'] == 'example.com'
    assert data[0]['manager_domains'] == ['openx.com']


def test_analyze_deduplicates_domains(client):
    mock_results = [{'domain': 'example.com', 'manager_domains': [], 'status': 'not_found'}]
    with patch('app.analyze_domains', new_callable=AsyncMock, return_value=mock_results) as mock:
        client.post('/analyze', json={'domains': ['example.com', 'example.com', '  example.com  ']})
    mock.assert_called_once_with(['example.com'])


def test_analyze_limits_to_250(client):
    domains = [f'domain{i}.com' for i in range(300)]
    mock_results = []
    with patch('app.analyze_domains', new_callable=AsyncMock, return_value=mock_results) as mock:
        client.post('/analyze', json={'domains': domains})
    assert len(mock.call_args[0][0]) == 250


def test_analyze_strips_protocol_from_input(client):
    mock_results = [{'domain': 'example.com', 'manager_domains': [], 'status': 'ok'}]
    with patch('app.analyze_domains', new_callable=AsyncMock, return_value=mock_results) as mock:
        client.post('/analyze', json={'domains': ['https://example.com']})
    mock.assert_called_once_with(['example.com'])
