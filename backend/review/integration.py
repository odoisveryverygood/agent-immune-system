"""Adapter from the review lane to the engine's shared model and budget context."""
from __future__ import annotations

import os

from backend.engine.errors import IntegrationError
from backend.models import (Message, Policy, PolicyPatch, ResearchResult, ReviewDecision, actual_violation)
from backend.review.context import ReviewContext
from backend.review.errors import LaneError
from backend.review.service import propose_patch, review, review_repair
from backend.research import research
from backend.providers.you import YouClient


class EngineReviewer:
    def __init__(self, you_client: YouClient):
        self.you_client = you_client

    @staticmethod
    def _context(run_context, you_client):
        async def complete(role, messages, _review_context):
            reply = await run_context.complete(
                role, [Message(role=message["role"], content=message["content"])
                       for message in messages])
            return reply.model_dump(mode="python")

        return ReviewContext(mode=run_context.run.request.mode, complete=complete,
                             research_call=run_context.research_call,
                             you_client=you_client)

    async def research(self, goal, run_context):
        try:
            result = await research(goal, self._context(run_context, self.you_client))
            return ResearchResult.model_validate(result)
        except LaneError:
            raise IntegrationError("research_integration_failed", "You.com research could not produce validated, relevant sources.") from None

    async def review(self, result, policy: Policy, research_result: ResearchResult, run_context):
        try:
            context = self._context(run_context, self.you_client)
            operation = review if actual_violation(result) else review_repair
            output = await operation(result, policy, research_result, context)
            if len(output.get("proposed_child_goals", [])) > 2:
                raise IntegrationError("review_child_limit_exceeded", "Review proposed more than the engine's two-child limit.")
            return ReviewDecision.model_validate(output)
        except LaneError:
            raise IntegrationError("independent_review_failed", "Nemotron review could not validate the observed evidence.") from None

    async def propose_patch(self, failures, policy: Policy, run_context):
        try:
            patch = await propose_patch(failures, policy,
                                        self._context(run_context, self.you_client))
            return PolicyPatch.model_validate(patch)
        except LaneError:
            raise IntegrationError("repair_proposal_failed", "The review lane could not produce a constrained, evidence-bound patch.") from None


def create_reviewer():
    key = os.environ.get("YOU_API_KEY", "").strip()
    if not key:
        raise IntegrationError("missing_you_key", "YOU_API_KEY is not configured on the backend host.")
    return EngineReviewer(YouClient(key))
