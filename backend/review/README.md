# Person 3 handoff

Implemented lane-local review, constrained repair, one-query research and final
evaluation review. This is a library boundary ready for engine integration;
the planning branch has no engine, target executor, API or UI to wire into yet.
No live sponsor calls or OpenShell enforcement have been verified by this lane.

## Run locally

Python 3.11+ and Pydantic 2 are required. **Person 1 owns the backend manifest**;
this lane deliberately does not create or edit it. Please include `pydantic>=2,<3`
in that manifest. No new HTTP client/test dependencies are required.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install 'pydantic>=2,<3'
.venv/bin/python -m unittest discover -s tests/review -v
.venv/bin/python -m backend.review.fixture_demo --fixtures tests/review/fixtures
```

The walkthrough is synthetic: canned model text, receipts, source excerpts and
held-out counters exercise the boundary. It does **not** execute attacks, run
held-out tests, enforce a sandbox, query You.com or invoke Nemotron. Its output
explicitly marks these limits. Research fixture URLs use `example.com` and are
not asserted to be real supporting sources.

## Engine adapter

Imports:

```python
from backend.research import research
from backend.review import (
    ReviewContext, LaneError, review, propose_patch,
    validate_patch, review_evaluation,
)
from backend.providers.you import YouClient
```

Public functions match `docs/CONTRACT.md` and return dictionaries. The optional
`review_evaluation(evidence, run_context)` consumes the `EvaluationEvidence`
schema in `evaluation.py` and returns the contract's evaluation envelope.
Lane models in `models.py` are strict Pydantic adapters, not replacements for
Person 1's shared models. Pass dictionaries or Pydantic objects with these wire
fields. The policy adapter uses `version` plus the three policy keys. The
violation oracle adapter expects numeric `expected=minimum_cents` and
`observed=charged_cents`, together with a nonempty `rule_id` for a violation.
Coordinate alternate shared representations before changing callers.

Construct a context once per root using closures bound to the **actual** engine
root context (names below denote engine methods to implement, not provided APIs):

```python
async def shared_complete(role, messages, _lane_context):
    # Engine reserves an atomic root model call; enforces cancellation,
    # deadline/concurrency/timeout; persists a sanitized completion receipt.
    return await engine.complete(role, messages, root_context)

async def shared_research_call(request):
    # Engine reserves root I/O BEFORE dispatch, checks root cancellation and
    # deadline, bounds the await, persists provenance and accounts for failure.
    return await engine.run_research_io(request, root_context)

context = ReviewContext(
    mode="live",
    complete=shared_complete,
    research_call=shared_research_call,
    you_client=YouClient(api_key=host_config.you_api_key),
)
sources = await research(task.goal, context)
decision = await review(target_result, trusted_policy, sources, context)
if decision["status"] == "supported":
    proposal = await propose_patch([target_result], trusted_policy, context)
