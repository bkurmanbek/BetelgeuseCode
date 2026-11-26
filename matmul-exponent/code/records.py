"""The record staircase: every published upper bound on the matrix multiplication exponent omega, from Strassen's
2.8074 in 1969 to 2.371177 in August 2026, drawn as text on the line from 2 to 3, with the gaps between records,
then OpenAI's 2026 steps down to 9/4.

    python3 records.py          # the staircase as text: instantly (also --quick, the same)
    python3 records.py --plot   # also records.png, if matplotlib is installed

An upper bound "omega <= x" means: someone found a method whose cost grows no faster than n^x (up to a constant,
and for every x a little above the record). Sources: the history table of Wikipedia's "Computational complexity of
matrix multiplication" (read 2026-11-25) and arXiv:2608.16884 for August 2026; OpenAI's steps as cited in its
November 24, 2026 paper. The 9/4 lower bound is a claim as of November 25, 2026, not a settled fact.
Standard library only (matplotlib optional).
"""

from __future__ import annotations

import argparse

RECORDS = [  # (year, omega below, who)
    (1969, 2.8074, "Strassen"),
    (1978, 2.796, "Pan"),
    (1979, 2.78, "Bini, Capovani, Romani"),
    (1981, 2.522, "Schönhage"),
    (1981, 2.517, "Romani"),
    (1981, 2.496, "Coppersmith, Winograd"),
    (1986, 2.479, "Strassen"),
    (1990, 2.3755, "Coppersmith, Winograd"),
    (2010, 2.3737, "Stothers"),
    (2012, 2.3729, "Williams"),
    (2014, 2.3728639, "Le Gall"),
    (2020, 2.3728596, "Alman, Williams"),
    (2022, 2.371866, "Duan, Wu, Zhou"),
    (2024, 2.371552, "Williams, Xu, Xu, Zhou"),
    (2024, 2.371339, "Alman, Duan, Williams, Xu, Xu, Zhou"),
    (2026, 2.371177, "Dupont et al. (AlphaEvolve)"),
]
OPENAI_2026 = [  # (date, bound, over, title)
    ("2026-09-24", 2.371055, "every field", "Staggered extraction for exact matrix multiplication over every field"),
    ("2026-09-24", 2.258, "the complex numbers", "Complex Matrix Multiplication Below 2.258 and Rectangular Bounds"),
    ("2026-10-02", 2.25, "the complex numbers", "An Upper Bound of 9/4 for the Matrix Multiplication Exponent"),
    ("2026-11-24", 2.25, "every field", "The matrix multiplication exponent is nine fourths (claims the matching "
                                        "lower bound)"),
]


def bar(x: float, width: int = 50) -> str:
    """Where x sits on the line from 2 (left) to 3 (right)."""
    pos = round((x - 2) * width)
    return "2 |" + "-" * pos + "*" + " " * (width - pos) + "| 3"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--quick", action="store_true", help="the same: there is nothing slow here")
    ap.add_argument("--plot", action="store_true", help="also draw records.png with matplotlib")
    a = ap.parse_args()

    print(f"{'year':<5} {'omega <':<10} {'gap':>9}  {'on the line from 2 to 3':<56} who")
    prev = None
    for year, w, who in RECORDS:
        gap = f"{prev - w:.6f}" if prev else ""
        print(f"{year:<5} {w:<10} {gap:>9}  {bar(w):<56} {who}")
        prev = w
    first, cw, last = RECORDS[0], RECORDS[7], RECORDS[-1]
    print(f"\n{len(RECORDS)} records; {2026 - first[0]} years since Strassen.")
    print(f"from {cw[1]} ({cw[0]}) to {last[1]} ({last[0]}): down {cw[1] - last[1]:.6f} in {last[0] - cw[0]} years.")
    print(f"from {last[1]} to 9/4: another {last[1] - 2.25:.6f}, in OpenAI's 2026 papers (the upper bound since"
          " re-proved by others; the matching lower bound a claim):")
    for date, w, over, title in OPENAI_2026:
        print(f"  {date}  {w:<9} over {over:<20} {title}")
    print("the floor: omega >= 2, because the answer alone has n^2 numbers.")

    if a.plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            raise SystemExit("--plot needs matplotlib (pip install matplotlib); the numbers above are the plot")
        years = [y for y, _, _ in RECORDS] + [2026.9]
        bounds = [w for _, w, _ in RECORDS] + [2.25]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.step(years, bounds, where="post", color="#B42A30", lw=2, label="best known upper bound")
        ax.plot(years, bounds, "o", color="#B42A30", ms=4)
        ax.axhline(2.25, color="#1E7346", ls="--", lw=1.2, label="9/4: claimed exact (Nov 24, 2026)")
        ax.axhline(2, color="#5C636E", ls=":", lw=1.2, label="2: the floor (the answer has n^2 numbers)")
        ax.set_xlabel("year")
        ax.set_ylabel("omega: the power of n")
        ax.set_ylim(1.95, 3.0)
        ax.legend(frameon=False, loc="upper right")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        fig.tight_layout()
        fig.savefig("records.png", dpi=150)
        print("wrote records.png")


if __name__ == "__main__":
    main()
