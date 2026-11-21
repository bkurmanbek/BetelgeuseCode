"""Watch append from inside the list: nums = [] then append 3, 1, 4, 1, 7, reading the list's own fields.

    python3 code/watch_append.py            # the notes' five appends; well under a second
    python3 code/watch_append.py --quick    # the same (it is already quick)
    python3 code/watch_append.py --items 3 1 4 1 7 9 2 6 5 3   # your own items

After every step it prints the length (ob_size), the capacity (allocated, checked against sys.getsizeof), the
bytes, the address of the block of slots (ob_item) and the list's own id. You see:
  * the empty list has no block at all (ob_item is NULL, capacity 0)
  * the first append asks for a block of four slots, not one
  * the next three appends write one arrow each into a spare slot: the block address doesn't change
  * append(7) finds the block full: CPython asks for a bigger one (list_resize in Objects/listobject.c), the
    arrows are copied across, the old block is handed back; ob_item changes, id(nums) never does

Needs CPython (it reads the struct fields with ctypes); listpeek.check() stops with a message elsewhere.
Addresses differ from the notes' and from run to run; whether a bigger block lands at a new address is the
memory allocator's choice (it can sometimes grow the block where it is).
"""

from __future__ import annotations

import argparse
import sys

from listpeek import about, capacity, check, fields, slots


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--items", nargs="*", type=int, default=[3, 1, 4, 1, 7], help="what to append (default 3 1 4 1 7)")
    ap.add_argument("--quick", action="store_true", help="accepted for symmetry: the run is already quick")
    a = ap.parse_args()
    check()
    print(about() + "\n")

    nums = []
    f = fields(nums)
    head = f"{'step':<18}{'len':>4}{'cap':>5}{'bytes':>7}   {'block (ob_item)':<16}{'id(nums)':<16}what happened"
    print(head)
    print("-" * len(head) + "-" * 30)
    print(f"{'nums = []':<18}{f['len']:>4}{f['cap']:>5}{sys.getsizeof(nums):>7}   {'NULL':<16}{id(nums):<#16x}"
          "an empty list has no block yet")
    list_id = id(nums)
    for x in a.items:
        before = fields(nums)
        nums.append(x)
        after = fields(nums)
        assert after["cap"] == capacity(nums), "ctypes and sys.getsizeof disagree on the capacity"
        if after["cap"] == before["cap"]:
            what = f"one arrow written into slot {after['len'] - 1}; nothing else moved"
        elif not before["block"]:
            what = f"first block: {after['cap']} slots at once"
        elif after["block"] != before["block"]:
            what = f"full: a bigger block ({after['cap']} slots) elsewhere, {before['len']} arrows copied, old one freed"
        else:
            what = f"full: the allocator grew the block in place to {after['cap']} slots"
        print(f"{f'nums.append({x})':<18}{after['len']:>4}{after['cap']:>5}{sys.getsizeof(nums):>7}   "
              f"{after['block']:<#16x}{id(nums):<#16x}{what}")

    print(f"\nid(nums) never changed: {id(nums) == list_id}. The list object stays put; only its block moves.")
    print("The slots now:", ", ".join(f"{s:#x}" for s in slots(nums)))
    print("id of each item:", ", ".join(f"{id(x):#x}" for x in nums))


if __name__ == "__main__":
    main()
