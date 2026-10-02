from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    CHECKPOINT = "checkpoint"
    INTERRUPTED = "interrupted"
    RECOVERING = "recovering"
    RESUMED = "resumed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Task:
    user_id: str
    conversation_id: str
    goal: str
    id: str = field(default_factory=lambda: str(uuid4()))
    status: TaskStatus = TaskStatus.CREATED
    current_step: int = 0
    plan: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    parent_task_id: str | None = None
    version: int = 0
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)

    def dump(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def load(cls, payload: dict[str, Any]) -> "Task":
        payload = dict(payload)
        payload["status"] = TaskStatus(payload["status"])
        return cls(**payload)


@dataclass(slots=True)
class ToolResult:
    ok: bool
    output: Any = None
    error: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
