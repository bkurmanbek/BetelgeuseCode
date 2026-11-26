"""Check the Riemann hypothesis up to a height T yourself, by counting the zeros of zeta two ways.

In plain words: zeta's zeros are points on a map, each a distance across and a distance up. The Riemann
hypothesis says that every one of them (apart from the easy ones at -2, -4, -6, ...) sits exactly halfway across.
This script counts the zeros up to the height you choose, twice. First every zero, wherever it sits, by walking
around the edge of that region and counting how many times zeta turns all the way around. Then only the zeros on
the halfway line, by walking up it and counting where a number flips sign. If the two counts agree, no zero up to
that height is off the line. The rest of this note is the maths behind the two counts.

    python3 check_rh.py 100             # T = 100: done in seconds
    python3 check_rh.py 1000             # the run in the notes (both counts 649): about nine minutes
    python3 check_rh.py 300 --zetazero   # also count mpmath's own list of zeros below T
    python3 check_rh.py 100 --step 2     # a grid too coarse for the zeros: the counts disagree, and say so

Count 1, every zero in the critical strip 0 < Re s < 1 with 0 < Im s <= T, wherever it sits: the argument
principle gives N(T) = theta(T)/pi + 1 + S(T). theta is the Riemann-Siegel theta function (mpmath.siegeltheta);
S(T) = arg zeta(1/2 + iT) / pi, with the argument followed continuously along the line Im s = T, from 3 + iT
(where zeta is close to 1) to 1/2 + iT. N(T) counts zeros, so the sum has to land on a whole number.

Count 2, the zeros ON the line Re s = 1/2: Hardy's Z(t) = exp(i theta(t)) zeta(1/2 + it) is real for real t and
|Z(t)| = |zeta(1/2 + it)|, so every sign change of Z between two grid points is a zero on the line.

    sign changes  <=  zeros on the line  <=  N(T)

so when the two counts are equal, no zero below T is off the line (and each one is simple). This is floating
point, not interval arithmetic: it shows the method that rigorous verifications make airtight (Turing's method,
interval arithmetic), it is not a proof. A grid that is too coarse can step over two close zeros; that never
hides a problem, it only makes the counts disagree.

Needs mpmath (`pip install mpmath`). Same method, step sizes and precision as the lesson's bench, so
`python3 check_rh.py 1000` prints the numbers in the notes.
"""

from __future__ import annotations

import argparse
import sys

try:
    import mpmath as mp
except ImportError:
    sys.exit("check_rh.py needs mpmath: pip install mpmath")

ARG_STEP = "0.002"   # sigma step along Im s = T, from 3 down to 1/2
GRID = 0.01          # t step for the sign changes of Z(t)


def count_in_strip(T: float) -> dict:
    """N(T) = theta(T)/pi + 1 + S(T), with S(T) from the continuous change of arg zeta along Im s = T."""
    with mp.workdps(20):
        theta = mp.siegeltheta(T)
        sig, step = mp.mpf(3), mp.mpf(ARG_STEP)
        prev = mp.zeta(mp.mpc(sig, T))
        arg, biggest, steps = mp.arg(prev), mp.mpf(0), 0
        while sig > 0.5:
            sig = max(mp.mpf(0.5), sig - step)
            cur = mp.zeta(mp.mpc(sig, T))
            d = mp.arg(cur / prev)          # this step's change of the argument, in (-pi, pi]
            biggest = max(biggest, abs(d))
            arg += d
            prev = cur
            steps += 1
        S = arg / mp.pi
        N = theta / mp.pi + 1 + S
        return {"theta_over_pi": theta / mp.pi, "S": S, "N_exact": N, "N": int(mp.nint(N)), "steps": steps,
                "largest_arg_step": biggest, "abs_zeta_at_T": abs(prev)}


def count_on_line(T: float, grid: float = GRID) -> dict:
    """Sign changes of Hardy's Z(t) on the grid t = 1, 1 + grid, … <= T, and at T (no zero lies below t = 14)."""
    with mp.workdps(15):
        n, prev, k = 0, mp.siegelz(1), 1
        while True:
            t = 1 + k * grid
            if t > T:
                break
            z = mp.siegelz(t)
            if (z > 0) != (prev > 0):
                n += 1
            prev = z
            k += 1
        if 1 + (k - 1) * grid < T:          # a coarse grid stops short of T: sample T itself too
            n += (mp.siegelz(T) > 0) != (prev > 0)
            k += 1
        return {"sign_changes": n, "points": k}


def count_listed(T: float) -> int:
    """How many of mpmath's zetazero(1), zetazero(2), … lie below T (it only ever looks on the line)."""
    n = 0
    while mp.zetazero(n + 1).imag <= T:
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("T", nargs="?", type=float, default=100.0, help="height to check up to (default 100)")
    ap.add_argument("--step", type=float, default=GRID, help=f"grid step for Z(t) (default {GRID})")
    ap.add_argument("--zetazero", action="store_true", help="also count mpmath's list of zeros below T")
    a = ap.parse_args()
    T = a.T
    if T < 15:
        print(f"T = {T:g}: the first zero is at height 14.13…, pick T >= 15")
        return 2

    print(f"Zeros of zeta with 0 < Im s <= T = {T:g}, counted two ways (mpmath {mp.__version__})\n")
    strip = count_in_strip(T)
    if strip["abs_zeta_at_T"] < 1e-3:
        print(f"T = {T:g} sits (almost) on a zero, where arg zeta is undefined: pick a height slightly above or below")
        return 2
    print("1. Every zero in the strip 0 < Re s < 1 (argument principle):")
    print(f"     theta(T)/pi       = {mp.nstr(strip['theta_over_pi'], 10)}")
    print(f"     S(T)              = {mp.nstr(strip['S'], 8)}")
    print(f"       (arg zeta followed from 3 + iT to 1/2 + iT in {strip['steps']:,} steps, "
          f"the largest {mp.nstr(strip['largest_arg_step'], 4)} rad)")
    print(f"     theta/pi + 1 + S  = {mp.nstr(strip['N_exact'], 10)}   ->  N(T) = {strip['N']} zeros")
    whole = abs(strip["N_exact"] - strip["N"]) < 0.01
    if not whole:
        print("     (that is not a whole number: the computation is off; raise the precision)")

    line = count_on_line(T, a.step)
    print("\n2. Zeros on the line Re s = 1/2 (sign changes of Hardy's Z(t)):")
    print(f"     t = 1 … {T:g} in steps of {a.step:g}, {line['points']:,} points")
    print(f"     {line['sign_changes']} sign changes")

    listed = None
    if a.zetazero:
        listed = count_listed(T)
        print(f"\n   mpmath's zetazero(n) list below T: {listed} zeros")
        print("   (it searches the line only, so it can't see a zero off it)")

    agree = whole and strip["N"] == line["sign_changes"] and listed in (None, strip["N"])
    print(f"\nAgree: {'yes' if agree else 'NO'}.", end=" ")
    if agree:
        print(f"Below height {T:g}, no zero of zeta lies off the line Re s = 1/2.")
    elif line["sign_changes"] < strip["N"]:
        print(f"{strip['N'] - line['sign_changes']} zero(s) in the strip weren't seen on the line:")
        print("either the grid stepped over close zeros (try a smaller --step) or a zero is off the line.")
    else:
        print("More sign changes than zeros can't happen: the precision is too low for this height.")
    return 0 if agree else 1


if __name__ == "__main__":
    sys.exit(main())
