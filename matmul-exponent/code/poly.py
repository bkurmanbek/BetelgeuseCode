"""The polynomial trick the nine-fourths upper bound starts from: multiply (3 + 2x)(5 + 4x) with three
multiplications instead of four, by putting numbers in for x, multiplying the values, and rebuilding the answer
with additions and divisions by fixed numbers (which the papers count as free).

    python3 poly.py --quick     # the example and polynomials up to 10 coefficients: instantly
    python3 poly.py             # also 100 coefficients, as in the notes: about 6 s on a laptop

Two polynomials with k coefficients each: the school way multiplies every pair, k * k products. The answer has
2k - 1 coefficients, and a polynomial with 2k - 1 coefficients is pinned down by its values at 2k - 1 points, so
2k - 1 products are enough: one per point. The numbers count their own multiplications (tally.py), the rebuild
uses exact fractions, and every answer is checked against the school way. Standard library only.
"""

from __future__ import annotations

import argparse
import random
from fractions import Fraction

from tally import Tally, Tracked


def show(coeffs) -> str:
    """[15, 22, 8] -> '15 + 22x + 8x^2'"""
    terms = [f"{c}" + ("" if i == 0 else "x" if i == 1 else f"x^{i}") for i, c in enumerate(coeffs)]
    return " + ".join(terms)


def school(a, b):
    """Every coefficient of a times every coefficient of b: len(a) * len(b) products."""
    out = [0] * (len(a) + len(b) - 1)
    for i in range(len(a)):
        for j in range(len(b)):
            out[i + j] = a[i] * b[j] + out[i + j]
    return out


def points(a, b):
    """Evaluate at len(a) + len(b) - 1 points, multiply the values (one product per point), rebuild the
    coefficients by Lagrange interpolation: only fixed numbers multiply or divide the values there."""
    k = len(a) + len(b) - 1
    xs = [Fraction(x) for x in range(-(k // 2), k - k // 2)]           # 3 points: -1, 0, 1

    def value(p, x):                                                    # p(x): coefficients times fixed powers
        return sum((q * x ** i for i, q in enumerate(p)), Fraction(0))

    vals = [value(a, x) * value(b, x) for x in xs]                      # the only products that count
    coef = [Fraction(0)] * k
    for i, xi in enumerate(xs):
        basis, den = [Fraction(1)], Fraction(1)                         # prod over j != i of (x - xj) / (xi - xj)
        for j, xj in enumerate(xs):
            if j != i:
                basis = [(basis[t - 1] if t else 0) - xj * (basis[t] if t < len(basis) else 0)
                         for t in range(len(basis) + 1)]
                den *= xi - xj
        for t, q in enumerate(basis):
            coef[t] = vals[i] * (q / den) + coef[t]
    return [int(c.v) for c in coef], xs, vals


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--quick", action="store_true", help="skip the 100-coefficient case")
    args = ap.parse_args()

    t = Tally()
    a, b = [Tracked(3, t), Tracked(2, t)], [Tracked(5, t), Tracked(4, t)]
    print(f"({show([3, 2])})({show([5, 4])})\n")

    want = [c.v for c in school(a, b)]
    print("the school way, every pair:")
    for i, p in enumerate((3, 2)):
        for j, q in enumerate((5, 4)):
            print(f"  {show([0] * i + [p]).split(' + ')[-1]} * {show([0] * j + [q]).split(' + ')[-1]}"
                  f" = {show([0] * (i + j) + [p * q]).split(' + ')[-1]}")
    print(f"  {t.n} multiplications -> {show(want)}\n")

    t.n = 0
    got, xs, vals = points(a, b)
    print("the trick: put in x = " + ", ".join(str(x) for x in xs) + ", multiply the values:")
    for x, v in zip(xs, vals):
        print(f"  x = {str(x):>2}: ({3 + 2 * x}) * ({5 + 4 * x}) = {v.v}")
    print(f"  {t.n} multiplications -> rebuilt: {show(got)}")
    v = {int(x): val.v for x, val in zip(xs, vals)}
    print("  the same rebuild by hand, adding and halving only:")
    print(f"    constant term = value at 0                                = {v[0]}")
    print(f"    x term        = (value at 1 - value at -1) / 2              = {(v[1] - v[-1]) // 2}")
    print(f"    x^2 term      = (value at 1 + value at -1) / 2 - value at 0 = {(v[1] + v[-1]) // 2 - v[0]}")
    assert got == want

    print(f"\n{'coefficients each':>18} {'school, k*k':>12} {'points, 2k-1':>13}")
    rng = random.Random(7)                                              # the notes' polynomials
    for k in (2, 3, 5, 10, 100):
        p = [rng.randint(1, 9) for _ in range(k)]
        q = [rng.randint(1, 9) for _ in range(k)]
        if args.quick and k > 10:
            continue
        t1, t2 = Tally(), Tally()
        ref = [c.v for c in school([Tracked(x, t1) for x in p], [Tracked(x, t1) for x in q])]
        assert points([Tracked(x, t2) for x in p], [Tracked(x, t2) for x in q])[0] == ref
        print(f"{k:>18,} {t1.n:>12,} {t2.n:>13,}   same answer")


if __name__ == "__main__":
    main()
