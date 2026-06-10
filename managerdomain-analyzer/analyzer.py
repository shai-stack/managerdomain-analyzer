import asyncio
import aiohttp
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/plain, text/html, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
}

SCRAPERAPI_KEY = os.environ.get('SCRAPERAPI_KEY', '')


def parse_managerdomain(text: str) -> list:
    results = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if stripped.lower().startswith('managerdomain='):
            value = stripped[len('managerdomain='):].strip()
            if value:
                results.append(value)
    return results


def is_html_response(text: str) -> bool:
    sample = text.strip()[:200].lower()
    return '<html' in sample or '<!doctype' in sample


async def fetch_via_scraperapi(session: aiohttp.ClientSession, url: str):
    if not SCRAPERAPI_KEY:
        return None
    proxy_url = f'https://api.scraperapi.com/?api_key={SCRAPERAPI_KEY}&url={url}'
    try:
        async with session.get(proxy_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                text = await resp.text(errors='replace')
                if not is_html_response(text):
                    return text
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass
    return None


CDN_BLOCK_STATUSES = {403, 503, 429}


async def fetch_managerdomain(session: aiohttp.ClientSession, domain: str) -> dict:
    blocked = False
    for scheme in ('https', 'http'):
        url = f'{scheme}://{domain}/ads.txt'
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    text = await resp.text(errors='replace')
                    if not is_html_response(text):
                        return {'domain': domain, 'manager_domains': parse_managerdomain(text), 'status': 'ok'}
                    blocked = True
                    break
                elif resp.status in CDN_BLOCK_STATUSES:
                    blocked = True
                    break
                else:
                    return {'domain': domain, 'manager_domains': [], 'status': 'not_found'}
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    if blocked:
        proxy_text = await fetch_via_scraperapi(session, f'https://{domain}/ads.txt')
        if proxy_text is not None:
            return {'domain': domain, 'manager_domains': parse_managerdomain(proxy_text), 'status': 'ok'}
        return {'domain': domain, 'manager_domains': [], 'status': 'blocked'}

    return {'domain': domain, 'manager_domains': [], 'status': 'error'}


async def analyze_domains(domains: list) -> list:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tasks = [fetch_managerdomain(session, d) for d in domains]
        return list(await asyncio.gather(*tasks))
