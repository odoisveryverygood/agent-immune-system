"""Sanitized boundary errors; never include provider bodies or credentials."""
from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    MISSING_CONFIG = "missing_config"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_ERROR = "provider_error"
    INVALID_MODEL_JSON = "invalid_model_json"
    INVALID_PROVIDER_RESPONSE = "invalid_provider_response"
    UNEXPECTED_MODEL = "unexpected_model"
    INVALID_EVIDENCE = "invalid_evidence"
    MISSING_EVIDENCE = "missing_evidence"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    INVALID_PATCH = "invalid_patch"
    STALE_POLICY = "stale_policy"
    UNRESOLVED_REVIEW = "unresolved_review"
    EMPTY_RESEARCH = "empty_research"
    IRRELEVANT_RESEARCH = "irrelevant_research"


class LaneError(Exception):
    def __init__(self, code: ErrorCode):
        self.code = code
        super().__init__(code.value)
