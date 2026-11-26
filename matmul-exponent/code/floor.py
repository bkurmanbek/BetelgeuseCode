"""The claimed floor, in numbers: OpenAI's nine-fourths paper claims that for every n >= 2, any circuit for two
n x n tables needs at least ceil(n^(9/4) / 2) multiplications or divisions, even if additions are free. This
prints that floor exactly (integer arithmetic, no rounding), next to the n^2 numbers of the answer and the school
way's n^3, and the "one quarter" on top of n^2: n^(1/4).

    python3 floor.py            # instantly (also --quick, the same)

It is a claim as of November 25, 2026 (an unreviewed preprint; its Lean proof covers circuits without division).
This script only does the arithmetic of the bound, it doesn't check the proof. Standard library only.
"""

from __future__ import annotations

import argparse
from math import isqrt


def floor_bound(n: int) -> int:
    """ceil(n^(9/4) / 2) exactly: the least m with 2m >= n^(9/4), i.e. (2m)^4 >= n^9."""
    r = isqrt(isqrt(n ** 9))            # floor of the 4th root of n^9
    if r ** 4 < n ** 9:
        r += 1                          # ceiling of n^(9/4)
    m = (r + 1) // 2                    # least m with 2m >= r
    assert (2 * m) ** 4 >= n ** 9 > (2 * m - 2) ** 4
    return m


def main() -> None:
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).add_argument("--quick", action="store_true")
    print(f"{'n':>12} {'answer, n^2':>22} {'claimed floor':>25} {'n^(1/4)':>9} {'school, n^3':>34}")
    for n in (2, 3, 4, 10, 100, 1000, 10_000, 100_000, 10 ** 8):
        print(f"{n:>12,} {n * n:>22,} {floor_bound(n):>25,} {n ** 0.25:>9.6g} {n ** 3:>34,}")

    print("\nthe floor is about growth, not about small tables:")
    print(f"  2 x 2: claimed floor {floor_bound(2)}; Strassen uses 7, and 7 are known to be necessary (Winograd, 1971)")
    print(f"  4 x 4: claimed floor {floor_bound(4)}; Strassen on blocks uses 49;"
          " AlphaEvolve found 48 over the complex numbers (2025)")
    print("\nn^(9/4) = n^2 * n^(1/4): the size of the answer times one quarter power more.")
    print(f"at n = 10,000 that extra factor is {10_000 ** 0.25:g}; at n = 100,000,000 it is {(10 ** 8) ** 0.25:g}.")


if __name__ == "__main__":
    main()
