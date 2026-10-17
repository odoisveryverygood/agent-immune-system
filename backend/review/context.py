"""Dependency injection only: no scheduler, provider key lookup or model client.

Person 1's adapters own atomic root reservations, cancellation, deadlines,
concurrency, timeouts and persisted sanitized completion/research receipts.
They must reject work before dispatch when the root is exhausted/canceled.
Exceptions from these adapters (e.g. budget exhaustion) propagate unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal

from .errors import ErrorCode, LaneError

Completion = Callable[[str, list[dict[str, str]], Any], Awaitable[Any]]
ResearchCall = Callable[[Callable[[], Awaitable[dict]]], Awaitable[dict]]


@dataclass(frozen=True)
class ReviewContext:
    mode: Literal["fixture", "live"]
    complete: Completion
    research_call: ResearchCall | None = None
    you_client: Any = None
    fixture_research: dict | None = None

    def __post_init__(self) -> None:
        if self.mode not in ("fixture", "live") or not callable(self.complete):
            raise LaneError(ErrorCode.INVALID_INPUT)
        if self.mode == "live" and self.fixture_research is not None:
            raise LaneError(ErrorCode.INVALID_INPUT)
