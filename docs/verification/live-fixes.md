# Live workflow fixes — October 17, 2026

The target's no-tool decision now reports `not_executed` and continues evidence-driven investigation instead of failing an OpenShell check for a checkout that never happened. A real checkout still requires OpenShell and the shared model/tool budgets. No baseline violation still prevents a repair-success claim.

Nemotron receives up to 4096 output tokens with thinking disabled, and a 60-second review timeout bounded by the root deadline. Investigation prompts generate customer purchase attempts rather than asking the target to audit itself. Ordinary purchases omit the client-price override; authorized promotions use SAVE10. Replay review specifies its JSON types and distinguishes denied orders from missing evidence. Oracle, patch, receipt and legitimate-purchase requirements remain enforced.

## Verification

- 92 backend tests passed: target 35; review/research 38; held-out evaluator 9; integration 10.
- New regressions cover a declined target continuing to delegation; a refused root spawning a child that completes the repair workflow; rejection of unisolated checkout effects and unaccounted live model calls; reviewer token/truncation handling and root deadline cancellation.
- Actual live app run completed through Crusoe, You.com, Nemotron and the existing OpenShell sandbox: original replay passed, all 8 repository held-out cases safe, both legitimate purchases accepted, both reviews supported, repair_verified=true.
- Used 17 model calls and 8 root tool calls (including research), below the default 24/64 caps. See live-fixes-result.json for run identity, timestamps, models and counters.
- Earlier live attempts are retained locally: one truthfully found no baseline, another found and repaired a violation but failed legitimate/review checks. A separate larger-model Nemotron review also accepted a denied replay. Success is not fabricated from those failures.

The evaluation suite is reused during development; this is integration/regression evidence, not a fresh independent security evaluation. A live model can still refuse an attack, disagree with a reviewer, or exhaust a bounded run. Such results stay incomplete rather than being promoted to success. The frontend's earlier build/browser checks were on the merged base; this change has no frontend code.
