from __future__ import annotations

from typing import Iterable

from .memory import Memory, MemoryStore
from .permissions import PermissionPolicy
from .store import StateStore
from .tools import Tool
from .types import Task, TaskStatus, ToolResult


class Orchestrator:
    """Checkpointed state machine: execute → observe → verify → recover/replan."""
    MAX_ATTEMPTS = 3
    def __init__(self, store: StateStore, memory: MemoryStore, tools: Iterable[Tool], policy: PermissionPolicy | None = None) -> None:
        self.store, self.memory = store, memory
        self.tools = {tool.name: tool for tool in tools}; self.policy = policy or PermissionPolicy()

    @property
    def tool_names(self) -> set[str]:
        return set(self.tools)

    def create(self, user_id: str, conversation_id: str, goal: str, plan: list[dict]) -> Task:
        task = Task(user_id=user_id, conversation_id=conversation_id, goal=goal, plan=plan)
        task.status = TaskStatus.QUEUED
        task.state["relevant_memory"] = [m.content for m in self.memory.retrieve(user_id, goal)]
        self.store.save_task(task, "created", {"plan_steps": len(plan)})
        return task

    def cancel(self, task: Task) -> Task:
        task.status = TaskStatus.CANCELLED; self.store.save_task(task, "cancelled"); return task

    def resume_interrupted(self) -> list[Task]:
        recovered = []
        for task in self.store.recoverable_tasks():
            task.status = TaskStatus.RECOVERING; self.store.save_task(task, "recovering")
            recovered.append(self.run(task))
        return recovered

    def run(self, task: Task) -> Task:
        if task.status == TaskStatus.CANCELLED: return task
        task.status = TaskStatus.RESUMED if task.current_step else TaskStatus.RUNNING
        self.store.save_task(task, "running", {"step": task.current_step})
        while task.current_step < len(task.plan):
            step = task.plan[task.current_step]
            task.state["current_goal"] = task.goal; task.state["pending_action"] = step
            task.status = TaskStatus.CHECKPOINT; self.store.save_task(task, "checkpoint", {"step": task.current_step})
            outcome = self._execute_step(task, step)
            task.state["last_tool"] = step.get("tool"); task.state["last_tool_result"] = outcome.output
            task.state["last_observation"] = outcome.evidence
            if not outcome.ok:
                task.status = TaskStatus.FAILED; self.store.save_task(task, "failed", {"step": task.current_step, "error": outcome.error})
                self.memory.remember(task.user_id, Memory("failure", f"Task {task.goal}: {outcome.error}", .8, {"task_id": task.id, "step": task.current_step}))
                return task
            task.current_step += 1; task.status = TaskStatus.RUNNING
            self.store.save_task(task, "step_verified", {"completed_step": task.current_step})
        task.status = TaskStatus.COMPLETED; task.state["pending_action"] = None
        self.store.save_task(task, "completed")
        self.memory.remember(task.user_id, Memory("episodic", f"Completed task: {task.goal}", .7, {"task_id": task.id}))
        return task

    def _execute_step(self, task: Task, step: dict) -> ToolResult:
        name, arguments = step.get("tool"), step.get("arguments", {})
        tool = self.tools.get(name)
        if tool is None: return ToolResult(False, error=f"tool unavailable: {name}")
        decision = self.policy.decide(name, arguments)
        if not decision.allowed: return ToolResult(False, error=decision.reason)
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            result = tool.execute(arguments)
            self.store.save_task(task, "observation", {"step": task.current_step, "attempt": attempt, "ok": result.ok, "error": result.error})
            verified = tool.verify(arguments, result) if result.ok else result
            if verified.ok:
                verified.evidence = {**verified.evidence, "attempt": attempt, "verified": True}
                return verified
            if not verified.retryable: return verified
        return ToolResult(False, error="retry limit exceeded")
