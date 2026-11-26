"""A list slot holds an arrow, not the item: read the slots of `nums = [3, 1, 4, 1]` and compare them with id().

    python3 code/arrows.py              # the notes' list; well under a second
    python3 code/arrows.py --quick      # the same (it is already quick)

What it shows, from the running interpreter:
  * the list object's own address and size, and the address of its block of slots
  * each slot read from memory next to id() of the item: the same number. The slot stores where the object is.
  * nums[1] is nums[3]: two slots, one object (CPython keeps one shared object for each int from -5 to 256)
  * the same four slots holding four strings of 1,000 letters: the list's size doesn't change, the strings
    live elsewhere

Your addresses differ from the notes' (and from run to run); the equalities don't. The raw slot read needs
CPython; elsewhere the script prints the parts that need only id and sys.getsizeof.
"""

from __future__ import annotations

import argparse
import sys

from listpeek import EMPTY, P, about, capacity, fields, layout_ok, slots


def build(items) -> list:
    """Build the list the way the video does, one append at a time."""
    lst = []
    for x in items:
        lst.append(x)
    return lst


def show(name: str, lst: list, raw: bool) -> None:
    print(f"{name}: the list object at {id(lst):#x}, sys.getsizeof = {sys.getsizeof(lst)} bytes "
          f"= {EMPTY} + {capacity(lst)} slots × {P}")
    if raw:
        print(f"  its block of slots at {fields(lst)['block']:#x}")
    print(f"  {'slot':<5}{'holds (read from the block)':<30}{'id(item)':<18}{'item':<12}getsizeof(item)")
    held = slots(lst) if raw else [None] * len(lst)
    for i, (x, h) in enumerate(zip(lst, held)):
        shown = repr(x) if len(repr(x)) < 12 else repr(x)[:6] + "…'"
        print(f"  {i:<5}{(f'{h:#x}' if h is not None else '(needs CPython)'):<30}{id(x):<#18x}{shown:<12}"
              f"{sys.getsizeof(x)}")
    if raw:
        print(f"  every slot == id(item): {slots(lst) == [id(x) for x in lst]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help="accepted for symmetry: the run is already quick")
    ap.parse_args()

    raw, why = layout_ok()
    print(about())
    if not raw:
        print(f"(raw slot reads skipped: {why})")
    print()

    nums = build([3, 1, 4, 1])
    show("nums = [3, 1, 4, 1]", nums, raw)
    print(f"\nnums[1] is nums[3] → {nums[1] is nums[3]}: both slots point at one int object, at {id(nums[1]):#x}")
    print("  (CPython keeps one ready-made object for each int from -5 to 256: every 1 a program uses is that one)")
    print(f"  id(nums) {id(nums):#x} vs id(nums[0]) {id(nums[0]):#x}: the list and its items are separate objects")

    print()
    words = build([ch * 1000 for ch in "abcd"])
    show("words = four strings of 1,000 letters", words, raw)
    held = sum(sys.getsizeof(w) for w in words)
    print(f"\nsys.getsizeof(nums) = {sys.getsizeof(nums)}, sys.getsizeof(words) = {sys.getsizeof(words)}: the list "
          f"counts its slots, not what they point at.")
    print(f"The four strings take {held:,} bytes of their own, somewhere else in memory.")


if __name__ == "__main__":
    main()
