"""Public review/repair boundary. All model calls use Person 1's completion.

No automatic retries: an engine retry must consume the same root budget.
Typed failures must be persisted by the engine and block repair verification.
"""
from __future__ import annotations

import json

from pydantic import ValidationError

from .context import ReviewContext
from .errors import ErrorCode, LaneError
from .evidence import inspect_result, policy_input
from .models import (ModelReview, Patch, ResearchResult, ReviewOutput,
                     as_data)
from .prompts import PATCH_SYSTEM, REPAIR_REVIEW_SYSTEM, REVIEW_SYSTEM


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


async def _completion(schema, role: str, system: str, data: dict,
                      context: ReviewContext):
    payload = json.dumps(data, ensure_ascii=True, allow_nan=False)
    if len(payload) > 100_000:
        raise LaneError(ErrorCode.INVALID_INPUT)
    try:
        completion = as_data(await context.complete(role, [
            {"role": "system", "content": system},
            {"role": "user", "content": payload},
        ], context))
    except TimeoutError:
        raise LaneError(ErrorCode.PROVIDER_TIMEOUT) from None
    # Cancellation and engine budget errors deliberately propagate. Never
    # catch arbitrary shared-client exceptions and turn them into successes.
    if not isinstance(completion, dict):
        raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE)
    provider, model = completion.get("provider"), completion.get("model")
    if not isinstance(provider, str) or not provider.strip() or not isinstance(model, str) or not model.strip():
        raise LaneError(ErrorCode.INVALID_PROVIDER_RESPONSE)
    if context.mode == "live":
        if "fixture" in (provider + model).casefold():
            raise LaneError(ErrorCode.UNEXPECTED_MODEL)
        if role == "reviewer" and "nemotron" not in model.casefold():
            raise LaneError(ErrorCode.UNEXPECTED_MODEL)
    elif provider != "fixture":
        raise LaneError(ErrorCode.UNEXPECTED_MODEL)
    raw = completion.get("text")
    if not isinstance(raw, str) or len(raw) > 32_000:
        raise LaneError(ErrorCode.INVALID_MODEL_JSON)
    try:
        parsed = json.loads(raw, object_pairs_hook=_unique_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        return schema.model_validate(parsed)
    except (ValueError, ValidationError, RecursionError):
        raise LaneError(ErrorCode.INVALID_MODEL_JSON) from None


async def review(result, policy, research, run_context: ReviewContext) -> dict:
    """Support a baseline finding only after deterministic AND model review.

Malformed model responses/citations raise LaneError. Missing or contradictory
    target evidence returns inconclusive without spending a model call.
    """
    trusted_policy = policy_input(policy)
    try:
        attack, violation_ids = inspect_result(result, trusted_policy)
    except LaneError as exc:
        if exc.code == ErrorCode.INVALID_INPUT:
            raise
        return ReviewOutput(status="inconclusive", reason=exc.code.value,
                            evidence_ids=[], proposed_child_goals=[]).model_dump()
    try:
        sources = ResearchResult.model_validate(as_data(research))
    except ValidationError:
        raise LaneError(ErrorCode.INVALID_INPUT) from None
    if sources.mode != run_context.mode:
        raise LaneError(ErrorCode.INVALID_EVIDENCE)
    source_ids = [source.source_id for source in sources.sources]
    receipt_ids = {r.receipt_id for r in attack.tool_receipts}
    if len(set(source_ids)) != len(source_ids) or set(source_ids) & receipt_ids:
        raise LaneError(ErrorCode.INVALID_EVIDENCE)
    if sources.error_code or not sources.sources:
        return ReviewOutput(status="inconclusive", reason="Research is unavailable or unresolved.",
                            evidence_ids=[], proposed_child_goals=[]).model_dump()
    if not violation_ids:
        return ReviewOutput(status="unsupported", reason="No accepted checkout receipt violates the trusted minimum.",
                            evidence_ids=sorted(receipt_ids), proposed_child_goals=[]).model_dump()
    decision = await _completion(ModelReview, "reviewer", REVIEW_SYSTEM, {
        "trusted_policy": trusted_policy.model_dump(),
        "target_result": attack.model_dump(),
        "research_untrusted": sources.model_dump(),
        "deterministic_violating_receipt_ids": violation_ids,
    }, run_context)
    allowed = receipt_ids | set(source_ids)
    if not set(decision.evidence_ids) <= allowed:
        raise LaneError(ErrorCode.INVALID_EVIDENCE)
    for child in decision.proposed_child_goals:
        if (not set(child.evidence_ids) <= allowed
                or not set(child.evidence_ids) & set(violation_ids)
                or not set(child.evidence_ids) <= set(decision.evidence_ids)
                or not any(rid in child.spawn_reason for rid in set(child.evidence_ids) & set(violation_ids))):
            raise LaneError(ErrorCode.INVALID_EVIDENCE)
    if decision.status == "supported" and not set(decision.evidence_ids) & set(violation_ids):
        raise LaneError(ErrorCode.MISSING_EVIDENCE)
    output = decision.model_dump(exclude={"uncertainty"})
    if decision.uncertainty:
        output.update(status="inconclusive", proposed_child_goals=[],
                      reason="Unresolved uncertainty: " + "; ".join(decision.uncertainty))
        output["reason"] = output["reason"][:4000]
    elif decision.status == "unsupported":
        # The model cannot erase a proven numeric violation. Its disagreement
        # means independent review is unresolved, not that the receipt is safe.
        output.update(status="inconclusive", proposed_child_goals=[],
                      reason=("Deterministic violation remains proven; independent review is unresolved: "
                              + decision.reason)[:4000])
    elif decision.status != "supported":
        output["proposed_child_goals"] = []
    return ReviewOutput.model_validate(output).model_dump()


async def review_repair(result, policy, research, run_context: ReviewContext) -> dict:
    """Independently verify a protected replay after a patch was applied."""
    trusted_policy = policy_input(policy)
    try:
        attack, violation_ids = inspect_result(result, trusted_policy)
    except LaneError as exc:
        if exc.code == ErrorCode.INVALID_INPUT:
            raise
        return ReviewOutput(status="inconclusive", reason=exc.code.value,
                            evidence_ids=[], proposed_child_goals=[]).model_dump()
    if violation_ids or not attack.tool_receipts:
        return ReviewOutput(status="inconclusive",
                            reason="The replay does not provide clean checkout evidence.",
                            evidence_ids=[], proposed_child_goals=[]).model_dump()
    try:
        sources = ResearchResult.model_validate(as_data(research))
    except ValidationError:
        raise LaneError(ErrorCode.INVALID_INPUT) from None
    if sources.mode != run_context.mode or sources.error_code or not sources.sources:
        return ReviewOutput(status="inconclusive", reason="Research is unavailable or unresolved.",
                            evidence_ids=[], proposed_child_goals=[]).model_dump()
    receipt_ids = {receipt.receipt_id for receipt in attack.tool_receipts}
    source_ids = {source.source_id for source in sources.sources}
    if receipt_ids & source_ids:
        raise LaneError(ErrorCode.INVALID_EVIDENCE)
    decision = await _completion(ModelReview, "reviewer", REPAIR_REVIEW_SYSTEM, {
        "trusted_policy": trusted_policy.model_dump(),
        "repaired_replay": attack.model_dump(),
        "research_untrusted": sources.model_dump(),
        "allowed_evidence_ids": sorted(receipt_ids | source_ids),
    }, run_context)
    if (not set(decision.evidence_ids) <= receipt_ids | source_ids
            or not set(decision.evidence_ids) & receipt_ids):
        raise LaneError(ErrorCode.INVALID_EVIDENCE)
    output = decision.model_dump(exclude={"uncertainty"})
    if decision.uncertainty or decision.status != "supported":
        output.update(status="inconclusive", proposed_child_goals=[],
                      reason=("Unresolved replay review: " + decision.reason)[:4000])
    else:
        output["proposed_child_goals"] = []
    return ReviewOutput.model_validate(output).model_dump()


def validate_patch(patch, policy, evidence_ids: set[str]) -> dict:
    """Call again immediately before application against the current policy.

This lane does not mutate/store policies. Person 1/2 must atomically compare the
    version, apply the returned changes and create a new immutable version.
    """
    trusted_policy = policy_input(policy)
    try:
        # Preserve fields_set: model_dump() would materialize omitted optional
        # change keys as null, making a valid parsed proposal fail revalidation.
        candidate = patch if isinstance(patch, Patch) else Patch.model_validate(as_data(patch))
    except ValidationError:
        raise LaneError(ErrorCode.INVALID_PATCH) from None
    if candidate.based_on_policy_version != trusted_policy.version:
        raise LaneError(ErrorCode.STALE_POLICY)
    changes = candidate.changes.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise LaneError(ErrorCode.INVALID_PATCH)
    # Stricter discount caps would break the required authorized 10% purchase.
    # Booleans may only enable protection; no arbitrary generated code.
    if (changes.get("reject_client_price") is False
            or changes.get("require_catalog_price") is False
            or ("max_discount_bps" in changes
                and changes["max_discount_bps"] != trusted_policy.max_discount_bps)):
        raise LaneError(ErrorCode.INVALID_PATCH)
    if all(getattr(trusted_policy, key) == value for key, value in changes.items()):
        raise LaneError(ErrorCode.INVALID_PATCH)
    if (not set(candidate.evidence_ids) <= evidence_ids
            or len(set(candidate.evidence_ids)) != len(candidate.evidence_ids)):
        raise LaneError(ErrorCode.INVALID_EVIDENCE)
    return {**candidate.model_dump(), "changes": changes}


async def propose_patch(failures, policy, run_context: ReviewContext) -> dict:
    """Accept only baseline AttackResults; never held-out corpus or summaries."""
    trusted_policy = policy_input(policy)
    if not isinstance(failures, (list, tuple)) or not 1 <= len(failures) <= 16:
        raise LaneError(ErrorCode.INVALID_INPUT)
    attacks, evidence_ids, case_ids, all_receipt_ids = [], set(), set(), set()
    for failure in failures:
        attack, violations = inspect_result(failure, trusted_policy)
        receipt_ids = {r.receipt_id for r in attack.tool_receipts}
        if (not violations or attack.case_id in case_ids or receipt_ids & all_receipt_ids):
            raise LaneError(ErrorCode.INVALID_EVIDENCE)
        case_ids.add(attack.case_id)
        all_receipt_ids.update(receipt_ids)
        evidence_ids.update(violations)
        attacks.append(attack.model_dump())
    candidate = await _completion(Patch, "repair", PATCH_SYSTEM, {
        "trusted_policy": trusted_policy.model_dump(),
        "proven_baseline_failures": attacks,
        "allowed_evidence_ids": sorted(evidence_ids),
    }, run_context)
    return validate_patch(candidate, trusted_policy, evidence_ids)
