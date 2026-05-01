# ETH Wallet Scanner — Design Spec

**Date:** 2026-04-30
**Status:** Approved

---

## Overview

A Python script that generates 100,000 random Ethereum wallets (each with a 12-word BIP39 seed phrase), checks each address against the Etherscan API for any ETH balance or transaction history, and sends matches to a Telegram bot. Progress is persisted in SQLite so the run can be resumed after any interruption. No address is ever generated or checked twice.

---

## Project Structure

```
fox-eth/
├── main.py          — entry point, orchestrates the full pipeline
├── generator.py     — BIP39 mnemonic generation + BIP44 ETH address derivation
├── checker.py       — async Etherscan API client (balance + tx checks)
├── notifier.py      — Telegram bot integration
├── state.py         — SQLite state: deduplication, resume, progress tracking
├── config.py        — API keys, constants, configurable settings
├── matches.csv      — output: all matched addresses + seed phrases
├── state.db         — SQLite database (auto-created on first run)
└── requirements.txt — Python dependencies
```

---

## Configuration (`config.py`)

| Setting | Value |
|---|---|
| `ETHERSCAN_API_KEY` | Set via environment variable `ETHERSCAN_API_KEY` |
| `TELEGRAM_BOT_TOKEN` | Set via environment variable `TELEGRAM_BOT_TOKEN` |
| `TELEGRAM_CHAT_ID` | Set via environment variable `TELEGRAM_CHAT_ID` |
| `TARGET_COUNT` | 100,000 |
| `BATCH_SIZE` | 20 (Etherscan `getbalancemulti` max) |
| `RATE_LIMIT` | 5 requests/second |
| `BIP44_DERIVATION_PATH` | `m/44'/60'/0'/0/0` |

API keys are read from environment variables, not hardcoded.

---

## Module Designs

### `generator.py`

- Uses the `mnemonic` library to generate a cryptographically random 12-word BIP39 mnemonic
- Derives the Ethereum address using `eth_account` with BIP44 path `m/44'/60'/0'/0/0`
- Returns a `(mnemonic: str, address: str)` tuple
- Deduplication is enforced at the database layer (INSERT OR IGNORE), not in this module

### `state.py`

Manages a SQLite database (`state.db`) with two tables:

```sql
CREATE TABLE IF NOT EXISTS addresses (
    address      TEXT PRIMARY KEY,
    seed_phrase  TEXT NOT NULL,
    checked      INTEGER DEFAULT 0,   -- 0 = pending, 1 = done
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

Key operations:
- `save_address(address, seed_phrase)` — INSERT OR IGNORE (silently skips duplicates)
- `get_pending_batch(n)` — returns up to `n` unchecked addresses
- `mark_checked(address, has_balance, has_tx)` — updates row + increments `total_checked`
- `get_progress()` — returns `(total_generated, total_checked)`

**Resume logic:** On startup, `main.py` queries `total_generated` from the progress table. Generation resumes from that count. Pending addresses (checked=0) already in the DB are processed before generating new ones.

### `checker.py`

Async Etherscan API client using `aiohttp`.

Two endpoints used:
1. **Balance batch:** `GET /api?module=account&action=getbalancemulti&address=<comma-separated-20>&tag=latest`
   - One call per 20 addresses
   - Returns balance in Wei; match if `int(balance) > 0`

2. **Transaction existence:** `GET /api?module=account&action=txlist&address=<addr>&page=1&offset=1&sort=desc`
   - One call per address
   - Match if `result` array is non-empty

Rate limiting: uses `asyncio-throttle` (`Throttler(rate_limit=5, period=1.0)`) to enforce a strict ≤5 requests/second ceiling — a semaphore alone limits concurrency but not per-second rate.

Both checks run concurrently for a batch: balance check fires first (single call for 20), then tx checks fire concurrently (up to 5 at a time). Results are merged: an address is a match if `has_balance OR has_tx`.

Error handling:
- Etherscan rate-limit responses (HTTP 429 or `"Max rate limit reached"`) trigger an exponential backoff retry (up to 3 retries)
- Network errors are retried once; on second failure the address is marked for retry in the next run

### `notifier.py`

Sends a Telegram message via the Bot API when a match is found.

Message format:
```
🎯 Match Found!
Address: 0x...
Seed Phrase: word1 word2 ... word12
Balance: 0.0042 ETH
Has Transactions: Yes
```

Uses `aiohttp` POST to `https://api.telegram.org/bot{TOKEN}/sendMessage`.

### `main.py`

Orchestrates the pipeline:

1. Initialize `state.py` (create DB if not exists)
2. Load progress — print resume status if continuing
3. Loop until `total_checked == TARGET_COUNT`:
   a. Fill pending queue: generate new addresses until there are `BATCH_SIZE` pending in DB (skipping duplicates via INSERT OR IGNORE)
   b. Fetch a batch of 20 pending addresses from DB
   c. Run async checks via `checker.py`
   d. For each match: append to `matches.csv`, send Telegram alert via `notifier.py`
   e. Mark all 20 as checked in DB
   f. Print live progress: `Checked: 42,000 / 100,000 | Matches: 3 | ETA: 4h 12m`
4. On completion: print summary + send final Telegram message

---

## Output

### `matches.csv`

```
address,seed_phrase,has_balance,balance_eth,has_tx,discovered_at
0xABC...,word1 word2 ... word12,true,0.0042,true,2026-04-30T18:22:01
```

### Console

Live progress line updated in place:
```
Checked: 42,000 / 100,000 | Matches: 3 | Rate: 4.9 req/s | ETA: 4h 12m
```

---

## Dependencies (`requirements.txt`)

```
aiohttp>=3.9
mnemonic>=0.21
eth-account>=0.11
asyncio-throttle>=1.0
```

All other dependencies (`sqlite3`, `csv`, `asyncio`) are Python stdlib.

---

## Runtime Estimate

| Step | API Calls | Time at 5 req/s |
|---|---|---|
| Balance batch checks | 5,000 | ~17 min |
| Transaction existence checks | 100,000 | ~5.5 hours |
| **Total** | **105,000** | **~5.8 hours** |

Async processing eliminates idle gaps between calls, keeping throughput at the Etherscan free-tier ceiling of 5 req/sec.

---

## Non-Goals

- No proxy/multi-key rotation (single Etherscan free-tier key)
- No ERC-20 token balance checks
- No derivation of multiple addresses per seed phrase (index 0 only)
- No GUI
