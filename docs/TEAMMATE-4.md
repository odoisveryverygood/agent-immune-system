# Person 4 — live UI, held-out evaluation and demo

Branch: `p4/ui-evaluation`. Read AGENTS.md first. Never push main; push this branch and open a PR.

## Own

`frontend/`, `tests/e2e/`, `tests/heldout/`, demo assets and final verification report. Own frontend dependencies; do not edit backend files to work around integration issues.

## Build in order

1. React/TypeScript/Vite app rendering a clearly labeled fixture run from contracts/example-events.jsonl.
2. One screen: start run, actual recursive task tree, selected-node evidence, budget counters and final before/after evaluation.
3. Connect Person 1's SSE API; deduplicate by sequence and restore the snapshot after refresh.
4. Display parent/child spawn reasons and actual status transitions. No simulated tree animation presented as real agent execution.
5. Write held-out attack cases and legitimate full-price/10%-discount purchase cases. Keep their prompt contents outside attack/repair model context.
6. Exercise the assembled app end to end and record live versus fixture/provider/runtime status.
7. Rehearse the 3-minute demo and prepare an accessible 1-minute recording.

## Acceptance

- Starting a run results in actual API events, not a frontend-only animation.
- Root, child and grandchild relationships match backend IDs.
- A budget stop, timeout, cancellation or missing provider configuration remains visible.
- Before/after panels show the same original attack, policy versions and actual tool receipts.
- Evaluation reports held-out totals, violations, errors and legitimate acceptance; missing checks cannot be green.
- UI labels read fixture OR live models / simulated store, with actual sandbox provenance shown separately.

## Handoff

Document frontend commands and API URL configuration. Provide integration tests, actual verification results and a short demo script. Do not publish or submit without explicit owner instruction.

## Copy/paste starting prompt

> Read AGENTS.md and docs/CONTRACT.md. Implement Person 4's lane in docs/TEAMMATE-4.md on p4/ui-evaluation. Use fixture events first to unblock UI, then connect real SSE. Keep held-out prompts out of generation/repair context. Display actual evidence and failures honestly. Do not edit another lane, push main, merge, deploy or submit. Open a PR with executed UI/end-to-end checks.
