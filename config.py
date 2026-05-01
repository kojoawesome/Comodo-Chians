import os

ETHERSCAN_API_KEY = os.environ["ETHERSCAN_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TARGET_COUNT    = 100_000   # addresses per batch
BATCH_SIZE      = 20        # Etherscan getbalancemulti max
RATE_LIMIT      = 5         # requests per second (Etherscan free tier)
DAILY_CALL_LIMIT = 100_000  # Etherscan daily API call cap
# Per batch of 20: 1 balancemulti per chain + 20 txlist + 20 tokentx (mainnet)
# = len(CHAINS) + BATCH_SIZE + BATCH_SIZE = 6 + 20 + 20 = 46
CALLS_PER_BATCH = 46

ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"

# Chains to scan (Etherscan V2 supports all with the same API key)
CHAINS = {
    "ethereum": "1",
    "bsc":      "56",
    "polygon":  "137",
    "arbitrum": "42161",
    "base":     "8453",
    "optimism": "10",
}

# Native token symbols per chain (for display)
CHAIN_SYMBOLS = {
    "ethereum": "ETH",
    "bsc":      "BNB",
    "polygon":  "MATIC",
    "arbitrum": "ETH",
    "base":     "ETH",
    "optimism": "ETH",
}
TELEGRAM_BASE  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
DB_PATH  = "state.db"
CSV_PATH = "matches.csv"
