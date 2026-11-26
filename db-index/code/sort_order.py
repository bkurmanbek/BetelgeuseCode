"""An index answers only the questions that follow its sort order. Shows it from both sides: SQLite's plan for each
WHERE, and where the matching entries actually sit among the index's leaf pages. A leading wildcard
('%@yahoo.com'), a prefix ('maria.lo%') and why LIKE can use this index at all, a function around the column, and a
two-column index used left to right.

    python3 sort_order.py --quick      # 100,000 rows: about two seconds
    python3 sort_order.py              # the notes' 1,000,000-row table: ~18 s, 90 MB in a temporary folder

Standard library only. Plans from EXPLAIN QUERY PLAN (https://www.sqlite.org/eqp.html); leaf pages decoded per
https://www.sqlite.org/fileformat2.html.
"""

from __future__ import annotations

import sqlite3

from usersdb import INDEXES, SCHEMA, TARGET, Pages, args, built, nocase, plan, roots, scratch

WILD, PREFIX = "%@yahoo.com", "maria.lo%"


def where_matches(pg: Pages, root: int, test) -> dict:
    """Walk an index's leaves in order; which leaves hold entries that pass `test`, and how many entries.
    Entries on signpost (interior) pages are counted apart: an index B-tree keeps entries there too."""
    leaves, on_leaves, n = [], 0, 0
    for n, leaf in enumerate(pg.leaves(root), 1):
        hits = sum(1 for _, entry in leaf["cells"] if test(entry))
        if hits:
            leaves.append((n, leaf["pgno"]))
            on_leaves += hits
    interior = [(p, entry) for level in pg.levels(root)[:-1] for p in level
                for _, entry in pg.page(p)["cells"] if test(entry)]
    return {"leaves": leaves, "of": n, "on_leaves": on_leaves, "interior": interior}


def runs(ordinals: list[int]) -> list[tuple[int, int]]:
    """Consecutive leaf numbers grouped: [3, 4, 5, 9] → [(3, 5), (9, 9)]."""
    out: list[tuple[int, int]] = []
    for o in ordinals:
        if out and o == out[-1][1] + 1:
            out[-1] = (out[-1][0], o)
        else:
            out.append((o, o))
    return out


def show(con, sql: str, args_: tuple = ()) -> None:
    shown = sql
    for v in args_:
        shown = shown.replace("?", repr(v), 1)
    print(f"  {shown:<66} → {plan(con, sql, args_)}")


