"""Owner-facing integration seam. Factories MUST return fresh per-run instances."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, TYPE_CHECKING

from backend.models import (AttackCase, AttackResult, CaseSuite, Message, ModelReply,
                            Policy, PolicyPatch, ResearchResult, ReviewDecision, Role)

if TYPE_CHECKING:
    from .context import RunContext


class Completer(Protocol):
    async def complete(self, role: Role, messages: list[Message], run_context: RunContext) -> ModelReply: ...
    async def close(self): ...


class Target(Protocol):
    async def describe(self, run_context: RunContext) -> Policy: ...
    async def execute_attack(self, case: AttackCase, policy_version: str, run_context: RunContext) -> AttackResult: ...
    async def apply_patch(self, patch: PolicyPatch, run_context: RunContext) -> Policy: ...


class Reviewer(Protocol):
    async def research(self, goal: str, run_context: RunContext) -> ResearchResult: ...
    async def review(self, result: AttackResult, policy: Policy, research: ResearchResult, run_context: RunContext) -> ReviewDecision: ...
    async def propose_patch(self, failures: list[AttackResult], policy: Policy, run_context: RunContext) -> PolicyPatch: ...


@dataclass
class IntegrationFactories:
    target: Callable[[], Target]
    reviewer: Callable[[], Reviewer]
    completer: Callable[[], Completer]
    suite: Callable[[], CaseSuite]
