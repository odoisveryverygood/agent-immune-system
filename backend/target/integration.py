"""Adapter from the target lane's executor to the shared run contract."""
from __future__ import annotations

import os

from backend.engine.errors import IntegrationError
from backend.models import AttackResult, Oracle, Policy, PolicyPatch, RuntimeProvenance
from backend.runtime.openshell import OpenShellRuntime

from .executor import TargetExecutor
from .policy import PolicyRegistry


class EngineTarget:
    def __init__(self, executor: TargetExecutor, registry: PolicyRegistry):
        self.executor, self.registry = executor, registry

    async def describe(self, run_context):
        policy = self.registry.current
        return Policy(version=policy.version, reject_client_price=policy.reject_client_price,
                      require_catalog_price=policy.require_catalog_price,
                      max_discount_bps=policy.max_discount_bps)

    async def execute_attack(self, case, policy_version, run_context):
        result = await self.executor.execute_attack(
            case.model_dump(mode="python"), policy_version, run_context)
        oracle = result["oracle"]
        observed = oracle["observed"]
        return AttackResult(
            case_id=result["case_id"], policy_version=result["policy_version"],
            model=result["model"] or "unknown-target-model",
            tool_receipts=result["tool_receipts"],
            oracle=Oracle(violation=oracle["violation"], rule_id=oracle["rule_id"],
                          expected=oracle["expected"], observed=observed),
            runtime=RuntimeProvenance.model_validate(result["runtime"]),
            error_code=result["error_code"],
        )

    async def apply_patch(self, patch: PolicyPatch, run_context):
        try:
            payload = patch.model_dump(mode="python")
            payload["changes"] = patch.changes.model_dump(exclude_none=True)
            policy = self.registry.apply_patch(payload)
        except (ValueError, TypeError):
            raise IntegrationError("target_patch_rejected", "The target rejected the constrained policy patch.") from None
        return Policy(version=policy.version, reject_client_price=policy.reject_client_price,
                      require_catalog_price=policy.require_catalog_price,
                      max_discount_bps=policy.max_discount_bps)


def create_target():
    """Build a fresh target and verified OpenShell runtime for one live run."""
    sandbox_id = os.environ.get("IMMUNE_SANDBOX_ID", "").strip()
    gateway = os.environ.get("IMMUNE_OPENSHELL_GATEWAY", "").strip()
    if not sandbox_id or not gateway:
        raise IntegrationError("openshell_configuration_missing", "Set IMMUNE_SANDBOX_ID and IMMUNE_OPENSHELL_GATEWAY on the backend host.")
    registry = PolicyRegistry()
    runtime = OpenShellRuntime(sandbox_id, gateway=gateway)
    return EngineTarget(TargetExecutor(registry=registry, runtime=runtime), registry)
