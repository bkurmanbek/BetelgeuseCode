"""Step 7: a key's hash must never change, and that's why a list can't be a key.

    python3 code/key_rules.py         # with PYTHONHASHSEED=0: the slots in the lesson; under a second

CPython 3.11 or newer, 64-bit, for the table read-outs (ctypes); the rest runs anywhere. Standard library only.

What it shows:
  1. the REPL session from the lesson: a list as a key is refused, a tuple is fine;
  2. what a hashable list would do: a key class that hashes its own contents goes into one slot, changes, and is
     lost inside its own dict. The entry still stores the old hash: read straight from the table;
  3. the contract behind it (equal keys, equal hashes; a hash never changes) and the keys it explains:
     1 == 1.0 == True are one key, and NaN is found only by identity.
"""

from __future__ import annotations

from dataclasses import dataclass

import cpython_tables as ct


def repl(src: str, ns: dict) -> None:
    """Run one line the way the REPL would and print what it prints."""
    print(f"  >>> {src}")
    try:
        try:
            val = eval(compile(src, "<stdin>", "eval"), ns)
            if val is not None:
                print(f"  {val!r}")
        except SyntaxError:
            exec(compile(src, "<stdin>", "exec"), ns)
    except Exception as e:  # noqa: BLE001 - the error is the output
        print(f"  {type(e).__name__}: {e}")


class Tag:
    """What a hashable list would be: hashes whatever it holds right now."""

    def __init__(self, parts):
        self.parts = parts

    def __hash__(self):
        return hash(tuple(self.parts))

    def __eq__(self, other):
        return isinstance(other, Tag) and self.parts == other.parts

    def __repr__(self):
        return f"Tag({self.parts!r})"


@dataclass(frozen=True)
class Point:
    """The fix: a key whose fields can't change, so its hash can't either (eq and hash come from the fields)."""
    x: int
    y: int


def stored_hash(d: dict, key) -> str:
    try:
        t = ct.read_dict(d)
    except ct.Unsupported as e:
        return f"(table not readable here: {e})"
    slot = next(i for i, s in enumerate(t["slots"]) if s >= 0 and t["entries"][s][0] is key)
    return f"the entry sits in slot {slot} and stores hash {t['entries'][t['slots'][slot]][2]}"


def main() -> None:
    ct.with_hash_seed("0")
    print("1. the lesson's session")
    ns: dict = {}
    for line in ['ages = {"leo": 31}', 'ages[["leo", "ana"]] = 31', 'ages[("leo", "ana")] = 31', "len(ages)"]:
        repl(line, ns)
    repl('ages[("leo", ["ana"])] = 31', ns)
    print("  (a tuple is hashable only if everything inside it is)")

    print("\n2. a key that changes after it went in")
    t = Tag(["leo"])
    d = {t: 31}
    print(f"  d = {{Tag(['leo']): 31}}   hash & 7 = {hash(t) & 7};  {stored_hash(d, t)}")
    t.parts.append("sam")
    print(f"  t.parts.append('sam')    hash & 7 = {hash(t) & 7} now;  {stored_hash(d, t)}")
    print(f"  t in d                → {t in d}    (the lookup goes to the new slot: nothing there)")
    print(f"  Tag(['leo']) in d     → {Tag(['leo']) in d}    (the old slot, but the key there is no longer equal)")
    print(f"  any(k is t for k in d) → {any(k is t for k in d)}   len(d) → {len(d)}   (still inside, unreachable)")

    print("\n3. the contract: a == b must imply hash(a) == hash(b), and a key's hash must never change")
    print(f"  Point(1, 2) in {{Point(1, 2): 'here'}} → {Point(1, 2) in {Point(1, 2): 'here'}}   "
          f"(frozen dataclass: fields can't change)")
    print(f"  {{1: 'a', True: 'b', 1.0: 'c'}} → {({1: 'a', True: 'b', 1.0: 'c'})}   "
          f"(equal and same hash: one key, the first key object kept, the last value)")
    nan = float("nan")
    print(f"  nan = float('nan'); nan in {{nan}} → {nan in {nan}}, float('nan') in {{nan}} → {float('nan') in {nan}}")
    print("  (the stored key is checked with `is` before `==`; a second NaN is another object, hashed by its")
    print("   identity since Python 3.10, and nan != nan)")

    class OnlyEq:
        def __eq__(self, other):
            return True
    print(f"  a class that defines __eq__ but not __hash__ gets __hash__ = {OnlyEq.__hash__}: unhashable")


if __name__ == "__main__":
    main()