```

There is no second scheduler or independent model transport. Model roles are
`reviewer` and `repair`; Person 1 must route `reviewer` to configured Nemotron and
return the actual `provider`/`model` metadata. Live reviews reject non-Nemotron
metadata or fixture labels. This check verifies reported identity, not vendor
attestation. Fixture mode requires a provider labeled `fixture` and an explicit
`fixture_research` payload. Live errors never load fixtures. There are no retries.

One call to `research()` makes at most one You.com request. The fixed query is
scoped to the sole checkout scenario; arbitrary agent goals cannot inject search
operators. Sources preserve URLs, titles and exact bounded snippets. A basic
topical filter rejects unrelated results; it does not establish source authority
or resistance to prompt injection. Research stays in an untrusted JSON message.
Nemotron must independently assess its relevance. Keys are constructor inputs,
never serialized; no environment file is read or printed by this lane.

The standard-library HTTPS transport uses POST, a fixed HTTPS endpoint, disabled
redirects, a finite socket timeout and a 1 MiB response cap. See the checked
[You.com API reference](https://you.com/docs/api-reference/search/v1-search).
It runs in a worker thread; canceling its await cannot kill an in-flight socket.
The root must retain/account for that reservation until the bounded I/O finishes.
It must not report cancellation as complete while this work is unaccounted for.

## Evidence and patch rules

Only trusted **target-boundary** AttackResults belong in these APIs. Never
construct them from generated text or let an agent populate oracle/receipt
fields. Schema validation cannot authenticate provenance. The deterministic
check recomputes integer-cent minima from the policy and contract's $500 laptop,
including quantity. Denied checkouts and claims without receipts are unsupported;
missing or contradictory evidence is inconclusive. Unsupported numeric types,
duplicate receipts, wrong versions and inconsistent oracle values cannot pass.

Model output must be plain JSON with exact keys; markdown fences, duplicate JSON
keys, missing uncertainty, invented evidence, uncited child goals and stale
patches block verification. A child goal needs a violating receipt reference in
both its evidence list and spawn reason; only the engine schedules it. Any stated
model uncertainty makes review inconclusive and suppresses delegation.

`propose_patch()` accepts baseline AttackResults only. Held-out prompts, expected
outputs and summaries are not accepted or sent to repair. A proposal must cite
a proven violating receipt and make a real change. Unknown keys, nulls, coerced
booleans/integers, commands and stale versions are rejected. Additional local
constraints preserve safeguards and the authorized 10% path: boolean changes can
only enable protection and `max_discount_bps` must remain at its existing value.
The schema still enforces the shared 0..1000 range.

Immediately before application, call `validate_patch(proposal, current_policy,
proven_violating_receipt_ids)`. The target/engine must atomically compare the
version, create a new immutable policy version and freeze the patch. This lane
does not apply policies, issue tools or run arbitrary generated code.

## Final evaluation review

After the patch is frozen, the engine supplies:

- Original and replay cases with the exact same case ID, messages and origin ID;
  baseline/replay AttackResults and their trusted policies.
- The validated baseline review, frozen patch and resulting immutable policy.
- Trusted held-out aggregate counters bound to that frozen version and the
  **predeclared** expected total; at least one held-out case is required.
- Exactly two legitimate AttackResults, ordered full-price ($500) then authorized
  10%-discount ($450), with distinct accepted receipts on the patched runtime.

`review_evaluation()` recomputes the baseline finding, patch/version, replay and
legitimate gates. It checks counter consistency, case coverage, actual receipts
and runtime identity. It ignores incoming `repair_verified`/status claims. Any
deterministic violation/regression prevents success; missing cases and errors
remain incomplete. Only after these gates pass does it spend one shared Nemotron
review call on the baseline, patch, replay, aggregate summary and legitimate
receipts. That reviewer must cite all execution groups with no uncertainty.
It never sees held-out prompts or expected answers.

The engine still owns held-out execution/provenance, exact replay input capture,
persisting every completion receipt and review event, evaluation manifest
freezing, and root limits. A forged engine summary cannot be authenticated by
this library; callers must not accept such summaries from agent/model text.

## Errors and integration status

`LaneError.code` is a sanitized `ErrorCode`; do not log raw provider bodies or
keys. Timeouts, JSON errors, missing configuration/evidence and stale policy
versions stay explicit. Root budget/cancellation exceptions propagate unchanged
so the engine can account for them. Missing/contradictory target evidence yields
a wire-compatible inconclusive review; the engine should emit `review.completed`
and block verification. Persist typed failures with the relevant task failure or
run-blocked event rather than inventing a successful completion event.

Local acceptance: tests use fixtures and mocked HTTP only. Live You.com,
Crusoe/Nemotron responses, full engine/target integration and OpenShell remain
unverified. The current shell did not have `YOU_API_KEY`, `CRUSOE_API_KEY` or
`NEMOTRON_MODEL` configured; no credential values were inspected or recorded.
The implementation branch starts from planning PR #1; merge that planning PR
before this implementation PR after human review. No direct main push or merge.
