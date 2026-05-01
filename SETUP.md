# ETH Wallet Scanner — Setup & Run Guide

## Prerequisites

You will need:
- An **Etherscan API key**
- A **Telegram Bot token** (from [@BotFather](https://t.me/BotFather))
- Your **Telegram Chat ID** (message [@userinfobot](https://t.me/userinfobot) to get it)

---

## Running on Desktop (Mac / Linux / Windows)

### 1. Install Python

Make sure Python 3.10+ is installed. Check with:

```bash
python3 --version
```

### 2. Set up a virtual environment

```bash
cd "Fox Eth"
python3 -m venv venv
```

Activate it:

- **Mac / Linux:**
  ```bash
  source venv/bin/activate
  ```
- **Windows:**
  ```bash
  venv\Scripts\activate
  ```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set environment variables

- **Mac / Linux:**
  ```bash
  export ETHERSCAN_API_KEY=your_etherscan_key
  export TELEGRAM_BOT_TOKEN=your_telegram_bot_token
  export TELEGRAM_CHAT_ID=your_chat_id
  ```

- **Windows (Command Prompt):**
  ```cmd
  set ETHERSCAN_API_KEY=your_etherscan_key
  set TELEGRAM_BOT_TOKEN=your_telegram_bot_token
  set TELEGRAM_CHAT_ID=your_chat_id
  ```

### 5. Run

```bash
python main.py
```

---

## Running on Termux (Android)

### 1. Install Termux

Download Termux from [F-Droid](https://f-droid.org/packages/com.termux/) (recommended over Play Store).

### 2. Update packages and install Python

```bash
pkg update && pkg upgrade
pkg install python
```

### 3. Install build tools (required for eth-account)

```bash
pkg install clang libffi openssl rust
```

### 4. Transfer project files to your phone

Copy the project folder to your phone via USB, then move it to Termux storage:

```bash
termux-setup-storage
cp -r /sdcard/Fox\ Eth ~/fox-eth
cd ~/fox-eth
```

Or clone/download it directly if hosted online.

### 5. Install dependencies

```bash
pip install aiohttp mnemonic eth-account asyncio-throttle
```

### 6. Set environment variables

```bash
export ETHERSCAN_API_KEY=your_etherscan_key
export TELEGRAM_BOT_TOKEN=your_telegram_bot_token
export TELEGRAM_CHAT_ID=your_chat_id
```

### 7. Run

```bash
python main.py
```

---

## Keeping it running in the background (Termux)

Install `tmux` to keep the scan running even after closing the Termux app:

```bash
pkg install tmux

# Start a named session
tmux new -s foxeth

# Run the scanner inside it
python main.py
```

**Detach** (leaves it running): `Ctrl+B` then `D`

**Reattach later:**
```bash
tmux attach -s foxeth
```

---

## Resuming after interruption

If the scan stops for any reason, just run it again:

```bash
python main.py
```

It will automatically resume from where it left off. No addresses are re-checked.

---

## Output

| File | Description |
|---|---|
| `state.db` | SQLite database tracking all generated addresses and progress |
| `matches.csv` | All matched addresses with seed phrases, balance, and tx status |

Matches are also sent to your Telegram in real time as they are found.

---

## Estimated Runtime

| Step | API Calls | Time |
|---|---|---|
| Balance checks (batched x20) | 5,000 | ~17 min |
| Transaction checks | 100,000 | ~5.5 hours |
| **Total** | **105,000** | **~5.8 hours** |

Runtime is limited by Etherscan's free-tier rate limit of 5 requests/second.
