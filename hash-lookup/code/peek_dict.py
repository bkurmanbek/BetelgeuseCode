"""Steps 3 to 6: the real table inside a dict, read out of memory after every insert.

    python3 code/peek_dict.py              # the lesson's dict with PYTHONHASHSEED=0: the exact table the video draws
    python3 code/peek_dict.py --salted     # the same keys with this process's own salt: other slots, same rules
    python3 code/peek_dict.py --keys a b c d e f g h i j k

Under a second. CPython 3.11 or newer, 64-bit (it reads the dict's memory with ctypes; anything else gets a clear
message). Standard library only.

What it prints, insert by insert: the key's last bits and the slot they pick, the 8 (later 16) index slots, the
entries list in insertion order, what is left before the table grows, and sys.getsizeof. A collision prints the
probe arithmetic; the resize prints where every key moved. Every table is read from the dict itself and checked
against a replay of CPython's own placement code (Objects/dictobject.c); the script stops if they ever differ.
"""

from __future__ import annotations

import argparse
import os
import sys

import cpython_tables as ct

KEYS = ["leo", "ana", "zoe", "ivy", "kai", "tom"]   # the lesson's dictionary
AGES = [31, 27, 45, 19, 38, 52]
LOOK_AFTER = 4                                      # the video looks up leo and ron when four keys are in
MISSING = "ron"


def show_table(t: dict, indent: str = "  ") -> None:
    w = max(2, len(str(t["size"] - 1)))
    print(f"{indent}index   " + " ".join(f"{i:>{w}}" for i in range(t["size"])))
    cells = ["." if s == ct.EMPTY else "x" if s == ct.DUMMY else str(s) for s in t["slots"]]
    print(f"{indent}        " + " ".join(f"{c:>{w}}" for c in cells))
    ents = "  ".join(f"{n}:{e[0]!r}→{e[1]!r}" for n, e in enumerate(t["entries"]) if e is not None)
    print(f"{indent}entries {ents}")


def trace_insert(d: dict, key, before: dict) -> None:
    """Explain where `key` went, from the table read just before the insert."""
    h = hash(key)
    if before["shared_empty"]:
        print(f"  the first key: Python allocates a table of {ct.MIN_SIZE} slots")
        size, slots = ct.MIN_SIZE, [ct.EMPTY] * ct.MIN_SIZE
    elif before["usable"] == 0:
        used = len(before["entries"])
        size = ct.grown_size(used)
        print(f"  no usable entry left ({used} entries in {before['size']} slots, the two-thirds limit)")
        print(f"  → resize: 3 × {used} = {3 * used} → the next power of two: {size} slots;"
              f" every entry is placed again, in entry order, by hash & {size - 1}")
        return
    else:
        size, slots = before["size"], before["slots"]
    mask = size - 1
    path = []
    for i in ct.probe(h, mask):
        path.append(i)
        if slots[i] == ct.EMPTY:
            break
    first = path[0]
    print(f"  hash = {h}  ...{ct.bits(h)}  & {mask} → slot {first}", end="")
    if len(path) == 1:
        print(": empty, so it takes it")
        return
    taken_by = before["entries"][slots[first]][0]
    print(f": taken by entry {slots[first]} ({taken_by!r}) → a collision")
    perturb = (h & ct.U64)
    i = first
    for jump, nxt in enumerate(path[1:]):
        perturb >>= ct.PERTURB_SHIFT
        label = "perturb = hash >> 5" if jump == 0 else "perturb = perturb >> 5"
        print(f"  {label} = {perturb};  (5 × {i} + 1 + perturb) & {mask} = {nxt}"
              f" → slot {nxt}: {'empty, takes it' if slots[nxt] == ct.EMPTY else 'taken, jump again'}")
        i = nxt


def trace_lookup(d: dict, key) -> None:
    t = ct.read_dict(d)
    mask = t["size"] - 1
    h = hash(key)
    visited = []
    for i in ct.probe(h, mask):
        visited.append(i)
        s = t["slots"][i]
        if s == ct.EMPTY:
            print(f"  ages[{key!r}]: hash & {mask} = {visited[0]}, slots visited {visited}: empty → "
                  f"KeyError, no key compared")
            return
        if s >= 0:
            stored = t["entries"][s][0]
            if stored is key or (hash(stored) == h and stored == key):
                print(f"  ages[{key!r}]: hash & {mask} = {visited[0]}, slots visited {visited} → entry {s} → "
                      f"{stored!r} == {key!r} → {t['entries'][s][1]!r}   (one key compared)")
                return


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salted", action="store_true", help="keep this process's random str salt")
    ap.add_argument("--keys", nargs="+", help="your own keys (values are 0, 1, 2, …)")
    a = ap.parse_args()
    if not a.salted:
        ct.with_hash_seed("0")
    try:
        ct.check_interpreter()
    except ct.Unsupported as e:
        ct.bail(e)

    keys = a.keys or KEYS
    values = AGES if not a.keys else list(range(len(keys)))
    print(f"PYTHONHASHSEED={os.environ.get('PYTHONHASHSEED', 'random')}\n")
    ages: dict = {}
    t = ct.read_dict(ages)
    print(f"ages = {{}}    getsizeof {sys.getsizeof(ages)} bytes: no table of its own yet "
          f"(an empty dict points at a shared, read-only one)")
    for n, (k, v) in enumerate(zip(keys, values), 1):
        before = t
        print(f"\nages[{k!r}] = {v!r}")
        trace_insert(ages, k, before)
        size_before = sys.getsizeof(ages)
        ages[k] = v
        t = ct.read_dict(ages)
        want, _ = ct.place([hash(x) for x in ages], t["size"])
        if want != t["slots"]:
            sys.exit(f"the real index {t['slots']} differs from the replay {want}: please report this Python build")
        show_table(t)
        grew = "" if before["shared_empty"] or before["size"] == t["size"] else f"{size_before} → "
        print(f"  {t['usable']} more {'entry fits' if t['usable'] == 1 else 'entries fit'} before the table grows · getsizeof {grew}{sys.getsizeof(ages)} bytes")
        if grew:
            moved = ", ".join(f"{e[0]!r} {hash(e[0]) & (before['size'] - 1)}→{t['slots'].index(m)}"
                              for m, e in enumerate(t["entries"]))
            print(f"  moved: {moved}")
        if n == LOOK_AFTER and not a.keys:
            print("\nlookups, with four keys in")
            trace_lookup(ages, "leo")
            trace_lookup(ages, MISSING)

    print(f"\nlist(ages)            {list(ages)}   ← a loop walks the entries: insertion order")
    in_slots = [t["entries"][s][0] for s in t["slots"] if s >= 0]
    print(f"the keys in slot order {in_slots}   ← what you would get if it walked the slots")
    print(f"index slots are {t['index_bytes']} byte(s) each, entries {t['entry_bytes']} bytes "
          f"({'key, value: every key is a str' if t['kind'] == 'unicode' else 'stored hash, key, value'})")
    print("replay of CPython's placement code matched the real table after every insert: yes")


if __name__ == "__main__":
    main()
