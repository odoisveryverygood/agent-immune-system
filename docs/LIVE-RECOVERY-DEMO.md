# Live recovery drill

Choose **Start investigation → Live models / simulated store → Recovery drill — seeded bad policy → Start API run**.

The drill deliberately seeds the starting attack and a broken discount policy. Say this explicitly: "We inject a bad policy to test whether the agents can catch and repair a regression." Do not say AI generated the starting mistake. Subsequent diagnosis, revision, target decisions, Nemotron review, You.com research and OpenShell checkout execution are live.

Watch candidate 1 prevent the original underpricing attack but fail the authorized promotion. Its investigator creates a repair child. That child restores the authorized discount while retaining catalog-derived prices. Candidate 2 must pass the original attack and both normal purchases, then face eight private attacks and independent review. Nothing receives a verified verdict merely for finishing.

## Start locally

Use a Python environment with `backend/requirements.txt` installed and run `npm ci` in `frontend` once. Configure the backend environment file with `CRUSOE_API_KEY`, `YOU_API_KEY`, `IMMUNE_SANDBOX_ID`, `IMMUNE_OPENSHELL_GATEWAY`, and optionally the model IDs. Never put secrets in frontend variables or Git.

```sh
python scripts/run_demo.py --env-file /absolute/path/to/.env.local
```

The UI listens at `http://127.0.0.1:5175`; the backend at `http://127.0.0.1:8011`. Use `--state-path` to restore a previously saved run database. A URL with `?run=RUN_ID` opens the persisted evidence from that same backend. It is historical evidence, not a fresh execution. To execute again, start a new run from the dialog.

The default limit remains 24 model calls, 64 tool calls, depth 2 and 180 seconds. The drill serializes model work. Bounded retries may recover brief HTTP 429 responses; persistent limits, invalid patches, refusals that prevent a baseline, or failed checks remain explicit failures. Do not repeatedly start overlapping runs onstage. Keep the completed evidence available in case the provider is unavailable, and describe it as a previous live run.
