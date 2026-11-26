"""The users table every script here looks inside, and a reader for SQLite's own file pages.

    python3 usersdb.py users.db                  # keep a copy to explore: 1,000,000 rows, ~4 s, 41 MB
    python3 usersdb.py users.db --indexes        # the same with both indexes from the notes (~6 s, 90 MB)
    python3 usersdb.py users.db --rows 100000    # a smaller table
    sqlite3 users.db                             # then look yourself: SELECT * FROM dbstat WHERE name = 'users' LIMIT 5;

The table is the one in the notes:

    CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT COLLATE NOCASE, city TEXT, age INTEGER)

1,000,000 rows from a fixed seed (2026). The emails look real: common first and last names from many countries,
paired at random, in the usual shapes (maria.lopez@, jkim@, sara_lee92@) at the big mail providers, so no row is a
real person's data. Exactly one row is maria.lopez@gmail.com, the one the notes look up. COLLATE NOCASE makes the
email column ignore upper and lower case, the usual choice for emails. With the same SQLite version the scripts
print the same page numbers as the notes, to the page.

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
import struct
import tempfile
from pathlib import Path

ROWS = 1_000_000
QUICK_ROWS = 100_000
SEED = 2026
TARGET = "maria.lopez@gmail.com"
PROBE = ("daniel.kim@outlook.com", "Seoul", 31)    # the one new row the notes write, and delete again (section 7.4)
SCHEMA = "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT COLLATE NOCASE, city TEXT, age INTEGER)"
LINE = "SELECT * FROM users WHERE email = ?"
INDEXES = {"email": "CREATE INDEX idx_users_email ON users(email)",
           "city_age": "CREATE INDEX idx_users_city_age ON users(city, age)"}
# Mail providers by a rough share of personal addresses: an order-of-magnitude picture, not a market statistic.
DOMAINS = {"gmail.com": 50, "yahoo.com": 12, "outlook.com": 12, "icloud.com": 10, "hotmail.com": 10, "proton.me": 6}
CITIES = ["Almaty", "Berlin", "Cairo", "Lima", "Oslo", "Paris", "Seoul", "Tokyo"]
FIRST = """emma olivia ava sophia mia isabella amelia harper ella grace chloe lily zoe hannah sarah anna laura julia
maria sofia lucia elena carmen ana paula camila valentina gabriela daniela aigerim aliya dana madina zarina dinara
asel kamila amina fatima leila yasmin nora ingrid freya astrid mei yuki hana sakura minji seoyeon priya ananya divya
aisha zainab james john michael david daniel matthew andrew ryan ethan noah liam lucas mason logan jacob william
thomas oliver jack henry samuel benjamin alexander max leon felix jonas lukas paul marco luca matteo diego carlos
javier pablo miguel mateo santiago arman timur daniyar aidar yerlan askar ruslan omar ali hassan karim yusuf ivan
dmitri alexei sergei kenji haruto takumi minho jisung wei jun raj arjun rohan vikram kwame kofi tunde emeka""".split()
LAST = """smith johnson williams brown jones miller davis wilson anderson taylor thomas moore martin jackson white harris
clark lewis walker hall young king wright scott green baker adams nelson hill campbell garcia rodriguez martinez
hernandez lopez gonzalez perez sanchez ramirez torres flores rivera gomez diaz morales ortiz castro silva santos
oliveira costa pereira ferreira rossi russo ferrari esposito bianchi romano colombo mueller schmidt schneider fischer
weber meyer wagner becker hoffmann novak kowalski nowak ivanov petrov smirnov popov volkov sokolov kim lee park choi
jung kang cho yoon tanaka suzuki sato takahashi watanabe ito nakamura wang li zhang liu chen yang huang zhao nguyen
tran pham patel sharma singh kumar gupta khan ahmed hassan ibrahim mensah okafor adeyemi nurlanov seitkali abenov
akhmetov omarov bekov iskakov suleimenov kassymov tulegenov ospanov""".split()


# ---------------------------------------------------------------- the table

def email_maker(rng: random.Random, reserved: set[str]):
    """Real-looking, unique emails: first.last@gmail.com, jkim@yahoo.com, sara_lee92@icloud.com, ...
    The same draws from the same random generator, in the same order, as the notes' run."""
    used = set(reserved)
    domains, weights = list(DOMAINS), list(DOMAINS.values())

    def make() -> str:
        first, last = rng.choice(FIRST), rng.choice(LAST)
        style = rng.random()
        if style < 0.40:
            local = f"{first}.{last}"                  # maria.lopez
        elif style < 0.55:
            local = f"{first}{last}"                   # marialopez
        elif style < 0.65:
            local = f"{first}_{last}"                  # maria_lopez
        elif style < 0.75:
            local = f"{first[0]}{last}"                # mlopez
        elif style < 0.90:
            local = f"{first}.{last}{rng.randint(1, 99)}"   # maria.lopez86
        else:
            local = f"{first}{rng.randint(1970, 2007)}"     # maria1994
        domain = rng.choices(domains, weights)[0]
        email = f"{local}@{domain}"
        while email in used:                           # taken: add digits, as a real sign-up form makes you do
            email = f"{local}{rng.randint(1, 999)}@{domain}"
        used.add(email)
        return email
    return make


