"""An index answers only the questions that follow its sort order. Shows it from both sides: SQLite's plan for each
WHERE, and where the matching entries actually sit among the index's leaf pages. A leading wildcard, a prefix
(and why LIKE 'kiw%' still scans), a function around the column, and a two-column index used left to right.

    python3 sort_order.py --quick      # 100,000 rows: a second or two
    python3 sort_order.py              # the notes' 1,000,000-row table: ~15 s, 78 MB in a temporary folder

Standard library only. Plans from EXPLAIN QUERY PLAN (https://www.sqlite.org/eqp.html); leaf pages decoded per
https://www.sqlite.org/fileformat2.html.
"""

from __future__ import annotations

from usersdb import INDEXES, Pages, args, built, plan, roots, scratch


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
    print(f"  {shown:<62} → {plan(con, sql, args_)}")


def main() -> None:
    a = args(__doc__)
    with scratch(a.db) as path:
        con, _ = built(a, path, ("email", "city_age"))
        pg = Pages(path)
        r = roots(con)
        email_root, combo_root = r["idx_users_email"], r["idx_users_city_age"]

        print("1) a leading wildcard: the emails that END in @post.test")
        q = "SELECT * FROM users WHERE email LIKE ?"
        show(con, q, ("%@post.test",))
        m = where_matches(pg, email_root, lambda e: e[0].endswith("@post.test"))
        count = con.execute("SELECT count(*) FROM users WHERE email LIKE ?", ("%@post.test",)).fetchone()[0]
        print(f"  {count:,} matches, on {len(m['leaves']):,} of {m['of']:,} leaf pages "
              f"({len(m['leaves']) / m['of']:.0%}): they start with every letter, so they are everywhere")
        print(f"  ({m['on_leaves']:,} on leaves, {len(m['interior']):,} on signpost pages)\n")

        print("2) a prefix: the emails that START with kiw are neighbours in email order")
        show(con, "SELECT * FROM users WHERE email GLOB ?", ("kiw*",))
        m = where_matches(pg, email_root, lambda e: e[0].startswith("kiw"))
        count = con.execute("SELECT count(*) FROM users WHERE email GLOB 'kiw*'").fetchone()[0]
        nums = " and ".join(f"{o:,}" for o, _ in m["leaves"])
        pages = " and ".join(f"{p:,}" for _, p in m["leaves"])
        many = "s" if len(m["leaves"]) > 1 else ""
        print(f"  {count:,} matches: {m['on_leaves']:,} on leaf{many} {nums} of {m['of']:,} (page{many} {pages})")
        for p, entry in m["interior"]:
            print(f"  and {entry[0]} on signpost page {p:,}, the key that separates those leaves")
        print()

        print("3) the same prefix with LIKE scans: LIKE ignores case, the index is sorted by exact bytes")
        show(con, "SELECT * FROM users WHERE email LIKE ?", ("kiw%",))
        print("  three ways to make it a range the index can answer:")
        show(con, "SELECT * FROM users WHERE email GLOB ?", ("kiw*",))
        show(con, "SELECT * FROM users WHERE email >= ? AND email < ?", ("kiw", "kix"))
        con.execute("CREATE INDEX idx_users_email_nocase ON users(email COLLATE NOCASE)")
        show(con, "SELECT * FROM users WHERE email LIKE ?", ("kiw%",))
        print("  (the last one after CREATE INDEX idx_users_email_nocase ON users(email COLLATE NOCASE):"
              " a third tree, sorted the way LIKE compares)\n")

        print("4) a function around the column: the index holds email, not lower(email)")
        show(con, "SELECT * FROM users WHERE lower(email) = ?", ("kiwi@mail.test",))
        con.execute("CREATE INDEX idx_users_lower_email ON users(lower(email))")
        show(con, "SELECT * FROM users WHERE lower(email) = ?", ("kiwi@mail.test",))
        print("  (after CREATE INDEX idx_users_lower_email ON users(lower(email)): an index on the expression)\n")

        print(f"5) a two-column index, {INDEXES['city_age'].split(' ON ')[1]}: sorted by city, then by age inside each city")
        first = next(pg.leaves(combo_root))
        for _, (city, age, rowid) in first["cells"][:3]:
            print(f"    ({city}, {age}, id {rowid:,})")
        print("    …")
        city, age = con.execute("SELECT city, age FROM users WHERE email = 'kiwi@mail.test'").fetchone()
        show(con, "SELECT * FROM users WHERE city = ?", (city,))
        show(con, "SELECT * FROM users WHERE city = ? AND age = ?", (city, age))
        show(con, "SELECT * FROM users WHERE age = ? AND city = ?", (age, city))
        show(con, "SELECT * FROM users WHERE city = ? AND age > ?", (city, age))
        show(con, "SELECT * FROM users WHERE city = ? ORDER BY age", (city,))
        show(con, "SELECT * FROM users WHERE age = ?", (age,))
        m = where_matches(pg, combo_root, lambda e: e[1] == age)
        groups = runs([o for o, _ in m["leaves"]])
        print(f"  age = {age} alone: the entries sit in {len(groups)} separate stretches of the index, one per city"
              f" (leaves {', '.join(f'{lo:,}-{hi:,}' for lo, hi in groups)} of {m['of']:,})")
        con.close()


if __name__ == "__main__":
    main()
