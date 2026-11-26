"""Steps 1 and 2: hash() turns a key into one big integer, and the lowest bits of that integer pick the slot.

    python3 code/hash_slot.py              # the lesson's keys with PYTHONHASHSEED=0: the numbers in the video
    python3 code/hash_slot.py --salted     # the same keys with this process's own random salt
    python3 code/hash_slot.py maria omar   # your own keys

Under a second (it starts a few fresh Pythons to show the salt). Standard library only, any Python 3.8+.

What to look at: the same key always gives the same number inside one process; a str gets a new number in every
new process unless PYTHONHASHSEED is fixed; an int is its own hash; `hash & 7` is just the last three bits.
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys

KEYS = ["leo", "ana", "zoe", "ivy", "kai", "tom"]   # the lesson's dictionary, in the order it is built
MISSING = "ron"                                     # a key the lesson looks up and doesn't find


def fresh_hash(key: str, seed: str | None) -> str:
    """hash(key) in a brand-new Python process, with PYTHONHASHSEED=seed (None: unset, a random salt)."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
    if seed is not None:
        env["PYTHONHASHSEED"] = seed
    out = subprocess.run([sys.executable, "-c", f"print(hash({key!r}))"], env=env, capture_output=True, text=True)
    return out.stdout.strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("keys", nargs="*", help="keys to hash (default: the lesson's)")
    ap.add_argument("--salted", action="store_true", help="keep this process's random salt")
    a = ap.parse_args()
    if not a.salted and os.environ.get("PYTHONHASHSEED") != "0":
        env = {**os.environ, "PYTHONHASHSEED": "0"}     # re-run with the lesson's fixed seed
        sys.exit(subprocess.run([sys.executable, *sys.argv], env=env).returncode)

    hi = sys.hash_info
    seed = os.environ.get("PYTHONHASHSEED", "random")
    print(f"{platform.python_implementation()} {platform.python_version()} · str hash: {hi.algorithm}, "
          f"{hi.width}-bit · PYTHONHASHSEED={seed}\n")

    keys = a.keys or KEYS + [MISSING]
    w = max(6, *(len(repr(k)) for k in keys))
    print(f"{'key':<{w}} {'hash(key)':>21}   {'last 8 bits':<12} {'& 7':>4} {'& 15':>5}")
    for k in keys:
        h = hash(k)
        note = "   (not in the lesson's dict)" if k == MISSING and not a.keys else ""
        print(f"{k!r:<{w}} {h:>21}   ...{h & 0xFF:08b}  {h & 7:>4} {h & 15:>5}{note}")
    print("\n& 7 keeps the last 3 bits: a slot from 0 to 7 in a table of 8 slots. & 15 keeps 4 bits: 16 slots.")
    print("A table's size is always a power of two, so 'hash mod size' is just this mask: no division.")

    k = keys[0]
    print(f"\nhash({k!r}) in three fresh Pythons, no seed set:")
    runs = [fresh_hash(k, None) for _ in range(3)]
    for r in runs:
        print(f"    {r:>21}")
    print(f"  all different: {len(set(runs)) == 3}   (str and bytes hashes are salted per process)")
    fixed = [fresh_hash(k, "0") for _ in range(2)]
    print(f"hash({k!r}) with PYTHONHASHSEED=0, twice: {fixed[0]}, {fixed[1]}   same: {fixed[0] == fixed[1]}")

    print("\nints are not salted, and a small int is its own hash:")
    print(f"  hash(31) = {hash(31)}   hash(-1) = {hash(-1)} (inside CPython -1 means 'error', so it is replaced)")
    print(f"  hash(2**61) = {hash(2**61)}   (ints hash modulo 2**61 - 1 = sys.hash_info.modulus: {hi.modulus})")
    print(f"  hash(1) == hash(1.0) == hash(True): {hash(1) == hash(1.0) == hash(True)}   (equal numbers, equal hashes)")


if __name__ == "__main__":
    main()
