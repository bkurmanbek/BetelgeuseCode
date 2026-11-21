# How a database index finds a row: inside SQLite's B-tree pages

What does SQLite actually read for `SELECT * FROM users WHERE email = ?`? These materials open the database
file and read its pages: the table's B-tree in id order, the scan that reads all 8,620 of its pages,
the index as a second B-tree of sorted `(email, id)` pairs, and the real path of one lookup:
6 pages, root to leaf in the index, then down the table's own tree to the row.

```text
index idx_users_email   page 8,622 (root) → page 11,158 (signpost) → page 11,249 (leaf): kiwi@mail.test, id 124,907
table users             page 2 (root)     → page 930 (signpost)    → page 1,076 (leaf):  the row
```

From there the usual rules stop being rules of thumb and become things you can see in the pages: why
`LIKE '%@post.test'` scans (250,821 matches spread over all 6,577 leaf pages), why
`GLOB 'kiw*'` doesn't (two neighbouring leaves) and `LIKE 'kiw%'` still does, why an index on `(city, age)`
can't answer `WHERE age = ?`, and why one `INSERT` changed pages in every tree.

![The real path of one lookup, read from the file: three pages down the index's B-tree.](figures/walk.png)

## What's inside

| | |
|---|---|
| [`notes.pdf`](notes.pdf) | The handout: the file of pages, the scan, what `CREATE INDEX` builds, the walk through both trees, the leading wildcard, the `LIKE` trap, two-column indexes, what one write changes, limits, common mistakes, exercises with answers |
| [`notebook.ipynb`](notebook.ipynb) | Build the table and read its pages yourself, with a page decoder you can read in one sitting; `FULL = True` for the notes' table |
| [`code/pages.py`](code/pages.py) | The page size in the file header, the table's B-tree, its root's signposts, the first leaf down to the bytes of one row |
| [`code/scan.py`](code/scan.py) | `SCAN users`: walks the leaves in id order and shows where the row is and why reading doesn't stop there |
| [`code/index_pages.py`](code/index_pages.py) | What `CREATE INDEX` built: both trees side by side, the index's first leaf, one entry byte by byte |
| [`code/walk.py`](code/walk.py) | The lookup page by page: index root → signpost → leaf → the table's root → signpost → leaf |
| [`code/sort_order.py`](code/sort_order.py) | Plans and leaf pages for a leading wildcard, a prefix, `LIKE` vs `GLOB`, a function on the column, a two-column index |
| [`code/writes.py`](code/writes.py) | One `INSERT` with zero, one and two indexes: every changed page, its tree, its cells and free bytes before → after |
| [`code/usersdb.py`](code/usersdb.py) | The table (same seed as the notes) and the page reader the scripts share; also builds a `users.db` to keep |
| [`figures/`](figures) | The pictures in the notes, stills from the video lesson |

## Run it

Python 3.9 or newer, standard library only. Every script builds its own database in a temporary folder.

```bash
python3 code/walk.py --quick          # 100,000 rows: about a second
python3 code/walk.py                  # the notes' 1,000,000-row table: a few seconds, 62 MB, temporary
python3 code/walk.py --email nobody@mail.test     # a missing key: the leaf proves it isn't there

python3 code/usersdb.py users.db --indexes        # keep a database to explore, then:
sqlite3 users.db "SELECT name, pagetype, count(*) FROM dbstat GROUP BY 1, 2"
sqlite3 users.db "EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'kiwi@mail.test'"
```

## How the numbers were made

Nothing is timed. A synthetic table of 1,000,000 users (made-up emails on `.test` domains, seed 2,026) is
built in SQLite 3.45.3 through Python's `sqlite3` module. Page counts and tree shapes come from SQLite's
`dbstat` table and, independently, from decoding the file page by page per the
[file format spec](https://www.sqlite.org/fileformat2.html); plans from `EXPLAIN QUERY PLAN`; what a write
changes from comparing the whole file before and after. With the same SQLite version the scripts print the same
page numbers as the notes, to the page.

Found a mistake, or a page number you can't reproduce? Open an issue with the output of `python3 code/walk.py`
and your SQLite version.

## About

Part of a series of short programming lessons that show what happens under the hood: a video, these notes, a
notebook and the code that reads every number from a real run.

Made by Bakytzhan Kurmanbek.

More lessons: [bkurmanbek on GitHub](https://github.com/bkurmanbek).
