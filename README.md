# 🦎 Comodo Chains ETH Wallet Scanner

An autonomous Ethereum wallet scanner that generates random BIP39 seed phrases, derives their addresses, and checks each one against the Etherscan API for any ETH balance or transaction history. Matches are instantly sent to your Telegram and saved to a CSV file.

Runs forever in infinite batches — fully autonomous, resumable, and rate-limit aware.

---

## Features

- 🔑 Generates cryptographically random 12-word BIP39 seed phrases
- 🔍 Checks ETH balance **and** transaction history via Etherscan API
- 📬 Sends real-time Telegram alerts on every match
- ♾️ Infinite batch mode — automatically starts the next 100k batch when done
- ⏳ Daily API limit aware — pauses and counts down to UTC midnight reset, then resumes
- 💾 SQLite-backed state — no address is ever checked twice, even across restarts
- ↩️ Fully resumable — crash or stop anytime, re-run to continue exactly where you left off
- 🎨 Coloured terminal output with a live progress bar

---

## Supported Operating Systems

| Platform                           | Supported |
| ---------------------------------- | --------- |
| macOS                              | ✅        |
| Linux (Ubuntu, Debian, Arch, etc.) | ✅        |
| Windows (via WSL recommended)      | ✅        |
| Android (Termux)                   | ✅        |

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
git clone https://github.com/yourusername/Comodo-Chians-Chians-eth.git
cd Comodo-Chians-Chians-Chians-eth
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

**4. Transfer project files to your device**

```bash
termux-setup-storage
cp -r /sdcard/Comodo-Chians-Chians-Chians-eth ~/Comodo-Chians-Chians-Chians-eth
cd ~/Comodo-Chians-Chians-Chians-eth
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
tmux new -s Comodo-Chians-Chianseth
python main.py
# Detach: Ctrl+B then D
# Reattach later: tmux attach -s Comodo-Chians-Chianseth
```

---

## Configuration

All settings are in `config.py`:

| Setting            | Default   | Description                   |
| ------------------ | --------- | ----------------------------- |
| `TARGET_COUNT`     | `100,000` | Addresses per batch           |
| `BATCH_SIZE`       | `20`      | Addresses per Etherscan call  |
| `RATE_LIMIT`       | `5`       | Max API requests per second   |
| `DAILY_CALL_LIMIT` | `100,000` | Etherscan free-tier daily cap |

---

## How It Works

```
Generate random 12-word seed phrase
        ↓
Derive ETH address (BIP44: m/44'/60'/0'/0/0)
        ↓
Batch check balance (20 at a time via getbalancemulti)
        ↓
Check transaction history (txlist, 1 result per address)
        ↓
Match? → Save to CSV + Send Telegram alert
        ↓
Repeat for 100,000 addresses → Batch complete → Start next batch
```

---

## Output

| File          | Description                                                      |
| ------------- | ---------------------------------------------------------------- |
| `state.db`    | SQLite database — tracks every generated address and progress    |
| `matches.csv` | All matched addresses with seed phrases, balance, and timestamps |

### Telegram alert example

```
🎯 Match Found!
0x4B8E3F2A1C9D7E6B5A4F3E2D1C0B9A8F7E6D5C4B

🔑 Seed: witch collapse practice feed shame open despair creek road again ice eager
💰 Balance: 0.042500 ETH
📜 Transactions: Yes
```

---

## Runtime Estimate

| Step                         | API Calls   | Time (free tier) |
| ---------------------------- | ----------- | ---------------- |
| Balance checks (batched ×20) | 5,000       | ~17 min          |
| Transaction checks           | 100,000     | ~5.5 hours       |
| **Total per batch**          | **105,000** | **~5.8 hours**   |

The daily API limit (100,000 calls) is hit before one full batch completes. The scanner automatically pauses at the limit and resumes after the UTC midnight reset — no intervention needed.

---

## Resuming

Just re-run the script at any time:

```bash
python main.py
```

It will print `Resuming Batch #N from X / 100,000` and continue from where it left off.

---

## Dependencies

| Package            | Purpose                           |
| ------------------ | --------------------------------- |
| `aiohttp`          | Async HTTP client                 |
| `mnemonic`         | BIP39 seed phrase generation      |
| `eth-account`      | BIP44 Ethereum address derivation |
| `asyncio-throttle` | API rate limiting                 |

---

## Disclaimer

This tool is for **educational purposes only**. The probability of randomly generating a seed phrase that corresponds to a funded wallet is astronomically small. Use responsibly and in accordance with applicable laws.

---

## License

MIT
