"""Follow SELECT * FROM users WHERE email = 'kiwi@mail.test' page by page, as SQLite does: down the index's
B-tree from its root to the leaf that holds (kiwi@mail.test, id), then with that id down the table's own B-tree
to the row. Every page is read from the database file and decoded here; the plans are SQLite's.

    python3 walk.py --quick                          # 100,000 rows: about a second
    python3 walk.py                                  # the notes' 1,000,000-row table: ~4 s, 62 MB, temporary
    python3 walk.py --email nobody@mail.test         # a missing key: the leaf proves it isn't there
    python3 walk.py --db users.db                    # keep the database file

Standard library only. Decodes pages per https://www.sqlite.org/fileformat2.html (section 1.6).
"""

from __future__ import annotations

from usersdb import LINE, TARGET, Pages, args, built, descend, plan, roots, scratch


def show_index_step(n: int, step: dict, email: str) -> None:
    role = " (root)" if n == 1 else (" (signpost)" if step["interior"] else "")
    unit = ("key" if step["interior"] else "entry") + ("s" if step["ncell"] != 1 else "")
    unit = unit.replace("entrys", "entries")
    print(f"  read {n}: page {step['pgno']:>6,}  {step['kind']}{role}, {step['ncell']} {unit}", end="")
    if step["interior"] and step.get("pos") is None:
        lo = step["lo"][0] if step["lo"] else "(start)"
        hi = step["hi"][0] if step["hi"] else "(end)"
        child = step["cells"][step["branch"]][0] if step["hi"] else step["right"]
        print(f" → {step['ncell'] + 1} children")
        print(f"          {email} sorts between {lo} and {hi}:"
              f" child {step['branch'] + 1} of {step['ncell'] + 1} → page {child:,}")
        return
    print()
    pos = step["pos"]
    if pos is None:
        print(f"          {email} would sit here, and it isn't: it's in no row of the table")
        return
    if step["interior"]:
        print(f"          {email} is a key on this signpost page itself (index B-trees keep entries above the leaves)")
    cells = [c[1] for c in step["cells"]]
    for k in range(max(0, pos - 2), min(len(cells), pos + 3)):
        mark = "→" if k == pos else " "
        print(f"        {mark} entry {k + 1:>3}  {cells[k][0]:<24} id {cells[k][1]:>9,}")


def main() -> None:
    a = args(__doc__, lambda ap: ap.add_argument("--email", default=TARGET, help="the email to look up"))
    with scratch(a.db) as path:
        con, _ = built(a, path, ("email",))
        pg = Pages(path)
        r = roots(con)
        print(f"{LINE}   with ? = {a.email!r}")
        print(f"  EXPLAIN QUERY PLAN → {plan(con, LINE, (a.email,))}\n")

        print("1) the index idx_users_email: (email, id) pairs in email order")
        ipath = descend(pg, r["idx_users_email"], a.email)
        for n, step in enumerate(ipath, 1):
            show_index_step(n, step, a.email)
        last = ipath[-1]
        if last.get("pos") is None:
            print(f"\n{len(ipath)} pages read to prove there is no such row (SELECT * finds nothing)")
            return
        rowid = last["cells"][last["pos"]][1][-1]

        print(f"\n2) the table users, in id order: SELECT * wants the whole row, so take id {rowid:,} down its tree")
        tpath = descend(pg, r["users"], rowid)
        for n, step in enumerate(tpath, len(ipath) + 1):
            role = " (root)" if n == len(ipath) + 1 else (" (signpost)" if step["interior"] else "")
            unit = ("key" if step["interior"] else "row") + ("s" if step["ncell"] != 1 else "")
            print(f"  read {n}: page {step['pgno']:>6,}  {step['kind']}{role}, {step['ncell']} {unit}", end="")
            if step["interior"]:
                lo = step["lo"][0] + 1 if step["lo"] else 1
                hi = f"{step['hi'][0]:,}" if step["hi"] else "the end"
                child = step["cells"][step["branch"]][0] if step["hi"] else step["right"]
                print(f" → child {step['branch'] + 1} of {step['ncell'] + 1}: ids {lo:,} … {hi} → page {child:,}")
            else:
                ids = [c[0] for c in step["cells"]]
                print(f", ids {ids[0]:,} … {ids[-1]:,}")
                print(f"        → row {step['pos'] + 1} of {step['ncell']}: {step['cells'][step['pos']][1]}")

        pages = [s["pgno"] for s in ipath + tpath]
        print(f"\n{len(pages)} pages in all: {', '.join(f'{p:,}' for p in pages)}")
        q = "SELECT id FROM users WHERE email = ?"
        print(f"\n{q}\n  EXPLAIN QUERY PLAN → {plan(con, q, (a.email,))}")
        print(f"  the id is already in the index entry: the first {len(ipath)} pages answer it, the table isn't read")
        con.close()


if __name__ == "__main__":
    main()
