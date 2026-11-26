"""Numbers that count their own multiplications, and the two ways to multiply n x n tables the other scripts
share: the school way (three loops) and Strassen's recipe applied to blocks inside blocks.

    python3 tally.py            # the cafe tables both ways, each multiplication listed as it happens: instantly

How the papers count, and how we count: multiplying two values that both depend on the input tables costs one.
Adding, subtracting, and multiplying or dividing by a fixed number cost nothing (the nine-fourths paper: "even if
linear operations are free"). So every count here is exact and the same on every machine. Nothing is timed.

A Tracked number carries its value and a shared Tally. Python calls __mul__ for every `*` it evaluates, so the
count comes from the arithmetic itself, not from a `count += 1` somebody remembered to write. Run any recipe on
Tracked numbers and read tally.n afterwards. Standard library only.
"""

from __future__ import annotations

from fractions import Fraction


class Tally:
    """How many multiplications of two input-dependent values have happened (the papers' "nonscalar" products).
    `log`, if a list, gets one line per multiplication."""

    def __init__(self, log: list | None = None) -> None:
        self.n = 0
        self.log = log


def _v(x):
    return x.v if isinstance(x, Tracked) else x


class Tracked:
    """A number that depends on the inputs. Arithmetic works as usual; only input x input products are counted."""

    __slots__ = ("v", "t")

    def __init__(self, v, t: Tally) -> None:
        self.v, self.t = v, t

    def __add__(self, o):                      # free
        return Tracked(self.v + _v(o), self.t)

    __radd__ = __add__

    def __sub__(self, o):                      # free
        return Tracked(self.v - _v(o), self.t)

    def __rsub__(self, o):
        return Tracked(o - self.v, self.t)

    def __neg__(self):
        return Tracked(-self.v, self.t)

    def __mul__(self, o):
        if isinstance(o, Tracked):             # both depend on the inputs: this is the one that costs
            self.t.n += 1
            if self.t.log is not None:
                self.t.log.append(f"#{self.t.n}: {self.v} * {o.v} = {self.v * o.v}")
            return Tracked(self.v * o.v, self.t)
        return Tracked(self.v * o, self.t)     # times a fixed number: free

    __rmul__ = __mul__                         # 3 * x: a plain number on the left is always a fixed number

    def __truediv__(self, o):
        if isinstance(o, Tracked):             # the paper's circuits may divide; dividing by an input counts too
            self.t.n += 1
            return Tracked(Fraction(self.v) / o.v, self.t)
        return Tracked(Fraction(self.v) / o, self.t)   # by a fixed number: free, and exact

    def __eq__(self, o):
        return self.v == _v(o)

    __hash__ = None

    def __repr__(self) -> str:
        return repr(self.v)


def track(M, tally: Tally):
    """A table of plain numbers -> the same table of Tracked numbers sharing one tally."""
    return [[Tracked(x, tally) for x in row] for row in M]


def plain(M):
    """A table of Tracked (or plain) numbers -> plain numbers, for printing and comparing."""
    return [[_v(x) for x in row] for row in M]


# ---------------------------------------------------------------- the school way

def school(A, B):
    """Three loops: answer[i][j] is row i of A against column j of B. n x n tables: n * n * n multiplications."""
    n, m, p = len(A), len(B), len(B[0])
    return [[sum(A[i][k] * B[k][j] for k in range(m)) for j in range(p)] for i in range(n)]


# ---------------------------------------------------------------- Strassen on blocks

def add(X, Y, s: int = 1):
    """X + Y (s = 1) or X - Y (s = -1), entry by entry: no multiplications that count."""
    return [[x + y if s == 1 else x - y for x, y in zip(r, q)] for r, q in zip(X, Y)]


def split(X):
    """Cut an even-sized table into its four quarter blocks: [[X11, X12], [X21, X22]]."""
    h = len(X) // 2
    return [[[r[:h] for r in X[:h]], [r[h:] for r in X[:h]]],
            [[r[:h] for r in X[h:]], [r[h:] for r in X[h:]]]]


def strassen(A, B, calls: dict | None = None):
    """Strassen's seven products with blocks in place of numbers, down to 1 x 1 blocks (plain numbers). For
    n = 2^k that is 7^k multiplications of numbers. `calls`, a dict, counts the block products of each size."""
    n = len(A)
    if calls is not None:
        calls[n] = calls.get(n, 0) + 1
    if n == 1:
        return [[A[0][0] * B[0][0]]]
    (a11, a12), (a21, a22) = split(A)
    (b11, b12), (b21, b22) = split(B)
    m1 = strassen(add(a11, a22), add(b11, b22), calls)
    m2 = strassen(add(a21, a22), b11, calls)
    m3 = strassen(a11, add(b12, b22, -1), calls)
    m4 = strassen(a22, add(b21, b11, -1), calls)
    m5 = strassen(add(a11, a12), b22, calls)
    m6 = strassen(add(a21, a11, -1), add(b11, b12), calls)
    m7 = strassen(add(a12, a22, -1), add(b21, b22), calls)
    c11 = add(add(m1, m4), add(m7, m5, -1))
    c12 = add(m3, m5)
    c21 = add(m2, m4)
    c22 = add(add(m1, m2, -1), add(m3, m6))
    return [r1 + r2 for r1, r2 in zip(c11, c12)] + [r1 + r2 for r1, r2 in zip(c21, c22)]


# ---------------------------------------------------------------- the cafe

ORDERS = [[2, 1], [1, 3]]     # Emma, Liam  x  coffee, tea
PRICES = [[5, 3], [4, 2]]     # coffee, tea x  Austin, Lima (dollars)


def main() -> None:
    for name, recipe in (("the school way", school), ("Strassen's way", strassen)):
        log: list[str] = []
        t = Tally(log)
        answer = plain(recipe(track(ORDERS, t), track(PRICES, t)))
        print(f"{name}: {answer}, {t.n} multiplications")
        for line in log:
            print("   ", line)


if __name__ == "__main__":
    main()
