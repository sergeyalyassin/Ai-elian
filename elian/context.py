from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .store import StateStore
from .types import Task, TaskStatus


class Intent(StrEnum):
    NEW_TASK = "new_task"
    CONTINUE = "continue"
    STOP = "stop"
    STATUS = "status"
    REPLAN = "replan"


@dataclass(frozen=True, slots=True)
class ContextDecision:
    intent: Intent
    task: Task | None


class ContextManager:
    CONTINUE = {"كمل", "تابع", "continue", "resume"}
    STOP = {"توقف", "أوقف", "stop", "cancel"}
    STATUS = {"النتيجة", "ماذا حدث", "الحالة", "status", "result"}
    REPLAN = {"غير الخطة", "أعد التخطيط", "replan"}

    def __init__(self, store: StateStore) -> None:
        self.store = store

    def resolve(self, conversation_id: str, message: str) -> ContextDecision:
        text = message.strip().lower().rstrip("؟?!. ")
        active = self.store.active_task(conversation_id)
        latest = active or self.store.latest_task(conversation_id)
        if active and text in self.CONTINUE:
            return ContextDecision(Intent.CONTINUE, active)
        if active and text in self.STOP:
            return ContextDecision(Intent.STOP, active)
        if latest and text in self.STATUS:
            return ContextDecision(Intent.STATUS, latest)
        if active and text in self.REPLAN:
            return ContextDecision(Intent.REPLAN, active)
        return ContextDecision(Intent.NEW_TASK, active)
