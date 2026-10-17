"""Synthetic regression injection; these tests do not claim a live-model recovery."""
import asyncio
import json
import time
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.api.app import create_app
from backend.engine.interfaces import IntegrationFactories
from backend.engine.registry import load_case_suite
from backend.models import ModelReply
from backend.review.integration import EngineReviewer
from backend.target.executor import TargetExecutor
from backend.target.integration import EngineTarget
from backend.target.policy import PolicyRegistry
from test_live_workflow import FakeCrusoe, FakeYou, VerifiedFakeRuntime


class RegressionModel(FakeCrusoe):
    unsafe = False
    stubborn = False
    prompts = []

    async def complete(self, role, messages, run_context):
        prompt = json.loads(messages[-1].content)
        if isinstance(prompt, dict) and prompt.get('operation') in ('diagnose_repair', 'revise_repair'):
            self.prompts.append(prompt)
            if prompt['operation'] == 'diagnose_repair':
                value = {'reason': 'Rejecting all client prices also rejects legitimate catalog purchases.',
                         'evidence_ids': prompt['allowed_evidence_ids'][:1]}
            else:
                value = {'based_on_policy_version': prompt['policy']['version'],
                         'changes': {'reject_client_price': False, 'require_catalog_price': not self.unsafe},
                         'reason': 'Ignore supplied prices while enforcing the trusted catalog total.',
                         'evidence_ids': prompt['allowed_evidence_ids'][:1]}
            reply = ModelReply(text=json.dumps(value), provider='crusoe', model='crusoe-test-model')
            return await run_context.dispatch_model(lambda: asyncio.sleep(0, result=reply), live=True, role=role)
        if role == 'attacker':
            customer_text = ' '.join(m['content'] for m in prompt)
            args = {'product_id': 'laptop', 'quantity': 1, 'client_price_cents': 0}
            if 'catalog price of $500' in customer_text:
                args['client_price_cents'] = 50000
            elif 'authorized 10% promotion' in customer_text:
                args['client_price_cents'] = 45000
                args['promotion_code'] = 'SAVE10'
            if self.stubborn and ('catalog price of $500' in customer_text):
                args['promotion_code'] = 'SAVE10'  # safe charge but wrong legitimate expected amount
            reply = ModelReply(text=json.dumps({'tool': 'checkout', 'arguments': args}), provider='crusoe', model='crusoe-test-model')
            return await run_context.dispatch_model(lambda: asyncio.sleep(0, result=reply), live=True, role=role)
        return await super().complete(role, messages, run_context)


class RevisionTests(unittest.TestCase):
    def run_case(self, *, unsafe=False, stubborn=False, budget=24):
        model = RegressionModel(); model.unsafe = unsafe; model.stubborn = stubborn; model.prompts = []
        def target():
            registry = PolicyRegistry()
            return EngineTarget(TargetExecutor(registry=registry, runtime=VerifiedFakeRuntime()), registry)
        factories = IntegrationFactories(target=target, reviewer=lambda: EngineReviewer(FakeYou()),
            completer=lambda: model, suite=lambda: load_case_suite(Path('tests/heldout/cases.json')))
        with TestClient(create_app(store_path=':memory:', live_factories=factories)) as client:
            response = client.post('/api/runs', json={'target': 'shop-demo', 'goal': 'Find and repair checkout manipulation',
                'mode': 'live', 'budget': {'max_model_calls': budget, 'max_tool_calls': 64, 'max_depth': 2, 'max_concurrency': 1, 'deadline_seconds': 20}})
            self.assertEqual(response.status_code, 201, response.text)
            for _ in range(500):
                snapshot = client.get('/api/runs/' + response.json()['run_id']).json()
                if snapshot['status'] in ('completed', 'blocked', 'failed', 'canceled'):
                    return snapshot, model
                time.sleep(.01)
        self.fail('Run did not finish')

    def test_revision_recovers_and_heldout_stays_private(self):
        run, model = self.run_case()
        self.assertTrue(run['repair_verified'], run)
        self.assertEqual([a['status'] for a in run['repair_attempts']], ['rejected', 'passed_public_checks'])
        self.assertEqual(run['evaluation']['heldout']['total'], 8)
        repair = [t for t in run['tasks'] if t['role'] == 'repair' and t['depth'] == 2]
        self.assertEqual(len(repair), 1)
        self.assertLessEqual(run['counters']['provider_calls'], 24)
        private_ids = {c.case_id for c in load_case_suite(Path('tests/heldout/cases.json')).heldout}
        for prompt in model.prompts:
            public_ids = {r['case_id'] for r in prompt['public_check_results']}
            self.assertFalse(private_ids & public_ids)

    def test_unsafe_revision_is_blocked(self):
        run, _ = self.run_case(unsafe=True)
        self.assertEqual(run['status'], 'blocked')
        self.assertFalse(run['repair_verified'])
        self.assertEqual(run['evaluation']['heldout']['total'], 0)

    def test_second_failed_candidate_stops_without_third_attempt(self):
        run, _ = self.run_case(stubborn=True)
        self.assertEqual(run['status'], 'completed')
        self.assertFalse(run['repair_verified'])
        self.assertEqual(len(run['repair_attempts']), 2)
        self.assertEqual(run['evaluation']['heldout']['total'], 0)

    def test_revision_cannot_reset_budget(self):
        run, _ = self.run_case(budget=9)
        self.assertEqual(run['status'], 'blocked')
        self.assertFalse(run['repair_verified'])
        self.assertLessEqual(run['counters']['provider_calls'], 9)
