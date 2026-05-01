# ETH Wallet Scanner — Implementation Plan

**Spec:** `docs/superpowers/specs/2026-04-30-eth-wallet-scanner-design.md`
**Date:** 2026-04-30

---

## Step 1 — `requirements.txt`

Create the file at the project root:

```
aiohttp>=3.9
mnemonic>=0.21
eth-account>=0.11
asyncio-throttle>=1.0
```

---

## Step 2 — `config.py`

Read all secrets from environment variables. Expose constants used across modules.

```python
import os

ETHERSCAN_API_KEY = os.environ["ETHERSCAN_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TARGET_COUNT = 100_000
BATCH_SIZE = 20
RATE_LIMIT = 5          # requests per second
DERIVATION_PATH = "m/44'/60'/0'/0/0"
ETHERSCAN_BASE = "https://api.etherscan.io/api"
TELEGRAM_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
DB_PATH = "state.db"
CSV_PATH = "matches.csv"
```

---

## Step 3 — `state.py`

Responsibilities: create DB schema, save addresses, fetch pending batches, mark checked, track progress.

### Schema

```sql
CREATE TABLE IF NOT EXISTS addresses (
    address      TEXT PRIMARY KEY,
    seed_phrase  TEXT NOT NULL,
    checked      INTEGER DEFAULT 0,
    has_balance  INTEGER DEFAULT 0,
    has_tx       INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS progress (
    id               INTEGER PRIMARY KEY DEFAULT 1,
    total_generated  INTEGER DEFAULT 0,
    total_checked    INTEGER DEFAULT 0
);
```

### Functions

| Function | Signature | Notes |
|---|---|---|
| `init_db` | `() -> None` | Create tables + seed progress row if absent |
| `save_address` | `(address, seed_phrase) -> bool` | INSERT OR IGNORE; returns True if new |
| `increment_generated` | `() -> None` | +1 to total_generated |
| `get_pending_batch` | `(n: int) -> list[dict]` | SELECT WHERE checked=0 LIMIT n |
| `mark_checked` | `(address, has_balance, has_tx) -> None` | UPDATE + increment total_checked |
| `get_progress` | `() -> (int, int)` | Returns (total_generated, total_checked) |

---

## Step 4 — `generator.py`

Responsibilities: produce a random (mnemonic, address) pair.

```python
from mnemonic import Mnemonic
from eth_account import Account

Account.enable_unaudited_hdwallet_features()

mnemo = Mnemonic("english")

def generate_wallet() -> tuple[str, str]:
    seed_phrase = mnemo.generate(strength=128)  # 12 words
    account = Account.from_mnemonic(seed_phrase, account_path="m/44'/60'/0'/0/0")
    return seed_phrase, account.address
```

No deduplication logic here — state.py handles that via INSERT OR IGNORE.

---

## Step 5 — `checker.py`

Responsibilities: async Etherscan queries with rate limiting.

### Rate limiter

Use `asyncio_throttle.Throttler(rate_limit=5, period=1.0)` — one global instance shared across all calls.

### Functions

**`check_balances(session, addresses) -> dict[str, bool]`**
- Endpoint: `getbalancemulti` with comma-joined addresses
- Returns `{address: has_balance}` where `has_balance = int(wei) > 0`

**`check_tx(session, address) -> bool`**
- Endpoint: `txlist?page=1&offset=1&sort=desc`
- Returns True if result list is non-empty
- Returns False on empty result or error status

**`check_batch(addresses) -> list[dict]`**
- Opens one `aiohttp.ClientSession`
- Calls `check_balances` for all 20 at once
- Calls `check_tx` concurrently for all 20 using `asyncio.gather`
- Merges results: `match = has_balance or has_tx`
- Returns list of `{address, has_balance, has_tx, match}`

### Retry logic

Wrap each API call in a helper that:
- On HTTP 429 or `"Max rate limit reached"` response: exponential backoff, up to 3 retries (1s, 2s, 4s)
- On other network error: retry once, then return safe default (False)

---

## Step 6 — `notifier.py`

Responsibilities: send Telegram messages.

**`send_match(session, address, seed_phrase, balance_eth, has_tx) -> None`**

POST to `https://api.telegram.org/bot{TOKEN}/sendMessage` with:
```
🎯 Match Found!
Address: {address}
Seed Phrase: {seed_phrase}
Balance: {balance_eth} ETH
Has Transactions: {Yes/No}
```

**`send_summary(session, total_checked, matches_found) -> None`**

Sends a final completion message.

Silently logs and continues on send failure (never crash the main loop over a notification).

---

## Step 7 — `main.py`

### Startup

1. Call `state.init_db()`
2. Load progress with `state.get_progress()`
3. If `total_checked > 0`: print `Resuming from {total_checked} / {TARGET_COUNT}`
4. Open/append `matches.csv` with header row (skip header if file already exists)

### Main loop

```
while total_checked < TARGET_COUNT:
    # 1. Fill pending queue up to BATCH_SIZE
    while pending_count < BATCH_SIZE and total_generated < TARGET_COUNT:
        seed, address = generator.generate_wallet()
        is_new = state.save_address(address, seed)
        if is_new:
            state.increment_generated()
            total_generated += 1

    # 2. Fetch batch
    batch = state.get_pending_batch(BATCH_SIZE)
    if not batch:
        break

    # 3. Check
    results = asyncio.run(checker.check_batch([r["address"] for r in batch]))

    # 4. Process results
    for r in results:
        seed = next(b["seed_phrase"] for b in batch if b["address"] == r["address"])
        if r["match"]:
            write_csv_row(r, seed)
            asyncio.run(notifier.send_match(...))
        state.mark_checked(r["address"], r["has_balance"], r["has_tx"])
        total_checked += 1

    # 5. Progress line (overwrite in place with \r)
    print_progress(total_checked, matches, start_time)
```

### Completion

- Print final summary
- Send Telegram summary message
- Exit 0

### Signal handling

Catch `KeyboardInterrupt` cleanly: print current progress and exit without corrupting DB (SQLite transactions ensure consistency).

---

## Build Order

1. `requirements.txt`
2. `config.py`
3. `state.py` + smoke test (create DB, save one address, fetch it)
4. `generator.py` + smoke test (generate one wallet, verify address format)
5. `checker.py` + smoke test (check one real address with a known balance)
6. `notifier.py` + smoke test (send a test message to Telegram)
7. `main.py` — wire everything together
8. End-to-end test with `TARGET_COUNT = 10` to verify full pipeline

---

## Environment Setup

```bash
cd "Fox Eth"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export ETHERSCAN_API_KEY=your_key
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id

python main.py
```
