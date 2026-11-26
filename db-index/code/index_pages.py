"""CREATE INDEX copies every (email, id) pair out of the table, sorts the pairs and packs them into pages of their
own: a second B-tree, in the same file, next to the table's. Prints both trees side by side, the index's first
leaf page, one entry down to its bytes, and why a signpost page of the index points to fewer children.

    python3 index_pages.py --quick     # 100,000 rows: about a second
    python3 index_pages.py             # the notes' 1,000,000-row table: ~5 s, 74 MB in a temporary folder

Standard library only. Decodes pages per https://www.sqlite.org/fileformat2.html (sections 1.6 and 2.1).
"""

from __future__ import annotations

from usersdb import INDEXES, Pages, args, built, roots, scratch, varint


def cell_size(raw: bytes, off: int, kind: str) -> int:
    """Bytes one interior cell takes: a 4-byte child page number, then a rowid (table) or a whole entry (index)."""
    if kind == "table interior":
        return varint(raw, off + 4)[1] - off
    size, j = varint(raw, off + 4)
    return j + size - off


def main() -> None:
    a = args(__doc__)
    with scratch(a.db) as path:
        con, _ = built(a, path, ("email",))
        print(f"{INDEXES['email']};\n")
        pg = Pages(path)
        r = roots(con)
        t, ix = pg.shape(r["users"]), pg.shape(r["idx_users_email"])
        last_table_page = max(pg.all_pages(r["users"]))
        print(f"one file, {pg.count:,} pages: the table's tree has root page {r['users']}, the index's root page "
              f"{r['idx_users_email']:,}\n(the index was written after the table's last page, {last_table_page:,})\n")

        print(f"{'':<26}{'users (the table)':>20}{'idx_users_email':>20}")
        rows = [("sorted by", "id", "email"), ("levels", t["levels"], ix["levels"]),
                ("pages per level", " / ".join(f"{n:,}" for n in t["pages_per_level"]),
                 " / ".join(f"{n:,}" for n in ix["pages_per_level"])),
                ("pages in all", t["pages"], ix["pages"]),
                ("cells per leaf page", t["avg_per_leaf"], ix["avg_per_leaf"]),
                ("children per signpost", t["avg_children"], ix["avg_children"])]
        for name, x, y in rows:
            fx = f"{x:,}" if isinstance(x, int) else x
            fy = f"{y:,}" if isinstance(y, int) else y
            print(f"  {name:<24}{fx:>20}{fy:>20}")

        first = next(pg.leaves(r["idx_users_email"]))
        raw = pg.raw(first["pgno"])
        print(f"\nthe index's first leaf, page {first['pgno']:,}: type 0x{raw[0]:02x} = {first['kind']},"
              f" {first['ncell']} entries, each (email, id):")
        for _, (email, rowid) in first["cells"][:4]:
            print(f"  {email:<24} {rowid:>9,}")
        print(f"  {'…':<24}\n  {first['cells'][-1][1][0]:<24} {first['cells'][-1][1][1]:>9,}")

        off = first["offsets"][0]
        size, j = varint(raw, off)
        hlen = raw[j]
        email, rowid = first["cells"][0][1]
        print(f"\nits first entry, byte by byte (at byte {off:,} of the page):")
        print(f"  {raw[off:j].hex(' '):<20} payload: {size} bytes")
        print(f"  {raw[j:j + hlen].hex(' '):<20} record header: column types {list(raw[j + 1:j + hlen])}"
              f" = text, {len(email)} bytes | int, {(0, 1, 2, 3, 4, 6, 8)[raw[j + 2]]} bytes")
        print(f"  {raw[j + hlen:j + hlen + 6].hex(' ') + ' …':<20} {email!r}")
        p = j + hlen + len(email)
        print(f"  {raw[p:j + size].hex(' '):<20} {rowid:,}: the id of the row it points back to")
        print("  no city, no age: the index holds the email and the id, nothing else")

        print("\nwhy an index signpost page has fewer children: what one signpost (interior cell) costs")
        for name in ("users", "idx_users_email"):
            root = pg.page(r[name])
            raw = pg.raw(root["pgno"])
            sizes = [cell_size(raw, o, root["kind"]) for o in root["offsets"]]
            key = root["cells"][0][1]
            print(f"  {name:<16} page {root['pgno']:>6,}: {sum(sizes) / len(sizes):5.1f} bytes per cell,"
                  f" e.g. child page {root['cells'][0][0]:,} + key {f'{key:,}' if isinstance(key, int) else key}")
        con.close()


if __name__ == "__main__":
    main()
