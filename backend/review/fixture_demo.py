"""Explicit synthetic boundary walkthrough, NOT a target/evaluation executor.

python -m backend.review.fixture_demo --fixtures tests/review/fixtures
No network, model inference, target execution or OpenShell enforcement occurs.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from backend.research import research

from . import ReviewContext, propose_patch, review, review_evaluation


async def walkthrough(directory: Path) -> dict:
    def load(name):
        return json.loads((directory / (name + ".json")).read_text())

    responses = iter([load("review"), load("patch"), load("evaluation-review")])
    calls = []

    async def complete(role, messages, context):
        calls.append(role)
        return {"text": json.dumps(next(responses)), "provider": "fixture",
                "model": "fixture-nemotron", "input_tokens": 0,
                "output_tokens": 0, "elapsed_ms": 0, "request_id": None}

    ctx = ReviewContext(mode="fixture", complete=complete, fixture_research=load("research"))
    sources = await research("Checkout price validation", ctx)
    decision = await review(load("baseline"), load("policy"), sources, ctx)
    proposal = await propose_patch([load("baseline")], load("policy"), ctx)
    evaluation_inputs = load("evaluation")
    evaluation_inputs.update(baseline_review=decision, patch=proposal)
    final = await review_evaluation(evaluation_inputs, ctx)
    return {"mode": "fixture", "synthetic_boundary_walkthrough": True,
            "notice": "Canned receipts, research, model responses and held-out counters; no target or provider ran.",
            "actual_provider_calls": 0, "fixture_completion_roles": calls,
            "research": sources, "review": decision, "patch": proposal,
            "evaluation_of_fixture_inputs": final}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(walkthrough(args.fixtures)), indent=2))


if __name__ == "__main__":
    main()
