"""OpenShell 0.0.116 transport. No local fallback, arbitrary commands, or keys."""
import asyncio
from dataclasses import asdict
import json
import math
import os
import re
from ..target.oracle import evaluate
from ..target.policy import canonical, digest, TargetError


class OpenShellRuntime:
    def __init__(self, sandbox_id: str, *, gateway: str, binary="openshell", timeout=20):
        if not all(isinstance(s, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", s)
                   for s in (sandbox_id, gateway)):
            raise TargetError("invalid_runtime_configuration")
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 180:
            raise TargetError("invalid_runtime_timeout")
        self.sandbox_id, self.gateway, self.binary, self.timeout = sandbox_id, gateway, binary, timeout

    async def _command(self, *args, payload=None):
        # CLI reads host gateway metadata. Provider keys never enter the child env.
        env = {k: os.environ[k] for k in ("HOME", "PATH", "TMPDIR", "SSL_CERT_FILE") if k in os.environ}
        try:
            process = await asyncio.create_subprocess_exec(
                self.binary, "--gateway", self.gateway, *args, env=env,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        except (OSError, ValueError):
            raise TargetError("openshell_unavailable") from None
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(payload), timeout=self.timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
            process.kill()
            await process.wait()
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise TargetError("openshell_timeout") from None
        if process.returncode:
            # Do not leak CLI diagnostics, environment values, or credential metadata.
            raise TargetError("openshell_command_failed")
        try:
            return json.loads(stdout)
        except (ValueError, UnicodeError):
            raise TargetError("invalid_openshell_response") from None

    async def _identity(self):
        metadata = await self._command("sandbox", "get", self.sandbox_id, "--output", "json")
        policy = await self._command("policy", "get", self.sandbox_id, "--full", "--output", "json")
        if (not isinstance(metadata, dict) or metadata.get("phase") != "Ready"
                or metadata.get("name") != self.sandbox_id or not metadata.get("id")
                or not isinstance(policy, dict) or policy.get("status") != "effective"
                or not isinstance(policy.get("policy"), dict)):
            raise TargetError("sandbox_not_ready")
        return metadata, policy

    async def execute(self, arguments, policy):
        before, effective = await self._identity()
        output = await self._command(
            "sandbox", "exec", "--name", self.sandbox_id, "--no-tty", "--timeout", str(math.ceil(self.timeout)),
            "--", "/usr/local/bin/python3", "-I", "/app/sandbox/worker.py",
            payload=canonical({"arguments": arguments, "policy": asdict(policy)}).encode())
        if not isinstance(output, dict):
            raise TargetError("invalid_worker_response")
        if output.get("error_code"):
            raise TargetError(output["error_code"])
        if output.get("policy_digest") != policy.digest:
            raise TargetError("target_policy_mismatch")
        receipt = output.get("receipt")
        if not isinstance(receipt, dict) or receipt.get("policy_version") != policy.version:
            raise TargetError("invalid_worker_response")
        evaluate([receipt])
        provenance = {"mode": "openshell", "sandbox_id": before["id"], "policy_digest": digest(effective)}
        try:
            after, current = await self._identity()
            if digest(effective) != digest(current) or before["id"] != after["id"]:
                raise TargetError("sandbox_policy_changed")
        except TargetError as exc:
            raise TargetError(exc.code, receipt=receipt, runtime=provenance) from None
        return receipt, provenance
