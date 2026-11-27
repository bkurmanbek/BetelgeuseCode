"""The family of walks that train real models, on the same twelve Lisbon apartments as rent_line.py: batch (all
twelve slopes averaged, every step), stochastic (one apartment per step), mini-batch (four), each with a constant step
and a shrinking one; momentum (a heavy ball that remembers its last steps); and Adam (a step size of its own for each
knob). Same flat start at 900 euros, same half-a-euro test, nothing timed: it counts steps and shows what each walk
does inside.

    python3 family.py             # every walk, to the end: under a second on a laptop, a few MB
    python3 family.py --plot      # also draws family.png (needs matplotlib; the rest doesn't)

The line is the one of rent_line.py: guess(m) = a + s * (m - 75) / 10. One apartment's error is
e_i = (guess(m_i) - rent_i)^2, and the error E is their average, so E's slope is the average of the twelve slopes:

    batch        knobs -= eta * (1/12) * sum of all twelve slopes
    stochastic   knobs -= eta * slope of one apartment          (the next one in a shuffled order)
    mini-batch   knobs -= eta * (1/4) * sum of four slopes       (the next four)
    momentum     v = beta * v + slope;  knobs -= eta * v        (beta = 0.9)
    Adam         per knob: m = running average of its slope, s = of its slope squared;
                 knob -= eta * m / (sqrt(s) + eps)              (with the start-up correction, below)

The apartments are shuffled once per epoch (one pass through all twelve) from a fixed seed (7), the same shuffles for
every stochastic run. "Line gap" is how far a line is from the best line, in euros: sqrt(E - best E), the typical
difference between the rents the two lines guess. Standard library only.
"""

from __future__ import annotations

import argparse
import math
import random
from fractions import Fraction as Fr
from itertools import combinations

APARTMENTS = [(48, 1010), (52, 1120), (56, 1320), (62, 1090), (63, 990), (68, 1090),
              (71, 1250), (87, 1600), (93, 1610), (95, 1690), (98, 1810), (107, 2120)]   # (m^2, euros a month)
PIVOT, PER = 75, 10
START = (900.0, 0.0)            # the flat line at 900 euros
ETA = 0.08                      # the plain walk's step (rent_line.py)
SHUFFLE_SEED, BETA = 7, 0.9
EPOCHS_CONST, EPOCHS_DECAY, TAU = 100, 10_000, 12   # constant step: 100 epochs; shrinking: eta_k = ETA / (1 + k/TAU)
B1, B2, EPS, ETA_ADAM, HORIZON = 0.9, 0.999, 1e-8, 1.0, 20_000

N = len(APARTMENTS)
SIZES = [m for m, _ in APARTMENTS]
U_EXACT = [Fr(m - PIVOT, PER) for m in SIZES]
Y_EXACT = [Fr(v) for _, v in APARTMENTS]
VAR_U_EXACT = sum(t * t for t in U_EXACT) / N
A_EXACT = sum(Y_EXACT) / N                                         # the best line (least squares, exact)
S_EXACT = sum(t * v for t, v in zip(U_EXACT, Y_EXACT)) / N / VAR_U_EXACT
A, S, VU = float(A_EXACT), float(S_EXACT), float(VAR_U_EXACT)
B, W = float(A_EXACT - S_EXACT / 10 * 75), float(S_EXACT / 10)    # the same line as rent = b + w * size
u = [float(t) for t in U_EXACT]
y = [float(v) for v in Y_EXACT]
x = [float(m) for m in SIZES]


def gap(a, s):
    """Line gap: E(a, s) - best E = (a - A)^2 + var(u) (s - S)^2 (the knobs don't mix), so this is sqrt(E - best E)."""
    return math.sqrt((a - A) ** 2 + VU * (s - S) ** 2)


def typical_miss(a, s):
    return math.sqrt(sum((a + s * t - v) ** 2 for t, v in zip(u, y)) / N)


def within(a, s):
    return abs(a - A) < 0.5 and abs(s - S) < 0.05


def within_raw(b, w):
    return abs(b - B) < 0.5 and abs(w - W) < 0.005


def slope_on(a, s, idx):
    """The slope of the error over the apartments idx only: 2 * average(miss), 2 * average(miss * u)."""
    res = [a + s * u[i] - y[i] for i in idx]
    return 2 * sum(res) / len(idx), 2 * sum(q * u[i] for q, i in zip(res, idx)) / len(idx)


def slope_raw(b, w):
    res = [b + w * p - v for p, v in zip(x, y)]
    return 2 * sum(res) / N, 2 * sum(q * p for q, p in zip(res, x)) / N


