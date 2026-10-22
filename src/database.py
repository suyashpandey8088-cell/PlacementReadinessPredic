"""SQLite history partitioned by a hashed, high-entropy workspace recovery key.

This is bearer-key isolation, NOT user authentication. Anyone with a key or access
 to the server/database can read that workspace. Queries always bind parameters.
"""
import hashlib
import io
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from src.config import ROOT


class HistoryError(RuntimeError):
    pass


def owner_id(key):
    if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
        raise HistoryError("Use the complete 64-character workspace recovery key, or create a new workspace.")
    return hashlib.sha256(key.encode()).hexdigest()


class HistoryStore:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("PATH2PLACEMENT_DB", ROOT / "data" / "history.sqlite3"))
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.connection() as conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS assessments (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, created_at TEXT NOT NULL,
                    score REAL NOT NULL, payload TEXT NOT NULL, recommendations TEXT NOT NULL
                )""")
                conn.execute("CREATE INDEX IF NOT EXISTS owner_time ON assessments(owner, created_at)")
        except OSError as exc:
            raise HistoryError("History storage is unavailable. Check PATH2PLACEMENT_DB and folder permissions.") from exc

    @contextmanager
    def connection(self):
        try:
            with sqlite3.connect(str(self.path), timeout=5) as conn:
                yield conn
        except sqlite3.Error as exc:
            raise HistoryError("Cannot access assessment history. Check database path, permissions and available disk space. You can still assess without saving.") from exc

    def save(self, key, result, recommendations, assessment_id=None):
        owner = owner_id(key)
        identifier = assessment_id or str(uuid.uuid4())
        with self.connection() as conn:
            # Idempotent: reruns cannot duplicate a single assessment submission.
            conn.execute("INSERT OR IGNORE INTO assessments VALUES (?, ?, ?, ?, ?, ?)",
                         (identifier, owner, datetime.now(timezone.utc).isoformat(),
                          result["score"], json.dumps(result, allow_nan=False), json.dumps(recommendations)))
        return identifier

    def list(self, key):
        with self.connection() as conn:
            rows = conn.execute("SELECT id, created_at, payload, recommendations FROM assessments WHERE owner = ? ORDER BY created_at, id", (owner_id(key),)).fetchall()
        return [{"id": row[0], "created_at": row[1], **json.loads(row[2]),
                 "recommendations": json.loads(row[3])} for row in rows]

    def clear(self, key):
        with self.connection() as conn:
            conn.execute("DELETE FROM assessments WHERE owner = ?", (owner_id(key),))


def export_csv(records):
    rows = []
    for r in records:
        rows.append({"assessment_id": r["id"], "timestamp_utc": r["created_at"],
                     "score": r["score"], "category": r["band"], "scoring_version": r["scoring_version"],
                     **{f"score_{k}": v for k, v in r["categories"].items()}, **r["inputs"]})
    # Fixed headers even for an empty export; no user text is accepted as CSV formulas.
    if not rows:
        return "assessment_id,timestamp_utc,score,category,scoring_version\n"
    buffer = io.StringIO()
    pd.DataFrame(rows).to_csv(buffer, index=False)
    return buffer.getvalue()
