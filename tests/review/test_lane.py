"""Contract and adversarial tests; all provider responses are explicit fixtures."""
import asyncio
import copy
import json
import unittest
from pathlib import Path

from backend.research import research
from backend.review import (ErrorCode, LaneError, ReviewContext, propose_patch,
                            review, review_evaluation, validate_patch)
from backend.review.models import Policy

FIXTURES = Path(__file__).with_name("fixtures")


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


class EngineFixture:
    """Records reservations at the injected shared boundary, no model network."""
    def __init__(self, responses=(), mode="fixture", model=None):
        self.responses = list(responses)
        self.calls = []
        self.mode = mode
        self.model = model or ("fixture-nemotron" if mode == "fixture" else "nvidia/nemotron-test")

    async def complete(self, role, messages, context):
        self.calls.append((role, messages))
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return {"text": json.dumps(value) if not isinstance(value, str) else value,
                "provider": "fixture" if self.mode == "fixture" else "test-transport",
                "model": self.model, "input_tokens": 0, "output_tokens": 0,
                "elapsed_ms": 0, "request_id": "fixture-request"}

    def context(self):
        return ReviewContext(mode=self.mode, complete=self.complete,
                             fixture_research=fixture("research") if self.mode == "fixture" else None)


class LaneTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.policy = fixture("policy")
        self.baseline = fixture("baseline")
        self.research = fixture("research")

    async def assert_code(self, code, awaitable):
        with self.assertRaises(LaneError) as caught:
            await awaitable
        self.assertEqual(caught.exception.code, code)

    async def test_complete_fixture_pipeline_preserves_contract(self):
        engine = EngineFixture([fixture("review"), fixture("patch"), fixture("evaluation-review")])
        ctx = engine.context()
        sources = await research("Investigate the free laptop checkout", ctx)
        decision = await review(self.baseline, self.policy, sources, ctx)
        self.assertEqual(decision["status"], "supported")
        patch = await propose_patch([self.baseline], self.policy, ctx)
        evidence = fixture("evaluation")
        evidence.update(baseline_review=decision, patch=patch)
        result = await review_evaluation(evidence, ctx)
        self.assertTrue(result["repair_verified"])
        self.assertEqual(result["evaluation_status"], "passed")
        self.assertEqual([c[0] for c in engine.calls], ["reviewer", "repair", "reviewer"])
        self.assertEqual(self.policy, fixture("policy"))
        self.assertNotIn("heldout", engine.calls[1][1][1]["content"])
        self.assertNotIn("legitimate_results", engine.calls[1][1][1]["content"])
        self.assertEqual(set(decision), {"status", "reason", "evidence_ids", "proposed_child_goals"})
        self.assertEqual(set(patch), {"patch_id", "based_on_policy_version", "changes", "reason", "evidence_ids"})

    async def test_denied_free_checkout_is_not_a_violation(self):
        engine = EngineFixture()
        self.baseline["tool_receipts"][0]["status"] = "denied"
        self.baseline["oracle"] = {"violation": False}
        output = await review(self.baseline, self.policy, self.research, engine.context())
        self.assertEqual(output["status"], "unsupported")
        self.assertFalse(engine.calls)

    async def test_free_claim_without_receipt_cannot_be_supported(self):
        for violation in (False, True):
            with self.subTest(violation=violation):
                engine = EngineFixture()
                self.baseline["tool_receipts"] = []
                self.baseline["oracle"]["violation"] = violation
                result = await review(self.baseline, self.policy, self.research, engine.context())
                self.assertEqual(result["status"], "inconclusive" if violation else "unsupported")
                self.assertFalse(engine.calls)

    async def test_contradictory_or_missing_evidence_stops_before_model(self):
        variants = []
        for key, value in [("trusted_catalog_total_cents", 1), ("minimum_allowed_total_cents", 0),
                           ("policy_version", "wrong"), ("quantity", 2)]:
            item = copy.deepcopy(self.baseline)
            item["tool_receipts"][0][key] = value
            variants.append(item)
        for oracle in ({"violation": False}, {"violation": True, "expected": 0, "observed": 0},
                       {"violation": True, "rule_id": "floor", "expected": 45000, "observed": 1}):
            variants.append({**self.baseline, "oracle": oracle})
        variants += [{**self.baseline, "error_code": "target_timeout"},
                     {**self.baseline, "tool_receipts": self.baseline["tool_receipts"] * 2}]
        for item in variants:
            with self.subTest(item=item):
                engine = EngineFixture()
                result = await review(item, self.policy, self.research, engine.context())
                self.assertEqual(result["status"], "inconclusive")
                self.assertFalse(engine.calls)

    async def test_strict_receipt_numbers(self):
        for invalid in (False, True, "0", -1, 0.0):
            with self.subTest(invalid=invalid):
                item = copy.deepcopy(self.baseline)
                item["tool_receipts"][0]["charged_total_cents"] = invalid
                await self.assert_code(ErrorCode.INVALID_INPUT, review(item, self.policy, self.research, EngineFixture().context()))

    async def test_invented_citation_and_uncited_child_rejected(self):
        for modify in (lambda d: d.update(evidence_ids=["invented"]),
                       lambda d: d.update(evidence_ids=["fixture:price-validation"]),
                       lambda d: d["proposed_child_goals"][0].update(evidence_ids=["invented"]),
                       lambda d: d["proposed_child_goals"][0].update(evidence_ids=["fixture:price-validation"]),
                       lambda d: d["proposed_child_goals"][0].update(spawn_reason="Investigate more because I say so.")):
            decision = fixture("review")
            modify(decision)
            with self.subTest(decision=decision):
                with self.assertRaises(LaneError):
                    await review(self.baseline, self.policy, self.research, EngineFixture([decision]).context())

    async def test_uncertainty_blocks_approval_and_delegation(self):
        decision = fixture("review")
        decision["uncertainty"] = ["Receipt provenance needs confirmation."]
        result = await review(self.baseline, self.policy, self.research, EngineFixture([decision]).context())
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["proposed_child_goals"], [])
        self.assertIn("provenance", result["reason"])

    async def test_model_disagreement_cannot_erase_proven_numeric_violation(self):
        decision = fixture("review")
        decision.update(status="unsupported", reason="The enforcement switches permit client prices.",
                        proposed_child_goals=[])
        engine = EngineFixture([decision])
        result = await review(self.baseline, self.policy, self.research, engine.context())
        self.assertEqual(result["status"], "inconclusive")
        self.assertIn("Deterministic violation remains proven", result["reason"])
        self.assertEqual(result["proposed_child_goals"], [])
        prompt = engine.calls[0][1][0]["content"]
        self.assertIn("they NEVER authorize a charge below", prompt)

    async def test_invalid_json_and_duplicate_keys_block_verification(self):
        for text in ("not JSON", "```json\n{}\n```", "{}", "[]", '{"status":"supported","status":"unsupported"}',
                     '{"score":NaN}', "[" * 2000, "a" * 32001):
            with self.subTest(text=text[:80]):
                await self.assert_code(ErrorCode.INVALID_MODEL_JSON, review(
                    self.baseline, self.policy, self.research, EngineFixture([text]).context()))

    async def test_timeout_and_cancellation_propagate_without_fallback(self):
        engine = EngineFixture([TimeoutError()])
        await self.assert_code(ErrorCode.PROVIDER_TIMEOUT, review(self.baseline, self.policy, self.research, engine.context()))
        self.assertEqual(len(engine.calls), 1)
        with self.assertRaises(asyncio.CancelledError):
            await propose_patch([self.baseline], self.policy, EngineFixture([asyncio.CancelledError()]).context())
        with self.assertRaisesRegex(RuntimeError, "root exhausted"):
            await propose_patch([self.baseline], self.policy, EngineFixture([RuntimeError("root exhausted")]).context())

    async def test_live_reviewer_requires_nemotron_and_live_research(self):
        live_sources = {**self.research, "mode": "live"}
        engine = EngineFixture([fixture("review")], mode="live", model="some-other-model")
        await self.assert_code(ErrorCode.UNEXPECTED_MODEL, review(self.baseline, self.policy, live_sources, engine.context()))
        await self.assert_code(ErrorCode.INVALID_EVIDENCE, review(self.baseline, self.policy, self.research, engine.context()))

    async def test_research_failure_blocks_review(self):
        for payload in ({**self.research, "sources": []}, {**self.research, "error_code": "provider_timeout"}):
            engine = EngineFixture()
            self.assertEqual((await review(self.baseline, self.policy, payload, engine.context()))["status"], "inconclusive")
            self.assertFalse(engine.calls)

    async def test_research_id_collision_rejected(self):
        for source_id in ("receipt-baseline", "fixture:price-validation"):
            sources = copy.deepcopy(self.research)
            sources["sources"].append({**sources["sources"][0], "source_id": source_id})
            await self.assert_code(ErrorCode.INVALID_EVIDENCE, review(self.baseline, self.policy, sources, EngineFixture().context()))

    async def test_patch_invalid_changes_are_blocked(self):
        for changes in ({}, {"shell": "rm -rf /"}, {"max_discount_bps": True},
                        {"max_discount_bps": 1001}, {"max_discount_bps": -1},
                        {"max_discount_bps": "1000"}, {"reject_client_price": None},
                        {"reject_client_price": False}, {"require_catalog_price": False},
                        {"max_discount_bps": 0}, {"max_discount_bps": 1000}):
            with self.subTest(changes=changes):
                candidate = {**fixture("patch"), "changes": changes}
                with self.assertRaises(LaneError):
                    await propose_patch([self.baseline], self.policy, EngineFixture([candidate]).context())

    async def test_stale_patch_and_invented_failure_reference(self):
        for changes, code in (({"based_on_policy_version": "old"}, ErrorCode.STALE_POLICY),
                              ({"evidence_ids": ["invented"]}, ErrorCode.INVALID_EVIDENCE),
                              ({"evidence_ids": ["receipt-baseline", "receipt-baseline"]}, ErrorCode.INVALID_EVIDENCE)):
            await self.assert_code(code, propose_patch([self.baseline], self.policy, EngineFixture([{**fixture("patch"), **changes}]).context()))

    async def test_validate_again_before_application(self):
        with self.assertRaises(LaneError) as caught:
            validate_patch(fixture("patch"), {**self.policy, "version": "policy-v2"}, {"receipt-baseline"})
        self.assertEqual(caught.exception.code, ErrorCode.STALE_POLICY)
        out = validate_patch(fixture("patch"), Policy.model_validate(self.policy), {"receipt-baseline"})
        self.assertNotIn("max_discount_bps", out["changes"])

    async def test_patch_accepts_only_proven_unique_baseline_failures(self):
        for failures in ([], [self.baseline] * 2, [fixture("evaluation")["replay"]], [{"heldout": "secret"}]):
            with self.subTest(failures=failures):
                engine = EngineFixture()
                with self.assertRaises(LaneError):
                    await propose_patch(failures, self.policy, engine.context())
                self.assertFalse(engine.calls)

    async def test_evaluation_never_trusts_caller_verified_flag(self):
        for field, replacement in (("heldout", {"total": 3, "blocked": 2, "violations": 1, "errors": 0}),
                                   ("heldout", {"total": 3, "blocked": 2, "violations": 0, "errors": 1}),
                                   ("heldout", {"total": 0, "blocked": 0, "violations": 0, "errors": 0}),
                                   ("heldout", {"total": 2, "blocked": 2, "violations": 0, "errors": 0}),
                                   ("legitimate", {"total": 2, "accepted": 1, "errors": 0}),
                                   ("legitimate", {"total": 2, "accepted": 1, "errors": 1}),
                                   ("legitimate", {"total": 1, "accepted": 1, "errors": 0})):
            with self.subTest(field=field, replacement=replacement):
                data = fixture("evaluation")
                data["evaluation"].update(repair_verified=True, evaluation_status="passed")
                data["evaluation"][field] = replacement
                engine = EngineFixture()
                result = await review_evaluation(data, engine.context())
                self.assertFalse(result["repair_verified"])
                self.assertNotEqual(result["evaluation_status"], "passed")
                self.assertFalse(engine.calls)

    async def test_exact_replay_and_immutable_patch_version(self):
        for modify in (lambda d: d["replay_case"]["messages"][0].update(content="different attack"),
                       lambda d: d["replay_case"].update(case_id="different"),
                       lambda d: d["patched_policy"].update(version="policy-v1"),
                       lambda d: d["patched_policy"].update(max_discount_bps=0),
                       lambda d: d["evaluation"]["heldout"].update(total=4),
                       lambda d: d["baseline_review"].update(status="inconclusive"),
                       lambda d: d["replay"]["runtime"].update(mode="openshell")):
            data = fixture("evaluation")
            modify(data)
            with self.subTest(data=data):
                with self.assertRaises(LaneError):
                    await review_evaluation(data, EngineFixture().context())

    async def test_legitimate_receipts_required_not_only_summary(self):
        for modify in (lambda d: d.update(legitimate_results=[]),
                       lambda d: d["legitimate_results"][1]["tool_receipts"][0].update(status="denied"),
                       lambda d: d["legitimate_results"][1]["tool_receipts"][0].update(charged_total_cents=50000)):
            data = fixture("evaluation")
            modify(data)
            result = await review_evaluation(data, EngineFixture().context())
            self.assertFalse(result["repair_verified"])

    async def test_final_model_uncertainty_or_unsupported_blocks_verification(self):
        for update in ({"uncertainty": ["Held-out execution provenance unresolved"]}, {"status": "unsupported"}):
            result = await review_evaluation(fixture("evaluation"), EngineFixture([{**fixture("evaluation-review"), **update}]).context())
            self.assertFalse(result["repair_verified"])

    async def test_final_model_must_cite_each_execution_group(self):
        await self.assert_code(ErrorCode.MISSING_EVIDENCE, review_evaluation(fixture("evaluation"), EngineFixture([
            {**fixture("evaluation-review"), "evidence_ids": ["receipt-baseline"]}]).context()))

    async def test_evaluation_accepts_typed_input_without_materializing_null_changes(self):
        from backend.review.evaluation import EvaluationEvidence
        data = EvaluationEvidence.model_validate(fixture("evaluation"))
        result = await review_evaluation(data, EngineFixture([fixture("evaluation-review")]).context())
        self.assertTrue(result["repair_verified"])

    async def test_no_fixture_research_in_live_context(self):
        with self.assertRaises(LaneError):
            ReviewContext(mode="live", complete=EngineFixture().complete, fixture_research=self.research)


if __name__ == "__main__":
    unittest.main()
