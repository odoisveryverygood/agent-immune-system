# Investigation lab — Person 4

React 19 / TypeScript / Vite UI for Agent Immune System. This lane implements the
browser client and isolated evaluation tooling. The backend and sponsor integrations
are owned by other teammates and are not present or verified on this branch.

## Run

Use Node 22.12+ (verified locally with Node 25.4.0):

```sh
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The initial local walkthrough imports the three shared
`contracts/example-events.jsonl` events verbatim, then appends explicitly illustrative
receipt, policy, replay and incomplete-evaluation events. No requests or model calls
are required to inspect it. No frontend animation impersonates execution.

`Start investigation` opens the run form. **Start API run** always sends an actual
POST, including in API fixture mode. It never substitutes the local walkthrough
when the API fails. The local fixture is a separate, explicit action.

```sh
# Development: proxy same-origin /api to Person 1's backend.
API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev

# Optional separate API origin, baked into the bundle at build time.
VITE_API_URL=http://127.0.0.1:8000 npm run build
npm run preview
```

`VITE_API_URL` is public configuration, never a credential. Do not put provider keys
in any `VITE_` variable. Cross-origin API origins must allow the browser origin;
EventSource uses no authorization headers. This preview does not implement auth.

## API integration handoff

The shared run creation/cancellation/event contracts are unchanged. The client uses:

- `POST /api/runs` with the exact goal, target, selected mode, seed and shared caps.
- `GET /api/runs/{id}` before every stream connection and after refresh.
- `GET /api/runs/{id}/events?after_seq=N`, one JSON envelope per unnamed SSE message.
- `POST /api/runs/{id}/cancel`, then snapshot confirmation. The POST alone does not
  change the display to canceled.

Only a run ID is saved under versioned localStorage key `ais.active-run.v1`. No
prompts, receipts or keys are saved in browser storage. A disconnected stream stops
and exposes **Reconnect**; reconnect restores a snapshot before resuming. Duplicate
sequences are ignored; missing sequences and wrong-run events stop consumption.

**Proposed snapshot/event payload adapter, pending Person 1 coordination:** the
shared contract does not yet name snapshot fields or the resume parameter. The UI
requires this representation and fails visibly for incompatible snapshots. Confirm
these field names before integrating; do not change another lane to match silently.

```json
{
  "run_id": "example",
  "mode": "live",
  "status": "running",
  "last_seq": 4,
  "tasks": [],
  "counters": {"model_calls": 2, "tool_calls": 1, "elapsed_seconds": 7},
  "evidence": [],
  "events": [],
  "runtime": {"mode": "openshell", "sandbox_id": "actual-id", "policy_digest": "actual-digest"}
}
```

Tasks follow the shared Task shape. Counters may include `max_model_calls`,
`max_tool_calls`, `max_depth`, `max_concurrency`, `elapsed_seconds` and
`deadline_seconds`. Missing usage stays “—”; displayed default caps match the POST.
Optional `patch` and `evaluation` follow their shared boundary shapes. Optional
`events` are persisted envelopes through `last_seq`; they let the stream inspector
show history after refresh. Tasks must have valid parents/depths and no cycles.

For streamed data, `task.created.data` contains task fields; `tool.observed.data`
contains the receipt itself (with `case_id` and exact original `messages` when
available); `violation.found.data` contains the oracle finding and receipt ID;
`patch.*.data` contains the patch/version fields; `evaluation.completed.data`
contains the shared evaluation result. Any event can carry `data.counters` and
`data.runtime`. Terminal event data contains typed errors/reasons shown in a visible
stop banner and in the event inspector. Alternative nested receipt shapes need an
explicit adapter here, not backend edits by Person 4.

Before/after receipts pair only when the baseline is an accepted below-minimum
receipt, the case IDs match and policy versions differ. This visual pairing does
not independently establish byte-identical replay; the isolated evaluator hashes
and reuses exact messages. Missing case IDs leave the replay panel pending.

## Verification

```sh
npm run build
npm test
# Browser tests use installed Chrome; no model credentials or Python backend needed.
npm run test:e2e
# From repository root:
python3 -m unittest discover -s tests/heldout -v
```

The E2E suite runs a separate local HTTP/SSE contract fixture on 8788 and Vite on
5174. These tests establish browser transport and failure handling against a test
server, not engine/provider/runtime behavior. Ports must be free. Chrome must be
installed; change `channel` in the test config if using installed Playwright Chromium.

Held-out prompts live only in `tests/heldout/`, outside frontend imports and public
assets. See that directory's README for the isolated adapter runner. UI source and
production bundle must not contain held-out prompt text.

See [demo rehearsal](demo/README.md), [caption track](demo/walkthrough.vtt), and
[verification report](demo/VERIFICATION.md). No deployment, merge, publication or
hackathon submission is performed by this lane.
