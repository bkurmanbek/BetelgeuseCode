"""So that's why: a set iterates in slot order, a dict in the order keys went in. Read from the real tables.

    python3 code/set_order.py         # under a second (it starts three fresh Pythons to show the salt)

CPython 3.11 or newer, 64-bit, for the slot read-outs (ctypes); the rest runs anywhere. Standard library only.

What to look at:
  1. small ints are their own hash, so you can predict a set's order by hand: slot = n & 7;
  2. one more element can make the set grow, and then every element sits in a different slot: the order changes;
  3. str hashes are salted per process, so the same set of names can print in a different order in each run,
     while a dict built from the same names keeps the order they went in, run after run.
"""

from __future__ import annotations

import os
import subprocess
import sys

import cpython_tables as ct

NAMES = ["leo", "ana", "zoe", "ivy", "kai"]


def slots_line(s: set) -> str:
    try:
        t = ct.read_set(s)
    except ct.Unsupported as e:
        return f"(table not readable here: {e})"
    return f"{t['size']} slots: " + " ".join("." if x is None else repr(x) for x in t["slots"])


def main() -> None:
    nums = [12, 3, 7, 1]
    s = set(nums)
    print(f"1. set({nums})")
    print(f"   slot = n & 7:     {[(n, n & 7) for n in nums]}")
    print(f"   the real table:   {slots_line(s)}")
    print(f"   list(the set)  →  {list(s)}       ← slot order")
    print(f"   list(dict.fromkeys({nums})) → {list(dict.fromkeys(nums))}   ← insertion order")

    s = {16, 1, 2, 3}
    print(f"\n2. s = {{16, 1, 2, 3}}   list(s) → {list(s)}")
    print(f"   {slots_line(s)}      (16 & 7 = 0: first)")
    s.add(4)
    print(f"   s.add(4)            list(s) → {list(s)}")
    print(f"   {slots_line(s)}")
    print("   five elements is past three-fifths of 8 slots: the set grew to 32, and 16 & 31 = 16 put 16 last")

    print("\n3. the same five names in three fresh Pythons (no PYTHONHASHSEED):")
    code = f"n = {NAMES!r}; print(list(set(n)), list(dict.fromkeys(n)))"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
    for run in range(3):
        out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True).stdout.strip()
        set_part, dict_part = out.split("] [")
        print(f"   run {run + 1}: set {set_part}]   dict [{dict_part}")
    print("   The set's order follows the salted hashes; the dict's follows its entries list.")


if __name__ == "__main__":
    main()
