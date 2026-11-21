"""The growth rule: append to an empty list N times, log every bigger block, and check CPython's formula.

    python3 code/growth_rule.py              # the notes' run: 1,000 appends; well under a second
    python3 code/growth_rule.py --quick      # the same (it is already quick)
    python3 code/growth_rule.py --n 1000000  # a million appends: under a second, about 50 MB

What it shows:
  * every length at which append found the block full, and the new capacity
  * the rule from list_resize (Objects/listobject.c, CPython 3.12; other versions may differ), checked:
        new capacity = (n + n // 8 + 6) rounded down to a multiple of 4      (n = the new length)
    i.e. about an eighth more room plus a few slots
  * the tally: how many appends asked for a bigger block, how many just wrote one arrow, how many of the bigger
    blocks landed at a new address (the arrows copied across) and how many the allocator grew in place
  * the arrows a resize had to carry, at most (the length at that moment), added up and per append

The capacity comes from sys.getsizeof (no ctypes); the block address from the list's ob_item field, read only on
CPython after listpeek's layout check. If your CPython uses another rule, the script says so instead of failing.
"""

from __future__ import annotations

import argparse
import ctypes
import sys

from listpeek import EMPTY, P, about, layout_ok


def rule(n: int) -> int:
    """CPython 3.12 list_resize, when one append overflows the block: n + n//8 + 6, rounded down to a multiple of 4."""
    return (n + (n >> 3) + 6) & ~3


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=1_000, help="appends (default 1,000, the notes' run)")
    ap.add_argument("--quick", action="store_true", help="accepted for symmetry: the default is already quick")
    ap.add_argument("--show", type=int, default=40, help="rows of the table to print (default 40)")
    a = ap.parse_args()
    raw, why = layout_ok()
    print(about() + ("" if raw else f"\n(block addresses skipped: {why})") + "\n")

    getsizeof = sys.getsizeof
    lst, cap, block = [], 0, 0
    rows, breaks = [], 0
    for i in range(a.n):
        lst.append(i)
        size = getsizeof(lst)
        new = (size - EMPTY) // P
        if new != cap:
            nb = (ctypes.c_void_p.from_address(id(lst) + 3 * P).value or 0) if raw else 0
            n = len(lst)
            moved = None if not raw else (bool(block) and nb != block)
            rows.append((n, cap, new, rule(n), moved, n - 1))
            breaks += new != rule(n)
            cap, block = new, nb

    print(f"{'length':>8}{'old cap':>9}{'new cap':>9}{'rule':>7}  {'block':<14}arrows to carry")
    for n, old, new, r, moved, carry in rows[:a.show]:
        where = "-" if moved is None else ("first block" if old == 0 else ("new address" if moved else "grew in place"))
        flag = "" if new == r else "   ← not the 3.12 rule"
        print(f"{n:>8,}{old:>9,}{new:>9,}{r:>7,}  {where:<14}{carry:,}{flag}")
    if len(rows) > a.show:
        print(f"{'…':>8}  ({len(rows) - a.show} more; --show {len(rows)} prints them all)")

    resizes = len(rows)
    carried = sum(r[5] for r in rows)
    print(f"\n{a.n:,} appends:")
    print(f"  {resizes} asked for a bigger block, {a.n - resizes:,} just wrote one arrow into a spare slot")
    if raw:
        moved = sum(1 for r in rows if r[4])
        print(f"  of the {resizes} bigger blocks: {moved} at a new address (arrows copied across), "
              f"{resizes - moved - 1} grown in place, 1 the first block")
    print(f"  arrows the resizes had to carry, at most: {carried:,} in all, {carried / a.n:.2f} per append")
    print(f"  final capacity {cap:,}: {cap - a.n:,} spare slots waiting")
    print(f"  the 3.12 rule matched {resizes - breaks} of {resizes} resizes"
          + ("" if not breaks else ": this CPython uses another growth rule (see Objects/listobject.c)"))


if __name__ == "__main__":
    main()
