# Person 1 — recursive engine and API

Branch: `p1/recursive-engine`. Read AGENTS.md first. Never push main; push this branch and open a PR.

## Own

`backend/engine/`, `backend/api/`, `backend/providers/crusoe.py`, `backend/models.py`, backend dependency manifest. Coordinate shared model changes through the contract.

## Build in order

1. Pydantic contract models and fixture FastAPI endpoints. Give Person 4 an SSE stream immediately.
2. One async recursive task executor. It accepts a task and may execute it or create justified child tasks using that same executor.
3. Root-wide atomic budget reservations, depth checks, semaphore, deadline, cancellation and persisted events.
4. Crusoe model transport with bounded response size, timeout and typed errors; one shared completion interface for Person 3.
5. Connect Person 2's target executor and Person 3's review/repair functions. Persist exact attack cases for replay.
6. Orchestrate baseline → investigation → patch → exact replay → held-out/legitimate evaluation.

## Acceptance

- A finding creates a child, and a child creates a grandchild through the same runner.
- No descendant resets the root's limits. Exhaustion stops before another dispatch.
- Canceled/timed-out work does not produce a fake completion event.
- UI receives persisted events in order; restart can show existing history without silently restarting paid work.
- Real Crusoe output is actually used, with sanitized provenance. Fixture and live modes cannot be confused.

## Handoff

Document startup commands and routes. Provide one fixture run ID, one event stream and the shared completion function. Open a small contract/API PR early; implementation follows in separate PRs.

## Copy/paste starting prompt

> Read AGENTS.md and docs/CONTRACT.md. Implement Person 1's lane in docs/TEAMMATE-1.md on p1/recursive-engine. Freeze models and fixture API first so teammates can build independently. Keep every child under the same root budget. Do not edit another lane, push main, merge or deploy. Push only your feature branch and open a PR with executed checks and limitations.
