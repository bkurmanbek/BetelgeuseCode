"""Teaching a line: gradient descent fits a line to twelve apartments in Lisbon, step by step, and lands on the
answer the textbook formula gives. Then the same fit with the usual pair of knobs, where the error landscape is a
long thin valley and the same walk needs hundreds of thousands of steps.

    python3 rent_line.py --quick      # the 40-step walk and the exact answer, instantly (skips the long walk)
    python3 rent_line.py              # also the usual knobs: 738,888 steps, about 2 s on a laptop, a few MB
    python3 rent_line.py --plot       # also draws rent_line.png (needs matplotlib; the rest doesn't)

The apartments are made up: sizes and rents generated from a fixed seed (1847) around a believable Lisbon price
line, not real listings. They are the same twelve as in the video.

The line has two knobs:
    a = the rent it guesses for an average-size apartment, 75 m^2 (it slides the line up and down)
    s = the extra rent for every 10 m^2 more (it tilts the line around 75 m^2)
    guess(m) = a + s * (m - 75) / 10

The error E(a, s) is the average of the squared misses (guess - rent)^2; its square root is the typical miss.
Its two slopes are
    dE/da = 2 * average(miss)              dE/ds = 2 * average(miss * u),   u = (m - 75) / 10
and the walk is (a, s) -> (a, s) - eta * (dE/da, dE/ds) with eta = 0.08 from a flat line at 900 euros. It stops
when it is within half a euro of the best a and 0.05 euro of the best s, as in the video's run. The best line
comes from algebra, in exact fractions (least squares), not from the walk. Standard library only.
"""

from __future__ import annotations

import argparse
import math
import random
import time
from fractions import Fraction as Fr

SEED, PIVOT, PER = 1847, 75, 10
APARTMENTS = [(48, 1010), (52, 1120), (56, 1320), (62, 1090), (63, 990), (68, 1090),
              (71, 1250), (87, 1600), (93, 1610), (95, 1690), (98, 1810), (107, 2120)]   # (m^2, euros a month)
ETA, START = 0.08, (900.0, 0.0)


def generate(seed=SEED):
    """How the twelve were made: 11 sizes from 38 to 112 m^2 and a 12th that makes the average exactly 75, then
    rent = 16.5 euros per m^2 + 150, plus noise (sd 90), rounded to 10 euros."""
    rng = random.Random(seed)
    while True:
        sizes = [rng.randrange(38, 113) for _ in range(11)]
        last = 900 - sum(sizes)
        if 38 <= last <= 112 and last not in sizes:
            sizes.append(last)
            break
    rents = [int(round((16.5 * m + 150 + rng.gauss(0, 90)) / 10) * 10) for m in sizes]
    return sorted(zip(sizes, rents))


def errors(a, s, u, y):
    misses = [a + s * t - v for t, v in zip(u, y)]
    return misses, sum(q * q for q in misses) / len(misses)


def slopes(a, s, u, y):
    misses, _ = errors(a, s, u, y)
    n = len(misses)
    return 2 * sum(misses) / n, 2 * sum(q * t for q, t in zip(misses, u)) / n


def exact_line(sizes, y):
    """Least squares in exact fractions: a = the average rent (the sizes average exactly 75), s = cov(u, y) / var(u)."""
    n = len(sizes)
    U, Y = [Fr(m - PIVOT, PER) for m in sizes], [Fr(v) for v in y]
    var_u = sum(t * t for t in U) / n
    return sum(Y) / n, sum(t * v for t, v in zip(U, Y)) / n / var_u, var_u


