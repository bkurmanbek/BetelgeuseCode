"""The front of a list: insert(0, x) shifts every arrow one slot right. A deque adds a slot on the left instead.

    python3 code/front.py              # the notes' list; well under a second
    python3 code/front.py --quick      # the same (it is already quick)

What it shows, read from memory (CPython):
  * nums = [3, 1, 4, 1, 7] built like the video, its slots before nums.insert(0, 2) and after: the address that
    was in slot i is now in slot i + 1, for every i, and slot 0 holds the 2. Same block, same capacity: only
    arrows moved (ins1 in Objects/listobject.c runs `items[i+1] = items[i]` from the last slot down)
  * the same for lists of 10, 1,000 and 100,000 items, every slot read before and after: the whole length
    moves, every time
  * collections.deque: a chain of fixed-size blocks with a free slot index at each end. appendleft writes into
    the free slot to the left of the first item, or links a new block on the left when there is none. The script
    reads the deque's left block and index (Modules/_collectionsmodule.c) and checks that the old first item is
    still in the very same slot after appendleft. sys.getsizeof shows one more block at a time.

The deque peek checks its assumptions (the slot it reads must hold id(d[0])) and is skipped if they don't hold.
"""

from __future__ import annotations

import argparse
import ctypes
import sys
from collections import deque

from listpeek import P, about, check, fields, slots


def build(items) -> list:
    lst = []
    for x in items:
        lst.append(x)
    return lst


def deque_left(d: deque) -> tuple[int, int]:
    """(address of the left block, index of the first item in it): dequeobject's leftblock and leftindex.
    Layout (CPython 3.12): ob_refcnt, ob_type, ob_size, leftblock, rightblock, leftindex, …; a block is
    leftlink, data[BLOCKLEN], rightlink, so data[i] sits at block + P + i * P."""
    base = id(d)
    block = ctypes.c_void_p.from_address(base + 3 * P).value or 0
    index = ctypes.c_ssize_t.from_address(base + 5 * P).value
    return block, index


def slot_in_block(block: int, index: int) -> int:
    return ctypes.c_void_p.from_address(block + P + index * P).value or 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help="accepted for symmetry: the run is already quick")
    ap.parse_args()
    check()
    print(about() + "\n")

    nums = build([3, 1, 4, 1, 7])
    before, fb = slots(nums), fields(nums)
    nums.insert(0, 2)
    after, fa = slots(nums), fields(nums)
    print("nums.insert(0, 2) on", nums[1:], "→", nums)
    print(f"  block {fb['block']:#x} → {fa['block']:#x}   capacity {fb['cap']} → {fa['cap']}   "
          f"length {fb['len']} → {fa['len']}")
    print(f"  {'slot':<6}{'before':<16}{'after':<16}")
    for i in range(len(after)):
        b = f"{before[i]:#x}" if i < len(before) else "(spare)"
        note = "← the new 2" if i == 0 else f"← was in slot {i - 1}"
        print(f"  {i:<6}{b:<16}{after[i]:<#16x}{note}")
    shifted = sum(after[i + 1] == before[i] for i in range(len(before)))
    print(f"  arrows that moved one slot right: {shifted} of {len(before)}, to add one item")

    print("\nThe same at the front of longer lists (every slot read before and after the insert):")
    for n in (10, 1_000, 100_000):
        lst = list(range(n))
        old = slots(lst)
        lst.insert(0, -1)
        new = slots(lst)
        moved = sum(new[i + 1] == old[i] for i in range(n))
        print(f"  length {n:>7,}: {moved:,} of {n:,} arrows now one slot to the right")

    print("\ncollections.deque, the structure built for both ends:")
    d = deque([3, 1, 4, 1, 7])
    block, index = deque_left(d)
    if slot_in_block(block, index) != id(d[0]):
        print("  (this CPython lays the deque out differently: peek skipped)")
    else:
        first = d[0]
        d.appendleft(2)
        print(f"  before appendleft(2): the 3 sits in block {block:#x}, slot {index}")
        print(f"  after: still there: {slot_in_block(block, index) == id(first)}; the 2 went into slot "
              f"{deque_left(d)[1]} of block {deque_left(d)[0]:#x}. Nothing shifted.")
        last_block, last_size = deque_left(d)[0], sys.getsizeof(d)
        steps = []
        for i in range(300):
            d.appendleft(i)
            b, _ = deque_left(d)
            if b != last_block:
                steps.append((len(d), sys.getsizeof(d) - last_size))
                last_block, last_size = b, sys.getsizeof(d)
        gaps = sorted({b[0] - a[0] for a, b in zip(steps, steps[1:])})
        print(f"  300 more appendleft: {len(steps)} new blocks linked on the left, at lengths "
              f"{', '.join(str(n) for n, _ in steps)}")
        print(f"  (one block every {', '.join(map(str, gaps))} items: the block's slot count), each adding "
              f"{steps[0][1] if steps else 0} bytes to sys.getsizeof(d).")
        print("  Between two new blocks, appendleft writes one arrow into the free slot on the left; no item moves.")


if __name__ == "__main__":
    main()
