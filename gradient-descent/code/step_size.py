"""The step size: the same one-knob walk with five values of eta, drawn on a number line step by step, and the one
number that decides what happens, 1 - 2 * eta.

    python3 step_size.py              # the video's five step sizes: 1/20, 1/4, 3/4, 1, 11/10, instantly
    python3 step_size.py --eta 0.4 0.6 0.99

Valley: height(x) = (x - 2)**2 + 1, bottom at 2, start at 6. One step does x - 2 -> (1 - 2 * eta) * (x - 2), so:

    0 < eta < 1/2     the factor is between 0 and 1: the walk creeps in from one side, never crossing the bottom
    eta = 1/2         the factor is 0: one step lands on the bottom
    1/2 < eta < 1     the factor is between -1 and 0: it crosses the bottom every step and bounces in closer
    eta = 1           the factor is -1: it bounces between 6 and -2 forever
    eta > 1           the factor is below -1: every bounce lands farther out, and the walk runs away

"Steps to within 0.01" counts steps until the walker is within one hundredth of the bottom, in exact fractions
(the video's 57, 9 and 9). Standard library only.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Fr

START, BOTTOM = Fr(6), 2
VIDEO = ["1/20", "1/4", "3/4", "1", "11/10"]
LO, HI, WIDTH = -8, 14, 67           # the number line drawn for each walk


def step(x, eta):
    return x - eta * 2 * (x - BOTTOM)


def steps_within(eta, tol=Fr(1, 100), cap=10_000):
    """Steps until |x - 2| <= tol (None if it never gets there: stuck bouncing or running away)."""
    x = START
    for k in range(cap + 1):
        if abs(x - BOTTOM) <= tol:
            return k
        if abs(x - BOTTOM) > 10 ** 6:
            return None
        x = step(x, eta)
    return None


def col(x) -> int:
    return round((float(x) - LO) / (HI - LO) * (WIDTH - 1))


def draw(eta, rows=8) -> None:
    """One line per step: '|' the bottom, 'o' where the walker stands, '>' or '<' if it has left the drawing."""
    x = START
    axis = [" "] * WIDTH
    for v in range(LO, HI + 1, 2):
        axis[col(v)] = "+"
    label = "".join(axis)
    print(f"        {LO:<4}{'':{col(BOTTOM) - 4}}2{'':{col(6) - col(BOTTOM) - 1}}6{'':{WIDTH - col(6) - 4}}{HI:>3}")
    print(f"        {label}")
    for k in range(rows + 1):
        line = [" "] * WIDTH
        line[col(BOTTOM)] = "|"
        c = col(x)
        if c < 0:
            line[0] = "<"
        elif c >= WIDTH:
            line[-1] = ">"
        else:
            line[c] = "o"
        print(f"  {k:>3}   {''.join(line)}   x = {float(x):g}")
        x = step(x, eta)


def verdict(f) -> str:
    if f == 0:
        return "lands on the bottom in one step"
    if 0 < f < 1:
        return "creeps in from one side"
    if -1 < f < 0:
        return "bounces in, a little closer each time"
    if f == -1:
        return "bounces between the same two spots forever"
    if f < -1:
        return "every bounce lands farther out: it flies off"
    return "doesn't move toward the bottom"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--eta", nargs="+", default=VIDEO, help="step sizes to try (fractions or decimals)")
    ap.add_argument("--rows", type=int, default=8, help="steps drawn per walk (default 8)")
    a = ap.parse_args()

    print(f"{'eta':>7} {'1 - 2*eta':>10} {'first positions':<44} {'steps to within 0.01':>21}")
    for e in a.eta:
        eta = Fr(e)
        xs, x = [], START
        for _ in range(6):
            xs.append(f"{float(x):g}")
            x = step(x, eta)
        n = steps_within(eta)
        print(f"{e:>7} {str(1 - 2 * eta):>10} {', '.join(xs):<44} {'never' if n is None else n:>21}")
    for e in a.eta:
        eta = Fr(e)
        f = 1 - 2 * eta
        print(f"\neta = {e}: distance x (1 - 2*eta) = distance x {f}: {verdict(f)}")
        draw(eta, a.rows)


if __name__ == "__main__":
    main()
