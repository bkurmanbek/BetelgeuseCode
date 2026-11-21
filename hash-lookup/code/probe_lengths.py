"""The limit of "one slot": how many slots lookups really visit in a big, real table (a set of 10 million names).

    python3 code/probe_lengths.py --quick   # 200,000 names, 20,000 missing names: a few seconds
    python3 code/probe_lengths.py           # 10,000,000 names, 1,000,000 missing: about 25 s, 1.3 GB of RAM

CPython 3.11 or newer, 64-bit (it reads the set's table in place with ctypes). Standard library only. Re-runs
itself with PYTHONHASHSEED=0, so the table, and every number it prints, is the same on every run.

How: build a set of N shuffled names (seed 42: user00000000, user00000001, …), view its table in memory without
copying it, then for every name walk the path `set_lookkey` in Objects/setobject.c walks (the home slot, up to 9
neighbours, then a jump mixed from the hash's higher bits) and count the slots until it meets the name (a hit) or
an empty slot (a miss: the name can't be further along, it would have been placed there). A set packs up to
three-fifths of its slots, a dict up to two-thirds; the dict's path has no neighbour run, only the jumps.
"""

from __future__ import annotations

import argparse
import ctypes
import random
import statistics

import cpython_tables as ct


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--n", type=int, help="names in the set")
    a = ap.parse_args()
    ct.with_hash_seed("0")
    try:
        ct.check_interpreter()
    except ct.Unsupported as e:
        ct.bail(e)
    n = a.n or (200_000 if a.quick else 10_000_000)
    n_miss = max(1, n // 10)

    random.seed(42)
    names = [f"user{i:08d}" for i in range(n)]
    random.shuffle(names)
    s = set(names)
    t = ct.read_set(s) if n <= 1_000_000 else None   # full check of the layout on small sets; big ones: header only
    word = lambda off: ctypes.c_ssize_t.from_address(id(s) + off).value  # noqa: E731
    used, mask, table = word(24), word(32), word(40)           # PySetObject: used, mask, table pointer
    if used != len(s) or (mask + 1) & mask:
        ct.bail(ct.Unsupported("the set header doesn't match len(s)"))
    size = mask + 1
    keys = memoryview((ctypes.c_char * (16 * size)).from_address(table)).cast("B").cast("q")   # no copy
    if t is not None:
        assert [keys[2 * i] or None for i in range(size)] == [id(x) if x is not None else None for x in t["slots"]]
    print(f"{n:,} names in {size:,} slots: {used / size:.1%} full")

    def visits(x, hit: bool) -> int:
        h = hash(x)
        perturb, i, count, me = h & ct.U64, h & mask, 0, id(x)
        while True:
            j, left = i, (ct.LINEAR_PROBES if i + ct.LINEAR_PROBES <= mask else 0)
            while True:
                k = keys[2 * j]
                count += 1
                if k == 0:
                    if hit:
                        raise SystemExit(f"{x!r} should be in the set: the replay is wrong for this build")
                    return count
                if hit and k == me:
                    return count
                if left == 0:
                    break
                left, j = left - 1, j + 1
            perturb >>= ct.PERTURB_SHIFT
            i = (i * 5 + 1 + perturb) & mask

    def summary(label: str, counts: list[int], first: str) -> None:
        print(f"\n{label}: {len(counts):,} lookups")
        print(f"  slots visited: mean {statistics.fmean(counts):.3f} · median {statistics.median(counts):g} · "
              f"max {max(counts)}")
        print(f"  {first}: {sum(c == 1 for c in counts) / len(counts):.1%}")
        for k in range(1, 9):
            share = sum(c == k for c in counts) / len(counts)
            print(f"  {k:>2} {'█' * round(share * 50):<50} {share:6.1%}")
        rest = sum(c > 8 for c in counts) / len(counts)
        print(f"  9+ {'█' * round(rest * 50):<50} {rest:6.1%}")

    hits = [visits(x, True) for x in names]
    summary("every name in the set (hits)", hits, "found in the first slot visited")
    print(f"  within two slots: {sum(c <= 2 for c in hits) / len(hits):.1%}")
    misses = []
    for i in range(n, n + n_miss):
        x = f"user{i:08d}"
        misses.append(visits(x, False))
    summary(f"names not in the set (misses: user{n:08d} on)", misses,
            "proved absent at the first slot (it was empty)")


if __name__ == "__main__":
    main()
