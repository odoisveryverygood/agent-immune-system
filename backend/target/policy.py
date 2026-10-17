"""Immutable checkout policies; deliberately vulnerable v1 is demo failure injection."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from threading import RLock


class TargetError(ValueError):
    def __init__(self, code: str, *, receipt=None, runtime=None):
        self.code = code
        self.receipt = receipt
        self.runtime = runtime
        super().__init__(code)


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value) -> str:
    return sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Policy:
    version: str
    reject_client_price: bool
    require_catalog_price: bool
    max_discount_bps: int

    def __post_init__(self):
        if not isinstance(self.version, str) or not self.version:
            raise TargetError("invalid_policy_version")
        if type(self.reject_client_price) is not bool or type(self.require_catalog_price) is not bool:
            raise TargetError("invalid_policy_boolean")
        if type(self.max_discount_bps) is not int or not 0 <= self.max_discount_bps <= 1000:
            raise TargetError("invalid_policy_discount")

    @property
    def digest(self):
        return digest(asdict(self))


VULNERABLE = Policy("v1-vulnerable", False, False, 1000)
HARDENED = Policy("v2-hardened", True, True, 1000)
ALLOWED_CHANGES = {"reject_client_price", "require_catalog_price", "max_discount_bps"}


class PolicyRegistry:
    """Compare-and-swap patches. Old versions remain available for exact replay."""

    def __init__(self):
        self._versions = {p.version: p for p in (VULNERABLE, HARDENED)}
        self._current = VULNERABLE.version
        self._lock = RLock()

    @property
    def current(self):
        with self._lock:
            return self._versions[self._current]

    def get(self, version):
        with self._lock:
            if not isinstance(version, str) or version not in self._versions:
                raise TargetError("unknown_policy_version")
            return self._versions[version]

    def apply_patch(self, patch):
        with self._lock:
            fields = {"patch_id", "based_on_policy_version", "changes", "reason", "evidence_ids"}
            if not isinstance(patch, dict) or set(patch) != fields:
                raise TargetError("invalid_patch_schema")
            if patch["based_on_policy_version"] != self._current:
                raise TargetError("stale_patch")
            if any(not isinstance(patch[k], str) or not patch[k].strip() for k in ("patch_id", "reason")):
                raise TargetError("invalid_patch_metadata")
            evidence = patch["evidence_ids"]
            if not isinstance(evidence, list) or not evidence or any(not isinstance(e, str) or not e for e in evidence):
                raise TargetError("missing_patch_evidence")
            changes = patch["changes"]
            if not isinstance(changes, dict) or not changes or not set(changes) <= ALLOWED_CHANGES:
                raise TargetError("invalid_patch_changes")
            values = asdict(self.current)
            values.update(changes)
            values["version"] = "patch-" + digest({"base": self.current.digest, "changes": changes})
            policy = Policy(**values)
            self._versions[policy.version] = policy
            self._current = policy.version
            return policy
