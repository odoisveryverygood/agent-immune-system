from __future__ import annotations

import time
import unittest

from fastapi.testclient import TestClient

from backend.api.app import create_app


class ApiContractTests(unittest.TestCase):
    def test_real_fixture_run_matches_ui_snapshot_and_resumes_after_seq(self):
        with TestClient(create_app(store_path=":memory:")) as client:
            response = client.post("/api/runs", json={
                "target": "shop-demo",
                "goal": "Verify the real API and UI snapshot contract",
                "mode": "fixture",
            })
            self.assertEqual(response.status_code, 201, response.text)
            run_id = response.json()["run_id"]

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                snapshot = client.get(f"/api/runs/{run_id}").json()
                if snapshot["status"] in {"completed", "blocked", "failed", "canceled"}:
                    break
                time.sleep(0.02)
            self.assertEqual(snapshot["status"], "completed", snapshot)

            for field in ("mode", "tasks", "events", "counters", "evidence", "evaluation", "last_seq"):
                self.assertIn(field, snapshot)
            self.assertEqual(snapshot["mode"], "fixture")
            self.assertGreater(snapshot["counters"]["tasks_started"], 1)
            self.assertTrue(snapshot["evidence"])
            self.assertEqual(snapshot["evaluation"]["evaluation_status"], "passed")
            self.assertEqual(snapshot["events"][-1]["type"], "run.completed")
            checkout_event = next(event for event in snapshot["events"] if event["type"] == "tool.observed")
            self.assertIn("receipt", checkout_event["data"])
            self.assertIn("case_id", checkout_event["data"])

            cursor = snapshot["last_seq"] - 1
            resumed = client.get(f"/api/runs/{run_id}/events", params={"after_seq": cursor})
            self.assertEqual(resumed.status_code, 200, resumed.text)
            self.assertIn(f"id: {snapshot['last_seq']}", resumed.text)
            self.assertIn("run.completed", resumed.text)


if __name__ == "__main__":
    unittest.main()
