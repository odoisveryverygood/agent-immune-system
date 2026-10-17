# Person 3 verification

## Automated acceptance

Python 3.12.13 / Pydantic 2.14.1: 38 tests passed using
`python -m unittest discover -s tests/review -v`. These tests use synthetic
fixtures or mocked HTTP, not live model/target execution. The explicit fixture
walkthrough also passed. A later live Nemotron probe exposed a status ambiguity; the prompt and
disagreement gate were clarified and a regression test was added.

## Live You.com research smoke test

- Time: 2026-10-17 20:52:27 UTC (1:52 PM Pacific).
- Code tested: commit `398a5e1`, `backend.research.research()` with `YouClient`.
- Endpoint: `POST https://ydc-index.io/v1/search`.
- Query: `prompt injection shopping agent checkout client supplied price validation trusted catalog discount mitigation`.
- Actual You.com calls: **1**. Actual model calls: **0**. Fixture fallback: **none**.
- Result: **passed**, five source IDs/URLs/titles/excerpt lists retained after
  schema and basic topical validation. Elapsed boundary time: 885 ms.
- The supplied API key was used in process memory only; it is absent from this
  report, repository and saved configuration files.

This verifies live authentication, request/response handling and the research
boundary. It does not verify a complete application run or root engine budget
integration: the smoke test injected an isolated one-call gate with a 30-second
await deadline and 20-second socket timeout. It made no Nemotron/Crusoe calls,
did not execute target attacks or held-out cases, and did not test OpenShell.

The retained sources were about checkout price validation and shopping-agent
prompt injection. They remain untrusted search results; this test does not
establish their authority or independently endorse their claims. A later live Nemotron
review consumed these results together with synthetic target receipts (below). The full sanitized response is saved
as the local chat deliverable `outputs/you-live-verification.json`; it contains
public result URLs/excerpts, no authentication headers or credential values.

## Live Crusoe/Nemotron boundary probes

The earlier supplied key authenticated to `GET /v1/models` on the official
`https://api.inference.crusoecloud.com/v1` endpoint. Thirteen models were listed,
including the exact ID `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B`.

An isolated one-call completion adapter invoked that model through the actual
`review()` function with the retained live You.com research and a clearly labeled
synthetic $0 checkout receipt. The first call completed with 1,939 input and
1,387 output tokens, but returned `unsupported` while describing the numerical
violation. It did not authorize a repair. This result is retained in the local
`outputs/nemotron-live-verification.json` deliverable.

This exposed an ambiguity between supporting the baseline finding and approving
the attack. The prompt now defines that distinction and explains that disabled
enforcement switches never authorize undercharging. A model rejection of a
deterministically proven finding is now explicitly `inconclusive`, preserving
the proven violation and blocking repair verification. A regression test covers
this disagreement.

The follow-up probe on the clarified prompt passed: Nemotron returned
`supported`, cited `receipt-baseline`, and proposed one child goal with that
receipt in its spawn reason. It used 2,051 input / 1,176 output tokens in
26,873 ms. The full sanitized result is the local deliverable
`outputs/nemotron-live-verification-2.json`. Across these separate probes there
were two actual model calls; neither executed a target or held-out evaluation.
The probe adapters were temporary, bounded test inputs to the lane API. No
Person 1 provider, engine, shared model or dependency files were changed.

## Still required

The engine teammate must configure host credentials, wire the shared completion
and root I/O adapters, route reviewer calls to supported Nemotron, and preserve
provider receipts/events in an actual run. Target execution, patch application,
frozen held-out evaluation and OpenShell evidence remain with the owning lanes.
