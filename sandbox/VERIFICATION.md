# Teammate 2 verification — October 17, 2026

Implemented locally on `p2/sandbox-target`, based on PR #1's planning branch.
No push, merge, deployment, provider call, or edit to another teammate's lane.

## Verified outcomes

| Check | Actual result |
|---|---|
| Target unit/integration suite | 35 tests passed using Python 3.12.13 |
| Local fixture acceptance | All 8 checkout operations passed; explicitly unisolated |
| OpenShell acceptance | All 8 operations passed inside the dedicated sandbox |
| Baseline | Actual simulated accepted receipt for 0 cents; oracle violation |
| Frozen repair replay | Identical case digest/messages; client price denied |
| Legitimate full price | Accepted 50000 cents |
| Legitimate `SAVE10` | Accepted 45000 cents |
| Public price regressions | Client prices 1, 44999, 45000, 50000 all denied |
| Filesystem positive control | `/sandbox` write/read/delete succeeded |
| Filesystem negative test | World-readable `/opt/immune-canary/blocked.txt` read denied, errno 13 |
| Canary outside OpenShell | Same image/user reads `public-negative-test-canary` successfully |
| Network negative test | Python HTTPS request to `example.com:443` rejected by OPA |
| Runtime enforcement | Landlock hard requirement; 9 rules applied, 0 skipped |
| Evidence integrity | All 8 OpenShell ledger entries and retained head verified |

The network probe alone labels the tunnel's 403 error **inconclusive**. The
separate OpenShell log resolves it: `NET:OPEN ... DENIED ... example.com:443`
with `engine:opa` and `reason:network connections not allowed by policy`.
No provider credentials were attached (`--no-auto-providers`, no `--provider`).

Actual OpenShell sandbox UUID: `6fd690fe-bdc1-46ed-8861-4263e9a47eea`.
Effective-policy response digest during acceptance:
`b25e498d46e13530f3026d89d71162ca5895af14b0d2a4defbf091a584e73a66`.
These identify this run, not a promise that the sandbox remains running forever.

## Evidence

- [OpenShell acceptance and original/replay receipts](evidence/openshell-acceptance.json)
- [Exact cases, policy snapshots and hash chain](evidence/openshell-receipts.jsonl)
- [Local acceptance](evidence/local-acceptance.json)
- [Actual effective OpenShell policy](evidence/runtime-policy.json)
- [Actual sandbox metadata](evidence/sandbox.json)
- [Negative probe output](evidence/probe.json)
- [OpenShell enforcement log excerpts](evidence/enforcement.log)
- [Built image ID](evidence/image-id.txt)
- [Full test output](evidence/unit-tests.txt)
- [Artifact and source SHA-256 manifest](evidence/manifest.json)

## Setup failures found and resolved

1. The host's default Docker context differed from the gateway's. Build directly
   in `colima-nemoclaw`; otherwise the gateway cannot find the local target image.
2. The slim Python image lacked `iproute2`; installing it enabled network namespace
   creation. `nftables` was added to avoid degraded bypass detection.
3. `/lib64` does not exist in this arm64 image. Removing that nonexistent path
   allowed the hard-requirement Landlock policy to apply with zero skipped rules.
4. OpenShell 0.0.116 rejects `--output json` with a trailing create command. Fetch
   sandbox/policy JSON separately. All failed sandboxes belonged to this lane
   and were deleted before retrying; unrelated sandboxes were left alone.

## Scope limits

The model adapter was checked with deterministic fixtures and injected test
transports. No live Crusoe, Nemotron or You.com calls were made. Provider
integration, recursive-engine wiring, reviewer validation, UI integration and
private held-out evaluation remain with their owners. The demo does not set or
claim project-level `repair_verified`.

This proves the tested filesystem/network denials and actual sandbox checkout
execution. It is not a general sandbox escape audit. Policy versions are immutable
within a run's in-memory registry; the host ledger stores policy snapshots for the
engine to persist/recover. Timeouts/cancellation during remote dispatch must remain
incomplete until reconciled, with no blind retry. No real payment/order system
exists or is contacted.
