from __future__ import annotations

import asyncio
from dataclasses import dataclass

from backend.models import Run, RunRequest, TERMINAL, fingerprint
from .errors import EngineError, IntegrationError
from .fixtures import fixture_factories
from .registry import discover_live
from .runner import RecursiveRunner
from .store import RunStore


@dataclass
class Job:
    task: asyncio.Task | None = None
    runner: RecursiveRunner | None = None


class RunService:
    def __init__(self, store: RunStore, *, live_factories=None, fixtures=None, max_runs=4):
        self.store, self.live_factories, self.fixtures = store, live_factories, fixtures or fixture_factories
        self.max_runs = max_runs
        self.jobs: dict[str, Job] = {}

    def capabilities(self):
        _, blockers = (self.live_factories, []) if self.live_factories else discover_live()
        return {"fixture": {"available": True}, "live": {"configured": not blockers,
                "blockers": blockers, "verified": False}, "simulated_store_only": True}

    def create(self, request: RunRequest, idempotency_key=None):
        digest = fingerprint(request)
        if idempotency_key:
            existing = self.store.lookup_key(idempotency_key)
            if existing:
                old_digest, run_id = existing
                if old_digest != digest:
                    raise IntegrationError("idempotency_conflict", "Idempotency key was already used with a different request.")
                return self.store.get(run_id), False
        if sum(not job.task.done() for job in self.jobs.values() if job.task) >= self.max_runs:
            raise IntegrationError("run_capacity_exhausted", "The local server already has its maximum active runs.")
        run = Run(request=request)
        self.store.create(run, idempotency_key=idempotency_key, request_digest=digest)
        job = Job()
        self.jobs[run.run_id] = job
        job.task = asyncio.create_task(self._execute(run, job), name=f"immune:{run.run_id}")
        return run, True

    async def _execute(self, run, job):
        try:
            if run.request.mode == "fixture":
                factories = self.fixtures()
            else:
                factories, blockers = (self.live_factories, []) if self.live_factories else discover_live()
                if blockers:
                    raise IntegrationError("live_prerequisites_missing", "; ".join(blockers))
            job.runner = RecursiveRunner(run, self.store, factories)
            await job.runner.run_workflow()
        except asyncio.CancelledError:
            run.status, run.cancel_requested = "canceled", True
            run.error_code, run.error_message = "canceled", "Queued run canceled before dispatch."
            self.store.emit(run, "run.canceled", task_id=run.root_task_id, data={"error_code": "canceled"})
        except Exception as exc:
            run.status = "blocked" if isinstance(exc, EngineError) else "failed"
            run.error_code = exc.code if isinstance(exc, EngineError) else "integration_initialization_failed"
            run.error_message = exc.public_message if isinstance(exc, EngineError) else "An integration could not initialize; no fallback was used."
            run.repair_verified = False
            self.store.emit(run, f"run.{run.status}", task_id=run.root_task_id,
                            data={"error_code": run.error_code, "message": run.error_message})

    async def cancel(self, run_id):
        run = self.store.get(run_id)
        if run is None or run.status in TERMINAL:
            return run
        job = self.jobs.get(run_id)
        if job and job.task:
            if job.runner:
                job.runner.budget.request_cancel()
            else:
                run.cancel_requested = True
                self.store.save(run)
            job.task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(job.task), timeout=2)
            except (TimeoutError, asyncio.CancelledError):
                # Still running is truthful if an integration has not acknowledged cancellation.
                pass
            if job.task.cancelled():
                current = self.store.get(run_id)
                if current.status not in TERMINAL:
                    current.status, current.cancel_requested = "canceled", True
                    current.error_code = "canceled"
                    self.store.emit(current, "run.canceled", task_id=current.root_task_id,
                                    data={"error_code": "canceled", "message": "Canceled before the worker started."})
        return self.store.get(run_id)

    async def shutdown(self):
        active = [run_id for run_id, job in self.jobs.items() if job.task and not job.task.done()]
        await asyncio.gather(*(self.cancel(run_id) for run_id in active))
        # Do not close the state DB while remaining children can still persist events.
        remaining = [job.task for job in self.jobs.values() if job.task and not job.task.done()]
        if remaining:
            await asyncio.gather(*remaining, return_exceptions=True)
