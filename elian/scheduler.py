from __future__ import annotations

import json
from datetime import datetime, timezone

from .runtime import ElianRuntime
from .types import now


class Scheduler:
    """Durable one-shot scheduler. Recurrence belongs behind a future cron parser."""
    def __init__(self, runtime: ElianRuntime) -> None:
        self.runtime = runtime
        with runtime.store.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS scheduled_tasks(
                id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, conversation_id TEXT NOT NULL,
                goal TEXT NOT NULL, plan TEXT NOT NULL, due_at TEXT NOT NULL, status TEXT NOT NULL)""")

    def schedule(self, user_id: str, conversation_id: str, goal: str, plan: list[dict], due_at: str) -> int:
        datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        with self.runtime.store.connect() as conn:
            cursor = conn.execute("INSERT INTO scheduled_tasks(user_id,conversation_id,goal,plan,due_at,status) VALUES(?,?,?,?,?,?)", (user_id, conversation_id, goal, json.dumps(plan), due_at, "queued"))
        return cursor.lastrowid

    def run_due(self) -> list[dict]:
        with self.runtime.store.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute("SELECT * FROM scheduled_tasks WHERE status='queued' AND due_at<=?", (now(),)).fetchall()
            for row in rows:
                conn.execute("UPDATE scheduled_tasks SET status='claimed' WHERE id=?", (row["id"],))
            conn.execute("COMMIT")
        results = []
        for row in rows:
            result = self.runtime.handle_message(row["user_id"], row["conversation_id"], row["goal"], json.loads(row["plan"]))
            with self.runtime.store.connect() as conn: conn.execute("UPDATE scheduled_tasks SET status=? WHERE id=?", ("completed" if result.get("task", {}).get("status") == "completed" else "failed", row["id"]))
            results.append(result)
        return results
