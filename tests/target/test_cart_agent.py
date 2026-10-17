import unittest
from types import SimpleNamespace
from backend.target.cart_agent import CartPlannerAgent
from backend.target.policy import TargetError
from backend.models import RunRequest


class FakeContext:
    def __init__(self, text):
        self.text, self.calls = text, 0
    async def complete(self, role, messages):
        self.calls += 1
        assert role == "attacker"
        assert messages[0].role == "system"
        return SimpleNamespace(text=self.text, model="test-model")


class CartAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_cart_translation_preserves_requested_price_and_coupon(self):
        ctx = FakeContext('{"action":"purchase","coupon":"SAVE10","requested_price_cents":0}')
        args, model = await CartPlannerAgent().decide([{"role":"user","content":"test"}],ctx)
        self.assertEqual(args, {"product_id":"laptop","quantity":1,"promotion_code":"SAVE10","client_price_cents":0})
        self.assertEqual(ctx.calls,1)
        self.assertEqual(model,"test-model")

    async def test_normal_cart_uses_store_price(self):
        args, _ = await CartPlannerAgent().decide([],FakeContext('{"action":"purchase"}'))
        self.assertNotIn("client_price_cents", args)

    async def test_decline_has_no_checkout(self):
        args, _ = await CartPlannerAgent().decide([],FakeContext('{"action":"decline"}'))
        self.assertIsNone(args)

    async def test_malformed_cart_is_not_executed(self):
        for text in ['{"action":"purchase","quantity":true}', '{"action":"purchase","action":"decline"}', '{"action":"purchase","unknown":1}', 'not json']:
            with self.assertRaises(TargetError):
                await CartPlannerAgent().decide([],FakeContext(text))

    def test_second_agent_cannot_silently_use_fixture(self):
        with self.assertRaises(ValueError):
            RunRequest(target="cart-planner", mode="fixture", goal="test")
