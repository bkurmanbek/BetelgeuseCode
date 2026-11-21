"""Read a dict's and a set's hash table straight out of CPython's memory, and replay CPython's own rules.

Shared by the scripts in this folder (not a script itself). Standard library only: `ctypes` reads the bytes.

What it reads (64-bit, regular GIL build of CPython 3.11 or newer; the struct names are CPython's own):

    PyDictObject      ob_refcnt, ob_type, ma_used, ma_version_tag, ma_keys, ma_values        8 bytes each
    PyDictKeysObject  dk_refcnt (8); dk_log2_size, dk_log2_index_bytes, dk_kind (1 each); dk_version (4);
                      dk_usable (8); dk_nentries (8); dk_indices[] (1, 2, 4 or 8 bytes per slot); the entries
    an entry          {me_key, me_value} when every key is a str (dk_kind 1), else {me_hash, me_key, me_value}
    PySetObject       ob_refcnt, ob_type, fill, used, mask, table -> setentry {key, hash}

Nothing is dereferenced on trust: the header must agree with len(), and every key pointer read from the table must
be the id() of a key the object really holds, or the read stops with `Unsupported` and a clear reason. On a build
whose layout differs (PyPy, free-threaded, a future CPython) you get that message, never made-up slots.

The replays below are CPython's placement code, rewritten in Python (Objects/dictobject.c, Objects/setobject.c).
"""

from __future__ import annotations

import ctypes
import os
import platform
import subprocess
import sys
import sysconfig

U64 = (1 << 64) - 1
PERTURB_SHIFT = 5        # both files: perturb >>= PERTURB_SHIFT on every jump
LINEAR_PROBES = 9        # setobject.c only: a set also tries up to 9 neighbours before it jumps
EMPTY, DUMMY = -1, -2    # DKIX_EMPTY, DKIX_DUMMY: an index slot that points to no entry (never used / deleted)
MIN_SIZE = 8             # PyDict_MINSIZE, PySet_MINSIZE


class Unsupported(RuntimeError):
    """This interpreter's memory doesn't match the layout above."""


def check_interpreter() -> None:
    if sys.implementation.name != "cpython":
        raise Unsupported(f"needs CPython; this is {sys.implementation.name} (its dicts are built differently)")
    if sys.maxsize != 2**63 - 1:
        raise Unsupported("needs a 64-bit build")
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        raise Unsupported("needs the regular build; the free-threaded build lays its objects out differently")
    if sys.version_info < (3, 11):
        raise Unsupported(f"reads the layout of CPython 3.11 and newer; this is {platform.python_version()}")


def _ssize(addr: int) -> int:
    return ctypes.c_ssize_t.from_address(addr).value


def _u8(addr: int) -> int:
    return ctypes.c_uint8.from_address(addr).value


def _ptr(addr: int) -> int:
    return ctypes.c_void_p.from_address(addr).value or 0


INDEX_TYPES = {1: ctypes.c_int8, 2: ctypes.c_int16, 4: ctypes.c_int32, 8: ctypes.c_int64}


def read_dict(d: dict) -> dict:
    """The real table of `d`:

    size      slots in the index (a power of two)
    slots     slots[i] = the entry number slot i points to, or EMPTY / DUMMY
    entries   in insertion order: (key, value, stored hash or None), or None for a deleted entry
    usable    entries that still fit before the table must grow
    kind      "unicode" (all keys are str: no stored hash) or "general"
    index_bytes, entry_bytes   bytes per index slot and per entry
    """
    check_interpreter()
    if type(d) is not dict:
        raise TypeError("read_dict reads a plain dict")
    base = id(d)
    used, keys_at, values_at = _ssize(base + 16), _ptr(base + 32), _ptr(base + 40)
    if used != len(d):
        raise Unsupported("ma_used doesn't equal len(d): this is not the dict layout these scripts read")
    if values_at:
        raise Unsupported("a split table (an instance __dict__): copy it into a plain dict first")
    if not keys_at or keys_at % 8:
        raise Unsupported("ma_keys is not a pointer")
    log2_size, log2_index, kind = _u8(keys_at + 8), _u8(keys_at + 9), _u8(keys_at + 10)
    usable, nentries = _ssize(keys_at + 16), _ssize(keys_at + 24)
    if len(d) == 0 and nentries == 0 and usable == 0:   # {}: points at one shared, empty, read-only table
        return {"size": 0, "slots": [], "entries": [], "usable": 0, "shared_empty": True,
                "kind": "unicode", "index_bytes": 0, "entry_bytes": 0}
    if not 3 <= log2_size <= 40 or kind not in (0, 1):
        raise Unsupported("the keys header doesn't look like PyDictKeysObject")
    size = 1 << log2_size
    width = (1 << log2_index) >> log2_size
    capacity = (size << 1) // 3                           # USABLE_FRACTION
    if width not in INDEX_TYPES or not (len(d) <= nentries <= capacity and 0 <= usable <= capacity):
        raise Unsupported("the keys header doesn't agree with len(d)")
    ix = INDEX_TYPES[width]
    slots = [ix.from_address(keys_at + 32 + width * i).value for i in range(size)]
    entry_bytes = 16 if kind == 1 else 24
    entries_at = keys_at + 32 + (1 << log2_index)
    items = list(d.items())          # iteration walks the entries, so this is entry order
    entries, j = [], 0
    for n in range(nentries):
        e = entries_at + entry_bytes * n
        stored = None if kind == 1 else _ssize(e)
        k_ptr = _ptr(e + entry_bytes - 16)
        v_ptr = _ptr(e + entry_bytes - 8)
        if k_ptr == 0:
            entries.append(None)     # a deleted entry: its key and value are gone, the space is not reused
            continue
        if j >= len(items) or k_ptr != id(items[j][0]) or v_ptr != id(items[j][1]):
            raise Unsupported("the entries are not this dict's keys and values in order: unexpected layout")
        entries.append((items[j][0], items[j][1], stored))
        j += 1
    if j != len(items):
        raise Unsupported("fewer live entries than keys: unexpected layout")
    pointed = sorted(s for s in slots if s >= 0)
    if pointed != [n for n, e in enumerate(entries) if e is not None]:
        raise Unsupported("the index slots don't point at exactly the live entries: unexpected layout")
    return {"size": size, "slots": slots, "entries": entries, "usable": usable, "shared_empty": False,
            "kind": "unicode" if kind == 1 else "general", "index_bytes": width, "entry_bytes": entry_bytes}


