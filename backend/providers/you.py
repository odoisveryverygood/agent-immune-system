"""Bounded You.com Search transport; not a model client or task scheduler.

Official reference checked 2026-10-17:
https://you.com/docs/api-reference/search/v1-search
POST https://ydc-index.io/v1/search; X-API-Key; {query, count}; results.web.
The caller MUST dispatch search() through the engine's root research_call gate.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import ValidationError

from backend.review.errors import ErrorCode, LaneError
from backend.review.models import Source

ENDPOINT = "https://ydc-index.io/v1/search"
MAX_RESPONSE_BYTES = 1_048_576


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class YouClient:
    api_key: str = field(repr=False)
    timeout_seconds: float = 10.0

    def __post_init__(self):
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise LaneError(ErrorCode.MISSING_CONFIG)
        if (type(self.timeout_seconds) not in (int, float)
                or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 30):
            raise LaneError(ErrorCode.INVALID_INPUT)

    async def search(self, query: str) -> dict:
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 1000:
            raise LaneError(ErrorCode.INVALID_INPUT)
        # Network timeout limits the worker even if the root await is canceled.
        # asyncio cancellation cannot kill a running urllib thread; the engine
        # must account for the reserved call until its timeout, not mark it free.
        payload = await asyncio.to_thread(self._request, query)
        return {"query": query, "sources": parse_sources(payload), "mode": "live", "error_code": None}

    def _request(self, query: str) -> dict:
        request = Request(ENDPOINT, method="POST", headers={
            "X-API-Key": self.api_key,
            "Content-Type": "application/json", "Accept": "application/json",
        }, data=json.dumps({"query": query, "count": 5}).encode("utf-8"))
        try:
            # Do not forward authorization to redirects or result URLs.
            with build_opener(_NoRedirect()).open(request, timeout=self.timeout_seconds) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE)
            parsed = json.loads(body)
        except HTTPError:
            raise LaneError(ErrorCode.PROVIDER_ERROR) from None
        except (TimeoutError, asyncio.TimeoutError):
            raise LaneError(ErrorCode.PROVIDER_TIMEOUT) from None
        except URLError as exc:
            code = ErrorCode.PROVIDER_TIMEOUT if isinstance(exc.reason, TimeoutError) else ErrorCode.PROVIDER_ERROR
            raise LaneError(code) from None
        except (ValueError, UnicodeError, RecursionError):
            raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE) from None
        return parsed


def parse_sources(payload) -> list[dict]:
    """Retain bounded actual excerpts. Never crawl returned URLs or invent text."""
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), dict):
        raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE)
    web = payload["results"].get("web")
    if not isinstance(web, list):
        raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE)
    if not web:
        raise LaneError(ErrorCode.EMPTY_RESEARCH)
    sources, seen = [], set()
    for item in web[:5]:
        if not isinstance(item, dict):
            raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE)
        url, title, snippets = item.get("url"), item.get("title"), item.get("snippets")
        if not isinstance(url, str) or not isinstance(title, str) or not isinstance(snippets, list):
            raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE)
        if url in seen:
            continue
        if not snippets or any(not isinstance(s, str) or not s.strip() for s in snippets[:3]):
            raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE)
        try:
            source = Source(source_id="you:" + hashlib.sha256(url.encode()).hexdigest()[:20],
                            url=url, title=title[:4000], excerpts=[s[:4000] for s in snippets[:3]])
        except ValidationError:
            raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE) from None
        seen.add(url)
        sources.append(source.model_dump())
    if not sources:
        raise LaneError(ErrorCode.EMPTY_RESEARCH)
    return sources
