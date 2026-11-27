"""One knob: what the slope is, how the computer feels it, and what each step of gradient descent does, in exact
fractions so nothing is hidden by rounding.

    python3 one_knob.py                     # the video's walk: x = 6, eta = 1/4 -> 4, 3, 5/2, 9/4 ... instantly
    python3 one_knob.py --eta 3/4           # any step size (a fraction or a decimal), any start, any number of steps
    python3 one_knob.py --start -1 --steps 12

The valley is height(x) = (x - 2)**2 + 1: a curve whose bottom is at x = 2, height 1. The computer doesn't get to
look at the curve. All it can do is ask for the height at a few spots near where it stands. Two heights a tiny step
apart give the slope (how fast the height changes as you turn the knob), and the rule is

    new x = old x - eta * slope            (eta: the step size, which machine learning calls the learning rate)

For this valley the slope is exactly 2 * (x - 2), so one step does x - 2  ->  (x - 2) - eta * 2 * (x - 2), that is,
it multiplies the distance to the bottom by (1 - 2 * eta). With eta = 1/4 that is 1/2: each step halves the
distance, and the steps shrink on their own because the ground gets flatter. Standard library only.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Fr

BOTTOM = 2


def height(x):
    return (x - BOTTOM) ** 2 + 1


def slope(x):
    """The exact slope (the derivative): how much the height rises per unit of knob, right at x."""
    return 2 * (x - BOTTOM)


def felt_slope(x, h):
    """The slope as a blind walker can measure it: two heights a tiny step h apart (a central difference)."""
    return (height(x + h) - height(x - h)) / (2 * h)


def show(v) -> str:
    """A Fraction as 9/4 or 2 (and a float as it is)."""
    if isinstance(v, Fr):
        return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"
    return f"{v:g}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--eta", default="1/4", help="step size, e.g. 1/4, 3/4, 0.05 (default 1/4)")
    ap.add_argument("--start", default="6", help="where the walk starts (default 6)")
    ap.add_argument("--steps", type=int, default=8, help="how many steps to take (default 8)")
    a = ap.parse_args()
    eta, x = Fr(a.eta), Fr(a.start)

    print("the valley: height(x) = (x - 2)**2 + 1, bottom at x = 2, height 1\n")

    h = 0.001
    x0 = float(x)
    up, down = height(x0 + h), height(x0 - h)
    print(f"feel the slope at x = {show(x)} from two heights a tiny step apart (h = {h}):")
    print(f"  height({x0 + h:g}) = {up:.6f}   height({x0 - h:g}) = {down:.6f}")
    print(f"  slope = (difference of heights) / (2 h) = {felt_slope(x0, h):.6f}")
    print(f"  the formula 2 * (x - 2) gives {show(slope(x))}: turn the knob a tiny bit right and the height rises"
          f" {show(abs(slope(x)))} times as much")
    print(f"  so uphill is to the {'right' if slope(x) > 0 else 'left'}, and the walk steps "
          f"{'left' if slope(x) > 0 else 'right'}\n")

    print(f"the walk: new x = old x - eta * slope, with eta = {show(eta)}, from x = {show(x)}")
    print(f"{'step':>4} {'x':>10} {'height':>12} {'slope':>8} {'eta*slope':>10} {'distance to 2':>14}")
    for k in range(a.steps + 1):
        s = slope(x)
        print(f"{k:>4} {show(x):>10} {show(height(x)):>12} {show(s):>8} {show(eta * s):>10} {show(abs(x - 2)):>14}")
        if abs(x - 2) > 10 ** 9:
            print("      ... the walk has left the valley")
            break
        x = x - eta * s
    factor = 1 - 2 * eta
    print(f"\neach step multiplies the distance to the bottom by 1 - 2 * eta = {show(factor)}", end="")
    if factor == 0:
        print(": one step lands exactly on the bottom")
    elif 0 < factor < 1:
        print(": the walk never crosses the bottom, and every step shrinks the gap")
    elif -1 < factor < 0:
        print(": the walk crosses the bottom every step, and bounces in closer")
    elif factor == -1:
        print(": the walk bounces between the same two spots forever")
    elif factor < -1:
        print(": every bounce lands farther out, and the walk runs away")
    else:
        print(": the walk goes uphill (eta is negative)" if eta < 0 else ": the walk stands still")
    print("at the bottom the slope is 0, so the step is 0 too: nothing tells the walk to stop, it just stops moving")


if __name__ == "__main__":
    main()