def stays_from(flags):
    """The step from which every later step passes the test; claimed only if the run went on at least as long after
    it as before it (else None: it may still leave)."""
    last_out = max((k for k, v in enumerate(flags) if not v), default=-1)
    return last_out + 1 if 2 * (last_out + 1) <= len(flags) - 1 else None


def shuffled(size, eta_at, epochs):
    """Stochastic (size 1) or mini-batch (size 4): a fresh seeded shuffle each epoch, `size` apartments per step."""
    rng = random.Random(SHUFFLE_SEED)
    a, s, k = START[0], START[1], 0
    pts, used = [(a, s)], []
    for _ in range(epochs):
        order = list(range(N))
        rng.shuffle(order)
        for j in range(0, N, size):
            idx = order[j:j + size]
            ga, gs = slope_on(a, s, idx)
            eta = eta_at(k)
            a, s, k = a - eta * ga, s - eta * gs, k + 1
            pts.append((a, s))
            used.append(idx)
    return pts, used


def look_inside_slopes() -> None:
    print("each apartment's own slope (along a, along s), and their average, which is the batch walk's slope:")
    for label, (a, s) in (("at the flat line, 900 euros", START), ("at the best line", (A, S))):
        own = [slope_on(a, s, [i]) for i in range(N)]
        print(f"  {label}:")
        print("    " + "  ".join(f"({ga:+.0f}, {gs:+.0f})" for ga, gs in own[:6]))
        print("    " + "  ".join(f"({ga:+.0f}, {gs:+.0f})" for ga, gs in own[6:]))
        avg = slope_on(a, s, range(N))
        print(f"    average: ({avg[0]:+.3f}, {avg[1]:+.3f})")
    print("  at the best line the average is zero, so the batch walk stops; each apartment's own slope isn't,")
    print("  so a walk that steps on one apartment at a time keeps getting kicked, even at the bottom")


def batch() -> list:
    a, s = START
    path = [(a, s)]
    while not within(a, s):
        ga, gs = slope_on(a, s, range(N))
        a, s = a - ETA * ga, s - ETA * gs
        path.append((a, s))
    print(f"\nbatch: all {N} apartments in every step, eta = {ETA}")
    print(f"  within half a euro after {len(path) - 1} steps; line gap by step: "
          + ", ".join(f"{k}: {gap(*path[k]):.1f}" for k in (0, 1, 2, 5, 10, 20, len(path) - 1)))
    return path


