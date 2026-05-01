from mnemonic import Mnemonic
from eth_account import Account

Account.enable_unaudited_hdwallet_features()

_mnemo = Mnemonic("english")

# strength → word count
STRENGTH_MAP = {
    12: 128,  # 128-bit entropy → 12 words
    24: 256,  # 256-bit entropy → 24 words
}


def generate_wallet(word_count: int = 12) -> tuple[str, str]:
    """Return a (seed_phrase, address) tuple using a random BIP39 mnemonic."""
    strength = STRENGTH_MAP.get(word_count, 128)
    seed_phrase = _mnemo.generate(strength=strength)
    account = Account.from_mnemonic(seed_phrase, account_path="m/44'/60'/0'/0/0")
    return seed_phrase, account.address
