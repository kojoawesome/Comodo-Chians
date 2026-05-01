import os

ETHERSCAN_API_KEY = os.environ["ETHERSCAN_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TARGET_COUNT    = 100_000   # addresses per batch
BATCH_SIZE      = 20        # Etherscan getbalancemulti max
RATE_LIMIT      = 5         # requests per second (Etherscan free tier)
DAILY_CALL_LIMIT = 100_000  # Etherscan daily API call cap
# Each batch of 20 addresses costs 21 calls (1 balancemulti + 20 txlist)
CALLS_PER_BATCH = 21

ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"
ETHERSCAN_CHAIN_ID = "1"  # Ethereum mainnet
TELEGRAM_BASE  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
DB_PATH  = "state.db"
CSV_PATH = "matches.csv"
