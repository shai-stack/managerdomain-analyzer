import asyncio
import aiohttp


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


async def fetch_managerdomain(session: aiohttp.ClientSession, domain: str) -> dict:
    for scheme in ('https', 'http'):
        url = f"{scheme}://{domain}/ads.txt"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    text = await resp.text(errors='replace')
                    return {
                        'domain': domain,
                        'manager_domains': parse_managerdomain(text),
                        'status': 'ok',
                    }
                return {'domain': domain, 'manager_domains': [], 'status': 'not_found'}
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue
    return {'domain': domain, 'manager_domains': [], 'status': 'error'}


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/plain, text/html, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
}


async def analyze_domains(domains: list) -> list:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tasks = [fetch_managerdomain(session, d) for d in domains]
        return list(await asyncio.gather(*tasks))
