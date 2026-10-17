# Person 4 demo rehearsal

This is a UI fixture walkthrough, not a live sponsor demonstration. No provider,
OpenShell execution, successful repair, or real purchase is claimed.

## Three-minute script

- **0:00–0:25** — Start at the mode banner. Explain the simulated $500 laptop,
  trusted $450 minimum, and that this recording uses illustrative fixture evidence.
- **0:25–1:00** — Select root, child, then grandchild. Show actual task IDs, parent
  IDs, depth and spawn reasons. The fixture illustrates nesting; it does not prove
  evidence-driven recursion by the unimplemented engine.
- **1:00–1:35** — Inspect the accepted $0 checkout receipt and violation finding.
  Open the full receipt and original messages. A model saying “success” is insufficient.
- **1:35–2:05** — Open Policy patch: the allowed fields and policy-v1 → policy-v2.
  Show the denied illustrative replay, paired using the original case ID.
- **2:05–2:35** — Show “Incomplete”: zero held-out and legitimate cases ran in
  this walkthrough. The separate evaluator contains eight attacks and two required
  legitimate purchases; its unit tests do not establish target behavior.
- **2:35–3:00** — Open Start investigation. A run sends the real POST request;
  missing backend/provider configuration is an error. Show shared caps and explain
  snapshot recovery and cancellation. End with remaining integration dependencies.

## One-minute browser recording

From `frontend/`, with the development server running on port 5173:

```sh
npx playwright install ffmpeg
node demo/record.mjs
```

Requires installed Chrome (`channel: chrome`). The script records real browser
interactions, adds readable explanatory captions to the capture only, and saves
`demo/walkthrough.webm`. Caption text and timings are in `walkthrough.vtt`.
No test server or model request is needed for this local fixture recording.
Generated video is ignored by Git; the script, captions, and screenshot are reviewable.
