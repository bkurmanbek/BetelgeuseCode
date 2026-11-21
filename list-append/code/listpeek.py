"""Read a CPython list's own fields: the small toolkit the other scripts share.

    python3 code/listpeek.py            # checks this interpreter, then shows one list from the inside

A list object in CPython 3.12 (Include/cpython/listobject.h) is five machine words:

    offset 0 × P   ob_refcnt   how many references point at the list
    offset 1 × P   ob_type     → the `list` type
    offset 2 × P   ob_size     the length, what len() returns
    offset 3 × P   ob_item     the address of the block of slots (NULL while the list has none)
    offset 4 × P   allocated   how many slots that block has: the capacity

(P is the pointer size, 8 bytes on a 64-bit machine.) Each slot of the block holds one address: the arrow to an
object. `id(x)` is that address in CPython, so slot i of a list holds exactly id(lst[i]).

The capacity also shows without ctypes: sys.getsizeof(lst) is the empty list's size plus P bytes per slot, so

    capacity(lst) == (sys.getsizeof(lst) - sys.getsizeof([])) // P

Reading raw memory is only safe when the layout is the one above, so `check()` tests it on a throwaway list
first (length, capacity and one slot against id) and stops with a message on anything else: PyPy, a
free-threaded build, a future layout. Standard library only.
"""

from __future__ import annotations

import ctypes
import platform
import struct
import sys
import sysconfig

P = struct.calcsize("P")          # bytes per pointer: one slot
EMPTY = sys.getsizeof([])         # the list object with no block (plus the garbage collector's header)


def capacity(lst: list) -> int:
    """Slots in the block, from sys.getsizeof alone (works wherever getsizeof counts the block)."""
    return (sys.getsizeof(lst) - EMPTY) // P


def fields(lst: list) -> dict:
    """The list's own fields, read from its memory: len, block (address of the slots), cap (allocated)."""
    base = id(lst)
    return {"len": ctypes.c_ssize_t.from_address(base + 2 * P).value,
            "block": ctypes.c_void_p.from_address(base + 3 * P).value or 0,
            "cap": ctypes.c_ssize_t.from_address(base + 4 * P).value}


def slots(lst: list, n: int | None = None) -> list[int]:
    """The addresses stored in the first n slots (default: the used ones). Only read up to the capacity."""
    f = fields(lst)
    n = f["len"] if n is None else min(n, f["cap"])
    return [ctypes.c_void_p.from_address(f["block"] + i * P).value or 0 for i in range(n)]


def layout_ok() -> tuple[bool, str]:
    """(True, '') when this interpreter's list layout is the one the module reads; else (False, why)."""
    if sys.implementation.name != "cpython":
        return False, f"this is {sys.implementation.name}: id() is not an address and lists are laid out differently"
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        return False, "this is a free-threaded CPython build: the object header is bigger and the offsets differ"
    probe = []
    for x in ("probe", 2.5, None, "list"):
        probe.append(x)
    probe.append(True)
    f = fields(probe)
    if f["len"] != len(probe) or f["cap"] != capacity(probe) or not f["block"]:
        return False, "the list's fields are not at the offsets this script expects"
    if slots(probe) != [id(x) for x in probe]:
        return False, "the slots don't hold the items' ids"
    return True, ""


def check() -> None:
    """Stop with a clear message unless the raw reads above are safe here."""
    ok, why = layout_ok()
    if not ok:
        sys.exit(f"Stopping: {why}. These scripts read CPython 3.x list internals (tested on 3.12); "
                 "sys.getsizeof-based parts still work: see capacity.py.")


def about() -> str:
    return (f"{platform.python_implementation()} {platform.python_version()} on {platform.machine()}, "
            f"{P}-byte pointers, empty list {EMPTY} bytes")


def main() -> None:
    print(about())
    ok, why = layout_ok()
    print("layout check:", "ok, the raw reads below are safe" if ok else f"not ok: {why}")
    if not ok:
        return
    nums = []
    for x in (3, 1, 4, 1):
        nums.append(x)
    f = fields(nums)
    print(f"\nnums = {nums}")
    print(f"  the list object  id {id(nums):#x}")
    print(f"  ob_size          {f['len']}   (len(nums) = {len(nums)})")
    print(f"  allocated        {f['cap']}   ((getsizeof - {EMPTY}) // {P} = {capacity(nums)})")
    print(f"  ob_item          {f['block']:#x}   the block of slots")
    for i, addr in enumerate(slots(nums)):
        print(f"    slot {i}: {addr:#x}   id(nums[{i}]) = {id(nums[i]):#x}   → {nums[i]!r}")


if __name__ == "__main__":
    main()
