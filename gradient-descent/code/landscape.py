"""Two knobs: the video's landscape, the gradient (the arrow made of the two slopes), and the walks on it: into the
deep valley, into the shallow one, into a small dip that traps a plain walk, a heavy ball (momentum) that rolls
through that dip, and a step too big to ever settle. Drawn as text maps you can read in a terminal.

    python3 landscape.py                    # everything the video shows on the landscape, instantly
    python3 landscape.py --eta 0.69         # the walk from the video's start with another step size
    python3 landscape.py --start 0.6 -2.6 --eta 0.6
    python3 landscape.py --start 0.6 -2.6 --eta 0.15 --beta 0.5    # a heavy ball with less memory
    python3 landscape.py --rows 21          # shorter maps, square on paper (the notes print one)
    python3 landscape.py --plot             # also draws landscape.png (needs matplotlib; the rest doesn't)

The landscape (the same formula as the video): a gentle bowl plus eight bumps, each a bell-shaped dent or hill

    h(x, y) = 0.06 (x^2 + y^2) + sum of  a * exp(-((x - cx)^2 + (y - cy)^2) / w)

with (a, cx, cy, w) listed in BUMPS below: a < 0 is a dent, a > 0 a hill, w sets its width. x and y are the two
knobs; h is the height, the number we want small. The land drawn in the video is the square |x|, |y| <= 2.9.

A walker only gets the height and the two slopes where it stands (here from the formula; check_slopes() shows they
agree with two nearby heights). The rule:

    (x, y)  ->  (x, y) - eta * (slope along x, slope along y)

It stops when the arrow is shorter than 0.001 (the ground is flat), after 400 steps, or if it leaves the map
(|x| or |y| > 3.2): the same rules as the video's runs. The heavy ball keeps a velocity v instead:
v -> beta * v + slope, (x, y) -> (x, y) - eta * v, and stops when the ground is flat and it has stopped moving.
Standard library only.
"""

from __future__ import annotations

import argparse
import math

BOWL = 0.06
BUMPS = [(-1.15, 1.3, 0.7, 0.85),    # the deep valley                      (height a, centre cx, cy, width^2 w)
         (-0.70, -1.5, -1.2, 0.55),  # the shallow valley
         (0.60, 0.0, 1.9, 0.45),     # the big hill at the back
         (0.45, -0.55, -0.05, 0.22), # a round hill in the middle
         (0.40, -2.0, 0.8, 0.35),    # a hill on the left
         (0.35, 1.9, -1.6, 0.40),    # a hill at the front right
         (-0.30, 0.5, -1.0, 0.18),   # the small dip (a trap for a plain walk)
         (0.25, 2.2, 2.2, 0.50)]     # a far corner rise
LAND = 2.9                           # the land the video draws: |x|, |y| <= 2.9
START, OTHER_START, TRAP_START = (-1.9, 2.5), (-2.6, 0.2), (0.6, -2.6)
ETA, BIG_ETA = 0.5, 1.0
HEAVY_ETA, BETA = 0.15, 0.9          # the heavy ball


def h(x, y):
    return BOWL * (x * x + y * y) + sum(a * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / w) for a, cx, cy, w in BUMPS)


def grad(x, y):
    """The two slopes (the gradient): how fast h rises per unit of x, and per unit of y."""
    gx, gy = 2 * BOWL * x, 2 * BOWL * y
    for a, cx, cy, w in BUMPS:
        e = a * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / w)
        gx += e * (-2 * (x - cx) / w)
        gy += e * (-2 * (y - cy) / w)
    return gx, gy


def check_slopes(x, y, d=1e-6):
    """The same two slopes felt the blind way: heights a tiny step apart along each knob."""
    return (h(x + d, y) - h(x - d, y)) / (2 * d), (h(x, y + d) - h(x, y - d)) / (2 * d)


def hessian(x, y, d=1e-5):
    """How fast the slopes themselves change (the curvature), from slopes a tiny step apart."""
    (ax, ay), (bx, by) = grad(x + d, y), grad(x - d, y)
    (cx, cy), (ex, ey) = grad(x, y + d), grad(x, y - d)
    return [[(ax - bx) / (2 * d), (cx - ex) / (2 * d)], [(ay - by) / (2 * d), (cy - ey) / (2 * d)]]