def frac(f: Fr) -> str:
    return f"{f.numerator}/{f.denominator}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="skip the long walk with the usual knobs")
    ap.add_argument("--eta", type=float, default=ETA, help=f"step size for the walk (default {ETA})")
    ap.add_argument("--plot", action="store_true", help="also draw rent_line.png with matplotlib")
    a_ = ap.parse_args()

    if generate() != APARTMENTS:
        print("note: this Python's random module made different apartments; using the table from the video\n")
    sizes, rents = [m for m, _ in APARTMENTS], [v for _, v in APARTMENTS]
    n = len(sizes)
    print(f"{n} apartments in Lisbon (generated, not real listings), average size {sum(sizes) / n:g} m^2:")
    print("  " + "  ".join(f"{m} m^2 {v:,}" for m, v in APARTMENTS[:6]))
    print("  " + "  ".join(f"{m} m^2 {v:,}" for m, v in APARTMENTS[6:]))

    u = [(m - PIVOT) / PER for m in sizes]
    best_a, best_s, var_u = exact_line(sizes, rents)
    _, best_e = errors(float(best_a), float(best_s), u, rents)
    print(f"\nthe best line (exact): a = {frac(best_a)} = {float(best_a):.4f} euros at 75 m^2, "
          f"s = {frac(best_s)} = {float(best_s):.4f} more per 10 m^2")
    print(f"  as rent = b + w * size: b = {float(best_a - best_s * PIVOT / PER):.4f} at 0 m^2, "
          f"w = {float(best_s / PER):.4f} per m^2; its typical miss {math.sqrt(best_e):.2f} euros")

    print(f"\nthe walk: eta = {a_.eta}, from a flat line at {START[0]:g} euros")
    print(f"{'step':>5} {'a (at 75 m2)':>13} {'s (per 10 m2)':>14} {'error':>11} {'typical miss':>13}"
          f" {'dE/da':>10} {'dE/ds':>10}")
    a, s = START
    path = []
    for k in range(5000):
        _, e = errors(a, s, u, rents)
        ga, gs = slopes(a, s, u, rents)
        path.append((a, s))
        if k <= 10 or k % 5 == 0 or (abs(a - float(best_a)) < 0.5 and abs(s - float(best_s)) < 0.05):
            print(f"{k:>5} {a:>13.3f} {s:>14.3f} {e:>11.1f} {math.sqrt(e):>13.1f} {ga:>10.3f} {gs:>10.3f}")
        if abs(a - float(best_a)) < 0.5 and abs(s - float(best_s)) < 0.05:
            break
        if not math.isfinite(e) or e > 1e30:
            print("      ... the walk flew off: the step is past this bowl's limit")
            break
        a, s = a - a_.eta * ga, s - a_.eta * gs
    print(f"  -> {len(path) - 1} steps; it misses the exact line by {a - float(best_a):+.2f} euros at 75 m^2 and "
          f"{s - float(best_s):+.4f} per 10 m^2: within half a euro")

    fa, fs = 1 - a_.eta * 2, 1 - a_.eta * 2 * float(var_u)
    print(f"\nwhy it moves the way it does: with these knobs the bowl's two curvatures are 2 (along a) and"
          f" 2 * var(u) = {2 * float(var_u):.4f} (along s),")
    print(f"and they don't mix (the sizes average exactly 75), so each knob walks on its own:")
    print(f"  the gap in a is multiplied by 1 - 2 * eta = {fa:.4f} each step, the gap in s by"
          f" 1 - 2 * var(u) * eta = {fs:.4f}")
    gap0 = START[0] - float(best_a)
    print(f"  so after {len(path) - 1} steps the gap in a is {gap0:.3f} x {fa:.2f}^{len(path) - 1} = "
          f"{gap0 * fa ** (len(path) - 1):+.2f}: first mostly a tilt, then a slow slide")
    print(f"  step-size limits: 2 / 2 = 1 for a and 2 / (2 * var(u)) = {1 / float(var_u):.6f} for s")

    usual(sizes, rents, best_a, best_s, a_.quick)
    if a_.plot:
        plot(APARTMENTS, path, float(best_a), float(best_s))


