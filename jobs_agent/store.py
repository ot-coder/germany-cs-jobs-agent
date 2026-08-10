from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Iterable

from .core import Job


class JobStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL,
                    location TEXT NOT NULL, url TEXT NOT NULL, description TEXT NOT NULL,
                    source TEXT NOT NULL, role_type TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'cs', remote INTEGER NOT NULL,
                    published_at TEXT NOT NULL, score INTEGER NOT NULL, reasons TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new'
                )
            """)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)")}
            if "category" not in columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN category TEXT NOT NULL DEFAULT 'cs'")

    def upsert(self, jobs: Iterable[Job]) -> int:
        inserted = 0
        with self._connect() as connection:
            for job in jobs:
                exists = connection.execute("SELECT 1 FROM jobs WHERE id = ?", (job.id,)).fetchone()
                if not exists:
                    inserted += 1
                connection.execute("""
                    INSERT INTO jobs (id,title,company,location,url,description,source,role_type,category,remote,published_at,score,reasons,first_seen_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title, company=excluded.company, location=excluded.location,
                        url=excluded.url, description=excluded.description, source=excluded.source,
                        role_type=excluded.role_type, category=excluded.category,
                        remote=excluded.remote, published_at=excluded.published_at,
                        score=excluded.score, reasons=excluded.reasons
                """, (
                    job.id, job.title, job.company, job.location, job.url, job.description,
                    job.source, job.role_type, job.category, int(job.remote), job.published_at,
                    job.score, json.dumps(job.reasons, ensure_ascii=False), job.first_seen_at,
                ))
        return inserted

    def list_jobs(self, status: str | None = None, limit: int = 200) -> list[dict]:
        query = "SELECT * FROM jobs"
        params: list[object] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY score DESC, first_seen_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = [dict(row) for row in connection.execute(query, params).fetchall()]
        for row in rows:
            row["reasons"] = json.loads(row["reasons"])
            row["remote"] = bool(row["remote"])
        return rows

    def set_status(self, job_id: str, status: str) -> None:
        if status not in {"new", "saved", "applied", "dismissed"}:
            raise ValueError("Invalid job status")
        with self._connect() as connection:
            connection.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
