import asyncio
import aiohttp
from asyncio_throttle import Throttler
from config import ETHERSCAN_BASE, ETHERSCAN_API_KEY, RATE_LIMIT

_throttler = Throttler(rate_limit=RATE_LIMIT, period=1.0)


async def _get(session: aiohttp.ClientSession, params: dict) -> dict:
    """Rate-limited GET to Etherscan with exponential backoff on transient errors."""
    params["apikey"] = ETHERSCAN_API_KEY
    for attempt in range(5):
        async with _throttler:
            try:
                async with session.get(
                    ETHERSCAN_BASE,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    data = await resp.json()
                    msg = str(data.get("result", "")).lower()
                    if "rate limit" in msg or "max rate" in msg:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return data
            except (aiohttp.ClientError, asyncio.TimeoutError):
                wait = 2 ** attempt
                await asyncio.sleep(wait)
    return {}


async def _check_balances(session: aiohttp.ClientSession, addresses: list[str]) -> dict[str, bool]:
    """Single batched balance call for up to 20 addresses."""
    data = await _get(session, {
        "module": "account",
        "action": "balancemulti",
        "address": ",".join(addresses),
        "tag": "latest",
    })
    raw = data.get("result")
    if not isinstance(raw, list):
        return {}
    result = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            result[item["account"]] = int(item["balance"]) > 0
        except (KeyError, ValueError):
            result[item.get("account", "")] = False
    return result


async def _check_tx(session: aiohttp.ClientSession, address: str) -> bool:
    """Returns True if address has at least one transaction."""
    data = await _get(session, {
        "module": "account",
        "action": "txlist",
        "address": address,
        "page": "1",
        "offset": "1",
        "sort": "desc",
    })
    result = data.get("result")
    return isinstance(result, list) and len(result) > 0


async def check_batch(batch: list[dict]) -> list[dict]:
    """
    Check balance + tx existence for a batch of address dicts.
    Each dict must have keys: address, seed_phrase.
    Returns list of {address, seed_phrase, has_balance, has_tx, match}.
    """
    addresses = [item["address"] for item in batch]
    seed_map  = {item["address"]: item["seed_phrase"] for item in batch}

    async with aiohttp.ClientSession() as session:
        balance_map, tx_results = await asyncio.gather(
            _check_balances(session, addresses),
            asyncio.gather(*[_check_tx(session, addr) for addr in addresses]),
        )

    tx_map = dict(zip(addresses, tx_results))

    return [
        {
            "address":     addr,
            "seed_phrase": seed_map[addr],
            "has_balance": balance_map.get(addr, False),
            "has_tx":      tx_map.get(addr, False),
            "match":       balance_map.get(addr, False) or tx_map.get(addr, False),
        }
        for addr in addresses
    ]