def build(path: Path, rows: int = ROWS) -> sqlite3.Connection:
    """users(id, email, city, age), no index yet: only the table's own B-tree, in id order."""
    path = Path(path)
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    con.execute(SCHEMA)
    rng = random.Random(SEED)
    target_at = rng.randrange(rows)
    make_email = email_maker(rng, {TARGET, PROBE[0]})

    def gen():
        for i in range(rows):
            email = TARGET if i == target_at else make_email()
            yield email, rng.choice(CITIES), rng.randint(18, 70)

    con.executemany("INSERT INTO users (email, city, age) VALUES (?, ?, ?)", gen())
    con.commit()
    return con


def make(path: Path, rows: int = ROWS, indexes: tuple[str, ...] = ()) -> tuple[sqlite3.Connection, dict]:
    """The table, then each index, in the same steps as the notes' run: after the table and after every
    CREATE INDEX, one new user (PROBE, Daniel Kim) is written and deleted again (`one_write`, what writes.py looks
    at). That write splits a leaf of a freshly built index, so doing it here keeps every page equal to the notes'.
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


_UPPER = {c: c + 32 for c in range(ord("A"), ord("Z") + 1)}


def nocase(s: str) -> str:
    """The key SQLite's NOCASE collation compares: A-Z folded to a-z, nothing else (not é, not İ)."""
    return s.translate(_UPPER)


def descend(pages: Pages, root: int, key, fold=None) -> list[dict]:
    """The pages one lookup reads from the root to the leaf, as SQLite's B-tree code does: on each interior page,
    the first key ≥ the one we want says which child to read (fileformat2 section 1.6). `key` is a rowid for a
    table, a value (or a tuple of values) for an index. `fold`: how the index compares text (`nocase` for the
    email index, whose column is COLLATE NOCASE). Each step: the page, the branch taken, the keys around it."""
    path, pgno = [], root
    is_index = isinstance(key, (str, tuple))
    want = key if isinstance(key, tuple) else (key,)
    if fold:
        want = tuple(fold(v) if isinstance(v, str) else v for v in want)

    def k_of(cell):                                      # the comparable part of a cell
        if not is_index:
            return (cell[1] if isinstance(cell[1], int) else cell[0],)
        vals = cell[1][:len(want)]
        return tuple(fold(v) if fold and isinstance(v, str) else v for v in vals)

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


def file_pages(path: Path) -> tuple[int, int]:
    """(pages in the file, bytes per page), from the file header itself: bytes 28-31 and 16-17."""
    with open(path, "rb") as f:
        head = f.read(100)
    size = int.from_bytes(head[16:18], "big")
    return int.from_bytes(head[28:32], "big"), 65536 if size == 1 else size


def built(a: argparse.Namespace, path: Path, indexes: tuple[str, ...] = ()) -> tuple[sqlite3.Connection, dict]:
    """Build the table (and the indexes asked for) and say what is in the file: pages, not seconds."""
    con, writes = make(path, a.n, indexes)
    pages, size = file_pages(path)
    print(f"built users: {a.n:,} rows{' + ' + ', '.join(INDEXES[i].split()[2] for i in indexes) if indexes else ''}"
          f" · {pages:,} pages of {size:,} bytes · SQLite {sqlite3.sqlite_version}\n")
    return con, writes


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("db")
    ap.add_argument("--rows", type=int, default=ROWS)
    ap.add_argument("--indexes", action="store_true", help="also create both indexes from the notes")
    a = ap.parse_args()
    make(Path(a.db), a.rows, tuple(INDEXES) if a.indexes else ())[0].close()
    pages, size = file_pages(Path(a.db))
    print(f"{a.rows:,} rows in {a.db}: {pages:,} pages of {size:,} bytes ({os.path.getsize(a.db) / 1e6:,.0f} MB)")
