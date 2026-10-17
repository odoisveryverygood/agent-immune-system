import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from backend.engine.runner import RecursiveRunner, AdvocatePosition
from backend.engine.errors import IntegrationError
from backend.models import Policy, Evaluation


class CouncilTests(unittest.IsolatedAsyncioTestCase):
    def runner(self, customer="challenge", forged=False, security="accept"):
        r = RecursiveRunner.__new__(RecursiveRunner)
        r.run = SimpleNamespace(request=SimpleNamespace(scenario="policy_council"), policies=[Policy()], advocate_positions=[])
        r.root = SimpleNamespace(task_id="root")
        r._require_live_role = lambda *a: None
        r.make_task = lambda *a: SimpleNamespace(task_id=a[2])
        self.payloads = []
        async def generate(ctx, role, model, payload):
            self.payloads.append(payload)
            side = payload["perspective"]
            return AdvocatePosition(verdict=security if side=="security" else customer,
                reason="Observed public receipts support this position.",
                evidence_ids=["invented" if forged else payload["allowed_evidence_ids"][0]],
                constraints={"require_catalog_price": True} if side=="security" else {"max_discount_bps":1000})
        r._json = generate
        async def execute(task, operation):
            return (await operation(SimpleNamespace(task_id=task.task_id, emit=lambda *a: None))).value
        r.execute_task = execute
        return r

    def checks(self):
        return [SimpleNamespace(case_id=i,tool_receipts=[],model_dump=lambda **k: {}) for i in ["attack", "normal", "discount"]]

    async def test_conflict_triggers_investigation_gate(self):
        r=self.runner()
        e=Evaluation(original_replay_passed=True,legitimate={"total":2,"accepted":1,"errors":0})
        r.suite=SimpleNamespace(legitimate=[1,2],expected_legitimate_totals={"normal":50000,"discount":45000})
        self.assertFalse(await r._council(Policy(),e,self.checks()))
        self.assertEqual([p['verdict'] for p in r.council_positions],["accept","challenge"])
        self.assertEqual(self.payloads[0]['allowed_evidence_ids'],['attack'])
        self.assertEqual(self.payloads[1]['allowed_evidence_ids'],['normal','discount'])

    async def test_agreement_allows_final_checks(self):
        r=self.runner(customer="accept")
        r.suite=SimpleNamespace(legitimate=[1,2],expected_legitimate_totals={})
        e=Evaluation(original_replay_passed=True,legitimate={"total":2,"accepted":2,"errors":0})
        self.assertTrue(await r._council(Policy(),e,self.checks()))

    async def test_models_cannot_overrule_failed_numeric_checks(self):
        r=self.runner(customer="accept")
        r.suite=SimpleNamespace(legitimate=[1,2],expected_legitimate_totals={})
        e=Evaluation(original_replay_passed=True,legitimate={"total":2,"accepted":1,"errors":0})
        with self.assertRaises(IntegrationError): await r._council(Policy(),e,self.checks())

    async def test_unknown_evidence_rejected(self):
        r=self.runner(forged=True)
        r.suite=SimpleNamespace(legitimate=[1,2],expected_legitimate_totals={})
        with self.assertRaises(IntegrationError): await r._council(Policy(),Evaluation(),self.checks())

    async def test_revision_must_cite_both_advocates(self):
        from backend.models import PolicyPatch
        r=self.runner()
        r.council_positions=[{'evidence_ids':['attack'],'constraints':{'require_catalog_price':True}}, {'evidence_ids':['discount'],'constraints':{'max_discount_bps':1000}}]
        r.run.patch=None
        r._revision_payload=lambda *a: {'allowed_evidence_ids':['attack','discount']}
        r._json=AsyncMock(return_value=PolicyPatch(based_on_policy_version='candidate',changes={'max_discount_bps':1000},reason='Restore the legitimate promotion.',evidence_ids=['attack']))
        ctx=SimpleNamespace(emit=lambda *a:None)
        with self.assertRaisesRegex(IntegrationError,'revision_missing_advocate_evidence'):
            await r._revise(ctx,Policy(version='candidate',require_catalog_price=True,max_discount_bps=0),[],SimpleNamespace(model_dump=lambda:{}))
        self.assertIsNone(r.run.patch)

    async def test_revision_must_satisfy_security_constraint(self):
        from backend.models import PolicyPatch
        r=self.runner()
        r.council_positions=[{'evidence_ids':['attack'],'constraints':{'require_catalog_price':True,'reject_client_price':True}}, {'evidence_ids':['discount'],'constraints':{'max_discount_bps':1000}}]
        r.run.patch=None
        r._revision_payload=lambda *a: {'allowed_evidence_ids':['attack','discount']}
        r._json=AsyncMock(return_value=PolicyPatch(based_on_policy_version='candidate',changes={'max_discount_bps':1000,'reject_client_price':False},reason='Restore the legitimate promotion.',evidence_ids=['attack','discount']))
        with self.assertRaisesRegex(IntegrationError,'revision_violates_advocate_constraint'):
            await r._revise(SimpleNamespace(emit=lambda *a:None),Policy(version='candidate',require_catalog_price=True,max_discount_bps=0),[],SimpleNamespace(model_dump=lambda:{}))
        self.assertIsNone(r.run.patch)