def usual(sizes, rents, best_a, best_s, quick) -> None:
    """The usual knobs: b = rent at 0 m^2 and w = rent per m^2. Same error, same best line, another landscape."""
    n = len(sizes)
    xbar = sum(sizes) / n
    sx2 = sum(m * m for m in sizes) / n
    # the bowl's curvatures in (b, w): eigenvalues of [[2, 2 xbar], [2 xbar, 2 mean(size^2)]]
    tr, det = 2 + 2 * sx2, 2 * 2 * sx2 - (2 * xbar) ** 2
    disc = math.sqrt(tr * tr / 4 - det)
    lo, hi = tr / 2 - disc, tr / 2 + disc
    eta = 1.0 / hi
    print(f"\nthe usual knobs: b = rent at 0 m^2, w = rent per m^2 (the same line: rent = b + w * size)")
    print(f"  curvatures of the error bowl: {lo:.6f} and {hi:.2f}: one direction is {hi / lo:,.0f} times more curved")
    print(f"  a safe step for the steep direction: eta = 1 / {hi:.2f} = {eta:.10f} (half its limit 2 / {hi:.2f})")
    if quick:
        print("  the walk with that step: skipped with --quick (run without it: about 2 s)")
        return
    b_best, w_best = float(best_a - best_s * PIVOT / PER), float(best_s / PER)
    b, w = START[0], 0.0
    t0 = time.time()
    for k in range(2_000_000):
        if abs(b - b_best) < 0.5 and abs(w - w_best) < 0.005:
            break
        res = [b + w * m - v for m, v in zip(sizes, rents)]
        gb, gw = 2 * sum(res) / n, 2 * sum(q * m for q, m in zip(res, sizes)) / n
        b, w = b - eta * gb, w - eta * gw
    print(f"  the same walk from a flat line at {START[0]:g} euros needs {k:,} steps to get within half a euro "
          f"({time.time() - t0:.1f} s here)")
    print(f"  across the valley the walk settles in a few steps; along it, each step shrinks the gap only by a factor of"
          f" 1 - {lo:.6f} * eta = {1 - lo * eta:.8f}")


def plot(apts, path, best_a, best_s) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit("--plot needs matplotlib (pip install matplotlib); everything else runs without it")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))
    ax1.scatter([m for m, _ in apts], [v for _, v in apts], color="#1D5FD0", zorder=3, label="apartments")
    for k in (0, 1, 2, 5, len(path) - 1):
        a, s = path[k]
        ax1.plot([40, 110], [a + s * (40 - PIVOT) / PER, a + s * (110 - PIVOT) / PER],
                 color="#1E7346" if k == len(path) - 1 else "#B57600", alpha=1 if k == len(path) - 1 else 0.35,
                 label=f"step {k}" if k in (0, len(path) - 1) else None)
    ax1.set_xlabel("size (m²)")
    ax1.set_ylabel("monthly rent (euros)")
    ax1.legend(fontsize=8)
    A = [800 + i * 10 for i in range(81)]
    S = [-50 + i * 4 for i in range(81)]
    u = [(m - PIVOT) / PER for m, _ in apts]
    y = [v for _, v in apts]
    Z = [[math.sqrt(errors(a, s, u, y)[1]) for a in A] for s in S]
    ax2.contour(A, S, Z, levels=20, cmap="Blues")
    ax2.plot([p[0] for p in path], [p[1] for p in path], "o-", ms=3, color="#B57600")
    ax2.plot(best_a, best_s, "o", mfc="none", mec="#1E7346", ms=12, mew=2)
    ax2.set_xlabel("a: rent at 75 m² (euros)")
    ax2.set_ylabel("s: extra rent per 10 m² (euros)")
    ax2.set_title("typical miss over the two knobs, and the walk", fontsize=10)
    fig.tight_layout()
    fig.savefig("rent_line.png", dpi=150)
    print("wrote rent_line.png")


if __name__ == "__main__":
    main()