def constant_run(name, size):
    per = N // size
    pts, used = shuffled(size, lambda k: ETA, EPOCHS_CONST)
    flags = [within(*p) for p in pts]
    print(f"\n{name}: {size} apartment{'s' if size > 1 else ''} per step ({per} steps an epoch), constant eta = {ETA}")
    print(f"  the first steps (apartment numbers are 0-11, smallest to largest):")
    for k in range(4):
        print(f"    step {k + 1}: apartments {used[k]}, the line moves to a = {pts[k + 1][0]:7.1f}, s = "
              f"{pts[k + 1][1]:6.1f}, line gap {gap(*pts[k + 1]):6.1f}")
    first = next((k for k, v in enumerate(flags) if v), None)
    best = min(range(len(pts)), key=lambda k: gap(*pts[k]))
    win = pts[(EPOCHS_CONST // 2) * per:]
    gaps = [gap(*p) for p in win]
    rms = math.sqrt(sum(g * g for g in gaps) / len(gaps))
    misses = [typical_miss(*p) for p in win]
    print(f"  {len(pts) - 1:,} steps ({EPOCHS_CONST} epochs): within half a euro "
          + (f"from step {first}" if first is not None else "never"))
    print(f"  closest pass: step {best}, line gap {gap(*pts[best]):.3f} (a {pts[best][0] - A:+.3f}, "
          f"s {pts[best][1] - S:+.4f}), and it moves on")
    print(f"  epochs {EPOCHS_CONST // 2 + 1}-{EPOCHS_CONST}: the line gap hovers at {rms:.2f} euros typical (root mean "
          f"square), up to {max(gaps):.2f}; typical miss {min(misses):.1f} to {max(misses):.1f}")
    print(f"     a from {min(p[0] for p in win):.1f} to {max(p[0] for p in win):.1f}, "
          f"s from {min(p[1] for p in win):.2f} to {max(p[1] for p in win):.2f}")
    return pts, rms


def decaying_run(name, size):
    pts, _ = shuffled(size, lambda k: ETA / (1 + k / TAU), EPOCHS_DECAY)
    flags = [within(*p) for p in pts]
    first, stay = next(k for k, v in enumerate(flags) if v), stays_from(flags)
    per = N // size
    print(f"\n{name}, shrinking step eta_k = {ETA} / (1 + k/{TAU}) (k = steps taken), {EPOCHS_DECAY:,} epochs:")
    for e in (1, 10, 100, 1000, EPOCHS_DECAY):
        print(f"  epoch {e:>6,}: eta {ETA / (1 + (e - 1) * per / TAU):.8f}  line gap {gap(*pts[e * per]):8.2f}")
    print(f"  first within half a euro at step {first:,}; within at every step from {stay:,} on "
          f"(eta there {ETA / (1 + stay / TAU):.3e})")
    return pts, stay


def limits() -> None:
    one = 2 / max(2 * (1 + t * t) for t in u)
    print(f"\nwhy eta can't simply grow: one apartment's error is a bowl too, curving by 2 (1 + u^2) along its"
          f" steepest way;\n  the largest apartment allows eta up to {one:.4f}, and eta = {ETA} sits just under it")

    def lim(idx):
        mu, mu2 = sum(u[i] for i in idx) / len(idx), sum(u[i] ** 2 for i in idx) / len(idx)
        tr, det = 2 + 2 * mu2, 4 * mu2 - (2 * mu) ** 2
        return 2 / (tr / 2 + math.sqrt(max(tr * tr / 4 - det, 0)))

    worst = min(lim(c) for c in combinations(range(N), 4))
    print(f"  the most sharply curved group of four allows up to {worst:.4f}")


def heavy(slope, eta, cap, test):
    p, q, vp, vq = START[0], START[1], 0.0, 0.0
    pts = [(p, q)]
    for _ in range(cap):
        gp, gq = slope(p, q)
        vp, vq = BETA * vp + gp, BETA * vq + gq
        p, q = p - eta * vp, q - eta * vq
        pts.append((p, q))
    flags = [test(*t) for t in pts]
    return pts, next(k for k, v in enumerate(flags) if v), stays_from(flags)


def momentum() -> None:
    print(f"\nmomentum (the heavy ball): v = {BETA} v + slope, knobs -= eta v; on a steady slope v grows to"
          f" slope / (1 - {BETA}) = {1 / (1 - BETA):.0f} x slope")
    pts, first, stay = heavy(lambda a, s: slope_on(a, s, range(N)), ETA, 3000, within)
    print(f"  centred knobs (a, s), eta = {ETA} as the plain walk: a swings up to "
          f"{max(t[0] for t in pts[:stay + 1]):.1f} (best {A:.1f}), s up to {max(t[1] for t in pts[:stay + 1]):.1f}"
          f" (best {S:.1f});")
    print(f"    within half a euro first at step {first}, for good from step {stay} (the plain walk: 40 steps)")
    sx2 = sum(Fr(m) * Fr(m) for m in SIZES) / N
    xbar = Fr(sum(SIZES), N)
    a_, b_, d_ = 2.0, float(2 * xbar), float(2 * sx2)
    tr, det = a_ + d_, a_ * d_ - b_ * b_
    hi = tr / 2 + math.sqrt(max(tr * tr / 4 - det, 0))
    eta_raw = round(1.0 / hi, 10)                  # the plain walk's step on these knobs (rent_line.py)
    plain_b, p, q = {}, START[0], START[1]
    marks = (1_000, 10_000, 50_000)
    for k in range(1, max(marks) + 1):
        gp, gq = slope_raw(p, q)
        p, q = p - eta_raw * gp, q - eta_raw * gq
        if k in marks:
            plain_b[k] = p
    pts, first, stay = heavy(slope_raw, eta_raw, 150_000, within_raw)
    print(f"  usual knobs (b at 0 m^2, w per m^2), eta = {eta_raw} as the plain walk there; how far b still is from"
          f" its best ({B:.2f}):")
    for k in marks:
        print(f"    after {k:>6,} steps: plain walk {plain_b[k] - B:+8.2f}   heavy ball {pts[k][0] - B:+8.2f}")
    print(f"  across the valley the memory swings and dies out; along it the steps pile up to about"
          f" {1 / (1 - BETA):.0f} x: within half a euro at step {first:,} (the plain walk: 738,888)")


def adam() -> None:
    th, m1, m2 = [START[0], START[1]], [0.0, 0.0], [0.0, 0.0]
    pts = [tuple(th)]
    print(f"\nAdam on the usual knobs (b at 0 m^2, w per m^2): beta1 {B1}, beta2 {B2}, eps {EPS}, eta {ETA_ADAM}")
    print(f"  {'step':>6} {'b - best':>10} {'w - best':>11} {'line gap':>9} {'step size b':>12} {'step size w':>12}"
          "   (step size = eta / sqrt(s), per knob)")
    show = {1, 2, 10, 100, 1000, 3000, 5000, 6000, 6500, 6530, 6535, 6540, 6600, 6700}
    for k in range(1, HORIZON + 1):
        g = slope_raw(*th)
        for i in range(2):
            m1[i] = B1 * m1[i] + (1 - B1) * g[i]
            m2[i] = B2 * m2[i] + (1 - B2) * g[i] ** 2
            th[i] -= ETA_ADAM * (m1[i] / (1 - B1 ** k)) / (math.sqrt(m2[i] / (1 - B2 ** k)) + EPS)
        pts.append(tuple(th))
        if k in show:
            sb, sw = (math.sqrt(m2[i] / (1 - B2 ** k)) for i in range(2))
            print(f"  {k:>6} {th[0] - B:>+10.3f} {th[1] - W:>+11.5f} {gap(th[0] + 75 * th[1], 10 * th[1]):>9.2f} "
                  f"{ETA_ADAM / sb:>12.4g} {ETA_ADAM / sw:>12.4g}")
    print(f"  the first step moved b by {pts[1][0] - pts[0][0]:.6f} and w by {pts[1][1] - pts[0][1]:.6f}: about eta"
          " each, whatever the slope")
    flags = [within_raw(*t) for t in pts]
    first = next(k for k, v in enumerate(flags) if v)
    exits = [k for k in range(1, len(flags)) if flags[k - 1] and not flags[k]]
    bursts = [[exits[0]]] if exits else []
    for e in exits[1:]:                               # a burst: exits less than 300 steps apart
        if e - bursts[-1][-1] < 300:
            bursts[-1].append(e)
        else:
            bursts.append([e])
    starts = [c[0] for c in bursts]
    spacing = sorted(b2 - b1 for b1, b2 in zip(starts[1:], starts[2:]))

    def peak(c):
        return max(gap(pts[k][0] + 75 * pts[k][1], 10 * pts[k][1]) for k in range(c[0], c[-1] + 1))

    share = sum(flags[first:]) / len(flags[first:])
    print(f"  within half a euro first at step {first:,} (the plain walk: 738,888); "
          f"stays there for good: {'from ' + str(stays_from(flags)) if stays_from(flags) is not None else 'no'}")
    if bursts:
        print(f"  over {HORIZON:,} steps it was within {share:.1%} of the time after that, thrown out {len(bursts)}"
              f" times: first at step {exits[0]:,}, then every {spacing[len(spacing) // 2]} steps or so (median);")
        print(f"  the first burst took the line {peak(bursts[0]):.2f} euros from the best one, later ones at most "
              f"{max(peak(c) for c in bursts[1:]):.2f}")
    print("  why: once the slopes vanish, s fades too (it remembers about the last 1/(1 - beta2) = "
          f"{1 / (1 - B2):,.0f} steps),\n  so eta / sqrt(s) grows until a tiny wobble is amplified; the slope jumps, s"
          " jumps with it, the steps shrink, and the walk comes back")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--plot", action="store_true", help="also draw family.png with matplotlib")
    a = ap.parse_args()

    print(f"the best line (exact): a = {A:.4f} euros at 75 m^2, s = {S:.4f} per 10 m^2; "
          f"its typical miss {typical_miss(A, S):.2f} euros\n")
    look_inside_slopes()
    path = batch()
    sgd, rms1 = constant_run("stochastic", 1)
    mb, rms4 = constant_run("mini-batch", 4)
    print(f"\n  the hover: {rms1:.2f} / {rms4:.2f} = {rms1 / rms4:.2f} times calmer with four. Averaging four"
          " independent draws would cut the spread by sqrt(4) = 2;")
    print("  here each epoch uses every apartment once, so the kicks cancel over an epoch, and what is left is the drift")
    print("  partway through one: four steps of eta on one apartment each, or one step of eta on their average")
    limits()
    decaying_run("stochastic", 1)
    decaying_run("mini-batch", 4)
    momentum()
    adam()
    if a.plot:
        plot(path, sgd, mb)


def plot(path, sgd, mb) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit("--plot needs matplotlib (pip install matplotlib); everything else runs without it")
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.semilogy([k / N for k in range(len(sgd))], [gap(*p) for p in sgd], lw=0.8, color="#B42A30",
                label="stochastic (1 per step)")
    ax.semilogy([k * 4 / N for k in range(len(mb))], [gap(*p) for p in mb], lw=1.2, color="#7C3AED",
                label="mini-batch (4 per step)")
    ax.semilogy(range(len(path)), [gap(*p) for p in path], "o-", ms=3, color="#B57600", label="batch (all 12)")
    ax.set_xlabel("epoch (each apartment used once)")
    ax.set_ylabel("line gap to the best line (euros)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig("family.png", dpi=150)
    print("wrote family.png")


if __name__ == "__main__":
    main()
