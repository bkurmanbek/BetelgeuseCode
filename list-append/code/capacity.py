"""Length is not capacity: watch a list's spare slots with sys.getsizeof alone (no ctypes, any CPython 3).

    python3 code/capacity.py            # append 0 … 24 one at a time; well under a second
    python3 code/capacity.py --quick    # the first 9 appends
    python3 code/capacity.py --n 100    # further

What it shows:
  * sys.getsizeof([]) and the pointer size: capacity = (getsizeof(lst) - getsizeof([])) // pointer size
  * after every append: the length, the bytes, the capacity, the spare slots, and a mark where the list asked
    for a bigger block (the capacity jumped). Most appends just use a spare slot.
  * other ways to build a list of the same length and the capacity each one gets: little or no spare room
    unless the list grew by appending

sys.getsizeof counts the list object and its block of slots, never the objects the slots point at.
"""

from __future__ import annotations

import argparse
import platform
import struct
import sys

P = struct.calcsize("P")
EMPTY = sys.getsizeof([])


def capacity(lst: list) -> int:
    return (sys.getsizeof(lst) - EMPTY) // P


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=25, help="appends to watch (default 25)")
    ap.add_argument("--quick", action="store_true", help="only the first 9 appends")
    a = ap.parse_args()
    n = 9 if a.quick else a.n

    print(f"{platform.python_implementation()} {platform.python_version()} on {platform.machine()}")
    print(f"sys.getsizeof([]) = {EMPTY} bytes: the list object, no slots yet")
    print(f"pointer size      = {P} bytes: one slot\n")
    print(f"{'after':<18}{'len':>5}{'bytes':>8}{'capacity':>10}{'spare':>7}")
    lst, last = [], 0
    print(f"{'lst = []':<18}{0:>5}{sys.getsizeof(lst):>8}{capacity(lst):>10}{0:>7}")
    for i in range(n):
        lst.append(i)
        cap = capacity(lst)
        mark = f"   ← a bigger block: {last} → {cap} slots" if cap != last else ""
        print(f"{f'lst.append({i})':<18}{len(lst):>5}{sys.getsizeof(lst):>8}{cap:>10}{cap - len(lst):>7}{mark}")
        last = cap

    k = len(lst)
    print(f"\nThe same {k} items, built other ways (capacity = what getsizeof shows):")
    built = {
        "appended one by one": lst,
        f"[i for i in range({k})]": [i for i in range(k)],
        f"list(range({k}))": list(range(k)),
        f"[None] * {k}": [None] * k,
        "lst.copy()": lst.copy(),
        "lst[:]": lst[:],
    }
    for name, other in built.items():
        print(f"  {name:<26} len {len(other):>4}   capacity {capacity(other):>4}   spare {capacity(other) - len(other):>4}")
    print("A comprehension appends (the LIST_APPEND bytecode), so it grows like append and keeps its spare room;")
    print("the others know the length up front and ask for a block that just fits it (give or take a slot).")


if __name__ == "__main__":
    main()
