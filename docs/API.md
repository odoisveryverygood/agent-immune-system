# Backend API and integration handoff

The backend is a local FastAPI service. Install and launch it using the commands in the repository README. It defaults to a deterministic fixture run; that mode is labeled `fixture` in the run and event records and never claims a real model or OpenShell sandbox.

## Routes

- `GET /health` — process health and simulated-store scope.
- `GET /api/capabilities` — fixture availability and configured live blockers. `live.verified` remains false until an end-to-end run establishes evidence.
- `POST /api/runs` — accepts the `RunRequest` from `docs/CONTRACT.md`. Returns `run_id` and `queued`; runs execute in the background. Optional `Idempotency-Key` can safely retry the same request. Reusing that key with a different request returns `409`.
- `GET /api/runs/{run_id}` — UI snapshot with `mode`, `tasks`, `events`, `counters`, normalized `evidence`, `patch`, `evaluation`, `repair_verified`, `runtime`, and `last_seq`.
- `GET /api/runs/{run_id}/events` — persisted SSE records in `seq` order. Resume with `Last-Event-ID: <seq>`, `?after=<seq>`, or the UI-compatible `?after_seq=<seq>`.
- `POST /api/runs/{run_id}/cancel` — requests cancellation and reports the current state.

The persisted record is the source of truth for reconnecting clients. On process restart, unfinished runs become `blocked` with `process_restarted`; they are never automatically restarted, since they may have spent provider credits or caused simulated side effects.

## Fixture example

```sh
curl -sS http://127.0.0.1:8000/api/runs \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: local-demo-1' \
  -d '{"target":"shop-demo","goal":"Find and repair a checkout price manipulation","mode":"fixture","seed":42}'
```

Then stream events with:

```sh
curl -N 'http://127.0.0.1:8000/api/runs/run_<id>/events'
```

## Person 1 handoff points

- Shared completion: `RunContext.complete(role, messages)` in `backend/engine/context.py`. It routes through the root-wide call budget, bounded concurrency, timeouts, and sanitized model receipts.
- Target interface: `backend/engine/interfaces.py` `Target`; every checkout side effect must use `RunContext.tool_call`.
- Reviewer interface: `Reviewer` in the same file; model work should use the shared completion boundary.
- Recursion: `RecursiveRunner.execute_task` executes root and children. Child tasks have evidence-checked lineage and share the root `RootBudget`.
- Live factory discovery: set host-side `IMMUNE_TARGET_FACTORY` and `IMMUNE_REVIEW_FACTORY` to `module:function`; the functions must return fresh instances for each run. `IMMUNE_CASES_PATH` points to Person 4's validated `CaseSuite` JSON. Missing integration code is a visible capability blocker, never a fixture fallback.
- Default target/reviewer adapters live in `backend/target/integration.py` and `backend/review/integration.py`. Live target setup also requires `IMMUNE_SANDBOX_ID` and `IMMUNE_OPENSHELL_GATEWAY`. Search and model calls reserve the same root-owned budget; checkout receipts are recorded through `RunContext.tool_call`.
- Crusoe client settings: export `CRUSOE_API_KEY`, `CRUSOE_MODEL`, and `NEMOTRON_MODEL` into the backend process environment. The model IDs must be listed in the account's current Crusoe catalog, and the reviewer model must be a distinct Nemotron ID. The backend does not silently choose a default model. Never place keys in frontend variables or commit them.
- Crusoe uses its OpenAI-compatible chat completions endpoint. Check the current [serverless inference quickstart](https://docs.cloud.crusoe.ai/quickstart/getting-started-with-serverless-inference/index.html) and account's model catalog before selecting IDs; catalog parameter support can vary by model. The transport sends standard chat messages and validates JSON in the engine instead of assuming every model supports provider-specific structured-output options.
- State path: `IMMUNE_STATE_PATH` defaults to `.state/runs.sqlite3`. Run one server worker per database file.

## Boundaries

Live mode requires a live Crusoe completion, live You.com research, a Nemotron reviewer, and actual OpenShell provenance from Person 2's target. API-key presence alone does not establish any of those. Only an end-to-end run can establish them. The target is a simulated store; there are no real orders, payment actions, or external attack targets.
