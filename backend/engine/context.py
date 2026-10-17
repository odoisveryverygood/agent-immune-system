from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

from backend.models import CheckoutReceipt, Message, ModelReply, Role, Run
from backend.models import now, uid
from .budget import RootBudget
from .errors import BudgetStopped, IntegrationError
from .store import RunStore

T = TypeVar("T")


class RunContext:
    """Task-local identity plus the root's shared budget, client and persistence.

    Person 2 MUST use tool_call for each checkout effect. Person 3 MUST use
    complete for every model request. Neither operation creates a child budget.
    """

    def __init__(self, run: Run, budget: RootBudget, store: RunStore, client, task_id: str):
        self.run, self.budget, self.store, self.client, self.task_id = run, budget, store, client, task_id
        self.tool_receipts: list[CheckoutReceipt] = []
        self.model_receipts: list[dict] = []

    @property
    def run_id(self):
        return self.run.run_id

    def child_context(self, task_id: str):
        return RunContext(self.run, self.budget, self.store, self.client, task_id)

    def emit(self, kind, data):
        task = next((t for t in self.run.tasks if t.task_id == self.task_id), None)
        return self.store.emit(self.run, kind, task_id=self.task_id,
                               parent_id=task.parent_id if task else None, data=data)

    async def bounded(self, operation: Awaitable[T], *, seconds=30) -> T:
        try:
            async with asyncio.timeout(min(seconds, self.budget.remaining)):
                return await operation
        except TimeoutError:
            self.budget.guard()
            raise IntegrationError("operation_timeout", "An integration operation timed out.") from None

    async def complete(self, role: Role, messages: list[Message]) -> ModelReply:
        return await self.client.complete(role, messages, self)

    async def research_call(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Reserve external search against the same root-owned I/O budget."""
        await self.budget.reserve("tool")
        return await self.bounded(operation())

    async def dispatch_model(self, operation: Callable[[], Awaitable[ModelReply]], *, live: bool, role: Role) -> ModelReply:
        self.budget.guard()
        async with asyncio.timeout(max(.001, self.budget.remaining)):
            async with self.budget.models:
                await self.budget.reserve("model")
                if live:
                    self.run.usage.provider_calls += 1
                    self.store.save(self.run)
                reply = await self.bounded(operation())
        self.budget.guard()
        self.run.usage.input_tokens += reply.input_tokens
        self.run.usage.output_tokens += reply.output_tokens
        receipt = {"receipt_id": uid("model"), "task_id": self.task_id, "role": role,
                   "provider": reply.provider, "model": reply.model, "live": live,
                   "input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens,
                   "elapsed_ms": reply.elapsed_ms, "request_id": reply.request_id, "timestamp": now()}
        self.model_receipts.append(receipt)
        self.run.model_receipts.append(receipt)
        self.store.save(self.run)
        return reply

    async def tool_call(self, tool_name: str, operation: Callable[[], Awaitable[CheckoutReceipt]],
                        *, case_id: str | None = None) -> CheckoutReceipt:
        if tool_name != "checkout":
            raise IntegrationError("unknown_tool", "Only the simulated checkout tool is enabled.")
        if case_id is not None and (not isinstance(case_id, str) or not 1 <= len(case_id) <= 100):
            raise IntegrationError("invalid_case_id", "Checkout evidence must use a bounded case identifier.")
        await self.budget.reserve("tool")
        try:
            receipt = await self.bounded(operation())
        except Exception as exc:
            # A sandbox may have completed the simulated checkout but fail its
            # later attestation read. Preserve that accepted effect for audit.
            observed = getattr(exc, "receipt", None)
            if observed is not None:
                self._record_tool_receipt(observed, case_id)
            raise
        return self._record_tool_receipt(receipt, case_id)

    def _record_tool_receipt(self, receipt, case_id=None) -> CheckoutReceipt:
        receipt = CheckoutReceipt.model_validate(receipt)
        if any(r.receipt_id == receipt.receipt_id for r in self.tool_receipts):
            raise IntegrationError("duplicate_receipt", "Tool receipt IDs must be unique within an execution.")
        self.tool_receipts.append(receipt)
        data = {"receipt": receipt.model_dump(mode="json")}
        if case_id is not None:
            data["case_id"] = case_id
        self.emit("tool.observed", data)
        self.budget.guard()
        return receipt
