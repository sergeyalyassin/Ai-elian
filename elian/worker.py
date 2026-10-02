"""Lease-based worker entrypoint for independently running queued tasks."""
from __future__ import annotations

import json
from dataclasses import dataclass

from .runtime import ElianRuntime
from .types import Task, TaskStatus, now


@dataclass(slots=True)
class Worker:
    runtime: ElianRuntime
    worker_id: str

    def claim_one(self) -> Task | None:
        """Atomically claim one queued task; another worker cannot execute it concurrently."""
        with self.runtime.store.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT payload FROM tasks WHERE status IN ('queued', 'recovering') ORDER BY updated_at LIMIT 1").fetchone()
            if not row:
                conn.execute("COMMIT")
                return None
            task = Task.load(json.loads(row["payload"]))
            timestamp = now()
            task.status = TaskStatus.RUNNING
            task.state["worker_id"], task.state["lease_started_at"] = self.worker_id, timestamp
            task.updated_at, task.version = timestamp, task.version + 1
            conn.execute("UPDATE tasks SET status=?,payload=?,version=?,updated_at=? WHERE id=? AND version=?",
                         (task.status.value, json.dumps(task.dump(), ensure_ascii=False, sort_keys=True), task.version, timestamp, task.id, task.version - 1))
            conn.execute("INSERT INTO events(task_id,kind,payload,created_at) VALUES(?,?,?,?)",
                         (task.id, "claimed", json.dumps({"worker_id": self.worker_id}), timestamp))
            conn.execute("COMMIT")
            return task

    def run_once(self) -> Task | None:
        task = self.claim_one()
        return self.runtime.orchestrator.run(task) if task else None
