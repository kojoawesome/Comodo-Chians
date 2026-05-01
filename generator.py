from mnemonic import Mnemonic
from eth_account import Account

Account.enable_unaudited_hdwallet_features()

_mnemo = Mnemonic("english")


def generate_wallet() -> tuple[str, str]:
    """Return a (seed_phrase, address) tuple from a fresh random 12-word mnemonic."""
    seed_phrase = _mnemo.generate(strength=128)  # 128 bits → 12 words
    account = Account.from_mnemonic(seed_phrase, account_path="m/44'/60'/0'/0/0")
    return seed_phrase, account.address
