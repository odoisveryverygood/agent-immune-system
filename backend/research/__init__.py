"""Exactly one explicit research query per call, no hidden fixture fallback."""
from __future__ import annotations

import re

from pydantic import ValidationError

from backend.review.context import ReviewContext
from backend.review.errors import ErrorCode, LaneError
from backend.review.models import ResearchResult


async def research(goal: str, run_context: ReviewContext) -> dict:
    if not isinstance(goal, str) or not 1 <= len(goal.strip()) <= 600:
        raise LaneError(ErrorCode.INVALID_INPUT)
    # Do not interpolate an attacker's arbitrary goal into search operators.
    # Scope is intentionally fixed to this app's simulated checkout failure.
    query = "prompt injection shopping agent checkout client supplied price validation trusted catalog discount mitigation"
    if run_context.mode == "fixture":
        if run_context.fixture_research is None:
            raise LaneError(ErrorCode.MISSING_CONFIG)
        payload = run_context.fixture_research
    else:
        if run_context.you_client is None or run_context.research_call is None:
            raise LaneError(ErrorCode.MISSING_CONFIG)
        # Engine reserves and records one root-owned I/O call before invoking.
        payload = await run_context.research_call(lambda: run_context.you_client.search(query))
    try:
        result = ResearchResult.model_validate(payload)
    except ValidationError:
        raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE) from None
    if result.mode != run_context.mode or result.query != query:
        raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE)
    if result.error_code:
        raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE)
    if not result.sources:
        raise LaneError(ErrorCode.EMPTY_RESEARCH)
    ids = [source.source_id for source in result.sources]
    if len(set(ids)) != len(ids):
        raise LaneError(ErrorCode.INVALID_EVIDENCE)
    # A conservative topical filter, NOT a claim of source reliability. Every
    # source is still untrusted and the independent reviewer judges relevance.
    retained = []
    for source in result.sources:
        words = set(re.findall(r"[a-z]+", " ".join([source.title, *source.excerpts]).lower()))
        if words & {"injection", "checkout", "pricing", "discount", "catalog"}:
            retained.append(source)
    if not retained:
        raise LaneError(ErrorCode.IRRELEVANT_RESEARCH)
    return result.model_copy(update={"sources": retained}).model_dump()
