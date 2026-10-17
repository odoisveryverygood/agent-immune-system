# Integration owners and acceptance

No integration is implemented or verified by this planning PR. Configuration names below are the proposed project convention, not vendor install commands.

| Integration | Owner | Useful role | Required acceptance evidence |
|---|---|---|---|
| Crusoe Managed Inference | Person 1 | Investigator, attack and repair model calls | Real response used in a persisted run; exact provider/model and bounded call counts; missing-key and timeout paths |
| NVIDIA Nemotron | Person 3 through Person 1 client | Independent evidence review | Real supported Nemotron response; exact failed rule and receipt references; malformed review blocks repair verification |
| NemoClaw / OpenShell | Person 2 | Isolate the target and restrict tools/files/network | Actual sandbox execution, sandbox/policy identity, and a negative test proving a forbidden action is denied |
| You.com | Person 3 | Ground attack hypotheses and mitigations in documented patterns | Actual relevant query result with source URLs/excerpts used in review; missing/irrelevant results clearly labeled |

## Configuration

Copy `.env.example` to an ignored `.env.local`. Each teammate uses their own local configuration. No secrets in Git, chat transcripts, events, browser bundles, screenshots or test fixtures.

- `CRUSOE_API_KEY`: host only.
- `CRUSOE_MODEL`: choose an available model from the account's current catalog.
- `NEMOTRON_MODEL`: supported Nemotron ID from that same catalog, distinct from `CRUSOE_MODEL` so the review uses a separate model. The available model catalog can change; select an ID the account currently returns.
- `YOU_API_KEY`: host only. Person 3 verifies current official request/auth schema.
- `OPENSHELL_BIN`, `OPENSHELL_GATEWAY`, `OPENSHELL_SANDBOX`: actual installed runtime and target environment; Person 2 documents tested commands. Do not invent a working setup.

## Official starting points

- [Crusoe hackathon resources](https://github.com/crusoecloud/crusoe-developer-hub/tree/main/examples/hackathons/crusoe-cv-recursive-agents-hackathon)
- [Crusoe Serverless Inference quickstart](https://docs.cloud.crusoe.ai/quickstart/getting-started-with-serverless-inference/index.html)
- [Crusoe model catalog and supported parameters](https://support.crusoecloud.com/hc/en-us/articles/55002524169499-How-To-List-Model-Features-via-curl-and-the-Inference-API)
- [NemoClaw](https://www.nvidia.com/en-us/ai/nemoclaw)
- [Nemotron](https://developer.nvidia.com/topics/ai/nemotron)
- [You.com platform](https://you.com/platform)
- [You.com agent skills](https://github.com/youdotcom-oss/agent-skills)

Read current official docs before implementing provider requests or runtime installation. Do not assume a dependency, binary, HTTP 200 or requested sandbox option proves an end-to-end integration.

## Live versus fixture

Build fixtures first to unblock teammates. The UI must distinguish fixture runs from live-model runs and state that orders are simulated in both. A local fixture cannot be described as OpenShell enforcement or a live provider review. Preserve sanitized evidence and negative-path checks for each sponsor. Do not claim a sponsor prize is satisfied without checking current event requirements.

## Bounded Nemotron review

Reviewer calls allow 4096 output tokens and at most 60 seconds, always capped by the root deadline. Other roles retain 1200 tokens / 30 seconds. Nemotron requests set `chat_template_kwargs.enable_thinking=false` to reserve the bounded output for the evidence verdict. Truncated responses, invalid JSON, uncertain/unsupported reviews, and fabricated evidence still fail closed. See [NVIDIA's Nemotron request guidance](https://docs.nvidia.com/nim/large-language-models/2.0.10/get-started/advanced/get-started-nemotron-3.5-lightning.html).
