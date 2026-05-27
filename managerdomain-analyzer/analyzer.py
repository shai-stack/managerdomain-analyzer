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


async def analyze_domains(domains: list) -> list:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_managerdomain(session, d) for d in domains]
        return list(await asyncio.gather(*tasks))
