"""Bounded host-side Crusoe transport. All dispatches go through RunContext."""
from __future__ import annotations

import json
import os
import time

import httpx

from backend.engine.errors import IntegrationError
from backend.models import Message, ModelReply, Role

ENDPOINT = "https://api.inference.crusoecloud.com/v1/chat/completions"
MAX_RESPONSE_BYTES = 131072


class CrusoeClient:
    def __init__(self, api_key: str, model: str, reviewer_model: str, *, http_client=None):
        if not api_key.strip():
            raise IntegrationError("missing_crusoe_key", "CRUSOE_API_KEY is not configured on the host.")
        if not model or not reviewer_model:
            raise IntegrationError("missing_model_config", "Set CRUSOE_MODEL and NEMOTRON_MODEL to model IDs available in this account's Crusoe catalog.")
        if len(model) > 200 or len(reviewer_model) > 200:
            raise IntegrationError("invalid_model", "Model IDs exceed the supported length.")
        if model.casefold() == reviewer_model.casefold():
            raise IntegrationError("reviewer_model_not_independent", "Set NEMOTRON_MODEL to a distinct model from CRUSOE_MODEL.")
        if "nemotron" not in reviewer_model.casefold():
            raise IntegrationError("invalid_reviewer_model", "NEMOTRON_MODEL must identify a Nemotron model.")
        self._key = api_key
        self.model, self.reviewer_model = model, reviewer_model
        self._http = http_client or httpx.AsyncClient(timeout=30, follow_redirects=False,
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4))

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("CRUSOE_API_KEY", ""), os.environ.get("CRUSOE_MODEL", ""),
                   os.environ.get("NEMOTRON_MODEL", ""))

    async def close(self):
        await self._http.aclose()

    async def complete(self, role: Role, messages: list[Message], run_context) -> ModelReply:
        if role not in {"investigator", "attacker", "reviewer", "repair"}:
            raise IntegrationError("invalid_role", "Unknown model role.")
        if not 1 <= len(messages) <= 24 or sum(len(m.content.encode()) for m in messages) > 48000:
            raise IntegrationError("model_input_too_large", "Model messages exceed the bounded input limit.")
        model = self.reviewer_model if role == "reviewer" else self.model
        async def request():
            return await self._request(model, messages)
        return await run_context.dispatch_model(request, live=True, role=role)

    async def _request(self, model, messages):
        payload = {"model": model, "messages": [m.model_dump() for m in messages],
                   "temperature": 0, "max_tokens": 1200}
        start = time.monotonic()
        try:
            async with self._http.stream("POST", ENDPOINT, json=payload,
                    headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}) as response:
                if response.status_code != 200:
                    code = {401: "authentication_failed", 403: "permission_denied", 429: "rate_limited"}.get(response.status_code, "provider_http_error")
                    raise IntegrationError(code, f"Crusoe returned HTTP {response.status_code}; no fallback was used.")
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise IntegrationError("response_too_large", "Crusoe response exceeded the byte limit.")
            body = json.loads(raw)
            if body.get("model") != model:
                raise IntegrationError("model_mismatch", "Crusoe response did not identify the requested model.")
            choice = body["choices"][0]
            if choice.get("finish_reason") == "length":
                raise IntegrationError("model_output_truncated", "Model output reached its token limit.")
            text = choice["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("missing text")
            usage = body.get("usage") or {}
            return ModelReply(text=text, provider="crusoe", model=model,
                input_tokens=usage.get("prompt_tokens", 0), output_tokens=usage.get("completion_tokens", 0),
                elapsed_ms=round((time.monotonic() - start) * 1000),
                request_id=body.get("id") if isinstance(body.get("id"), str) else None)
        except httpx.TimeoutException:
            raise IntegrationError("provider_timeout", "Crusoe inference timed out.") from None
        except httpx.HTTPError:
            raise IntegrationError("provider_network_error", "Crusoe could not be reached.") from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise IntegrationError("malformed_provider_response", "Crusoe returned an invalid response shape.") from None
