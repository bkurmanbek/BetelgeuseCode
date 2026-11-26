"""Every write updates every index. Inserts one new user, Daniel Kim from Seoul, three times (with no index, then
after CREATE INDEX on email, then after a second index on (city, age)), compares the database file before and
after, page by page, and names the B-tree each changed page belongs to, with its cells and free bytes before →
after. The row is deleted after each look, so the three writes are the same.

    python3 writes.py --quick          # 100,000 rows: about a second
    python3 writes.py                  # the notes' 1,000,000-row table: ~6 s, 90 MB in a temporary folder

Standard library only. Page headers decoded per https://www.sqlite.org/fileformat2.html (sections 1.3 and 1.6).
"""

from __future__ import annotations

import textwrap

from usersdb import INDEXES, PROBE, args, built, scratch

STAGES = [("none", "no index"), ("email", "after " + INDEXES["email"]),
          ("city_age", "after " + INDEXES["city_age"])]


def show(w: dict) -> None:
    trees = sorted({o for o in w["owner"].values() if o not in ("file header", "free")})
    print(f"  {len(w['pages'])} pages changed, in {len(trees)} B-tree{'s' * (len(trees) != 1)}: {', '.join(trees)}")
    for p in w["pages"]:
        owner = w["owner"][p]
        old, new = w["cells"][p]
        if p == 1:
            a, b = w["counter"]
            print(f"    page {p:>6,}  {owner:<19} bytes 24-27, the file change counter: {a} → {b}")
            continue
        unit = "keys" if "interior" in new[0] else ("entries" if "index" in new[0] else "rows")
        if old is None:
            print(f"    page {p:>6,}  {owner:<19} NEW {new[0]}: {new[1]} {unit}, {new[2]:,} bytes free"
                  f"  (the file grew {w['file_pages'][0]:,} → {w['file_pages'][1]:,} pages)")
        else:
            print(f"    page {p:>6,}  {owner:<19} {new[0]:<15} {old[1]:>4} → {new[1]:<4} {unit:<8}"
                  f" free bytes {old[2]:>5,} → {new[2]:,}")


def main() -> None:
    a = args(__doc__)
    with scratch(a.db) as path:
        con, writes = built(a, path, ("email", "city_age"))
        print(f"INSERT INTO users (email, city, age) VALUES {PROBE!r}   (then DELETE it again)\n")
        for key, title in STAGES:
            print(f"{title}:")
            show(writes[key])
            print()
        email = writes["email"]
        split = [p for p in email["pages"] if email["cells"][p][0] is None]
        if split:
            n = email["by"].get("idx_users_email", 0)
            print(textwrap.fill(f"The first write after CREATE INDEX changed {n} pages of the email index, {len(split)} of them new:"
                  " CREATE INDEX had packed the leaves full, so the leaf where the new email belongs"
                  " had no room. SQLite split it and rebalanced it with its neighbours (balance_nonroot in btree.c),"
                  " and the signposts above changed with them. The next write into the same index found room.", 100))
        con.close()


if __name__ == "__main__":
    main()
