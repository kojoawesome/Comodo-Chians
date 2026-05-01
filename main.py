import asyncio
import csv
import os
import sys
import time
from datetime import datetime, timezone

import state
import generator
import checker
import notifier
from config import TARGET_COUNT, BATCH_SIZE, CSV_PATH, DAILY_CALL_LIMIT, CALLS_PER_BATCH

# ── ANSI colours ────────────────────────────────────────────────────────────
R   = "\033[0m"    # reset
B   = "\033[1m"    # bold
DIM = "\033[2m"
RED = "\033[91m"
GRN = "\033[92m"
YLW = "\033[93m"
BLU = "\033[94m"
MAG = "\033[95m"
CYN = "\033[96m"
WHT = "\033[97m"
GRY = "\033[90m"


def _bar(current: int, total: int, width: int = 24, color: str = GRN) -> str:
    filled = int(width * current / total) if total > 0 else 0
    empty  = width - filled
    return f"{color}{'█' * filled}{GRY}{'░' * empty}{R}"


def _eta_str(checked: int, total: int, elapsed: float) -> str:
    if checked == 0 or elapsed == 0:
        return "?"
    rate = checked / elapsed
    secs = int((total - checked) / rate)
    h, rem = divmod(secs, 3600)
    m = rem // 60
    return f"{h}h {m:02d}m"


def _hms(secs: int) -> str:
    h, rem = divmod(max(secs, 0), 3600)
    m, s   = divmod(rem, 60)
    return f"{h}h {m:02d}m {s:02d}s"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _log(icon: str, msg: str, color: str = WHT) -> None:
    """Print a timestamped event line (scrolls up naturally)."""
    sys.stdout.write(f"\r{GRY}[{_now_utc()}]{R} {icon}  {color}{msg}{R}\n")
    sys.stdout.flush()


def _print_progress(
    batch: int,
    checked: int,
    matches: int,
    api_today: int,
    rate: float,
    elapsed: float,
) -> None:
    addr_bar = _bar(checked,   TARGET_COUNT,    16, GRN)
    api_bar  = _bar(api_today, DAILY_CALL_LIMIT, 16, CYN)
    eta      = _eta_str(checked, TARGET_COUNT, elapsed)
    pct      = checked / TARGET_COUNT * 100 if TARGET_COUNT else 0

    line = (
        f"\033[2K\r"
        f"{B}{MAG}#{batch}{R} "
        f"{addr_bar} {YLW}{checked:,}/{TARGET_COUNT:,}{R} ({pct:.1f}%) "
        f"{GRY}│{R} "
        f"API {api_bar} {CYN}{api_today:,}{R} "
        f"{GRY}│{R} "
        f"🎯{GRN}{B}{matches}{R} "
        f"{GRY}│{R} "
        f"{DIM}{rate:.1f}/s ETA {eta}{R}"
    )
    sys.stdout.write(line)
    sys.stdout.flush()


def _print_header() -> None:
    w = 72
    border = f"{BLU}{'═' * w}{R}"
    print(f"\n{border}")
    print(f"{BLU}║{R}  {B}{YLW}🦎  COMODO CHAINS ETH WALLET SCANNER{R}{' ' * (w - 38)}{BLU}║{R}")
    print(f"{BLU}║{R}  {DIM}Generating · Scanning · Alerting · Infinite batches{R}{' ' * (w - 54)}{BLU}║{R}")
    print(f"{border}\n")


def _select_word_count() -> int:
    """Interactive menu to choose 12 or 24 word seed phrases."""
    w = 48
    border = f"{BLU}{'─' * w}{R}"
    print(border)
    print(f"{BLU}│{R}  {B}Select seed phrase length:{R}{' ' * (w - 28)}{BLU}│{R}")
    print(f"{BLU}│{R}{' ' * (w)}{BLU}│{R}")
    print(f"{BLU}│{R}  {GRN}{B}[1]{R}  12 words  {DIM}(128-bit entropy){R}{' ' * (w - 35)}{BLU}│{R}")
    print(f"{BLU}│{R}  {YLW}{B}[2]{R}  24 words  {DIM}(256-bit entropy){R}{' ' * (w - 35)}{BLU}│{R}")
    print(f"{BLU}│{R}{' ' * (w)}{BLU}│{R}")
    print(border)

    while True:
        try:
            choice = input(f"\n{B}Enter choice [1/2]:{R} ").strip()
            if choice == "1":
                return 12
            elif choice == "2":
                return 24
            else:
                print(f"{RED}Invalid choice. Enter 1 or 2.{R}")
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)


def _wait_for_daily_reset(reset_at: float) -> None:
    """Block with a live countdown until the Etherscan daily limit resets."""
    asyncio.run(notifier.send_rate_limit_wait(int(reset_at - time.time())))
    _log("⏳", f"{YLW}Daily API limit reached. Waiting for UTC midnight reset…{R}")
    try:
        while True:
            secs_left = int(reset_at - time.time())
            if secs_left <= 0:
                break
            sys.stdout.write(
                f"\r{GRY}   └─ Resets in {R}{YLW}{B}{_hms(secs_left)}{R}   "
            )
            sys.stdout.flush()
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        raise
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    _log("✅", f"{GRN}Daily limit reset. Resuming…{R}")


def _ensure_csv() -> None:
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow([
                "address", "seed_phrase",
                "matched_chains",
                "ethereum_eth", "bsc_bnb", "polygon_matic",
                "arbitrum_eth", "base_eth", "optimism_eth",
                "has_eth_tx", "has_token_tx",
                "discovered_at",
            ])


