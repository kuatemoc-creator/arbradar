"""SQLite store. One row per deduplicated item; issues recorded separately."""
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from .config import DB_PATH, DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id            INTEGER PRIMARY KEY,
    fingerprint   TEXT UNIQUE NOT NULL,
    url           TEXT NOT NULL,
    source        TEXT NOT NULL,
    source_tier   INTEGER NOT NULL DEFAULT 2,
    title         TEXT NOT NULL,
    summary       TEXT,
    body          TEXT,
    published_at  TEXT,
    fetched_at    TEXT NOT NULL,
    event_type    TEXT,
    institution   TEXT,
    sectors       TEXT,
    claimants     TEXT,
    respondents   TEXT,
    states        TEXT,
    treaty        TEXT,
    amount_usd    REAL,
    counsel       TEXT,
    arbitrators   TEXT,
    case_ref      TEXT,
    score         REAL DEFAULT 0,
    score_detail  TEXT,
    llm_stage     TEXT DEFAULT 'none',
    relevant      INTEGER DEFAULT 1,
    why_it_matters TEXT,
    issue_id      INTEGER
);
CREATE INDEX IF NOT EXISTS idx_items_pub   ON items(published_at);
CREATE INDEX IF NOT EXISTS idx_items_score ON items(score);
CREATE INDEX IF NOT EXISTS idx_items_issue ON items(issue_id);

CREATE TABLE IF NOT EXISTS issues (
    id          INTEGER PRIMARY KEY,
    number      INTEGER,
    created_at  TEXT NOT NULL,
    subject     TEXT,
    html_path   TEXT,
    md_path     TEXT,
    item_count  INTEGER,
    sent_at     TEXT
);

CREATE TABLE IF NOT EXISTS fetch_log (
    id         INTEGER PRIMARY KEY,
    source     TEXT NOT NULL,
    ran_at     TEXT NOT NULL,
    found      INTEGER,
    new_items  INTEGER,
    error      TEXT
);
"""

LIST_FIELDS = ("sectors", "claimants", "respondents", "states", "counsel", "arbitrators")

# Columns added after the first release; applied on every connect().
MIGRATIONS = (
    ("items", "excluded", "INTEGER DEFAULT 0"),
    ("items", "pinned", "INTEGER DEFAULT 0"),
    ("items", "editor_note", "TEXT"),
)


def _migrate(conn: sqlite3.Connection) -> None:
    for table, column, decl in MIGRATIONS:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info({})".format(table))}
        if column not in cols:
            conn.execute("ALTER TABLE {} ADD COLUMN {} {}".format(table, column, decl))
    conn.commit()


def connect(path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _enc(v: Any) -> Any:
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v


def upsert_item(conn: sqlite3.Connection, item: Dict[str, Any]) -> Optional[int]:
    """Insert if the fingerprint is new. Returns rowid, or None if duplicate."""
    cols = [c for c in item.keys()]
    vals = [_enc(item[c]) for c in cols]
    sql = "INSERT OR IGNORE INTO items ({}) VALUES ({})".format(
        ",".join(cols), ",".join("?" * len(cols)))
    cur = conn.execute(sql, vals)
    return cur.lastrowid if cur.rowcount else None


def update_item(conn: sqlite3.Connection, item_id: int, **fields: Any) -> None:
    if not fields:
        return
    sets = ",".join("{}=?".format(k) for k in fields)
    conn.execute("UPDATE items SET {} WHERE id=?".format(sets),
                 [_enc(v) for v in fields.values()] + [item_id])


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    for f in LIST_FIELDS:
        if d.get(f):
            try:
                d[f] = json.loads(d[f])
            except (ValueError, TypeError):
                d[f] = [d[f]]
        else:
            d[f] = []
    if d.get("score_detail"):
        try:
            d["score_detail"] = json.loads(d["score_detail"])
        except (ValueError, TypeError):
            d["score_detail"] = {}
    return d


def pending(conn: sqlite3.Connection, stage: str, limit: int = 500) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM items WHERE llm_stage=? AND relevant=1 "
        "ORDER BY COALESCE(published_at, fetched_at) DESC LIMIT ?",
        (stage, limit)).fetchall()
    return [row_to_dict(r) for r in rows]