def curvatures(H):
    """The two curvatures of a bottom: the least and the most curved direction (eigenvalues of the 2 x 2 Hessian)."""
    a, b, c, d = H[0][0], H[0][1], H[1][0], H[1][1]
    tr, det = a + d, a * d - b * c
    disc = math.sqrt(max(tr * tr / 4 - det, 0))
    return tr / 2 - disc, tr / 2 + disc


def walk(x, y, eta, tol=1e-3, cap=400, box=3.2):
    path = [(x, y)]
    for _ in range(cap):
        gx, gy = grad(x, y)
        if math.hypot(gx, gy) < tol:
            break
        x, y = x - eta * gx, y - eta * gy
        path.append((x, y))
        if abs(x) > box or abs(y) > box:
            break
    return path


def heavy(x, y, eta, beta, tol=1e-3, cap=5000, box=3.2):
    """Momentum (Polyak's heavy ball): each step keeps beta of the last velocity and adds the new slope."""
    path, vx, vy = [(x, y)], 0.0, 0.0
    for _ in range(cap):
        gx, gy = grad(x, y)
        if math.hypot(gx, gy) < tol and math.hypot(vx, vy) * eta < tol * eta:
            break
        vx, vy = beta * vx + gx, beta * vy + gy
        x, y = x - eta * vx, y - eta * vy
        path.append((x, y))
        if abs(x) > box or abs(y) > box:
            break
    return path


def bottom_from(x, y):
    """Walk with small steps until the ground is flat, then polish with Newton's method; check it is a bottom."""
    x, y = walk(x, y, 0.3, tol=1e-9, cap=20_000)[-1]
    for _ in range(20):
        gx, gy = grad(x, y)
        H = hessian(x, y)
        det = H[0][0] * H[1][1] - H[0][1] * H[1][0]
        x -= (H[1][1] * gx - H[0][1] * gy) / det
        y -= (-H[1][0] * gx + H[0][0] * gy) / det
    lo, hi = curvatures(hessian(x, y))
    if not (math.hypot(*grad(x, y)) < 1e-10 and lo > 0):
        raise SystemExit("not a bottom: the polish failed")
    return x, y, lo, hi


def ascii_map(paths, marks, cols=59, rows=31, span=LAND) -> str:
    """Heights as shades (low ' .:-=+*#%@ high) over the land; walk points and marks on top."""
    ramp = " .:-=+*#%@"
    lo, hi = -1.05, 1.05
    grid = []
    for r in range(rows):
        y = span - 2 * span * r / (rows - 1)
        row = []
        for c in range(cols):
            x = -span + 2 * span * c / (cols - 1)
            v = (h(x, y) - lo) / (hi - lo)
            row.append(ramp[max(0, min(len(ramp) - 1, int(v * len(ramp))))])
        grid.append(row)

    def put(x, y, ch):
        c = round((x + span) / (2 * span) * (cols - 1))
        r = round((span - y) / (2 * span) * (rows - 1))
        if 0 <= r < rows and 0 <= c < cols:
            grid[r][c] = ch

    for path, ch in paths:
        for x, y in path:
            put(x, y, ch)
    for (x, y), ch in marks:
        put(x, y, ch)
    border = "+" + "-" * cols + "+"
    return "\n".join([border] + ["|" + "".join(row) + "|" for row in grid] + [border])


def report_walk(name, path, eta, every=1):
    print(f"\n{name}: eta = {eta}, from ({path[0][0]:g}, {path[0][1]:g})")
    print(f"{'step':>5} {'x':>9} {'y':>9} {'height':>9} {'slope x':>9} {'slope y':>9} {'arrow':>8} {'step len':>9}")
    for k, (x, y) in enumerate(path):
        if k % every and k != len(path) - 1:
            continue
        gx, gy = grad(x, y)
        moved = math.dist(path[k - 1], path[k]) if k else 0.0
        print(f"{k:>5} {x:>9.4f} {y:>9.4f} {h(x, y):>9.4f} {gx:>9.4f} {gy:>9.4f} {math.hypot(gx, gy):>8.4f}"
              f" {moved:>9.4f}")


