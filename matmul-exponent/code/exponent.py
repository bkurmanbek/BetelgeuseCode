"""From a recipe to an exponent: a recipe that multiplies v x v blocks with r block products, used inside itself,
costs r^k multiplications for n = v^k, which is n^(log_v r). Then the packing thresholds from Rafael Pass's
explicit proof of the nine-fourths upper bound, closing in on 9/4 as the packing grows.

    python3 exponent.py         # instantly (also --quick, the same)

Pass (arXiv:2610.28627) builds a (c + 2)-for-c polynomial packing and reaches "any exponent strictly above
3/2 * log(1 + 3/(c - 1)) / log(1 + 2/c)"; "this threshold tends to 9/4 as c -> infinity". We only evaluate his
formula here: the packing itself is in his paper. Standard library only.
"""

from __future__ import annotations

import argparse
import math


def threshold(c: int) -> float:
    """Pass's threshold for a (c + 2)-for-c packing (his formula, evaluated)."""
    return 1.5 * math.log(1 + 3 / (c - 1)) / math.log(1 + 2 / c)


def main() -> None:
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).add_argument("--quick", action="store_true")
    print("a recipe for v x v blocks with r block products -> exponent log_v r")
    for name, v, r in (("the school way", 2, 8), ("Strassen 1969", 2, 7)):
        print(f"  {name:<15} v = {v}, r = {r}: log_{v} {r} = {math.log(r, v):.6f}")
    print("  (each doubling of n multiplies the count by 2^exponent: "
          f"2^3 = 8, 2^{math.log2(7):.3f} = 7, 2^2.25 = {2 ** 2.25:.5f}, 2^2 = 4)\n")

    print("Pass's packings: the exponent each one reaches (any exponent strictly above)")
    for c in (2, 3, 4, 10, 100, 1000, 10 ** 6):
        print(f"  c = {c:>9,}: {threshold(c):.6f}")
    print("\nwhy 9/4: for large c, log(1 + 3/(c - 1)) is close to 3/c and log(1 + 2/c) to 2/c,")
    print(f"so the threshold is close to 3/2 * (3/c) / (2/c) = 3/2 * 3/2 = 9/4 = {9 / 4}")


if __name__ == "__main__":
    main()
