# Elian architecture plan

## Runtime flow

`transport → ContextManager → active task → MemoryStore.retrieve → planner adapter → validated task plan → Orchestrator → permission policy → tool → observation → tool verification → checkpoint/event → recovery or completion → episodic/failure memory → transport report`

P0 implements the durable centre of this flow. Plans are structured data supplied by an adapter rather than free-form shell text. Each mutation is persisted in SQLite with an optimistic version check and an append-only event record. A restarted runtime converts in-flight/checkpoint tasks to `recovering` and resumes from `current_step`.

## State and concurrency

SQLite WAL plus `BEGIN IMMEDIATE` makes individual state updates atomic. The version field rejects stale writers; a future multi-worker queue must claim tasks atomically before execution. Child tasks use `parent_task_id`; no delegation scheduler is enabled yet.

## Memory policy

Memory is scoped by user and typed (`conversation`, `long_term`, `semantic`, `episodic`, `procedural`, `user`, `project`, `failure`, `skill`). Only explicit runtime outcomes are written today: successful tasks and failures. Retrieval is lexical and transparent; a future embedding provider can be installed behind the same API. Memory is never asserted unless it is returned from this store.

## Security and autonomy

Normal workspace file writes and bounded local commands can be automated. Sensitive shell commands and unregistered tools are denied by policy, rather than using a full-access bypass. External uploads, credential use, browser authentication, destructive operations, and self-modification require dedicated policies and verification before implementation.

## Delivery roadmap

1. **P0 (implemented):** context directives, task/event persistence, checkpoint recovery, tool result normalization, verification, bounded retries, policy checks.
2. **P1:** planner/model provider contract; worker queue and notifications; browser session/tool with action-observe-verify; Telegram adapter and commands; skill registry/version/test/promotion lifecycle; vector memory.
3. **P2:** scheduled jobs, isolated parallel workers and leases, parent/child delegation, provider routing, sandboxed self-improvement proposals with tests/promotion/rollback.

## P1 implementation update

The runtime now includes an OpenAI-compatible planner adapter configured only through `ELIAN_MODEL_ENDPOINT`, `ELIAN_MODEL`, and `ELIAN_MODEL_API_KEY`; the secret is never persisted. Model output is JSON-decoded and validated against registered tool names before a task is created. A versioned skill store accepts candidates but only loads a skill after an explicit successful-test promotion. A transport-neutral Telegram command translator handles `/status`, `/cancel`, `/resume`, `/tools`, and `/queue` without storing credentials. The one-shot durable scheduler claims due rows in an immediate SQLite transaction and invokes the normal verified task flow.

These are integration foundations, not a claim of full browser automation, recurring cron parsing, production Telegram polling, parallel worker leasing, or self-modifying code. Those capability boundaries remain deliberate until their dependencies, policies, and end-to-end tests are added.

## P2 execution and browser foundations

`Worker` uses `BEGIN IMMEDIATE` to claim a queued/recovering task and records the worker identity plus lease timestamp before invoking the existing checkpointed orchestrator. This makes a single queued task unavailable to a second worker after claim; production deployments still need lease expiry, heartbeats, process supervision, and a bounded multi-worker runner.

`BrowserTool` is backend-agnostic and records fresh URL/DOM observations after every action. It supports navigation, click, fill, keyboard press, screenshots, and explicit observation; its verifier evaluates expected URL/text postconditions. A concrete browser backend (for example Playwright) must be installed and registered by a deployment adapter—there is deliberately no hidden browser process or credential store in the runtime.

## Autonomous permission profiles and Playwright backend

Deployments select permissions explicitly with `ELIAN_PERMISSION_PROFILE=standard|unrestricted`. `standard` continues to block sensitive shell commands; `unrestricted` authorizes registered shell commands without per-step approval. This is a visible deployment configuration, not a hidden `AGENT_FULL_ACCESS` bypass: the tool schema, workspace file containment, checkpoints, observations, verifier, and event log still apply.

Install browser support with `pip install .[browser]` and register `BrowserTool(PlaywrightBrowserBackend(...))` as an extra runtime tool. The Playwright backend uses a persistent Chromium profile and supports tabs, typing, waiting, upload input elements, cookie inspection, storage-state export, screenshots, automatic dialog dismissal, and DOM/URL observation. Credentials and browser profile files are deployment data and must not be committed.