def _append_csv(result: dict) -> None:
    cb = result.get("chain_balances", {})
    with open(CSV_PATH, "a", newline="") as f:
        csv.writer(f).writerow([
            result["address"],
            result["seed_phrase"],
            ",".join(result.get("matched_chains", [])),
            cb.get("ethereum", 0.0),
            cb.get("bsc", 0.0),
            cb.get("polygon", 0.0),
            cb.get("arbitrum", 0.0),
            cb.get("base", 0.0),
            cb.get("optimism", 0.0),
            result["has_tx"],
            result["has_token_tx"],
            datetime.utcnow().isoformat(),
        ])


# ── Main loop ────────────────────────────────────────────────────────────────

def run_batch(batch_number: int, total_generated: int, total_checked: int, word_count: int = 12) -> int:
    """
    Run one full batch of TARGET_COUNT address checks.
    Returns total matches found in this batch.
    """
    matches    = 0
    start_time = time.monotonic()

    _log("🚀", f"{GRN}{B}Batch #{batch_number} started{R} — scanning {TARGET_COUNT:,} addresses "
                f"({YLW}{word_count}-word seeds{R})")
    asyncio.run(notifier.send_new_batch_start(batch_number))

    while total_checked < TARGET_COUNT:
        # ── Check / reset daily limit ─────────────────────────────────────
        if state.maybe_reset_daily_calls():
            _log("🔄", f"{CYN}Daily API counter reset (UTC midnight passed){R}")

        p = state.get_progress()
        api_today = p["api_calls_today"]
        reset_at  = p["daily_reset_at"]

        if api_today + CALLS_PER_BATCH > DAILY_CALL_LIMIT:
            sys.stdout.write("\n")  # clear progress line
            _wait_for_daily_reset(reset_at)
            state.maybe_reset_daily_calls()
            api_today = 0

        # ── Fill pending queue ────────────────────────────────────────────
        pending = state.get_pending_batch(BATCH_SIZE)
        while len(pending) < BATCH_SIZE and total_generated < TARGET_COUNT:
            seed, address = generator.generate_wallet(word_count)
            if state.save_address(address, seed):
                state.increment_generated()
                total_generated += 1
        pending = state.get_pending_batch(BATCH_SIZE)
        if not pending:
            break

        # ── Check batch ───────────────────────────────────────────────────
        results = asyncio.run(checker.check_batch(pending))
        state.add_api_calls(CALLS_PER_BATCH)
        api_today += CALLS_PER_BATCH

        # ── Process results ───────────────────────────────────────────────
        for r in results:
            if r["match"]:
                matches += 1
                _append_csv(r)
                sys.stdout.write("\n")
                chains_str = ",".join(r.get("matched_chains", [])) or "none"
                _log(
                    "🎯",
                    f"{GRN}{B}Match!{R}  {r['address']}  "
                    f"Chains: {YLW}{chains_str}{R}  "
                    f"Tokens: {'Yes' if r['has_token_tx'] else 'No'}  "
                    f"TX: {'Yes' if r['has_tx'] else 'No'}",
                )
                asyncio.run(notifier.send_match(
                    r["address"], r["seed_phrase"],
                    r.get("chain_balances", {}),
                    r["has_tx"], r["has_token_tx"],
                ))
            state.mark_checked(
                r["address"], r["has_balance"], r["has_tx"],
                r.get("has_token_tx", False),
                ",".join(r.get("matched_chains", [])),
            )
            total_checked += 1

        # ── Progress line ─────────────────────────────────────────────────
        elapsed = time.monotonic() - start_time
        rate    = total_checked / elapsed if elapsed > 0 else 0
        _print_progress(batch_number, total_checked, matches, api_today, rate, elapsed)

    return matches


def main() -> None:
    state.init_db()
    _ensure_csv()
    _print_header()

    p = state.get_progress()
    batch_number    = p["batch_number"]
    total_generated = p["total_generated"]
    total_checked   = p["total_checked"]
    word_count      = p.get("mnemonic_strength", 12)

    if total_checked > 0:
        _log("↩️ ", f"{YLW}Resuming Batch #{batch_number} from "
                     f"{total_checked:,} / {TARGET_COUNT:,} "
                     f"({word_count}-word seeds){R}")
    else:
        print()
        word_count = _select_word_count()
        state.set_mnemonic_strength(word_count)
        print()
        _log("▶️ ", f"{GRN}Starting Batch #{batch_number} with {word_count}-word seed phrases{R}")

    try:
        while True:
            batch_matches = run_batch(batch_number, total_generated, total_checked, word_count)

            # ── Batch complete ────────────────────────────────────────────
            sys.stdout.write("\n")
            _log(
                "✅",
                f"{GRN}{B}Batch #{batch_number} complete!{R}  "
                f"Checked {TARGET_COUNT:,}  │  Matches: {GRN}{batch_matches}{R}",
            )
            asyncio.run(notifier.send_batch_complete(batch_number, TARGET_COUNT, batch_matches))

            # ── Start next batch ──────────────────────────────────────────
            batch_number = state.start_new_batch()
            state.set_mnemonic_strength(word_count)  # carry choice into new batch
            total_generated = 0
            total_checked   = 0
            print()

    except KeyboardInterrupt:
        p = state.get_progress()
        sys.stdout.write("\n")
        _log("🛑", f"{YLW}Interrupted. Progress saved — run again to resume.{R}")
        _log("📊", f"Batch #{p['batch_number']}  │  "
                    f"Checked: {p['total_checked']:,}  │  "
                    f"API calls today: {p['api_calls_today']:,}")
        sys.exit(0)


if __name__ == "__main__":
    main()
