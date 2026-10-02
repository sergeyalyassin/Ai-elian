# Hermes audit and Elian integration policy — 2026-10-02

## 1. Local Elian baseline

Before this work, this checkout had only a greeting `main.py` and a short `README.md`; it had no agent runtime, provider layer, tools, browser automation, persistent memory, task queue, Telegram adapter, skills implementation, test suite, requirements, or configuration. The current `elian/` package is an independent P0 foundation, not a fork of Hermes.

## 2. Hermes licence audit

The official [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent) repository declares the **MIT License**, copyright **2025 Nous Research**. The MIT grant permits use, copying, modification, merging, publishing, distribution, sublicensing, and sale. Its operative condition is that the copyright and permission notice accompany all copies or substantial portions. It supplies software without warranty.

### What this permits for Elian

- We may copy selected Hermes source files and modify or integrate them.
- We may create a derivative/fork, including commercial distribution.
- For every copied substantial source portion, we must retain the upstream copyright and MIT permission notice and identify the upstream source/commit in our notices.

### What this does **not** establish

- It does not automatically licence third-party dependencies, model weights, hosted services, trademarks, credentials, or separately licensed plugin/skill content.
- “MIT” is not legal advice. Dependency licences and any nested `LICENSE`/`NOTICE` files must be audited for each imported component.
- We must not claim endorsement by Nous Research or call Elian an official Hermes build.

## 3. Source-access result

A direct read-only Git clone and a codeload archive request were both blocked by this execution environment's network tunnel with HTTP 403. No repository objects were downloaded to this workspace. The official GitHub pages were reviewed through the available read-only browser: they expose Hermes's top-level areas including `agent`, `gateway`, `providers`, `skills`, `tools`, `cron`, `tests`, `plugins`, and `web`.

**Current compliance state: no Hermes source, tests, assets, or licence text have been copied into Elian.** The P0 implementation is independent. The audit has verified the top-level project licence, but a file/dependency-level audit still requires a reproducible local checkout pinned to a commit SHA.

## 4. Keep / merge / replace / improve / reimplement decision

| Hermes area | Elian status | Decision now | Integration condition |
|---|---|---|---|
| Agent loop and task state | independent P0 state machine | improve independently | compare against pinned source; retain notice if copying |
| Provider routing | absent | implement adapter contract | audit provider package dependencies |
| Persistent memory / FTS | typed SQLite lexical store | improve independently | inspect state/FTS implementation and licences |
| Gateway / Telegram | absent | implement independent adapter | audit messaging dependencies and secrets policy |
| Browser and tools | minimal file/shell tools | implement independent adapter | audit browser libraries and their licences |
| Skills / plugins | absent | implement compatible, independent lifecycle | audit skills' own content licences |
| Cron / delegation | absent | implement independently | preserve task isolation and lease invariants |

## 5. Safe integration procedure

1. Obtain a local Hermes checkout in a network-enabled environment and record its exact commit SHA.
2. Enumerate root and nested licences/notices and generate a dependency licence inventory.
3. Select small, testable components rather than copying the full multi-surface repository wholesale.
4. Copy the upstream file verbatim only when appropriate; retain its header and add an entry to `THIRD_PARTY_NOTICES.md` naming path, SHA, licence, and modifications.
5. Add upstream-derived tests plus Elian integration, security, recovery, and regression tests.
6. Review credentials, network operations, destructive actions, subprocesses, and externally supplied skills before enabling them.

## 6. Remaining risks

P0 has no LLM planner, browser, Telegram transport, scheduler, worker service, vector index, skill lifecycle, or self-improvement sandbox. It must not be represented as a complete Hermes-equivalent autonomous agent until those capabilities and their integration/E2E tests exist.
