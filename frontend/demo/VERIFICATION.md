# Person 4 verification — October 17, 2026

## Implemented and locally verified

- React/TypeScript/Vite investigation dashboard: fixture labels, actual task IDs and
  parent/depth lineage, selection, spawn reasons, evidence, receipts, constrained
  patch inspector, budgets, runtime provenance, before/after and incomplete results.
- Real POST/snapshot/SSE/cancel browser client. Duplicate events are ignored;
  missing sequences, malformed envelopes and invalid lineage fail visibly.
- Refresh restores persisted snapshot. Interrupted active stream reconnects from
  `after_seq=3` in the HTTP fixture test. Cancellation is confirmed by the server.
- Explicit budget-stop and timeout causes remain visible and inspectable.
- Desktop 1440px and mobile 390px screenshots inspected. Mobile has no horizontal
  overflow in browser tests. Modal keyboard dismissal restores focus; tabs support
  arrow/Home/End navigation. No full assistive-technology or WCAG audit is claimed.
- Held-out suite contains eight attacks and the two required legitimate purchases.
  The isolated runner uses exact original messages, frozen version identity,
  consistent repaired runtime-policy digest, trusted integer-cent receipt checks,
  and validated review receipt references. Missing evidence is never a pass.
- Captioned real-browser fixture walkthrough and three-minute rehearsal script.
  The capture is silent with visible captions, a VTT track and text transcript.

## Executed checks

| Check | Result | Scope |
|---|---|---|
| `npm ci` / locked dependency install | Passed | Frontend dependencies |
| `npm run build` | Passed | TypeScript and production bundle |
| `npm test` | 11 passed | Event integrity and evaluation display |
| `npm run test:e2e` | 9 passed | Chrome against separate local HTTP/SSE fixture |
| `python3 -m unittest discover -s tests/heldout -v` | 9 passed | Evaluator with synthetic adapters |
| `python3 tests/heldout/check_isolation.py` | Passed, all 10 cases | Prompts absent from source/public/bundle |
| `npm audit --audit-level=moderate` | 0 vulnerabilities reported | Resolved dependency tree at verification time |
| `git diff --check` | Passed | Whitespace |

Browser scenarios: task/evidence/policy inspection; start request and shared caps;
duplicate SSE events; terminal refresh recovery; provider-configuration failure;
sequence-gap rejection; deadline failure; cancellation; mobile layout; active
stream disconnection and snapshot/resume; keyboard modal dismissal. Some scenarios
share one test; total is nine test cases.

Earlier verification exposed a wrong expected fixture event count and unscoped
JSON selector, both fixed. An intermediate Vite reload during edits reset a selected
task; final tests ran without source edits and passed. The Playwright Chromium
binary was absent, so tests use installed Chrome explicitly. Current final checks
are the evidence, not the initial failed attempts.

## Not verified / integration dependencies

This branch has no Person 1 API/engine, Person 2 target/runtime adapter or Person 3
review/research implementation. The assembled live workflow, actual recursive
execution, real target attack/repair, held-out target outcomes, valid live purchases,
Crusoe, Nemotron, You.com and OpenShell enforcement have not been exercised.
No live repair success, sponsor eligibility or production readiness is claimed.

Snapshot field names, streamed data nesting and `after_seq` are a documented
frontend adapter proposal because the shared planning contract does not define
those details. Person 1 must coordinate them before assembled integration; an
incompatible response yields an explicit error. No backend files were changed.

The fixture walkthrough reports `evaluation_status: incomplete` and
`repair_verified: false`. Its receipts and patch are illustrative UI data. Evaluator
unit tests are synthetic and do not change that status. Runtime provenance strings
alone do not prove sandbox enforcement. Held-out target execution requires an
explicit bounded adapter and an already-frozen policy version.

The implementation starts from planning PR #1. Review/merge that prerequisite
before this lane PR. No merge, deployment, publication, submission or push to main
was performed.
