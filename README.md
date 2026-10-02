# Ai-Agent-Elian

Elian is being rebuilt as a durable autonomous-agent runtime: it persists task state and selected memory in SQLite, maintains an active conversation task, executes structured tool plans under a permission policy, verifies results, records checkpoints, and resumes interrupted work after restart.

> **Current status:** P0 is implemented and tested. It is not yet a complete browser/Telegram/LLM-worker platform. The remaining implementation roadmap and its explicit limits are in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Run

```bash
python main.py
python -m pytest
```

The runtime is adapter-first: a model/planner or transport must submit a validated structured plan. This avoids treating arbitrary user text as an executable shell command.

## Phase report

### Phase 1 — audit

- **Done:** audited this checkout and attempted a read-only Hermes clone.
- **Files changed:** none during the audit.
- **Problems fixed:** established that the baseline was only a greeting script, not an existing agent runtime.
- **Tests:** repository/source inspection; Hermes clone attempt.
- **Result:** Hermes's official top-level MIT licence was verified through a read-only browser, but direct source download was blocked by the environment (HTTP 403); no Hermes source was copied.
- **Remaining risks:** a file-level Hermes source/dependency audit and pinned local checkout are required before copying any component.
- **Next:** P0 independent runtime, documented below and in [`docs/AUDIT.md`](docs/AUDIT.md).

### Phase 2 — architecture

- **Done:** designed the persistent runtime boundary, data model, memory policy, permission layer, and phased roadmap.
- **Files changed:** `docs/ARCHITECTURE.md`.
- **Risks:** no planner or remote transport is implemented yet.
- **Next:** P1 adapters and worker/browser/Telegram/skills subsystems after a pinned Hermes source/dependency audit can be completed.

### Phase 3 — P0 implementation

- **Done:** context directives (`continue`, `stop`, `status`, `replan`); SQLite task/event persistence; restart recovery; typed persistent memories; tool schema checks; workspace containment; policy decisions; tool observations; verification; retry limits; failure/episodic memories.
- **Files changed:** `elian/`, `tests/`, `main.py`, and project metadata.
- **Problems fixed:** there is now a real state machine rather than a stateless greeting/chat loop.
- **Tests:** unit/integration coverage for persistence, active-task context, recovery, memory isolation, verification, and sensitive command denial.
- **Remaining risks:** no LLM planner, browser, Telegram adapter, durable external worker, concurrency lease, scheduler, semantic embeddings, skills lifecycle, or self-improvement sandbox.
- **Next:** implement P1 behind the documented extension points.

## Design guarantees

- Elian only reports a tool step as verified when its tool verifier returns evidence.
- It does not claim memory unless the data is retrieved from the persistent store.
- Task state survives Python process restarts in the configured SQLite database.
- Sensitive shell commands are denied by default; there is no `AGENT_FULL_ACCESS` bypass.
- Hermes code has not been imported; the verified MIT licence and required reuse procedure are documented in [`docs/AUDIT.md`](docs/AUDIT.md).

### Phase 4 — P1 foundations

- **Done:** OpenAI-compatible model-planner adapter, strict plan validation before task creation, versioned candidate/promoted skills, transport-neutral Telegram command control plane, and a durable one-shot scheduler.
- **Files changed:** `elian/planning.py`, `elian/skills.py`, `elian/telegram.py`, `elian/scheduler.py`, runtime entrypoint, tests, and architecture documentation.
- **Tests:** model-plan rejection, skill promotion gate, Telegram command mapping, and scheduled verified execution.
- **Remaining risks:** Browser sessions, recurring cron syntax, worker leases/parallel execution, live Telegram polling, and self-improvement sandbox remain unimplemented.

### Phase 5 — P2 foundations

- **Done:** lease-style atomic worker claiming and a backend-neutral browser tool with action/observe/verify semantics and screenshot artifacts.
- **Files changed:** `elian/worker.py`, `elian/browser.py`, runtime tool registration, permissions, tests, and architecture documentation.
- **Tests:** browser state/postcondition verification and single worker claim/execution.
- **Remaining risks:** a concrete Playwright/Selenium backend, download/upload/dialog/frame handling, persistent authenticated browser sessions, worker lease expiry/heartbeats, recurring cron expressions, and safe parallel task graphs are still required for production parity.

### Full autonomous deployment profile

For an explicitly trusted, isolated deployment, set `ELIAN_PERMISSION_PROFILE=unrestricted`. This enables registered shell commands without per-step approval, while retaining structured-plan validation, event logging, checkpoints, and verification. Do **not** use this profile for untrusted prompts or shared machines.

Install the concrete persistent Chromium backend with `pip install .[browser]`; deployments then register `BrowserTool(PlaywrightBrowserBackend(...))` with `ElianRuntime(extra_tools=[...])`. It supports browser action/observation/verification and persistent auth state, but production credential and domain policies remain the deployer's responsibility.
