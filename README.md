# 🦎 Comodo Chains ETH Wallet Scanner

An autonomous multi-chain wallet scanner that generates random BIP39 seed phrases, derives their Ethereum addresses, and checks each one across 6 blockchains for native coin balances, ERC-20 token holdings, and transaction history. Matches are instantly sent to your Telegram and saved to a CSV file.

Runs forever in infinite batches — fully autonomous, resumable, and rate-limit aware.

---

## Features

- 🔑 Generates cryptographically random 12-word BIP39 seed phrases
- 🔍 Checks native balance across **6 chains** — Ethereum, BSC, Polygon, Arbitrum, Base, Optimism
- 🪙 Detects **ERC-20 token holdings** on Ethereum mainnet
- 📜 Checks **transaction history** on Ethereum mainnet
- 📬 Sends real-time Telegram alerts on every match with full breakdown
- ♾️ Infinite batch mode — automatically starts the next 100k batch when done
- ⏳ Daily API limit aware — pauses and counts down to UTC midnight reset, then resumes
- 💾 SQLite-backed state — no address is ever checked twice, even across restarts
- ↩️ Fully resumable — crash or stop anytime, re-run to continue exactly where you left off
- 🎨 Coloured terminal output with a live progress bar

---

## Supported Operating Systems

| Platform | Supported |
|---|---|
| macOS | ✅ |
| Linux (Ubuntu, Debian, Arch, etc.) | ✅ |
| Windows (via WSL recommended) | ✅ |
| Android (Termux) | ✅ |

---

## Chains Scanned

| Chain | Native Token | Checked |
|---|---|---|
| Ethereum | ETH | ✅ |
| BNB Smart Chain | BNB | ✅ |
| Polygon | MATIC | ✅ |
| Arbitrum One | ETH | ✅ |
| Base | ETH | ✅ |
| Optimism | ETH | ✅ |
| ERC-20 Tokens (Ethereum) | Any | ✅ |

---

## Requirements

- Python 3.10+
- Etherscan API key — [etherscan.io/apis](https://etherscan.io/apis)
- Telegram Bot token — create one via [@BotFather](https://t.me/BotFather)
- Your Telegram Chat ID — get it from [@userinfobot](https://t.me/userinfobot)

---

## Installation

### macOS / Linux

**1. Clone the repository**

```bash
git clone https://github.com/kojoawesome/Comodo-Chians.git
cd Comodo-Chians
```

**2. Create and activate a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Set environment variables**

```bash
export ETHERSCAN_API_KEY=your_etherscan_api_key
export TELEGRAM_BOT_TOKEN=your_telegram_bot_token
export TELEGRAM_CHAT_ID=your_telegram_chat_id
```

**5. Run**

```bash
python main.py
```

---

### Windows (WSL)

**1. Install WSL** (if not already)

```powershell
wsl --install
```

**2. Open a WSL terminal and follow the macOS / Linux steps above**

---

### Android (Termux)

**1. Install Termux** from [F-Droid](https://f-droid.org/packages/com.termux/) (recommended over Play Store)

**2. Update packages and install Python**

```bash
pkg update && pkg upgrade
pkg install python
```

**3. Install build tools** (required for `eth-account`)

```bash
pkg install clang libffi openssl rust
```

**4. Clone the repository**

```bash
pkg install git
git clone https://github.com/kojoawesome/Comodo-Chians.git
cd Comodo-Chians
```

**5. Install dependencies**

```bash
pip install -r requirements.txt
```

**6. Set environment variables**

```bash
export ETHERSCAN_API_KEY=your_etherscan_api_key
export TELEGRAM_BOT_TOKEN=your_telegram_bot_token
export TELEGRAM_CHAT_ID=your_telegram_chat_id
```

**7. Run**

```bash
python main.py
```

**Keep it running after closing Termux** using `tmux`:

```bash
pkg install tmux
tmux new -s comodo
python main.py
# Detach: Ctrl+B then D
# Reattach later: tmux attach -s comodo
```

---

## Configuration

All settings are in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `TARGET_COUNT` | `100,000` | Addresses per batch |
| `BATCH_SIZE` | `20` | Addresses per Etherscan call |
| `RATE_LIMIT` | `5` | Max API requests per second |
| `DAILY_CALL_LIMIT` | `100,000` | Etherscan free-tier daily cap |
| `CHAINS` | 6 chains | Chains to scan (edit to add/remove) |

---

## How It Works

```
Generate random 12-word BIP39 seed phrase
        ↓
Derive ETH address (BIP44: m/44'/60'/0'/0/0)
        ↓
Check native balance on 6 chains simultaneously (batched ×20)
        ↓
Check ETH transaction history on mainnet
        ↓
Check ERC-20 token transfers on mainnet
        ↓
Match? → Save to CSV + Send Telegram alert
        ↓
Repeat for 100,000 addresses → Batch complete → Start next batch
```

---

## Output

| File | Description |
|---|---|
| `state.db` | SQLite database — tracks every generated address and progress |
| `matches.csv` | All matched addresses with seed phrases, per-chain balances, and timestamps |

### `matches.csv` columns

```
address, seed_phrase, matched_chains, ethereum_eth, bsc_bnb, polygon_matic,
arbitrum_eth, base_eth, optimism_eth, has_eth_tx, has_token_tx, discovered_at
```

### Telegram alert example

```
🎯 Match Found!
0x4B8E3F2A1C9D7E6B5A4F3E2D1C0B9A8F7E6D5C4B

🔑 Seed:
witch collapse practice feed shame open despair creek road again ice eager

💰 Balances:
  • Ethereum: 0.042500 ETH
  • Bsc: 0.310000 BNB

📜 ETH Transactions: Yes
🪙 ERC-20 Tokens: Yes
```

---

## Runtime Estimate

| Step | API Calls | Time (free tier) |
|---|---|---|
| Native balance checks × 6 chains (batched ×20) | 30,000 | ~1.7 hours |
| ETH transaction checks | 100,000 | ~5.5 hours |
| ERC-20 token checks | 100,000 | ~5.5 hours |
| **Total per batch** | **230,000** | **~2.3 days** |

The daily API limit (100,000 calls) is hit well before one full batch completes. The scanner automatically pauses at the limit and resumes after the UTC midnight reset — no intervention needed.

---

## Resuming

Just re-run the script at any time:

```bash
python main.py
```

It will print `Resuming Batch #N from X / 100,000` and continue exactly where it left off.

---

## Dependencies

| Package | Purpose |
|---|---|
| `aiohttp` | Async HTTP client |
| `mnemonic` | BIP39 seed phrase generation |
| `eth-account` | BIP44 Ethereum address derivation |
| `asyncio-throttle` | API rate limiting |

---

## Disclaimer

This tool is for **educational purposes only**. The probability of randomly generating a seed phrase that corresponds to a funded wallet is astronomically small. Use responsibly and in accordance with applicable laws.

---

## License

MIT
