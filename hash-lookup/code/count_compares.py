"""Step 4: a lookup compares one key, however many keys the dictionary holds. Counted, not timed.

    python3 code/count_compares.py --quick   # 100,000 users: about a second
    python3 code/count_compares.py           # 1,000,000 users, as in the notes: about 2 s, 280 MB of RAM

Standard library only, any Python 3.8+. The dictionary maps a million made-up email addresses (code/people.py) to
user ids 0, 1, 2, … A key class wraps each address and counts every time Python hashes it (__hash__) and every
time Python compares it with another key (__eq__).

What to look at:
  * a hit calls __hash__ once and __eq__ once, at any size;
  * a miss usually calls __eq__ zero times: the slot is empty, or the entries on its path store a different hash,
    and CPython compares the stored hash before it ever calls __eq__;
  * the limit: give every key the same hash and one lookup compares key after key, the way a list search would.
"""

from __future__ import annotations

import argparse
import random

from people import NOBODY, emails


class Key:
    """An email address that counts how often Python hashes it and compares it."""
    __slots__ = ("s",)
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
    """The worst possible key: every one hashes to the same number, so every key shares one path of slots."""
    __slots__ = ()

    def __hash__(self):
        Key.hash_calls += 1
        return 42


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="100,000 users instead of 1,000,000")
    ap.add_argument("--n", type=int, help="number of users")
    a = ap.parse_args()
    n = a.n or (100_000 if a.quick else 1_000_000)

    addresses = emails(n)
    users = {Key(e): user_id for user_id, e in enumerate(addresses)}
    print(f"users: a dictionary of {len(users):,} email addresses → user ids\n")

    target = addresses[424242 % n]
    Key.reset()
    value = users[Key(target)]                  # a fresh object, equal to the stored key: no `is` shortcut
    print(f"users[Key({target!r})] → {value}")
    print(f"  __hash__ calls: {Key.hash_calls}   __eq__ calls (keys compared): {Key.eq_calls}")

    Key.reset()
    found = Key(NOBODY) in users
    print(f"Key({NOBODY!r}) in users → {found}")
    print(f"  __hash__ calls: {Key.hash_calls}   __eq__ calls (keys compared): {Key.eq_calls}")

    rng = random.Random(42)
    sample = [Key(addresses[rng.randrange(n)]) for _ in range(10_000)]
    Key.reset()
    for k in sample:
        users[k]
    print(f"\n{len(sample):,} lookups of random users: {Key.eq_calls:,} keys compared in total "
          f"({Key.eq_calls / len(sample):g} per lookup)")

    m = 2_000
    bad = {SameHash(e): user_id for user_id, e in enumerate(addresses[:m])}
    Key.reset()
    bad[SameHash(addresses[m - 1])]
    print(f"\nthe limit: {m:,} keys that all hash to 42 share one path of slots")
    print(f"  looking up the last one compared {Key.eq_calls:,} keys")


if __name__ == "__main__":
    main()
