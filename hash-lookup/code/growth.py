"""Step 6: a hash table grows in jumps. sys.getsizeof and the real slot count, key by key, for a dict and a set.

    python3 code/growth.py               # up to 100 keys: under a second
    python3 code/growth.py --upto 5000

CPython 3.11 or newer, 64-bit, for the slot counts (read from memory with ctypes; elsewhere the script prints the
sizes only). Standard library only.

What to look at: getsizeof stays flat, then jumps. A dict jumps when its entries are two-thirds of its slots and
grows to the next power of two at least 3 × the keys it holds; a set allows three-fifths and grows to 4 × its
elements. Each jump is checked against that rule, replayed from Objects/dictobject.c and Objects/setobject.c.
"""

from __future__ import annotations

import argparse
import sys

import cpython_tables as ct


def set_grown_size(used: int) -> int:
    """Set: set_table_resize(so, used > 50000 ? used*2 : used*4): the smallest power of two above that."""
    minused = used * 2 if used > 50_000 else used * 4
    size = ct.MIN_SIZE
    while size <= minused:
        size <<= 1
    return size


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--upto", type=int, default=100)
    ap.add_argument("--quick", action="store_true", help="(the default run already takes under a second)")
    a = ap.parse_args()
    try:
        ct.check_interpreter()
        peek = True
    except ct.Unsupported as e:
        print(f"(slot counts skipped: {e})\n")
        peek = False

    print("dict with str keys: where sys.getsizeof jumps")
    print(f"{'keys':>7} {'bytes':>8} {'slots':>7} {'fit before next jump':>21}   rule")
    d: dict = {}
    last = sys.getsizeof(d)
    print(f"{0:>7} {last:>8} {'shared':>7} {0:>21}")
    for n in range(1, a.upto + 1):
        d[f"key{n:06d}"] = n
        size = sys.getsizeof(d)
        if size != last:
            row = f"{n:>7} {size:>8}"
            if peek:                               # read the table only at a jump: reading it is O(slots)
                t = ct.read_dict(d)
                cap = ct.usable_fraction(t["size"])
                want = ct.MIN_SIZE if n == 1 else ct.grown_size(n - 1)
                rule = "first key: 8 slots" if n == 1 else f"full at {n - 1}: 3 × {n - 1} = {3 * (n - 1)} → {want}"
                row += f" {t['size']:>7} {cap:>21}   {rule}{'' if t['size'] == want else '  (rule MISMATCH)'}"
            print(row)
            last = size

    print("\nset: where sys.getsizeof jumps")
    print(f"{'items':>7} {'bytes':>8} {'slots':>7}   rule")
    s: set = set()
    last = sys.getsizeof(s)
    print(f"{0:>7} {last:>8} {ct.read_set(s)['size'] if peek else '':>7}   (8 slots live inside the set object)")
    slots = ct.MIN_SIZE
    for n in range(1, a.upto + 1):
        s.add(f"key{n:06d}")
        size = sys.getsizeof(s)
        if size != last:
            row = f"{n:>7} {size:>8}"
            if peek:
                got, want = ct.read_set(s)["size"], set_grown_size(n)
                row += (f" {got:>7}   {n} × 5 ≥ 3 × {slots - 1}: grow for {'2' if n > 50_000 else '4'} × {n}"
                        f" → {want}{'' if got == want else '  (rule MISMATCH)'}")
                slots = got
            print(row)
            last = size
    print("\nThe bytes are the table only: the keys and values are separate objects, not counted by getsizeof.")


if __name__ == "__main__":
    main()
