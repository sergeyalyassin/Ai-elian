from pathlib import Path

from elian.memory import Memory, MemoryStore
from elian.runtime import ElianRuntime
from elian.store import StateStore
from elian.types import TaskStatus


def write_plan(path="output/result.txt", content="done"):
    return [{"tool": "file.write", "arguments": {"path": path, "content": content}}]


def test_task_is_verified_persisted_and_reports_context(tmp_path: Path):
    runtime = ElianRuntime(tmp_path / "state.db", tmp_path)
    result = runtime.handle_message("u", "chat", "create report", write_plan())
    task = result["task"]
    assert task["status"] == "completed"
    assert (tmp_path / "output/result.txt").read_text() == "done"
    assert task["state"]["last_observation"]["verified"] is True
    status = runtime.handle_message("u", "chat", "النتيجة؟")
    assert status["kind"] == "status"
    assert status["task"]["id"] == task["id"]
    assert any(event["kind"] == "step_verified" for event in status["events"])


def test_recovery_resumes_a_checkpoint_after_runtime_restart(tmp_path: Path):
    first = ElianRuntime(tmp_path / "state.db", tmp_path)
    task = first.orchestrator.create("u", "chat", "recoverable", write_plan("recovered.txt", "yes"))
    task.status = TaskStatus.CHECKPOINT
    first.store.save_task(task, "simulated_interruption")
    second = ElianRuntime(tmp_path / "state.db", tmp_path)
    recovered = second.recover()
    assert len(recovered) == 1
    assert recovered[0].status is TaskStatus.COMPLETED
    assert (tmp_path / "recovered.txt").read_text() == "yes"


def test_memory_is_persistent_and_scoped_to_user(tmp_path: Path):
    store = StateStore(tmp_path / "state.db")
    memories = MemoryStore(store)
    memories.remember("a", Memory("project", "Repository uses SQLite checkpoints", .9))
    reopened = MemoryStore(StateStore(tmp_path / "state.db"))
    assert [item.content for item in reopened.retrieve("a", "SQLite repository")] == ["Repository uses SQLite checkpoints"]
    assert reopened.retrieve("b", "SQLite repository") == []


def test_sensitive_shell_command_is_not_autonomously_run(tmp_path: Path):
    runtime = ElianRuntime(tmp_path / "state.db", tmp_path)
    result = runtime.handle_message("u", "chat", "delete", [{"tool": "shell.run", "arguments": {"command": ["rm", "-rf", "x"]}}])
    assert result["task"]["status"] == "failed"
    events = runtime.store.events(result["task"]["id"])
    assert events[-1]["kind"] == "failed"
    assert "requires approval" in events[-1]["payload"]["error"]


def test_model_plan_is_validated_before_execution(tmp_path: Path):
    class Planner:
        def plan(self, goal, context):
            return [{"tool": "not.allowed", "arguments": {}}]
    runtime = ElianRuntime(tmp_path / "state.db", tmp_path, planner=Planner())
    result = runtime.handle_message("u", "chat", "unsafe plan")
    assert result["kind"] == "plan_error"
    assert not runtime.store.recoverable_tasks()


def test_skills_require_promotion_after_tests(tmp_path: Path):
    runtime = ElianRuntime(tmp_path / "state.db", tmp_path)
    candidate = runtime.skills.propose("report-writer", "Write a verified report.")
    assert runtime.skills.load("report-writer") is None
    promoted = runtime.skills.promote(candidate.name, candidate.version, tests_passed=True)
    assert runtime.skills.load("report-writer") == promoted


def test_telegram_commands_are_control_plane_not_new_tasks(tmp_path: Path):
    from elian.telegram import TelegramControlPlane
    runtime = ElianRuntime(tmp_path / "state.db", tmp_path)
    control = TelegramControlPlane(runtime)
    assert control.handle("u", "chat", "/tools")["tools"] == ["file.write", "shell.run"]
    assert control.handle("u", "chat", "/queue")["recoverable"] == []


def test_one_shot_scheduler_runs_a_verified_task(tmp_path: Path):
    from elian.scheduler import Scheduler
    runtime = ElianRuntime(tmp_path / "state.db", tmp_path)
    scheduler = Scheduler(runtime)
    scheduler.schedule("u", "scheduled", "scheduled write", write_plan("scheduled.txt", "ok"), "2000-01-01T00:00:00+00:00")
    results = scheduler.run_due()
    assert results[0]["task"]["status"] == "completed"
    assert (tmp_path / "scheduled.txt").read_text() == "ok"


def test_replan_revalidates_untrusted_steps(tmp_path: Path):
    runtime = ElianRuntime(tmp_path / "state.db", tmp_path)
    task = runtime.orchestrator.create("u", "chat", "awaiting", write_plan())
    result = runtime.handle_message("u", "chat", "replan", [{"tool": "not.allowed", "arguments": {}}])
    assert result["kind"] == "plan_error"
    assert runtime.store.get_task(task.id).status is TaskStatus.QUEUED


def test_browser_tool_observes_and_verifies_state(tmp_path: Path):
    from elian.browser import BrowserTool

    class FakeBrowser:
        current = ""
        html = ""
        def navigate(self, url): self.current, self.html = url, "<h1>Ready</h1>"
        def click(self, selector): self.html = f"clicked {selector}"
        def fill(self, selector, value): self.html = value
        def press(self, key): self.html = key
        def content(self): return self.html
        def url(self): return self.current
        def screenshot(self, path): Path(path).write_bytes(b"image")

    tool = BrowserTool(FakeBrowser(), tmp_path / "artifacts")
    result = tool.execute({"action": "navigate", "url": "https://example.test"})
    verified = tool.verify({"action": "navigate", "url": "https://example.test", "expect_url": "https://example", "expect_text": "Ready"}, result)
    assert verified.ok and verified.evidence["text_ok"]


def test_worker_claims_and_runs_queued_task_once(tmp_path: Path):
    from elian.worker import Worker
    runtime = ElianRuntime(tmp_path / "state.db", tmp_path)
    queued = runtime.orchestrator.create("u", "worker-chat", "write", write_plan("worker.txt", "done"))
    finished = Worker(runtime, "worker-1").run_once()
    assert finished.id == queued.id
    assert finished.status is TaskStatus.COMPLETED
    assert Worker(runtime, "worker-2").run_once() is None


def test_explicit_unrestricted_profile_allows_sensitive_shell(tmp_path: Path):
    from elian.permissions import PermissionPolicy
    runtime = ElianRuntime(tmp_path / "state.db", tmp_path, permission_policy=PermissionPolicy("unrestricted"))
    result = runtime.orchestrator.policy.decide("shell.run", {"command": ["git", "status"]})
    assert result.allowed and not result.requires_approval
