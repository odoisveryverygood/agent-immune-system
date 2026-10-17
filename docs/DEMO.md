# Three-minute demo

1. **0:00–0:20 — Problem.** Our sandbox shopping agent can be manipulated into accepting an invalid price. All orders are simulated; identify whether models and runtime are live.
2. **0:20–1:00 — Evidence-driven recursion.** Start an investigation. Show a task spawning a child and that child spawning a narrower investigation because of evidence. Explain one spawn reason, not every agent name.
3. **1:00–1:30 — Proven failure.** Show the accepted checkout receipt, trusted catalog price 50000 cents, minimum 45000 cents, actual charged amount and deterministic violated rule.
4. **1:30–2:20 — Repair and replay.** Show the constrained patch and exact original attack replay against the new policy. Then show held-out cases and valid purchases.
5. **2:20–3:00 — Result and boundaries.** Explain which attacks were blocked, whether valid purchases still work, resource usage, and what remains unresolved. Point to actual sponsor/runtime evidence.

If the live run fails, show the actual failure and switch explicitly to a recorded or fixture demonstration. Do not silently substitute success. Do not claim guaranteed security, universal self-improvement, live revenue or real payments.

One-minute submission video: the problem, one visible nested delegation, the actual violation, the patch and before/after test results. Confirm current event submission instructions before submitting.
