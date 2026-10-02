from __future__ import annotations

from pathlib import Path

from .context import ContextManager, Intent
from .memory import MemoryStore
from .orchestrator import Orchestrator
from .planning import Planner, PlanValidationError, validate_plan
from .permissions import PermissionPolicy
from .skills import SkillStore
from .store import StateStore
from .tools import FileWriteTool, ShellTool, Tool
from .types import Task


class ElianRuntime:
    """Integration boundary for transport adapters (CLI today; Telegram/API later)."""
    def __init__(self, data_path: str | Path = "data/elian.db", workspace: str | Path = ".", planner: Planner | None = None, extra_tools: list[Tool] | None = None, permission_policy: PermissionPolicy | None = None) -> None:
        store = StateStore(data_path); memory = MemoryStore(store)
        self.store, self.memory, self.context, self.planner = store, memory, ContextManager(store), planner
        self.orchestrator = Orchestrator(store, memory, [FileWriteTool(workspace), ShellTool(workspace), *(extra_tools or [])], permission_policy)
        self.skills = SkillStore(store)

    def handle_message(self, user_id: str, conversation_id: str, message: str, plan: list[dict] | None = None) -> dict:
        decision = self.context.resolve(conversation_id, message)
        if decision.intent is Intent.STATUS:
            return {"kind": "status", "task": decision.task.dump(), "events": self.store.events(decision.task.id)}
        if decision.intent is Intent.STOP:
            return {"kind": "cancelled", "task": self.orchestrator.cancel(decision.task).dump()}
        if decision.intent is Intent.CONTINUE:
            return {"kind": "continued", "task": self.orchestrator.run(decision.task).dump()}
        if decision.intent is Intent.REPLAN:
            if plan is None: return {"kind": "needs_plan", "task_id": decision.task.id}
            try:
                decision.task.plan = validate_plan(plan, self.orchestrator.tool_names)
            except PlanValidationError as error:
                return {"kind": "plan_error", "message": str(error)}
            decision.task.current_step = 0
            return {"kind": "replanned", "task": self.orchestrator.run(decision.task).dump()}
        if plan is None and self.planner is None:
            return {"kind": "needs_plan", "message": "Configure a planner/model adapter or submit a validated plan."}
        try:
            raw_plan = plan if plan is not None else self.planner.plan(message, {"active_task": decision.task.dump() if decision.task else None, "memory": [m.content for m in self.memory.retrieve(user_id, message)]})
            plan = validate_plan(raw_plan, self.orchestrator.tool_names)
        except (PlanValidationError, RuntimeError) as error:
            return {"kind": "plan_error", "message": str(error)}
        task = self.orchestrator.create(user_id, conversation_id, message, plan)
        return {"kind": "task", "task": self.orchestrator.run(task).dump()}

    def recover(self) -> list[Task]: return self.orchestrator.resume_interrupted()