def main() -> None:
    a = args(__doc__)
    with scratch(a.db) as path:
        con, _ = built(a, path, ("email", "city_age"))
        pg = Pages(path)
        r = roots(con)
        email_root, combo_root = r["idx_users_email"], r["idx_users_city_age"]
        q = "SELECT * FROM users WHERE email LIKE ?"

        print(f"1) a leading wildcard: the emails that END in {WILD[1:]}")
        show(con, q, (WILD,))
        suffix = WILD[1:]
        m = where_matches(pg, email_root, lambda e: nocase(e[0]).endswith(suffix))
        count = con.execute("SELECT count(*) FROM users WHERE email LIKE ?", (WILD,)).fetchone()[0]
        first, last = (con.execute(f"SELECT email FROM users WHERE email LIKE ? ORDER BY email {d} LIMIT 1",
                                   (WILD,)).fetchone()[0] for d in ("ASC", "DESC"))
        letters = {row[0][0] for row in con.execute("SELECT email FROM users WHERE email LIKE ?", (WILD,))}
        print(f"  {count:,} matches, from {first} to {last}: they start with {len(letters)} different letters,")
        print(f"  so they sit on {len(m['leaves']):,} of the index's {m['of']:,} leaf pages "
              f"({len(m['leaves']) / m['of']:.0%}) ({m['on_leaves']:,} on leaves, {len(m['interior']):,} on signpost pages)")
        print("  the sort order can't narrow that down, so SQLite reads the table instead\n")

        print(f"2) a prefix: the emails that START with {PREFIX[:-1]} are neighbours in email order")
        show(con, q, (PREFIX,))
        start = PREFIX[:-1]
        m = where_matches(pg, email_root, lambda e: nocase(e[0]).startswith(start))
        count = con.execute("SELECT count(*) FROM users WHERE email LIKE ?", (PREFIX,)).fetchone()[0]
        nums = " and ".join(f"{o:,}" for o, _ in m["leaves"])
        pages = " and ".join(f"{p:,}" for _, p in m["leaves"])
        many = "s" if len(m["leaves"]) > 1 else ""
        print(f"  {count:,} matches: {m['on_leaves']:,} on leaf{many} {nums} of {m['of']:,} (page{many} {pages})")
        for p, entry in m["interior"]:
            print(f"  and {entry[0]} on signpost page {p:,}, a key that separates two leaves")
        for (email,) in con.execute("SELECT email FROM users WHERE email LIKE ? ORDER BY email LIMIT 4", (PREFIX,)):
            print(f"    {email}")
        print("    …")
        print("  the range in the plan, (email>? AND email<?), is 'maria.lo' ≤ email < 'maria.lp'\n")

        print("3) why LIKE can use this index at all: LIKE ignores upper and lower case (for A-Z),")
        print("   and so does this index, because the column was declared email TEXT COLLATE NOCASE")
        show(con, q, ("Maria.Lo%",))
        print(f"  the same table with a plain email TEXT column (an empty copy in memory: a plan doesn't need rows):")
        plain = sqlite3.connect(":memory:")
        plain.execute(SCHEMA.replace(" COLLATE NOCASE", ""))
        plain.execute(INDEXES["email"])
        show(plain, q, (PREFIX,))
        show(plain, "SELECT * FROM users WHERE email >= ? AND email < ?", ("maria.lo", "maria.lp"))
        print("  sorted by exact bytes, 'M' and 'm' are far apart, so LIKE can't be one range there; the range")
        print("  written out compares bytes too, so it can\n")

        print("4) the index holds email, sorted ignoring case; it doesn't hold lower(email)")
        show(con, "SELECT * FROM users WHERE email = ?", (TARGET.title(),))
        print(f"    → {con.execute('SELECT * FROM users WHERE email = ?', (TARGET.title(),)).fetchone()}")
        show(con, "SELECT * FROM users WHERE lower(email) = ?", (TARGET,))
        con.execute("CREATE INDEX idx_users_lower_email ON users(lower(email))")
        show(con, "SELECT * FROM users WHERE lower(email) = ?", (TARGET,))
        print("  (the last one after CREATE INDEX idx_users_lower_email ON users(lower(email)): an index on the"
              " expression, a third tree)\n")
        con.execute("DROP INDEX idx_users_lower_email")

        print(f"5) a two-column index, {INDEXES['city_age'].split(' ON ')[1]}: sorted by city, then by age inside each city")
        first_leaf = next(pg.leaves(combo_root))
        for _, (city, age, rowid) in first_leaf["cells"][:3]:
            print(f"    ({city}, {age}, id {rowid:,})")
        print("    …")
        city, age = con.execute("SELECT city, age FROM users WHERE email = ?", (TARGET,)).fetchone()
        show(con, "SELECT * FROM users WHERE city = ?", (city,))
        show(con, "SELECT * FROM users WHERE city = ? AND age = ?", (city, age))
        show(con, "SELECT * FROM users WHERE age = ? AND city = ?", (age, city))
        show(con, "SELECT * FROM users WHERE city = ? AND age > ?", (city, age))
        show(con, "SELECT * FROM users WHERE city = ? ORDER BY age", (city,))
        show(con, "SELECT * FROM users WHERE age = ?", (age,))
        m = where_matches(pg, combo_root, lambda e: e[1] == age)
        groups = runs([o for o, _ in m["leaves"]])
        cities = [c for (c,) in con.execute("SELECT DISTINCT city FROM users ORDER BY city")]
        print(f"  age = {age} alone: the entries sit in {len(groups)} separate stretches of the index, one per city"
              f" ({', '.join(cities)}):")
        print(f"  leaves {', '.join(f'{lo:,}-{hi:,}' for lo, hi in groups)} of {m['of']:,}; no single range covers them")
        con.close()


if __name__ == "__main__":
    main()
