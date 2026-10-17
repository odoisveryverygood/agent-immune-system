# Repository instructions

## Hard Git rule

**NEVER PUSH DIRECTLY TO MAIN. NEVER FORCE-PUSH MAIN. NEVER AUTO-MERGE.**

- Work on your lane's feature branch; push only that branch and open a PR into main.
- Never run `git push origin main`, `git push origin HEAD:main`, or equivalent API/ref updates.
- Do not bypass hooks or disable GitHub protection. Do not merge a PR unless the human owner explicitly authorizes that merge.
- This applies to docs, fixes, generated files, initial code and emergency changes too.
- Run `sh scripts/setup.sh` after cloning to enable the local push guard.

## Scope and ownership

This is a new project, not Silico. Do not copy Silico's implementation or claim previous sponsor verification as evidence for this app.

| Lane | Owned files |
|---|---|
| Person 1 | `backend/engine/`, `backend/api/`, `backend/providers/crusoe.py`, `backend/models.py`, backend dependency manifest |
| Person 2 | `backend/target/`, `backend/runtime/`, `sandbox/`, `tests/target/` |
| Person 3 | `backend/review/`, `backend/research/`, `backend/providers/you.py`, `tests/review/` |
| Person 4 | `frontend/`, `tests/e2e/`, `tests/heldout/`, demo assets and verification report |

Contracts in `docs/CONTRACT.md` are shared. Propose changes in a PR and coordinate before changing callers. Do not overwrite another lane or add dependencies to another lane's manifest. Person 1 owns Python dependencies; Person 4 owns frontend dependencies.

## Implementation constraints

- Python 3.11+, FastAPI, asyncio, Pydantic for the backend. React/TypeScript/Vite for the frontend. These are chosen directions; dependencies and application files are not scaffolded yet.
- One recursive task runner: a child can invoke the same runner, with an actual parent ID and a reason tied to observed evidence.
- Root-wide default caps: 24 model calls, 64 target tool calls, depth 2, 4 concurrent tasks, 180 seconds. Descendants cannot reset limits. Reserve budget before dispatch.
- Target operations are simulated only. No payment processors, real purchases, customer outreach or public third-party attack targets.
- Repair is a constrained policy patch, not arbitrary generated code or host commands.
- Trusted deterministic checks decide numeric policy violations. Nemotron cannot override them.
- Preserve exact attack replay, policy versions, task lineage and tool receipts. Do not pass a repair merely because a rerun finished.
- Network calls require explicit provider/runtime configuration. No hidden fixture fallback.
- Keys stay on the host, outside Git and browser bundles. Never print credentials, authorization headers or private environment contents.
- OpenShell enforcement must be tested, not inferred from a configuration file or installed binary.

## Before a PR

Run the lane's acceptance checks and the affected integration checks. State what ran locally, against fixtures and against live providers. Include exact limitations. A build or model HTTP 200 alone does not prove the user flow works.

Keep changes small enough for another teammate to review. PRs target main; pushes never do.
