"""A table on disk is a file of fixed-size pages, and the rows sit in id order in the leaf pages of a B-tree.
Reads it from the file itself: the page size in the file header, the shape of the table's tree, the root page's
signposts, and the first leaf page down to the bytes of one row.

    python3 pages.py --quick          # 100,000 rows: about a second
    python3 pages.py                  # the notes' 1,000,000-row table: ~4 s, 41 MB in a temporary folder
    python3 pages.py --db users.db    # keep the database file afterwards

Standard library only. Decodes pages per https://www.sqlite.org/fileformat2.html (sections 1.3, 1.6, 2.1).
"""

from __future__ import annotations

from usersdb import Pages, args, built, has_dbstat, roots, scratch, varint


def cell_bytes(raw: bytes, off: int) -> list[tuple[str, str]]:
    """One table-leaf cell, field by field: (hex bytes, what they mean)."""
    out = []
    size, j = varint(raw, off)
    out.append((raw[off:j].hex(" "), f"payload size: {size} bytes"))
    rowid, k = varint(raw, j)
    out.append((raw[j:k].hex(" "), f"rowid {rowid:,} (the id column itself is not stored again)"))
    hlen, m = varint(raw, k)
    types, p = [], m
    while p < k + hlen:
        t, p = varint(raw, p)
        types.append(t)
    names = {0: "NULL", 1: "int, 1 byte", 2: "int, 2 bytes", 3: "int, 3 bytes", 4: "int, 4 bytes"}
    desc = " | ".join(names.get(t, f"text, {(t - 13) // 2} bytes" if t % 2 else f"blob, {(t - 12) // 2} bytes")
                     for t in types)
    out.append((raw[k:k + hlen].hex(" "), f"record header: {hlen} bytes; column types {types} = {desc}"))
    p = k + hlen
    for t in types:
        n = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}.get(t, (t - 13) // 2 if t % 2 else (t - 12) // 2)
        if n:
            val = raw[p:p + n]
            shown = repr(val.decode()) if t >= 13 else f"{int.from_bytes(val, 'big', signed=True)}"
            out.append((val.hex(" ") if n <= 6 else val[:6].hex(" ") + " …", shown))
        p += n
    return out


def main() -> None:
    a = args(__doc__)
    with scratch(a.db) as path:
        con, _ = built(a, path)
        pg = Pages(path)
        r = roots(con)

        print(f"{path.name}: {path.stat().st_size:,} bytes = {pg.count:,} pages of {pg.size:,} bytes")
        print(f"  bytes 0-15 of the file   {pg.head[:16]!r}")
        print(f"  bytes 16-17              {pg.head[16:18].hex(' ')}  = {pg.size:,}, the page size"
              f"  (PRAGMA page_size: {con.execute('PRAGMA page_size').fetchone()[0]:,})")
        print(f"  bytes 28-31              {pg.head[28:32].hex(' ')}  = {pg.count:,}, the file's size in pages")
        print("  page 1 = this 100-byte header + the schema table (one row per table and index):")
        for name, root in r.items():
            print(f"      {name:<8} root page {root}")

        sh = pg.shape(r["users"])
        print(f"\nthe table's B-tree, users: {sh['levels']} levels, {sh['pages']:,} pages")
        names = ["root"] + ["signposts"] * (sh["levels"] - 2) + ["leaves"]
        for name, n in zip(names, sh["pages_per_level"]):
            print(f"  {name:<10} {n:>7,} page{'s' * (n != 1)}")
        print(f"  {sh['avg_per_leaf']:,} rows per leaf page and {sh['avg_children']:,} children per signpost page,"
              " on average")

        root = pg.page(r["users"])
        raw = pg.raw(root["pgno"])
        print(f"\npage {root['pgno']:,}, the root: first byte 0x{raw[0]:02x} = {root['kind']}, {root['ncell']} keys,"
              f" {root['ncell'] + 1} children")
        lo = 1
        for child, key in root["cells"][:3]:
            print(f"  ids {lo:>9,} … {key:<9,} → page {child:,}")
            lo = key + 1
        print(f"  {'…':>13}\n  ids {root['cells'][-1][1] + 1:>9,} … the end   → page {root['right']:,} (the right-most child)")

        first = next(pg.leaves(r["users"]))
        raw = pg.raw(first["pgno"])
        ids = [rid for rid, _ in first["cells"]]
        print(f"\npage {first['pgno']:,}, the first leaf: header {raw[:8].hex(' ')}")
        print(f"  0x{raw[0]:02x} = {first['kind']}, {first['ncell']} cells (bytes 3-4), ids {ids[0]:,} … {ids[-1]:,}")
        for rid, row in first["cells"][:3]:
            print(f"  {row}")
        print(f"  …\n  {first['cells'][-1][1]}")
        print(f"\nthe first row's cell, at byte {first['offsets'][0]:,} of the page:")
        for hx, what in cell_bytes(raw, first["offsets"][0]):
            print(f"  {hx:<24} {what}")

        if has_dbstat(con):
            print("\nSQLite's own count (the dbstat table) agrees:")
            q = ("SELECT pagetype, count(*), sum(ncell) FROM dbstat WHERE name = 'users' "
                 "GROUP BY pagetype ORDER BY pagetype")
            for kind, n, cells in con.execute(q):
                print(f"  {kind:<9} {n:>7,} pages, {cells:>9,} cells")
        con.close()


if __name__ == "__main__":
    main()
