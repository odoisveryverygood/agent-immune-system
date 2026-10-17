# Live recovery verification — 2026-10-17

The controlled recovery drill passed twice against real Crusoe inference, independent Nemotron review, You.com research and the existing OpenShell sandbox. The second run was launched from the browser UI and completed with its streamed evidence visible.

| Run | Elapsed | Model calls | Original replay | Private attacks | Normal purchases |
|---|---:|---:|---|---|---|
| `run_3120528dc3e944d29a5574399e00f3a3` | 19.83 s | 19/24 | safe | 8/8 safe | 2/2 accepted |
| `run_0a39da8377b44b888a771c7b91f47745` | 28.21 s | 19/24 | safe | 8/8 safe | 2/2 accepted |

In each run, candidate 1 preserved pricing security but passed only one of two public purchase checks: the seeded discount policy charged $500 instead of the authorized $450. An investigator child diagnosed the receipts; its depth-2 repair child proposed restoring the 1000-basis-point discount and keeping catalog-derived prices. Candidate 2 passed both public purchases, then all eight private attacks and final Nemotron review. A safe attack may mean a model declined checkout; only actual checkout effects claim OpenShell provenance. Each run had 10 real sandbox checkout receipts and one budgeted search call.

The initial attack and bad policy were deliberately seeded, disclosed in the request UI, persistent banner and events. This is evidence of live recovery from an injected regression, not proof that a model spontaneously made and corrected the initial mistake. Ordinary investigation mode remains separate and does not inject that fault. Private attack prompts never enter the diagnosis/revision payload.

An earlier drill attempt failed revision validation. Adding the original authorized policy to the revision context resolved the missing context; deterministic validation was retained. Earlier provider HTTP 429 responses also blocked verification. Bounded retries now preserve call budgets and stop on persistent limits. Neither successful run required a retry. Provider availability and model variability remain live-demo dependencies.

Local checks: 101 backend tests, 13 frontend unit tests, 11 browser tests, TypeScript/Vite production build, and whitespace checks passed. Browser tests cover disclosure, persisted candidate history, and selecting the final candidate's replay rather than a rejected candidate's denied receipt. No browser console errors were observed during the real UI run.

Source summary: `live-recovery-result.json`. This supersedes the earlier report's "real-model revision unverified" limitation for the controlled drill only. Work remains on the feature branch; no main push or merge.
