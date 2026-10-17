from __future__ import annotations

import asyncio
import json
import os
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.models import RunRequest, TERMINAL
from backend.engine.errors import EngineError
from backend.engine.service import RunService
from backend.engine.store import RunStore


class BodyLimit:
    """Bound POST data before JSON parsing, including chunked requests."""
    def __init__(self, app, limit=131072):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > self.limit:
                await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"detail":"Request body exceeds 128 KiB."}'})
                return
            chunks.append(body)
            if not message.get("more_body", False):
                break
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()
        await self.app(scope, replay, send)


def create_app(*, store_path=None, live_factories=None, fixtures=None, max_runs=4):
    @asynccontextmanager
    async def lifespan(app):
        store = RunStore(store_path or os.environ.get("IMMUNE_STATE_PATH", ".state/runs.sqlite3"))
        store.recover_interrupted()
        app.state.service = RunService(store, live_factories=live_factories, fixtures=fixtures, max_runs=max_runs)
        try:
            yield
        finally:
            await app.state.service.shutdown()
            store.close()

    app = FastAPI(title="Agent Immune System", version="1.0.0", lifespan=lifespan)
    origins = os.environ.get("IMMUNE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type", "Last-Event-ID", "Idempotency-Key"])
    app.add_middleware(BodyLimit)

    @app.get("/health")
    async def health():
        return {"status": "ok", "simulated_store_only": True}

    @app.get("/api/capabilities")
    async def capabilities():
        return app.state.service.capabilities()

    @app.post("/api/runs", status_code=201)
    async def start(body: RunRequest, response: Response, idempotency_key: str | None = Header(default=None)):
        if idempotency_key and not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", idempotency_key):
            raise HTTPException(400, "Idempotency-Key must be 1–100 safe identifier characters.")
        try:
            run, created = app.state.service.create(body, idempotency_key)
        except EngineError as exc:
            raise HTTPException(409 if exc.code == "idempotency_conflict" else 429,
                                {"error_code": exc.code, "message": exc.public_message}) from None
        response.status_code = 201 if created else 200
        return {"run_id": run.run_id, "status": run.status}

    def get_run(run_id):
        if not re.fullmatch(r"run_[a-f0-9]{32}", run_id):
            raise HTTPException(404, "Run not found.")
        run = app.state.service.store.get(run_id)
        if run is None:
            raise HTTPException(404, "Run not found.")
        return run

    @app.get("/api/runs/{run_id}")
    async def snapshot(run_id: str):
        run = get_run(run_id)
        events = app.state.service.store.events(run.run_id, after=0, limit=512)
        result_by_receipt = {
            receipt.receipt_id: result.case_id
            for result in run.results
            for receipt in result.tool_receipts
        }
        evidence = []
        for event in events:
            if event.type == "tool.observed":
                receipt = event.data.get("receipt")
                if isinstance(receipt, dict):
                    evidence.append({**receipt, "case_id": result_by_receipt.get(receipt.get("receipt_id")),
                                     "task_id": event.task_id, "event_seq": event.seq,
                                     "event_type": event.type})
            elif event.type == "violation.found":
                evidence.append({**event.data, "task_id": event.task_id,
                                 "event_seq": event.seq, "event_type": event.type})
        last_result = next((result for result in reversed(run.results) if result.tool_receipts), run.results[-1] if run.results else None)
        return {
            "run_id": run.run_id,
            "status": run.status,
            "mode": run.request.mode,
            "scenario": run.request.scenario,
            "target": run.request.target,
            "error_code": run.error_code,
            "error_message": run.error_message,
            "tasks": [task.model_dump(mode="json") for task in run.tasks],
            "events": [event.model_dump(mode="json") for event in events],
            "counters": run.usage.model_dump(mode="json"),
            "evidence": evidence,
            "patch": run.patch.model_dump(mode="json") if run.patch else None,
            "evaluation": run.evaluation.model_dump(mode="json"),
            "repair_attempts": run.repair_attempts,
            "advocate_positions": run.advocate_positions,
            "repair_verified": run.repair_verified,
            "last_seq": run.last_seq,
            "runtime": last_result.runtime.model_dump(mode="json") if last_result else None,
        }

    @app.post("/api/runs/{run_id}/cancel", status_code=202)
    async def cancel(run_id: str):
        get_run(run_id)
        run = await app.state.service.cancel(run_id)
        return {"run_id": run.run_id, "status": run.status, "cancel_requested": run.cancel_requested}

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id: str, request: Request, after: int | None = Query(default=None, ge=0),
                     after_seq: int | None = Query(default=None, ge=0),
                     last_event_id: str | None = Header(default=None)):
        run = get_run(run_id)
        if after is not None and after_seq is not None and after != after_seq:
            raise HTTPException(400, "Use one event cursor value.")
        if after is None:
            after = after_seq
        if after is None:
            try:
                after = int(last_event_id) if last_event_id else 0
            except ValueError:
                raise HTTPException(400, "Last-Event-ID must be an integer.") from None
        if after < 0 or after > run.last_seq:
            raise HTTPException(400, "Event cursor is outside this run's persisted sequence.")
        async def stream():
            cursor, heartbeats = after, 0
            while True:
                if await request.is_disconnected():
                    break
                batch = app.state.service.store.events(run_id, after=cursor)
                for event in batch:
                    cursor = event.seq
                    yield f"id: {event.seq}\ndata: {event.model_dump_json()}\n\n"
                current = app.state.service.store.get(run_id)
                if current.status in TERMINAL and cursor >= current.last_seq:
                    break
                heartbeats += 1
                if heartbeats >= 20:
                    yield ": heartbeat\n\n"
                    heartbeats = 0
                await asyncio.sleep(.1)
        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


app = create_app()
