import unittest
import httpx
from unittest.mock import AsyncMock, patch
from backend.models import Run, RunRequest, Message
from backend.providers.crusoe import CrusoeClient
from backend.engine.budget import RootBudget
from backend.engine.context import RunContext
from backend.engine.store import RunStore
from backend.engine.errors import IntegrationError, BudgetStopped

class RetryTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, statuses, *, maximum=24, cancel=False, retry_after='0'):
        requests=[]
        def respond(request):
            requests.append(request)
            status=statuses[min(len(requests)-1, len(statuses)-1)]
            return httpx.Response(status, headers={'retry-after': retry_after}, json={
                'model':'test-model', 'choices':[{'message':{'content':'{}'}, 'finish_reason':'stop'}]})
        client=CrusoeClient('test-only', 'test-model', 'nvidia/nemotron-test', http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
        store=RunStore(':memory:');run=Run(request=RunRequest(goal='Retry test', mode='live',budget={'max_model_calls':maximum}))
        store.create(run);budget=RootBudget(run,store);ctx=RunContext(run,budget,store,client,'root')
        async def sleep(_):
            if cancel: budget.request_cancel()
        error=None
        try:
            with patch('backend.providers.crusoe.asyncio.sleep', new=AsyncMock(side_effect=sleep)):
                await client.complete('investigator',[Message(role='user',content='test')],ctx)
        except (IntegrationError,BudgetStopped) as exc: error=exc.code
        finally: await client.close()
        return run,requests,error

    async def test_transient_rate_limit_retries_with_accounted_budget(self):
        run,requests,error=await self.exercise([429,200])
        self.assertIsNone(error)
        self.assertEqual(len(requests),2)
        self.assertEqual(run.usage.model_calls,2)
        self.assertEqual(run.usage.provider_calls,2)

    async def test_persistent_limit_stops_after_two_retries(self):
        run,requests,error=await self.exercise([429])
        self.assertEqual(error,'rate_limited')
        self.assertEqual(len(requests),3)
        self.assertEqual(run.usage.model_calls,3)

    async def test_retry_respects_budget_cancellation_and_cooldown(self):
        for kwargs,code,count in [({'maximum':1},'model_budget_exhausted',1), ({'cancel':True},'canceled',1), ({'retry_after':'60'},'provider_cooldown',1)]:
            with self.subTest(kwargs=kwargs):
                _,requests,error=await self.exercise([429],**kwargs)
                self.assertEqual(error,code)
                self.assertEqual(len(requests),count)
