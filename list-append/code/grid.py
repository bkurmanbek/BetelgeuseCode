"""Why `[[0] * 3] * 3` changes three rows at once: the outer list's three slots hold one address.

    python3 code/grid.py                # the notes' grid; well under a second
    python3 code/grid.py --quick        # the same (it is already quick)

What it shows:
  * id() of each row of [[0] * 3] * 3: one number, three times; the outer list's slots read from memory say
    the same (CPython)
  * grid[0][0] = 9, then the grid printed: every row changed, because there is one row
  * the inner list's reference count: three arrows from the grid (+1 for the call that asks)
  * [[0] * 3 for _ in range(3)]: three rows, three ids, one change in one row
  * copy.copy vs copy.deepcopy on the fixed grid: the first copies the outer arrows, the second follows them

`* 3` on a list copies its slots (list_repeat in Objects/listobject.c copies the pointers and adds to each
object's reference count); nothing is copied *behind* the arrows.
"""

from __future__ import annotations

import argparse
import copy
import sys

from listpeek import about, layout_ok, slots


def ids(rows) -> str:
    return ", ".join(f"{id(r):#x}" for r in rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help="accepted for symmetry: the run is already quick")
    ap.parse_args()
    raw, why = layout_ok()
    print(about() + ("" if raw else f"\n(raw slot reads skipped: {why})"))

    grid = [[0] * 3] * 3
    print("\ngrid = [[0] * 3] * 3")
    print(f"  id of each row:            {ids(grid)}")
    if raw:
        print(f"  the outer list's slots:    {', '.join(f'{a:#x}' for a in slots(grid))}")
    print(f"  grid[0] is grid[2]:        {grid[0] is grid[2]}")
    print(f"  rows that are distinct objects: {len({id(r) for r in grid})}")
    print(f"  sys.getrefcount(grid[0]):  {sys.getrefcount(grid[0])}   (three slots of grid, +1 for this call)")
    grid[0][0] = 9
    print(f"grid[0][0] = 9  →  {grid}")

    fixed = [[0] * 3 for _ in range(3)]
    print("\nfixed = [[0] * 3 for _ in range(3)]   (the expression runs three times: three new rows)")
    print(f"  id of each row:            {ids(fixed)}")
    print(f"  rows that are distinct objects: {len({id(r) for r in fixed})}")
    fixed[0][0] = 9
    print(f"fixed[0][0] = 9  →  {fixed}")

    shallow, deep = copy.copy(fixed), copy.deepcopy(fixed)
    print("\ncopies of `fixed`:")
    print(f"  copy.copy(fixed) is a new outer list: {shallow is not fixed}; its rows are the same rows: "
          f"{all(a is b for a, b in zip(shallow, fixed))}")
    print(f"  copy.deepcopy(fixed) has new rows too: {all(a is not b for a, b in zip(deep, fixed))}")
    print("  (fixed[:], list(fixed) and fixed.copy() are shallow copies like copy.copy)")


if __name__ == "__main__":
    main()
