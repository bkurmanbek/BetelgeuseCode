"""The users table every script here looks inside, and a reader for SQLite's own file pages.

    python3 usersdb.py users.db                  # keep a copy to explore: 1,000,000 rows, ~3 s, 35 MB
    python3 usersdb.py users.db --indexes        # the same with both indexes from the notes (78 MB)
    python3 usersdb.py users.db --rows 100000    # a smaller table
    sqlite3 users.db                             # then look yourself: SELECT * FROM dbstat WHERE name = 'users' LIMIT 5;

The table is the one in the notes: users(id, email, city, age), 1,000,000 rows from a fixed seed (2026), made-up
emails on .test domains, exactly one of them kiwi@mail.test. With the same SQLite version the scripts print the
same page numbers as the notes, to the page.

The page reader follows the file format spec (https://www.sqlite.org/fileformat2.html, sections 1.3 and 1.6) and
uses no SQLite call: it seeks to a page in the .db file and decodes its bytes. Imported by the other scripts.
Standard library only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import random
import sqlite3
import string
import struct
import tempfile
import time
from pathlib import Path

ROWS = 1_000_000
QUICK_ROWS = 100_000
SEED = 2026
TARGET = "kiwi@mail.test"
DOMAINS = ["mail.test", "post.test", "inbox.test", "box.test"]
CITIES = ["Almaty", "Berlin", "Cairo", "Lima", "Oslo", "Paris", "Seoul", "Tokyo"]
LINE = "SELECT * FROM users WHERE email = ?"
INDEXES = {"email": "CREATE INDEX idx_users_email ON users(email)",
           "city_age": "CREATE INDEX idx_users_city_age ON users(city, age)"}
PROBE = ("probe@box.test", "Oslo", 30)        # the one test row the notes write (section 7.4)


# ---------------------------------------------------------------- the table

def build(path: Path, rows: int = ROWS) -> sqlite3.Connection:
    """users(id, email, city, age), no index yet: only the table's own B-tree, in id order."""
    path = Path(path)
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, city TEXT, age INTEGER)")
    rng = random.Random(SEED)
    target_at = rng.randrange(rows)

    def gen():
        for i in range(rows):
            local = "kiwi" if i == target_at else "".join(rng.choices(string.ascii_lowercase, k=8))
            email = TARGET if i == target_at else f"{local}@{rng.choice(DOMAINS)}"
            yield email, rng.choice(CITIES), rng.randint(18, 80)

    con.executemany("INSERT INTO users (email, city, age) VALUES (?, ?, ?)", gen())
    con.commit()
    return con


def make(path: Path, rows: int = ROWS, indexes: tuple[str, ...] = ()) -> tuple[sqlite3.Connection, dict]:
    """The table, then each index, in the same steps as the notes' run: after the table and after every
    CREATE INDEX, one test row is written and deleted again (`one_write`, what writes.py looks at). That write
    splits a leaf of a freshly built index, so doing it here keeps every page count equal to the notes'.
    Returns the connection and {stage: pages that write changed}."""
    con = build(path, rows)
    writes = {"none": one_write(con, path)}
    for name in indexes:
        con.execute(INDEXES[name])
        con.commit()
        writes[name] = one_write(con, path)
    return con, writes


