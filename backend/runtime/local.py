from ..target.store import checkout


class LocalFixtureRuntime:
    """No isolation. This runtime never claims OpenShell provenance."""
    async def execute(self, arguments, policy):
        runtime = {"mode": "local_fixture", "sandbox_id": None, "policy_digest": policy.digest}
        return checkout(arguments, policy), runtime
