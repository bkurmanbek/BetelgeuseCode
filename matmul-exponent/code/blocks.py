"""Strassen's saving compounds: run the school way and Strassen's recipe on blocks inside blocks for n x n tables,
n = 2, 4, 8, ..., count every multiplication and check that both give the same answer. Then the formulas, n^3
and 7^k, out to n = 1,024. Counts, not timings: the same numbers on every machine.

    python3 blocks.py --quick   # n = 2 ... 32 run for real: about a second
    python3 blocks.py           # n = 2 ... 128 run for real, as in the notes: about 6 s on a laptop, ~20 MB
    python3 blocks.py --levels 64      # where the 7^k comes from: block products of each size inside one 64 x 64

The tables hold random whole numbers from -9 to 9 (seed 20261125, the same as the notes), and the counting is done
by the numbers themselves (tally.py): only a product of two values that depend on the inputs counts. For
n = 2^k the school way does n^3 = 8^k multiplications and Strassen's 7^k, so the ratio shrinks by 7/8 with every
doubling, and the count grows like n^(log2 7) = n^2.807... Standard library only.
"""

from __future__ import annotations

import argparse
import math
import random

from tally import Tally, plain, school, strassen, track

SEED = 20261125


def run(n: int, rng: random.Random) -> tuple[int, int]:
    """Both recipes on the same random n x n tables, counted; stops if the answers differ."""
    A = [[rng.randint(-9, 9) for _ in range(n)] for _ in range(n)]
    B = [[rng.randint(-9, 9) for _ in range(n)] for _ in range(n)]
    t1, t2 = Tally(), Tally()
    want = plain(school(track(A, t1), track(B, t1)))
    got = plain(strassen(track(A, t2), track(B, t2)))
    if got != want:
        raise SystemExit(f"n = {n}: Strassen's answer differs from the school way's")
    return t1.n, t2.n


def levels(n: int) -> None:
    """Inside one n x n Strassen product: how many block products of each size it makes."""
    rng = random.Random(SEED)
    A = [[rng.randint(-9, 9) for _ in range(n)] for _ in range(n)]
    B = [[rng.randint(-9, 9) for _ in range(n)] for _ in range(n)]
    calls: dict[int, int] = {}
    t = Tally()
    strassen(track(A, t), track(B, t), calls)
    print(f"one {n} x {n} product, Strassen's recipe on blocks:")
    for size in sorted(calls, reverse=True):
        what = "multiplications of numbers" if size == 1 else f"products of {size} x {size} blocks"
        school_way = (n // size) ** 3
        print(f"  {calls[size]:>9,} {what:<34} (the school way: {school_way:,})")
    print(f"  counted by the numbers themselves: {t.n:,} = 7^{int(math.log2(n))}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="run for real up to n = 32 (about a second)")
    ap.add_argument("--levels", type=int, metavar="N", help="show the block products inside one N x N product")
    a = ap.parse_args()
    if a.levels:
        if a.levels < 1 or a.levels & (a.levels - 1):
            raise SystemExit("--levels takes a power of two: 2, 4, 8, ...")
        levels(a.levels)
        return
    run_up_to = 32 if a.quick else 128
    rng = random.Random(SEED)
    print(f"{'n':>6} {'school, n^3':>15} {'Strassen, 7^k':>15} {'Strassen / school':>18}   how")
    for k in range(1, 11):
        n = 2 ** k
        if n <= run_up_to:
            s, st = run(n, rng)
            assert (s, st) == (n ** 3, 7 ** k)
            how = "run and counted, same answer"
        else:
            s, st = n ** 3, 7 ** k
            how = "formula"
        print(f"{n:>6,} {s:>15,} {st:>15,} {st / s:>18.4f}   {how}")
    print("\neach doubling of n: the school way x 8, Strassen's x 7.")
    print(f"so the counts grow like n^3 and n^(log2 7) = n^{math.log2(7):.6f}")


if __name__ == "__main__":
    main()
