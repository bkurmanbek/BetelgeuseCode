"""With no index, SQLite has to read every page of the table: the plan says SCAN, and walking the leaf pages in
id order, as the scan does, shows where maria.lopez@gmail.com sits and why reading can't stop there.

    python3 scan.py --quick                         # 100,000 rows: about a second
    python3 scan.py                                 # the notes' 1,000,000-row table: ~9 s, 41 MB, temporary
    python3 scan.py --email arjun.gupta352@gmail.com     # the newest user, id 1,000,000: met on the very last leaf

The walk below is our own (it reads the file page by page); the plan is SQLite's. Standard library only.
"""

from __future__ import annotations

from usersdb import LINE, TARGET, Pages, args, built, nocase, plan, roots, scratch


def main() -> None:
    a = args(__doc__, lambda ap: ap.add_argument("--email", default=TARGET, help="the email to look for"))
    with scratch(a.db) as path:
        con, _ = built(a, path)
        print(f"{LINE}\n  EXPLAIN QUERY PLAN → {plan(con, LINE, (a.email,))}\n")

        pg = Pages(path)
        root = roots(con)["users"]
        shape = pg.shape(root)
        n_leaves, found = shape["leaf_pages"], []
        want = nocase(a.email)                                       # the column is COLLATE NOCASE
        for ordinal, leaf in enumerate(pg.leaves(root), 1):          # left to right = id order
            for rowid, row in leaf["cells"]:
                if nocase(row[1]) == want:
                    found.append((ordinal, leaf["pgno"], row))
            if ordinal in (1, 2, 3) or ordinal == n_leaves:
                ids = [r for r, _ in leaf["cells"]]
                print(f"  leaf {ordinal:>6,} of {n_leaves:,}: page {leaf['pgno']:>6,}, ids {ids[0]:>9,} … {ids[-1]:<9,}"
                      f"  {'match!' if any(f[0] == ordinal for f in found) else ''}")
            elif ordinal == 4:
                print(f"  {'…':>13}")
            elif found and found[-1][0] == ordinal:
                print(f"  leaf {ordinal:>6,} of {n_leaves:,}: page {leaf['pgno']:>6,}  {a.email} → {found[-1][2]}")

        print()
        for ordinal, pgno, row in found:
            print(f"found on leaf {ordinal:,} of {n_leaves:,} (page {pgno:,}), {ordinal / n_leaves:.0%} of the way in")
        if not found:
            print(f"{a.email} is on no page: every leaf had to be read to know that")
        unique = con.execute("SELECT count(*) FROM pragma_index_list('users') WHERE \"unique\"").fetchone()[0]
        print(f"email is not declared UNIQUE ({unique} unique indexes), so another row could match on any later page:")
        print(f"the scan reads all {n_leaves:,} leaves, and the {shape['interior_pages']:,} signpost pages that lead"
              f" to them: {shape['pages']:,} pages")
        con.close()


if __name__ == "__main__":
    main()
