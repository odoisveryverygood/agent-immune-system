"""Lane-local strict adapters for CONTRACT v1; shared models remain Person 1's.

Inputs may be dictionaries or Pydantic models. Wire outputs are dictionaries.
No receipt is trustworthy merely because it passes this schema: the engine must
obtain AttackResult from the target boundary, never from generated model text.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


Identifier = Annotated[str, Field(min_length=1, max_length=200)]
Text = Annotated[str, Field(min_length=1, max_length=4000)]
Cents = Annotated[StrictInt, Field(ge=0)]
Discount = Annotated[StrictInt, Field(ge=0, le=1000)]


class Policy(StrictModel):
    version: Identifier
    reject_client_price: StrictBool
    require_catalog_price: StrictBool
    max_discount_bps: Discount


class CheckoutReceipt(StrictModel):
    receipt_id: Identifier
    tool: Literal["checkout"]
    product_id: Literal["laptop"]
    quantity: Annotated[StrictInt, Field(ge=1, le=100)]
    trusted_catalog_total_cents: Cents
    charged_total_cents: Cents | None
    minimum_allowed_total_cents: Cents
    status: Literal["accepted", "denied"]
    side_effect: Literal["simulated_order"]
    policy_version: Identifier

    @model_validator(mode="after")
    def accepted_charge_exists(self):
        if self.status == "accepted" and self.charged_total_cents is None:
            raise ValueError("Accepted checkout receipts require a charged total")
        return self


class Oracle(StrictModel):
    violation: StrictBool
    rule_id: Identifier | None = None
    expected: Cents | None = None
    observed: Cents | None = None


class Runtime(StrictModel):
    mode: Literal["openshell", "local_fixture", "not_executed"]
    sandbox_id: Identifier | None
    policy_digest: Identifier | None


class AttackResult(StrictModel):
    case_id: Identifier
    policy_version: Identifier
    model: Identifier
    tool_receipts: Annotated[list[CheckoutReceipt], Field(max_length=64)]
    oracle: Oracle
    runtime: Runtime
    error_code: Identifier | None = None


class Source(StrictModel):
    source_id: Identifier
    url: Annotated[str, Field(min_length=1, max_length=2048)]
    title: Text
    excerpts: Annotated[list[Text], Field(min_length=1, max_length=3)]

    @field_validator("url")
    @classmethod
    def public_url(cls, value: str) -> str:
        from urllib.parse import urlsplit
        import ipaddress
        try:
            parts = urlsplit(value)
            host = parts.hostname
            if parts.scheme not in ("https", "http") or not host or parts.username or parts.password:
                raise ValueError("source must be an HTTP(S) URL without credentials")
            if host.lower() == "localhost" or host.lower().endswith((".local", ".internal")):
                raise ValueError("source must be public")
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                address = None
            if address is not None and not address.is_global:
                raise ValueError("source must be public")
        except (ValueError, TypeError) as exc:
            raise ValueError("invalid public source URL") from exc
        return value


class ResearchResult(StrictModel):
    query: Annotated[str, Field(min_length=1, max_length=1000)]
    sources: Annotated[list[Source], Field(max_length=5)]
    mode: Literal["fixture", "live"]
    error_code: Identifier | None = None


class ChildGoal(StrictModel):
    goal: Text
    spawn_reason: Text
    evidence_ids: Annotated[list[Identifier], Field(min_length=1, max_length=8)]


class ReviewOutput(StrictModel):
    status: Literal["supported", "unsupported", "inconclusive"]
    reason: Text
    evidence_ids: Annotated[list[Identifier], Field(max_length=16)]
    proposed_child_goals: Annotated[list[ChildGoal], Field(max_length=3)]


class ModelReview(ReviewOutput):
    # Required in model JSON, deliberately absent from the v1 wire envelope.
    uncertainty: Annotated[list[Text], Field(max_length=8)]


class Changes(StrictModel):
    reject_client_price: StrictBool | None = None
    require_catalog_price: StrictBool | None = None
    max_discount_bps: Discount | None = None


class Patch(StrictModel):
    patch_id: Identifier
    based_on_policy_version: Identifier
    changes: Changes
    reason: Text
    evidence_ids: Annotated[list[Identifier], Field(min_length=1, max_length=16)]


class HeldoutSummary(StrictModel):
    total: Annotated[StrictInt, Field(ge=0)]
    blocked: Annotated[StrictInt, Field(ge=0)]
    violations: Annotated[StrictInt, Field(ge=0)]
    errors: Annotated[StrictInt, Field(ge=0)]


class LegitimateSummary(StrictModel):
    total: Annotated[StrictInt, Field(ge=0)]
    accepted: Annotated[StrictInt, Field(ge=0)]
    errors: Annotated[StrictInt, Field(ge=0)]


class Evaluation(StrictModel):
    original_replay_passed: StrictBool
    heldout: HeldoutSummary
    legitimate: LegitimateSummary
    repair_verified: StrictBool
    evaluation_status: Literal["passed", "failed", "incomplete"]


def as_data(value: Any) -> Any:
    return value.model_dump(mode="python") if isinstance(value, BaseModel) else value
