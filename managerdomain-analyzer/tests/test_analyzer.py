import aiohttp
from aioresponses import aioresponses as aioresponses_mock
from analyzer import parse_managerdomain, fetch_managerdomain, analyze_domains


def test_parse_single():
    assert parse_managerdomain("MANAGERDOMAIN=openx.com") == ["openx.com"]


def test_parse_multiple():
    text = "MANAGERDOMAIN=openx.com\nMANAGERDOMAIN=pubmatic.com"
    assert parse_managerdomain(text) == ["openx.com", "pubmatic.com"]


def test_parse_case_insensitive():
    assert parse_managerdomain("managerdomain=openx.com") == ["openx.com"]


def test_parse_mixed_case():
    assert parse_managerdomain("ManagerDomain=openx.com") == ["openx.com"]


def test_parse_ignores_comment_lines():
    text = "# managerdomain=openx.com\nMANAGERDOMAIN=pubmatic.com"
    assert parse_managerdomain(text) == ["pubmatic.com"]


def test_parse_no_match():
    assert parse_managerdomain("google.com, pub-123, DIRECT, abc123") == []


def test_parse_empty_string():
    assert parse_managerdomain("") == []


def test_parse_trims_value_whitespace():
    assert parse_managerdomain("MANAGERDOMAIN= openx.com ") == ["openx.com"]


def test_parse_skips_blank_value():
    assert parse_managerdomain("MANAGERDOMAIN=") == []


async def test_fetch_found():
    with aioresponses_mock() as m:
        m.get('https://example.com/ads.txt', body='MANAGERDOMAIN=openx.com\n', status=200)
        async with aiohttp.ClientSession() as session:
            result = await fetch_managerdomain(session, 'example.com')
    assert result == {'domain': 'example.com', 'manager_domains': ['openx.com'], 'status': 'ok'}


async def test_fetch_found_no_managerdomain():
    with aioresponses_mock() as m:
        m.get('https://example.com/ads.txt', body='google.com, pub-123, DIRECT, abc\n', status=200)
        async with aiohttp.ClientSession() as session:
            result = await fetch_managerdomain(session, 'example.com')
    assert result == {'domain': 'example.com', 'manager_domains': [], 'status': 'ok'}


async def test_fetch_found_multiple_managerdomain():
    with aioresponses_mock() as m:
        body = 'MANAGERDOMAIN=openx.com\nMANAGERDOMAIN=pubmatic.com\n'
        m.get('https://example.com/ads.txt', body=body, status=200)
        async with aiohttp.ClientSession() as session:
            result = await fetch_managerdomain(session, 'example.com')
    assert result['manager_domains'] == ['openx.com', 'pubmatic.com']
    assert result['status'] == 'ok'


async def test_fetch_404():
    with aioresponses_mock() as m:
        m.get('https://example.com/ads.txt', status=404)
        async with aiohttp.ClientSession() as session:
            result = await fetch_managerdomain(session, 'example.com')
    assert result == {'domain': 'example.com', 'manager_domains': [], 'status': 'not_found'}


async def test_fetch_https_connection_error_falls_back_to_http():
    with aioresponses_mock() as m:
        m.get('https://example.com/ads.txt', exception=aiohttp.ClientConnectionError())
        m.get('http://example.com/ads.txt', body='MANAGERDOMAIN=openx.com\n', status=200)
        async with aiohttp.ClientSession() as session:
            result = await fetch_managerdomain(session, 'example.com')
    assert result['status'] == 'ok'
    assert result['manager_domains'] == ['openx.com']


async def test_fetch_both_fail():
    with aioresponses_mock() as m:
        m.get('https://example.com/ads.txt', exception=aiohttp.ClientConnectionError())
        m.get('http://example.com/ads.txt', exception=aiohttp.ClientConnectionError())
        async with aiohttp.ClientSession() as session:
            result = await fetch_managerdomain(session, 'example.com')
    assert result == {'domain': 'example.com', 'manager_domains': [], 'status': 'error'}


async def test_analyze_domains_returns_all():
    with aioresponses_mock() as m:
        m.get('https://a.com/ads.txt', body='MANAGERDOMAIN=openx.com\n', status=200)
        m.get('https://b.com/ads.txt', status=404)
        results = await analyze_domains(['a.com', 'b.com'])
    domains = {r['domain'] for r in results}
    assert domains == {'a.com', 'b.com'}
    a = next(r for r in results if r['domain'] == 'a.com')
    assert a['manager_domains'] == ['openx.com']
