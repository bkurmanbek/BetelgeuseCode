"""Step 4: a lookup compares one key, however many keys the dict holds. Counted, not timed.

    python3 code/count_compares.py --quick   # 100,000 keys: about a second
    python3 code/count_compares.py           # 1,000,000 keys, as in the lesson: a few seconds, about 300 MB

Standard library only, any Python 3.8+. A key class counts every __eq__ and __hash__ call Python makes on it.

What to look at:
  * a hit calls __hash__ once and __eq__ once, at any size;
  * a miss usually calls __eq__ zero times: the slot is empty, or the entries it passes store a different hash, and
    CPython compares the stored hash before it ever calls __eq__;
  * the limit: give every key the same hash and one lookup compares key after key, like a list would.
"""

from __future__ import annotations

import argparse
import random


class Key:
    """A string key that counts how often Python hashes it and compares it."""
    eq_calls = 0
    hash_calls = 0

    def __init__(self, s: str):
        self.s = s

    def __hash__(self):
        Key.hash_calls += 1
        return hash(self.s)

    def __eq__(self, other):
        Key.eq_calls += 1
        return isinstance(other, Key) and self.s == other.s

    @classmethod
    def reset(cls):
        cls.eq_calls = cls.hash_calls = 0


class SameHash(Key):
    """The worst possible key: every one hashes to the same number, so every key shares one probe path."""

    def __hash__(self):
        Key.hash_calls += 1
        return 42


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="100,000 keys instead of 1,000,000")
    ap.add_argument("--n", type=int, help="number of keys")
    a = ap.parse_args()
    n = a.n or (100_000 if a.quick else 1_000_000)

    d = {Key(f"user{i:07d}"): i for i in range(n)}
    print(f"a dict of {len(d):,} keys\n")

    target = f"user{424242 % n:07d}"
    Key.reset()
    value = d[Key(target)]                      # a fresh object, equal to the stored key: no identity shortcut
    print(f"d[Key({target!r})] → {value}")
    print(f"  __hash__ calls: {Key.hash_calls}   __eq__ calls (keys compared): {Key.eq_calls}")

    Key.reset()
    found = Key("someone") in d
    print(f"Key('someone') in d → {found}")
    print(f"  __hash__ calls: {Key.hash_calls}   __eq__ calls: {Key.eq_calls}")

    rng = random.Random(42)
    sample = [Key(f"user{rng.randrange(n):07d}") for _ in range(10_000)]
    Key.reset()
    for k in sample:
        d[k]
    print(f"\n{len(sample):,} random hits: {Key.eq_calls:,} keys compared in total "
          f"({Key.eq_calls / len(sample):g} per lookup)")

    m = 2_000
    bad = {}
    for i in range(m):
        bad[SameHash(f"user{i:07d}")] = i
    Key.reset()
    bad[SameHash(f"user{m - 1:07d}")]
    print(f"\nthe limit: {m:,} keys that all hash to 42 share one probe path")
    print(f"  looking up the last one compared {Key.eq_calls:,} keys")


if __name__ == "__main__":
    main()
