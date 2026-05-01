import asyncio
import aiohttp
from asyncio_throttle import Throttler
from config import ETHERSCAN_BASE, ETHERSCAN_API_KEY, CHAINS, RATE_LIMIT

_throttler = Throttler(rate_limit=RATE_LIMIT, period=1.0)


async def _get(session: aiohttp.ClientSession, params: dict, chain_id: str = "1") -> dict:
    """Rate-limited GET to Etherscan V2 with exponential backoff."""
    params["apikey"] = ETHERSCAN_API_KEY
    params["chainid"] = chain_id
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
                await asyncio.sleep(2 ** attempt)
    return {}


async def _check_native_balances(
    session: aiohttp.ClientSession, addresses: list[str], chain_id: str
) -> dict[str, float]:
    """Batch native balance check for one chain. Returns {address: balance_in_ether}."""
    data = await _get(session, {
        "module": "account",
        "action": "balancemulti",
        "address": ",".join(addresses),
        "tag": "latest",
    }, chain_id)
    raw = data.get("result")
    if not isinstance(raw, list):
        return {}
    result = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            result[item["account"]] = int(item["balance"]) / 1e18
        except (KeyError, ValueError):
            result[item.get("account", "")] = 0.0
    return result


async def _check_tx(session: aiohttp.ClientSession, address: str) -> bool:
    """Returns True if address has at least one ETH transaction on mainnet."""
    data = await _get(session, {
        "module": "account",
        "action": "txlist",
        "address": address,
        "page": "1",
        "offset": "1",
        "sort": "desc",
    }, "1")
    result = data.get("result")
    return isinstance(result, list) and len(result) > 0


async def _check_token_tx(session: aiohttp.ClientSession, address: str) -> bool:
    """Returns True if address has at least one ERC-20 token transfer on mainnet."""
    data = await _get(session, {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "page": "1",
        "offset": "1",
        "sort": "desc",
    }, "1")
    result = data.get("result")
    return isinstance(result, list) and len(result) > 0


async def check_batch(batch: list[dict]) -> list[dict]:
    """
    Full multi-chain + token check for a batch of address dicts.
    Each dict must have keys: address, seed_phrase.
    Returns list of enriched result dicts.
    """
    addresses = [item["address"] for item in batch]
    seed_map  = {item["address"]: item["seed_phrase"] for item in batch}

    async with aiohttp.ClientSession() as session:
        # Run all chain balance checks + mainnet tx + mainnet token tx concurrently
        chain_tasks = [
            _check_native_balances(session, addresses, chain_id)
            for chain_id in CHAINS.values()
        ]
        tx_tasks    = [_check_tx(session, addr) for addr in addresses]
        token_tasks = [_check_token_tx(session, addr) for addr in addresses]

        all_results = await asyncio.gather(
            *chain_tasks,
            asyncio.gather(*tx_tasks),
            asyncio.gather(*token_tasks),
        )

    chain_names  = list(CHAINS.keys())
    chain_maps   = all_results[:len(chain_names)]   # one dict per chain
    tx_results   = all_results[-2]                  # list of bools
    token_results = all_results[-1]                 # list of bools

    tx_map    = dict(zip(addresses, tx_results))
    token_map = dict(zip(addresses, token_results))

    results = []
    for addr in addresses:
        # Collect per-chain balances
        chain_balances = {
            chain: chain_maps[i].get(addr, 0.0)
            for i, chain in enumerate(chain_names)
        }
        matched_chains = [c for c, bal in chain_balances.items() if bal > 0]
        has_balance  = len(matched_chains) > 0
        has_tx       = tx_map.get(addr, False)
        has_token_tx = token_map.get(addr, False)

        results.append({
            "address":        addr,
            "seed_phrase":    seed_map[addr],
            "has_balance":    has_balance,
            "has_tx":         has_tx,
            "has_token_tx":   has_token_tx,
            "matched_chains": matched_chains,
            "chain_balances": chain_balances,
            "match":          has_balance or has_tx or has_token_tx,
        })

    return results
