"""SQLite snapshots and append-only, monotonically sequenced events."""
from __future__ import annotations

import sqlite3
import threading
import os
import fcntl
from pathlib import Path

from backend.models import Event, EventType, Run, TERMINAL, now


class RunStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.owner = None
        if self.path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.owner = open(str(path) + ".owner", "a")
            os.chmod(str(path) + ".owner", 0o600)
            try:
                fcntl.flock(self.owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.owner.close()
                raise RuntimeError("State is already owned by another server. Use one worker per database.") from None
        self.db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        if self.path != ":memory:":
            os.chmod(path, 0o600)
        self.lock = threading.RLock()
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(run_id TEXT NOT NULL, seq INTEGER NOT NULL,
                body TEXT NOT NULL, PRIMARY KEY(run_id,seq), FOREIGN KEY(run_id) REFERENCES runs(id));
            CREATE TABLE IF NOT EXISTS request_keys(key TEXT PRIMARY KEY, digest TEXT NOT NULL, run_id TEXT NOT NULL);
        """)

    def create(self, run: Run, *, idempotency_key=None, request_digest=None):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.db.execute("INSERT INTO runs VALUES(?,?)", (run.run_id, run.model_dump_json()))
                if idempotency_key:
                    self.db.execute("INSERT INTO request_keys VALUES(?,?,?)", (idempotency_key, request_digest, run.run_id))
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def lookup_key(self, key):
        with self.lock:
            return self.db.execute("SELECT digest,run_id FROM request_keys WHERE key=?", (key,)).fetchone()

    def get(self, run_id: str) -> Run | None:
        with self.lock:
            row = self.db.execute("SELECT body FROM runs WHERE id=?", (run_id,)).fetchone()
        return Run.model_validate_json(row[0]) if row else None

    def save(self, run: Run):
        with self.lock:
            run.updated_at = now()
            self.db.execute("UPDATE runs SET body=? WHERE id=?", (run.model_dump_json(), run.run_id))

    def emit(self, run: Run, kind: EventType, *, task_id=None, parent_id=None, data=None) -> Event:
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                seq = self.db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM events WHERE run_id=?", (run.run_id,)).fetchone()[0]
                event_data = dict(data or {})
                event_data.setdefault("counters", run.usage.model_dump(mode="json"))
                event = Event(run_id=run.run_id, seq=seq, type=kind, task_id=task_id,
                              parent_id=parent_id, data=event_data)
                run.last_seq = seq
                run.updated_at = now()
                self.db.execute("INSERT INTO events VALUES(?,?,?)", (run.run_id, seq, event.model_dump_json()))
                self.db.execute("UPDATE runs SET body=? WHERE id=?", (run.model_dump_json(), run.run_id))
                self.db.execute("COMMIT")
                return event
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def events(self, run_id: str, after=0, limit=256) -> list[Event]:
        with self.lock:
            rows = self.db.execute("SELECT body FROM events WHERE run_id=? AND seq>? ORDER BY seq LIMIT ?",
                                   (run_id, after, limit)).fetchall()
        return [Event.model_validate_json(row[0]) for row in rows]

    def recover_interrupted(self):
        with self.lock:
            rows = self.db.execute("SELECT body FROM runs").fetchall()
        for row in rows:
            run = Run.model_validate_json(row[0])
            if run.status not in TERMINAL:
                run.status = "blocked"
                run.repair_verified = False
                run.evaluation.repair_verified = False
                run.evaluation.evaluation_status = "incomplete"
                run.evaluation_status = "incomplete"
                run.error_code = "process_restarted"
                run.error_message = "Previous execution was interrupted. History is retained; no paid work was restarted."
                for task in run.tasks:
                    if task.status not in TERMINAL:
                        task.status = "blocked"
                        task.error_code = "process_restarted"
                self.emit(run, "run.blocked", task_id=run.root_task_id,
                          data={"error_code": run.error_code, "message": run.error_message})

    def close(self):
        self.db.close()
        if self.owner:
            self.owner.close()