def ends_at(path, bottoms) -> str:
    x, y = path[-1]
    for name, b in bottoms.items():
        if math.dist((x, y), b[:2]) < 0.01:
            return f"the {name} bottom"
    if max(abs(x), abs(y)) > 3.2:
        return "off the map"
    return "not settled, still moving"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--eta", type=float, help="walk from the video's start (or --start) with this step size")
    ap.add_argument("--start", type=float, nargs=2, metavar=("X", "Y"), help="where your walk starts")
    ap.add_argument("--beta", type=float, help="make your walk a heavy ball with this much memory (0 to 1)")
    ap.add_argument("--rows", type=int, default=31, help="rows of the text maps (default 31, square in a terminal)")
    ap.add_argument("--plot", action="store_true", help="also draw landscape.png with matplotlib")
    a = ap.parse_args()

    bottoms = {"deep": bottom_from(1.2, 0.6), "shallow": bottom_from(-1.4, -1.1), "dip": bottom_from(0.5, -0.9)}
    deep, shallow, dip = bottoms["deep"], bottoms["shallow"], bottoms["dip"]
    print("three bottoms (slope 0, and curving up in every direction), each with the step size it can settle under:")
    for name, (x, y, lo, hi) in bottoms.items():
        print(f"  {name:<8} at ({x:.6f}, {y:.6f})  height {h(x, y):+.6f}  curvatures {lo:.6f} and {hi:.6f}"
              f"  limit 2 / {hi:.4f} = {2 / hi:.4f}")

    gx, gy = grad(*START)
    fx, fy = check_slopes(*START)
    print(f"\nat the start {START}: height {h(*START):.6f}")
    print(f"  slope along the first knob {gx:.6f}, along the second {gy:.6f}"
          f"  (felt from nearby heights: {fx:.6f}, {fy:.6f})")
    print(f"  the gradient is the arrow ({gx:.1f}, {gy:.1f}); its length sqrt(gx^2 + gy^2) = {math.hypot(gx, gy):.6f}:"
          " the steepness uphill")
    print(f"  the walk steps against it: by -eta * ({gx:.3f}, {gy:.3f})")

    if a.eta is not None or a.start or a.beta is not None:
        eta, start = a.eta if a.eta is not None else ETA, tuple(a.start) if a.start else START
        if a.beta is not None:
            path, name, cap = heavy(*start, eta, a.beta), f"your heavy ball (beta = {a.beta})", 5000
        else:
            path, name, cap = walk(*start, eta), "your walk", 400
        report_walk(name, path, eta, every=max(1, len(path) // 40))
        print(f"\n{len(path) - 1} steps (at most {cap}); it ends at height {h(*path[-1]):.4f}: {ends_at(path, bottoms)}")
        print(ascii_map([(path, "o")], [(start, "S"), (deep[:2], "D"), (shallow[:2], "s"), (dip[:2], "d")],
                        rows=a.rows))
        return

    hero = walk(*START, ETA)
    report_walk("the walk into the deep valley", hero, ETA)
    print(f"  -> {len(hero) - 1} steps; it ends {math.dist(hero[-1], deep[:2]):.6f} from the deep bottom. Look at the"
          " step lengths: they shrink on a flat shelf, then grow as it drops")

    other = walk(*OTHER_START, ETA)
    report_walk("the same rule from another start", other, ETA)
    print(f"  -> {len(other) - 1} steps; it ends {math.dist(other[-1], shallow[:2]):.6f} from the shallow bottom,"
          f" height {h(*other[-1]):.4f}: a bottom, not the lowest one")

    trap = walk(*TRAP_START, ETA)
    report_walk("and from a third start", trap, ETA)
    print(f"  -> {len(trap) - 1} steps; it stops {math.dist(trap[-1], dip[:2]):.6f} from the bottom of the small dip,"
          f" height {h(*trap[-1]):.4f}")

    ball = heavy(*TRAP_START, HEAVY_ETA, BETA)
    in_at = next(k for k, p in enumerate(ball) if math.dist(p, deep[:2]) < 0.05)
    past = next(k for k, p in enumerate(ball) if p[1] > dip[1] + 0.3)
    report_walk(f"a heavy ball from the same third start (beta = {BETA})", ball, HEAVY_ETA, every=4)
    print(f"  -> past the dip by step {past}, first in the deep valley (within 0.05 of its bottom) at step {in_at},"
          f" then it swings and settles: {len(ball) - 1} steps, {math.dist(ball[-1], deep[:2]):.6f} from the bottom")

    limit = 2 / deep[3]
    print(f"\nthe step-size limit of the deep valley: 2 / (its steepest curvature {deep[3]:.6f}) = {limit:.4f}")
    big = walk(*START, BIG_ETA, cap=30)
    fell = next(k for k, p in enumerate(big) if h(*p) < -0.8)
    report_walk("a step past the limit", big, BIG_ETA)
    long = walk(*START, BIG_ETA, cap=2000)
    settled = len(long) <= 2000
    print(f"  -> it falls in at step {fell} (height below -0.8), then bounces from wall to wall; "
          f"{'settled' if settled else 'still not settled'} after {len(long) - 1} steps")

    print("\nthe land seen from above (x across, y up, both from -2.9 to 2.9): ' ' is low, '@' is high;")
    print("S the starts; 'o' the walk into the deep valley (D its bottom), 'x' the walk into the shallow one (s),")
    print("'v' the walk that stops in the small dip (d)")
    print(ascii_map([(hero, "o"), (other, "x"), (trap, "v")],
                    [(START, "S"), (OTHER_START, "S"), (TRAP_START, "S"), (deep[:2], "D"), (shallow[:2], "s"),
                     (dip[:2], "d")], rows=a.rows))
    print(f"\nfrom the third start: 'v' the plain walk (eta = {ETA}), 'o' the heavy ball (eta = {HEAVY_ETA},"
          f" beta = {BETA})")
    print(ascii_map([(ball, "o"), (trap, "v")], [(TRAP_START, "S"), (deep[:2], "D"), (dip[:2], "d")], rows=a.rows))
    print(f"\nthe walk with eta = {BIG_ETA} ('o'): it reaches the deep valley and keeps jumping across it")
    print(ascii_map([(big, "o")], [(START, "S"), (deep[:2], "D")], rows=a.rows))

    if a.plot:
        plot(hero, other, trap, ball, big, bottoms)


def plot(hero, other, trap, ball, big, bottoms) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit("--plot needs matplotlib (pip install matplotlib); everything else runs without it")
    n = 121
    xs = [-LAND + 2 * LAND * i / (n - 1) for i in range(n)]
    Z = [[h(x, y) for x in xs] for y in xs]
    fig, ax = plt.subplots(figsize=(6.4, 6))
    cs = ax.contourf(xs, xs, Z, levels=24, cmap="Blues_r")
    ax.contour(xs, xs, Z, levels=24, colors="k", linewidths=0.3, alpha=0.4)
    fig.colorbar(cs, ax=ax, label="height")
    for path, c, lab in ((big, "#B42A30", f"eta = {BIG_ETA}"),          # the long walks first, so the others show
                         (ball, "#1E7346", f"heavy ball, eta = {HEAVY_ETA}, beta = {BETA}"),
                         (hero, "#B57600", f"eta = {ETA}"), (other, "#7C3AED", f"eta = {ETA}, another start"),
                         (trap, "#5C636E", f"eta = {ETA}, a third start")):
        ax.plot([p[0] for p in path], [p[1] for p in path], "o-", ms=2.5, lw=1, color=c, label=lab)
    for x, y, _, _ in bottoms.values():
        ax.plot(x, y, "o", mfc="none", mec="#1E7346", ms=12, mew=2)
    ax.set_xlabel("first knob, x")
    ax.set_ylabel("second knob, y")
    ax.set_aspect("equal")
    ax.legend(loc="lower left", fontsize=7)
    fig.tight_layout()
    fig.savefig("landscape.png", dpi=150)
    print("wrote landscape.png")


if __name__ == "__main__":
    main()