def one_write(con: sqlite3.Connection, path: Path, row: tuple = PROBE) -> dict:
    """INSERT one row and commit; compare the file before and after, page by page; delete the row again.
    Returns the changed page numbers, the tree each belongs to, and each page's cell count before → after."""
    path = Path(path)
    size = con.execute("PRAGMA page_size").fetchone()[0]
    before = path.read_bytes()
    con.execute("INSERT INTO users (email, city, age) VALUES (?, ?, ?)", row)
    con.commit()
    after = path.read_bytes()
    changed = [i + 1 for i in range(max(len(before), len(after)) // size)
               if before[i * size:(i + 1) * size] != after[i * size:(i + 1) * size]]
    owner = owners(con, path)
    cells = {}
    for p in changed:
        old = header_of(before, p, size) if p * size <= len(before) else None
        new = header_of(after, p, size)
        cells[p] = (old, new)
    con.execute("DELETE FROM users WHERE email = ?", (row[0],))
    con.commit()
    by: dict[str, int] = {}
    for p in changed:
        name = "file header" if p == 1 else owner.get(p, "free")
        by[name] = by.get(name, 0) + 1
    return {"pages": changed, "by": by, "owner": {p: ("file header" if p == 1 else owner.get(p, "free"))
                                                  for p in changed},
            "cells": cells, "file_pages": (len(before) // size, len(after) // size),
            "counter": (int.from_bytes(before[24:28], "big"), int.from_bytes(after[24:28], "big"))}


def header_of(data: bytes, pgno: int, size: int) -> tuple[str, int, int] | None:
    """(kind, number of cells, free bytes) of one page in a copy of the file, or None if not a B-tree page.
    Free = the gap between the cell pointers and the cells, plus freed blocks and fragments (fileformat2 1.6)."""
    base = (pgno - 1) * size
    h = base + (100 if pgno == 1 else 0)
    kind = KIND.get(data[h])
    if not kind:
        return None
    ncell = int.from_bytes(data[h + 3:h + 5], "big")
    content = int.from_bytes(data[h + 5:h + 7], "big") or 65536
    pointers_end = (h - base) + (12 if data[h] in (2, 5) else 8) + 2 * ncell
    free, block = content - pointers_end + data[h + 7], int.from_bytes(data[h + 1:h + 3], "big")
    while block:                                         # the chain of freed blocks inside the cell area
        free += int.from_bytes(data[base + block + 2:base + block + 4], "big")
        block = int.from_bytes(data[base + block:base + block + 2], "big")
    return kind, ncell, free


# ---------------------------------------------------------------- SQLite's own answers

def plan(con: sqlite3.Connection, sql: str, args: tuple = ()) -> str:
    """EXPLAIN QUERY PLAN on one line: 'SCAN users' or 'SEARCH users USING INDEX …'."""
    return " / ".join(r[-1] for r in con.execute("EXPLAIN QUERY PLAN " + sql, args))


def roots(con: sqlite3.Connection) -> dict[str, int]:
    """Every B-tree in the file and its root page, from the schema table on page 1."""
    return dict(con.execute("SELECT name, rootpage FROM sqlite_master WHERE rootpage > 0"))


def has_dbstat(con: sqlite3.Connection) -> bool:
    """dbstat is a compile-time option; most builds of Python and the sqlite3 shell have it."""
    try:
        con.execute("SELECT 1 FROM dbstat LIMIT 1").fetchall()
        return True
    except sqlite3.OperationalError:
        return False


def owners(con: sqlite3.Connection, path: Path) -> dict[int, str]:
    """page number → the B-tree it belongs to, by walking every tree from its root."""
    pages, out = Pages(path), {}
    for name, root in roots(con).items():
        for pgno in pages.all_pages(root):
            out[pgno] = name
    return out


# ---------------------------------------------------------------- the file's own pages

KIND = {2: "index interior", 5: "table interior", 10: "index leaf", 13: "table leaf"}


def varint(b: bytes, i: int) -> tuple[int, int]:
    """SQLite's varint: 7 bits per byte, big-endian, high bit set = more follows; a 9th byte uses all 8 bits."""
    v = 0
    for k in range(8):
        c = b[i + k]
        v = (v << 7) | (c & 0x7F)
        if c < 0x80:
            return v, i + k + 1
    return (v << 8) | b[i + 8], i + 9


def record(b: bytes, i: int) -> list:
    """One record: a header of serial types (one per column), then the values (fileformat2 section 2.1)."""
    hlen, j = varint(b, i)
    types = []
    while j < i + hlen:
        t, j = varint(b, j)
        types.append(t)
    out, p = [], i + hlen
    for t in types:
        if t == 0:
            out.append(None)                     # NULL; also the INTEGER PRIMARY KEY column, which is the rowid
        elif t in (8, 9):
            out.append(t - 8)                    # the constants 0 and 1 take no bytes at all
        elif t <= 6:
            n = (0, 1, 2, 3, 4, 6, 8)[t]
            out.append(int.from_bytes(b[p:p + n], "big", signed=True))
            p += n
        elif t == 7:
            out.append(struct.unpack(">d", b[p:p + 8])[0])   # a REAL: an 8-byte IEEE float
            p += 8
        else:                                    # even ≥ 12: a blob, odd ≥ 13: text, length in the type itself
            n = (t - 12) // 2 if t % 2 == 0 else (t - 13) // 2
            out.append(b[p:p + n] if t % 2 == 0 else b[p:p + n].decode())
            p += n
    return out


class Pages:
    """The pages of one SQLite database file, read straight from disk."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.f = open(self.path, "rb")
        head = self.f.read(100)
        if head[:16] != b"SQLite format 3\x00":
            raise SystemExit(f"{self.path} is not an SQLite 3 database file")
        if head[18] == 2:
            raise SystemExit(f"{self.path} is in WAL mode: recent pages may live in the -wal file. Run "
                             "PRAGMA wal_checkpoint(TRUNCATE) or PRAGMA journal_mode=DELETE first")
        self.size = int.from_bytes(head[16:18], "big")
        self.size = 65536 if self.size == 1 else self.size
        self.usable = self.size - head[20]               # bytes per page minus the reserved tail (usually 0)
        self.count = int.from_bytes(head[28:32], "big")  # the file's size in pages, as the header says
        self.head = head
        self.reads = 0

    def raw(self, pgno: int) -> bytes:
        self.f.seek((pgno - 1) * self.size)
        return self.f.read(self.size)

    def header(self, pgno: int) -> dict:
        """The page header only: type, number of cells, right-most child (fileformat2 section 1.6)."""
        b = self.raw(pgno)
        h = 100 if pgno == 1 else 0                      # page 1 starts with the 100-byte file header
        if b[h] not in KIND:
            raise SystemExit(f"page {pgno} is not a B-tree page (type byte {b[h]})")
        interior = b[h] in (2, 5)
        return {"pgno": pgno, "kind": KIND[b[h]], "type": b[h], "interior": interior,
                "ncell": int.from_bytes(b[h + 3:h + 5], "big"),
                "right": int.from_bytes(b[h + 8:h + 12], "big") if interior else None}

    def page(self, pgno: int) -> dict:
        """The page decoded: its header and every cell. Table interior: (child, rowid). Table leaf: (rowid, row).
        Index interior: (child, entry). Index leaf: (None, entry); an entry is the indexed values + the rowid."""
        self.reads += 1
        b = self.raw(pgno)
        p = self.header(pgno)
        h = 100 if pgno == 1 else 0
        ptrs = h + (12 if p["interior"] else 8)          # the cell pointer array follows the page header
        cells = []
        for k in range(p["ncell"]):
            off = int.from_bytes(b[ptrs + 2 * k:ptrs + 2 * k + 2], "big")
            if p["type"] == 5:                           # table interior: 4-byte child page, varint rowid
                cells.append((int.from_bytes(b[off:off + 4], "big"), varint(b, off + 4)[0]))
                continue
            j = off + 4 if p["type"] == 2 else off
            size, j = varint(b, j)
            rowid = None
            if p["type"] == 13:
                rowid, j = varint(b, j)
            limit = self.usable - 35 if p["type"] == 13 else (self.usable - 12) * 64 // 255 - 23
            if size > limit:
                raise SystemExit(f"page {pgno}: a cell spills onto overflow pages, which this reader doesn't follow")
            rec = record(b, j)
            if p["type"] == 13:
                cells.append((rowid, [rowid] + rec[1:]))  # the id column is stored as NULL: it *is* the rowid
            else:
                cells.append((int.from_bytes(b[off:off + 4], "big") if p["type"] == 2 else None, rec))
        p["cells"] = cells
        p["offsets"] = [int.from_bytes(b[ptrs + 2 * k:ptrs + 2 * k + 2], "big") for k in range(p["ncell"])]
        return p

    def children(self, pgno: int) -> list[int]:
        p = self.page(pgno)
        return [c for c, _ in p["cells"]] + [p["right"]] if p["interior"] else []

    def levels(self, root: int) -> list[list[int]]:
        """The page numbers on each level, root first. Only interior pages are decoded."""
        out, level = [], [root]
        while level:
            out.append(level)
            if not self.header(level[0])["interior"]:    # every leaf is at the same depth
                break
            level = [c for p in level for c in self.children(p)]
        return out

    def all_pages(self, root: int) -> list[int]:
        return [p for level in self.levels(root) for p in level]

    def leaves(self, root: int):
        """Every leaf page of a tree, left to right (key order): what a SCAN walks through."""
        p = self.page(root)
        if not p["interior"]:
            yield p
            return
        for child in [c for c, _ in p["cells"]] + [p["right"]]:
            yield from self.leaves(child)

    def shape(self, root: int) -> dict:
        """Levels, pages per level, cells per leaf and children per interior page, from the pages themselves."""
        levels = self.levels(root)
        leaf = [self.header(p)["ncell"] for p in levels[-1]]
        inner = [self.header(p)["ncell"] + 1 for lv in levels[:-1] for p in lv]
        return {"levels": len(levels), "pages_per_level": [len(lv) for lv in levels],
                "pages": sum(len(lv) for lv in levels), "leaf_pages": len(leaf),
                "interior_pages": len(inner), "avg_per_leaf": round(sum(leaf) / len(leaf)),
                "avg_children": round(sum(inner) / len(inner)) if inner else None}


def descend(pages: Pages, root: int, key) -> list[dict]:
    """The pages one lookup reads from the root to the leaf, as SQLite's B-tree code does: on each interior page,
    the first key ≥ the one we want says which child to read (fileformat2 section 1.6). `key` is a rowid for a
    table, a value (or a tuple of values) for an index. Each step: the page, the branch taken, the keys around it."""
    path, pgno = [], root
    is_index = isinstance(key, (str, tuple))
    want = key if isinstance(key, tuple) else (key,)

    def k_of(cell):                                      # the comparable part of a cell
        if not is_index:
            return (cell[1] if isinstance(cell[1], int) else cell[0],)
        return tuple(cell[1][:len(want)])

    while True:
        p = pages.page(pgno)
        keys = [k_of(c) for c in p["cells"]]
        if not p["interior"]:
            hit = next((i for i, k in enumerate(keys) if k == want), None)
            path.append({**p, "pos": hit})
            return path
        b = next((i for i, k in enumerate(keys) if want <= k), len(keys))
        step = {**p, "branch": b, "lo": keys[b - 1] if b else None, "hi": keys[b] if b < len(keys) else None}
        path.append(step)
        if is_index and b < len(keys) and keys[b] == want:   # an index keeps entries on interior pages too
            step["pos"] = b
            return path
        pgno = p["cells"][b][0] if b < len(keys) else p["right"]


# ---------------------------------------------------------------- command line helpers

@contextlib.contextmanager
def scratch(db: str | None):
    """Where to build: the path given (kept afterwards), or a temporary folder (deleted afterwards)."""
    if db:
        yield Path(db)
        return
    with tempfile.TemporaryDirectory(prefix="db-index-") as d:
        yield Path(d) / "users.db"


def args(doc: str, extra=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help=f"{QUICK_ROWS:,} rows: about a second")
    ap.add_argument("--rows", type=int, help=f"table size (default {ROWS:,}, the notes' table)")
    ap.add_argument("--db", help="build the database here and keep it (default: a temporary file)")
    if extra:
        extra(ap)
    a = ap.parse_args()
    a.n = a.rows or (QUICK_ROWS if a.quick else ROWS)
    return a


def built(a: argparse.Namespace, path: Path, indexes: tuple[str, ...] = ()) -> tuple[sqlite3.Connection, dict]:
    t = time.perf_counter()
    con, writes = make(path, a.n, indexes)
    print(f"built users: {a.n:,} rows{' + ' + ', '.join(INDEXES[i].split()[2] for i in indexes) if indexes else ''}"
          f" ({time.perf_counter() - t:.1f} s, SQLite {sqlite3.sqlite_version})\n")
    return con, writes


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("db")
    ap.add_argument("--rows", type=int, default=ROWS)
    ap.add_argument("--indexes", action="store_true", help="also create both indexes from the notes")
    a = ap.parse_args()
    t = time.perf_counter()
    make(Path(a.db), a.rows, tuple(INDEXES) if a.indexes else ())[0].close()
    print(f"{a.rows:,} rows in {a.db} ({os.path.getsize(a.db) / 1e6:,.0f} MB) in {time.perf_counter() - t:.1f} s")
