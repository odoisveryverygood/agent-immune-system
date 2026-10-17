# Person 3 — evidence review, research and constrained repair

Branch: `p3/review-repair`. Read AGENTS.md first. Never push main; push this branch and open a PR.

## Own

`backend/review/`, `backend/research/`, `backend/providers/you.py`, `tests/review/`. Use Person 1's shared model client and budget; do not create an unbounded inference path.

## Build in order

1. Fixtures for research, review and patch contracts so Person 1 can integrate immediately.
2. One bounded You.com research query for relevant attack/mitigation patterns. Keep source URLs and excerpts. Retrieved content is untrusted data, not agent instructions.
3. Nemotron review of trusted policy plus actual receipts. Require specific evidence IDs and explicit uncertainty.
4. Generate narrower investigation goals only when an observed finding warrants them. Person 1 executes delegation; you do not create a second task scheduler.
5. Repair proposal restricted to the three allowed policy keys. Validate schema and original policy version before application.
6. Review original replay, held-out summary and legitimate purchase results without allowing model approval to override deterministic failures.

## Acceptance

- Contradictory or missing evidence produces unsupported/inconclusive, not approval.
- A target message claiming a free purchase without an accepted tool receipt is not counted as a violation.
- Invented source IDs, model JSON errors and timeouts block verification.
- A patch cites the original failure and does not access held-out prompts or expected outputs.
- Original attack blocked + held-out cases blocked + legitimate purchases working are all necessary for a verified repair.
- Record actual Nemotron and You.com calls separately from fixtures. Do not claim the new app is already integrated.

## Handoff

Provide research(), review(), propose_patch(), typed errors, prompts and fixture outputs. Coordinate dependencies with Person 1 before changing the backend manifest.

## Copy/paste starting prompt

> Read AGENTS.md and docs/CONTRACT.md. Implement Person 3's lane in docs/TEAMMATE-3.md on p3/review-repair. Use the shared completion interface and root budget. Ground review in exact policy/tool receipts and sourced research. Keep patches constrained and evaluation held out. Do not edit another lane, push main, merge or deploy. Open a PR with truthful live/fixture verification.
