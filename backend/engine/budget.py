from __future__ import annotations

import asyncio
import time

from backend.models import Run
from .errors import BudgetStopped
from .store import RunStore


class RootBudget:
    """One ledger per run; children receive references, never fresh limits."""

    def __init__(self, run: Run, store: RunStore):
        self.run, self.store = run, store
        self.deadline = time.monotonic() + run.request.budget.deadline_seconds
        self.lock = asyncio.Lock()
        self.cancel = asyncio.Event()
        self.workers = asyncio.Semaphore(run.request.budget.max_concurrency)
        self.models = asyncio.Semaphore(run.request.budget.max_concurrency)
        self.active = 0

    @property
    def remaining(self):
        return max(0.0, self.deadline - time.monotonic())

    def guard(self):
        if self.cancel.is_set() or self.run.cancel_requested:
            raise BudgetStopped("canceled", "Run cancellation was requested.")
        if self.remaining <= 0:
            raise BudgetStopped("deadline_exceeded", "The root run deadline was reached.")

    async def reserve(self, kind: str):
        async with self.lock:
            self.guard()
            field, maximum = ("model_calls", self.run.request.budget.max_model_calls) if kind == "model" else ("tool_calls", self.run.request.budget.max_tool_calls)
            if getattr(self.run.usage, field) >= maximum:
                raise BudgetStopped(f"{kind}_budget_exhausted", f"The root {kind} call budget is exhausted.")
            setattr(self.run.usage, field, getattr(self.run.usage, field) + 1)
            # Persistence precedes the external dispatch, including failed attempts.
            self.store.save(self.run)

    def request_cancel(self):
        self.run.cancel_requested = True
        self.cancel.set()
        self.store.save(self.run)
