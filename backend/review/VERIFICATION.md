# Person 3 verification

## Automated acceptance

Python 3.12.13 / Pydantic 2.14.1: 37 tests passed using
`python -m unittest discover -s tests/review -v`. These tests use synthetic
fixtures or mocked HTTP, not live model/target execution. The explicit fixture
walkthrough also passed. Application/test code is unchanged by this report.

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
establish their authority or independently endorse their claims. A live Nemotron
review has not consumed these results yet. The full sanitized response is saved
as the local chat deliverable `outputs/you-live-verification.json`; it contains
public result URLs/excerpts, no authentication headers or credential values.

## Still required

The engine teammate must configure host credentials, wire the shared completion
and root I/O adapters, route reviewer calls to supported Nemotron, and preserve
provider receipts/events in an actual run. Target execution, patch application,
frozen held-out evaluation and OpenShell evidence remain with the owning lanes.
