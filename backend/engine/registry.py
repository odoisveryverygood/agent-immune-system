"""Lazy integration discovery: missing teammate code is an explicit blocker."""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path

from backend.models import CaseSuite
from backend.providers.crusoe import CrusoeClient
from .errors import IntegrationError
from .interfaces import IntegrationFactories


def factory(spec):
    module, name = spec.split(":", 1)
    function = getattr(importlib.import_module(module), name)
    if not callable(function):
        raise ValueError("Factory must be callable")
    return function


def discover_live():
    blockers = []
    target = reviewer = suite = None
    for variable in ("CRUSOE_API_KEY", "CRUSOE_MODEL", "NEMOTRON_MODEL", "YOU_API_KEY"):
        if not os.environ.get(variable, "").strip():
            blockers.append(f"{variable} is not configured on the host")
    model = os.environ.get("CRUSOE_MODEL", "").strip()
    reviewer_model = os.environ.get("NEMOTRON_MODEL", "").strip()
    if model and reviewer_model and model.casefold() == reviewer_model.casefold():
        blockers.append("CRUSOE_MODEL and NEMOTRON_MODEL must be distinct for independent review")
    if reviewer_model and "nemotron" not in reviewer_model.casefold():
        blockers.append("NEMOTRON_MODEL must identify a Nemotron model")
    for kind, spec in [
        ("target", os.environ.get("IMMUNE_TARGET_FACTORY", "backend.target.integration:create_target")),
        ("reviewer", os.environ.get("IMMUNE_REVIEW_FACTORY", "backend.review.integration:create_reviewer")),
    ]:
        try:
            loaded = factory(spec)
            if kind == "target":
                target = loaded
            else:
                reviewer = loaded
        except (ImportError, AttributeError, ValueError):
            blockers.append(f"{kind} integration factory is unavailable")
    path = Path(os.environ.get("IMMUNE_CASES_PATH", "tests/heldout/cases.json"))
    try:
        if path.stat().st_size > 65536:
            raise ValueError("oversized case suite")
        suite = CaseSuite.model_validate_json(path.read_text())
    except (OSError, ValueError):
        blockers.append("Person 4's validated held-out/legitimate case suite is unavailable")
    if blockers:
        return None, blockers
    return IntegrationFactories(target, reviewer, CrusoeClient.from_env, lambda: suite.model_copy(deep=True)), []