def read_set(s: set) -> dict:
    """The real table of `s`: size, and slots[i] = the element stored in slot i, or None (empty)."""
    check_interpreter()
    if type(s) not in (set, frozenset):
        raise TypeError("read_set reads a set or a frozenset")
    base = id(s)
    fill, used, mask, table = (_ssize(base + off) for off in (16, 24, 32, 40))
    if used != len(s) or fill < used or mask < MIN_SIZE - 1 or (mask + 1) & mask or not table:
        raise Unsupported("the header doesn't agree with len(s): not the set layout these scripts read")
    by_id = {id(x): x for x in s}
    slots, found = [], 0
    for i in range(mask + 1):
        k = _ptr(table + 16 * i)
        if k in by_id:
            slots.append(by_id[k])
            found += 1
        else:
            slots.append(None)                     # empty, or a deleted element's dummy marker
    if found != len(s):
        raise Unsupported("the table doesn't hold exactly the elements of the set: unexpected layout")
    return {"size": mask + 1, "slots": slots, "fill": fill}


# ---------------------------------------------------------------- CPython's rules, replayed in Python

def probe(h: int, mask: int):
    """Dict: the slots a key visits, in order (lookup and insert walk the same path).
    i = hash & mask; then perturb >>= 5; i = (5*i + 1 + perturb) & mask, forever."""
    perturb, i = h & U64, h & mask
    while True:
        yield i
        perturb >>= PERTURB_SHIFT
        i = (i * 5 + perturb + 1) & mask


def place(hashes: list[int], size: int) -> tuple[list[int], list[list[int]]]:
    """Dict: the index after inserting entries with these hashes in order into `size` slots (also what a resize
    builds: it re-inserts every entry in entry order), and each entry's path."""
    slots, paths = [EMPTY] * size, []
    for n, h in enumerate(hashes):
        path = []
        for i in probe(h, size - 1):
            path.append(i)
            if slots[i] == EMPTY:
                slots[i] = n
                break
        paths.append(path)
    return slots, paths


def usable_fraction(size: int) -> int:
    """Dict: entries a table of `size` slots takes before it grows (USABLE_FRACTION: two thirds)."""
    return (size << 1) // 3


def grown_size(used: int) -> int:
    """Dict: the new slot count when an insert finds no usable entry left: the smallest power of two that is at
    least 3 × used (GROWTH_RATE), never below 8."""
    size = MIN_SIZE
    while size < used * 3:
        size <<= 1
    return size


def set_probe(h: int, mask: int):
    """Set: like the dict, but first up to LINEAR_PROBES neighbours (they share a cache line), then the jump."""
    perturb, i = h & U64, h & mask
    while True:
        yield i
        if i + LINEAR_PROBES <= mask:
            yield from range(i + 1, i + LINEAR_PROBES + 1)
        perturb >>= PERTURB_SHIFT
        i = (i * 5 + 1 + perturb) & mask


def bits(h: int, n: int = 8) -> str:
    """The lowest n bits of a hash, as the drawings show them."""
    return format(h & ((1 << n) - 1), f"0{n}b")


def with_hash_seed(seed: str = "0") -> None:
    """str hashes are salted per process. Re-run this script with PYTHONHASHSEED fixed (unless it already is), so
    its numbers match the lesson's. Returns only in the re-run."""
    if os.environ.get("PYTHONHASHSEED") == seed:
        return
    env = {**os.environ, "PYTHONHASHSEED": seed}
    sys.exit(subprocess.run([sys.executable, *sys.argv], env=env).returncode)


def bail(e: Unsupported) -> None:
    sys.exit(f"Can't read the table on this interpreter: {e}.\n"
             f"(Python {platform.python_version()}, {sys.implementation.name}; the scripts read CPython 3.11+, 64-bit.)")
