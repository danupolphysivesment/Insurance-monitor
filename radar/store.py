# -*- coding: utf-8 -*-
"""SQLite persistence: leads, their triage status, and scan history."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "leads.db")

STATUSES = ["new", "watching", "contacted", "qualified", "won", "dismissed"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id          TEXT PRIMARY KEY,
    url         TEXT UNIQUE NOT NULL,
    platform    TEXT,
    title       TEXT,
    snippet     TEXT,
    score       INTEGER,
    tier        TEXT,
    products    TEXT,
    signals     TEXT,
    reasons     TEXT,
    query       TEXT,
    first_seen  TEXT,
    last_seen   TEXT,
    status      TEXT DEFAULT 'new',
    notes       TEXT DEFAULT '',
    alerted     INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);

CREATE TABLE IF NOT EXISTS runs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT,
    platforms TEXT,
    scanned   INTEGER,
    new_leads INTEGER,
    hot       INTEGER,
    errors    TEXT
);
"""


def lead_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def connect(path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_lead(conn: sqlite3.Connection, lead: Dict) -> bool:
    """Insert a lead. Returns True if it is new to us (worth alerting on)."""
    now = datetime.now().isoformat(timespec="seconds")
    lid = lead_id(lead["url"])
    cur = conn.execute("SELECT id, score FROM leads WHERE id = ?", (lid,))
    row = cur.fetchone()
    if row:
        conn.execute(
            "UPDATE leads SET last_seen = ?, score = ?, tier = ? WHERE id = ?",
            (now, lead["score"], lead["tier"], lid))
        conn.commit()
        return False
    conn.execute(
        """INSERT INTO leads (id, url, platform, title, snippet, score, tier,
                              products, signals, reasons, query, first_seen,
                              last_seen, status, notes, alerted)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'new','',0)""",
        (lid, lead["url"], lead["platform"], lead["title"], lead["snippet"],
         lead["score"], lead["tier"], json.dumps(lead["products"], ensure_ascii=False),
         json.dumps(lead["signals"], ensure_ascii=False),
         json.dumps(lead["reasons"], ensure_ascii=False), lead.get("query", ""),
         now, now))
    conn.commit()
    return True


def mark_alerted(conn: sqlite3.Connection, ids: List[str]) -> None:
    conn.executemany("UPDATE leads SET alerted = 1 WHERE id = ?", [(i,) for i in ids])
    conn.commit()


def set_status(conn: sqlite3.Connection, lid: str, status: str,
               notes: Optional[str] = None) -> None:
    if notes is None:
        conn.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lid))
    else:
        conn.execute("UPDATE leads SET status = ?, notes = ? WHERE id = ?",
                     (status, notes, lid))
    conn.commit()


def log_run(conn: sqlite3.Connection, platforms: List[str], scanned: int,
            new_leads: int, hot: int, errors: List[str]) -> None:
    conn.execute(
        "INSERT INTO runs (ts, platforms, scanned, new_leads, hot, errors) VALUES (?,?,?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), ",".join(platforms),
         scanned, new_leads, hot, json.dumps(errors, ensure_ascii=False)[:2000]))
    conn.commit()


def fetch_leads(conn: sqlite3.Connection, min_score: int = 0,
                statuses: Optional[List[str]] = None,
                platforms: Optional[List[str]] = None,
                limit: int = 500) -> List[sqlite3.Row]:
    sql = "SELECT * FROM leads WHERE score >= ?"
    args: List = [min_score]
    if statuses:
        sql += f" AND status IN ({','.join('?' * len(statuses))})"
        args += statuses
    if platforms:
        sql += f" AND platform IN ({','.join('?' * len(platforms))})"
        args += platforms
    sql += " ORDER BY score DESC, last_seen DESC LIMIT ?"
    args.append(limit)
    return conn.execute(sql, args).fetchall()


def rescore_all(conn: sqlite3.Connection) -> Dict[str, int]:
    """Re-grade every stored lead with the current keyword rules.

    Tuning `keywords.py` is the expected workflow, so the database must be able
    to catch up — otherwise old rows keep scores that the rules no longer give.
    """
    from .scoring import score_post

    rows = conn.execute("SELECT id, title, snippet, url, score FROM leads").fetchall()
    changed = dropped = 0
    for r in rows:
        v = score_post(r["title"] or "", r["snippet"] or "", r["url"])
        if v["score"] == r["score"]:
            continue
        changed += 1
        if not v["is_lead"] or v["score"] == 0:
            dropped += 1
        conn.execute(
            "UPDATE leads SET score = ?, tier = ?, products = ?, reasons = ? WHERE id = ?",
            (v["score"], v["tier"], json.dumps(v["products"], ensure_ascii=False),
             json.dumps(v["reasons"], ensure_ascii=False), r["id"]))
    conn.commit()
    return {"total": len(rows), "changed": changed, "zeroed": dropped}


def purge_zero_scores(conn: sqlite3.Connection) -> int:
    """Delete leads that now score 0 and were never triaged."""
    cur = conn.execute("DELETE FROM leads WHERE score = 0 AND status = 'new'")
    conn.commit()
    return cur.rowcount


def fetch_runs(conn: sqlite3.Connection, limit: int = 50) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
