"""Contract v1 target executor. The engine supplies shared budget callbacks."""
from copy import deepcopy
from dataclasses import asdict
import asyncio
import inspect
import json
from ..runtime.local import LocalFixtureRuntime
from .adapter import FIXTURE_MODEL, SYSTEM_PROMPT, fixture_decision, parse_decision
from .oracle import evaluate
from .policy import PolicyRegistry, TargetError, digest


async def _resolve(value):
    return await value if inspect.isawaitable(value) else value


async def _check_active(check):
    if await _resolve(check()) is False:
        raise TargetError("root_inactive")


def validate_case(case):
    if not isinstance(case, dict) or set(case) != {"case_id", "messages", "origin_task_id"}:
        raise TargetError("invalid_case")
    if any(not isinstance(case[k], str) or not case[k].strip() for k in ("case_id", "origin_task_id")):
        raise TargetError("invalid_case")
    messages = case["messages"]
    if not isinstance(messages, list) or not 1 <= len(messages) <= 64:
        raise TargetError("invalid_messages")
    for m in messages:
        if (not isinstance(m, dict) or set(m) != {"role", "content"}
                or m["role"] not in ("user", "assistant", "system", "tool")
                or not isinstance(m["content"], str) or len(m["content"]) > 32000):
            raise TargetError("invalid_messages")


class TargetExecutor:
    def __init__(self, registry=None, runtime=None, ledger=None, decision_agent=None):
        self.registry = registry or PolicyRegistry()
        self.runtime = runtime or LocalFixtureRuntime()
        self.ledger = ledger
        self.decision_agent = decision_agent

    async def execute_attack(self, case, policy_version, run_context):
        # Copy before the first await; caller changes cannot rewrite the replay.
        case = deepcopy(case)
        validate_case(case)
        policy = self.registry.get(policy_version)
        engine_context = hasattr(run_context, "tool_call") and hasattr(run_context, "complete")
        mode = run_context.run.request.mode if engine_context else (
            run_context.get("mode") if isinstance(run_context, dict) else None)
        if mode not in ("fixture", "live"):
            raise TargetError("explicit_execution_mode_required")
        model = FIXTURE_MODEL if mode == "fixture" else None
        receipts = []
        # Runtime stays unknown until an operation has actually executed.
        provenance = {"mode": "not_executed", "sandbox_id": None, "policy_digest": None}
        error = None
        try:
            check = run_context.budget.guard if engine_context else run_context.get("check_active")
            reserve = None if engine_context else run_context.get("reserve_tool_call")
            if not callable(check) or (not engine_context and not callable(reserve)):
                raise TargetError("missing_budget_callbacks")
            await _check_active(check)
            if mode == "fixture":
                arguments = fixture_decision(case["messages"])
            elif self.decision_agent is not None:
                if not engine_context:
                    raise TargetError("cart_agent_requires_engine_context")
                arguments, model = await self.decision_agent.decide(case["messages"], run_context)
            else:
                complete = None if engine_context else run_context.get("target_complete")
                if not engine_context and not callable(complete):
                    raise TargetError("missing_target_provider")
                # Transport is injected by Person 1 and must reserve model budget itself.
                try:
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        # Original roles remain data, never attacker-granted system priority.
                        {"role": "user", "content": json.dumps(case["messages"], ensure_ascii=False)},
                    ]
                    if engine_context:
                        from backend.models import Message
                        reply = await run_context.complete("attacker", [Message(**message) for message in messages])
                        response = {"text": reply.text, "model": reply.model}
                    else:
                        response = await _resolve(complete(role="target", messages=messages, run_context=run_context))
                except TargetError:
                    raise
                except asyncio.TimeoutError:
                    raise TargetError("target_provider_timeout") from None
                except Exception:
                    raise TargetError("target_provider_failed") from None
                if not isinstance(response, dict) or not isinstance(response.get("model"), str) or not response["model"]:
                    raise TargetError("invalid_provider_response")
                model = response["model"]
                arguments = parse_decision(response.get("text"))
            await _check_active(check)
            if arguments is not None:
                if engine_context:
                    async def checkout():
                        nonlocal provenance
                        receipt, provenance = await self.runtime.execute(arguments, policy)
                        return receipt
                    receipt = await run_context.tool_call("checkout", checkout, case_id=case["case_id"])
                    receipt = receipt.model_dump(mode="json")
                else:
                    reservation = await _resolve(reserve())
                    if reservation is False:
                        raise TargetError("tool_budget_exhausted")
                    await _check_active(check)
                    receipt, provenance = await self.runtime.execute(arguments, policy)
                receipts.append(receipt)
            oracle = evaluate(receipts)
        except TargetError as exc:
            error = exc.code
            # An accepted effect survives a subsequent attestation/read failure.
            if exc.receipt is not None:
                receipts.append(exc.receipt)
                provenance = exc.runtime
            oracle = evaluate(receipts)
        result = {"case_id": case["case_id"], "policy_version": policy.version, "model": model,
                  "tool_receipts": receipts, "oracle": oracle, "runtime": provenance, "error_code": error}
        if self.ledger is not None:
            self.ledger.append({"case": case, "case_digest": digest(case), "policy": asdict(policy),
                                "policy_digest": policy.digest, "result": result})
        return result


async def execute_attack(case, policy_version, run_context):
    """Convenience boundary. Inject a persistent executor through run_context."""
    if not isinstance(run_context, dict):
        raise TargetError("explicit_execution_mode_required")
    executor = run_context.get("target_executor") or TargetExecutor()
    return await executor.execute_attack(case, policy_version, run_context)
