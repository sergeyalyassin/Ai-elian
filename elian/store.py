from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .types import Task, TaskStatus, now


class StateStore:
    """Durable SQLite state. Each write is a short, atomic transaction."""

    def __init__(self, path: str | Path = "data/elian.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tasks (
                  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, conversation_id TEXT NOT NULL,
                  status TEXT NOT NULL, payload TEXT NOT NULL, version INTEGER NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS tasks_active ON tasks(conversation_id, status, updated_at);
                CREATE TABLE IF NOT EXISTS events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                  kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, kind TEXT NOT NULL,
                  content TEXT NOT NULL, importance REAL NOT NULL, metadata TEXT NOT NULL,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS memories_user_kind ON memories(user_id, kind, updated_at);
            """)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def save_task(self, task: Task, event: str, details: dict | None = None) -> Task:
        task.updated_at = now()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT version FROM tasks WHERE id=?", (task.id,)).fetchone()
            if existing and existing["version"] != task.version:
                conn.execute("ROLLBACK")
                raise RuntimeError(f"concurrent task update rejected for {task.id}")
            task.version += 1
            payload = json.dumps(task.dump(), ensure_ascii=False, sort_keys=True)
            conn.execute("""INSERT INTO tasks(id,user_id,conversation_id,status,payload,version,updated_at)
                VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,
                payload=excluded.payload,version=excluded.version,updated_at=excluded.updated_at""",
                (task.id, task.user_id, task.conversation_id, task.status.value, payload, task.version, task.updated_at))
            conn.execute("INSERT INTO events(task_id,kind,payload,created_at) VALUES(?,?,?,?)",
                         (task.id, event, json.dumps(details or {}, ensure_ascii=False), task.updated_at))
            conn.execute("COMMIT")
        return task

    def get_task(self, task_id: str) -> Task | None:
        with self.connect() as conn:
            row = conn.execute("SELECT payload FROM tasks WHERE id=?", (task_id,)).fetchone()
        return Task.load(json.loads(row["payload"])) if row else None

    def active_task(self, conversation_id: str) -> Task | None:
        terminal = (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value)
        with self.connect() as conn:
            row = conn.execute(f"SELECT payload FROM tasks WHERE conversation_id=? AND status NOT IN ({','.join('?'*3)}) ORDER BY updated_at DESC LIMIT 1", (conversation_id, *terminal)).fetchone()
        return Task.load(json.loads(row["payload"])) if row else None

    def latest_task(self, conversation_id: str) -> Task | None:
        with self.connect() as conn:
            row = conn.execute("SELECT payload FROM tasks WHERE conversation_id=? ORDER BY updated_at DESC LIMIT 1", (conversation_id,)).fetchone()
        return Task.load(json.loads(row["payload"])) if row else None

    def recoverable_tasks(self) -> list[Task]:
        states = (TaskStatus.RUNNING.value, TaskStatus.CHECKPOINT.value, TaskStatus.RECOVERING.value, TaskStatus.RESUMED.value)
        with self.connect() as conn:
            rows = conn.execute(f"SELECT payload FROM tasks WHERE status IN ({','.join('?'*4)})", states).fetchall()
        return [Task.load(json.loads(row["payload"])) for row in rows]

    def events(self, task_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT kind,payload,created_at FROM events WHERE task_id=? ORDER BY id", (task_id,)).fetchall()
        return [{"kind": r["kind"], "payload": json.loads(r["payload"]), "created_at": r["created_at"]} for r in rows]
