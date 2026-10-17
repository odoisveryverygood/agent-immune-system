"""Fixed sandbox entry point. No eval, subprocess, providers, or host credentials."""
import json
import sys

sys.path.insert(0, "/app")
from backend.target.policy import Policy, TargetError, canonical
from backend.target.store import checkout


def main():
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise TargetError("worker_input_too_large")
        request = json.loads(raw)
        if not isinstance(request, dict) or set(request) != {"arguments", "policy"}:
            raise TargetError("invalid_worker_request")
        policy = Policy(**request["policy"])
        output = {"receipt": checkout(request["arguments"], policy), "policy_digest": policy.digest,
                  "error_code": None}
    except TargetError as exc:
        output = {"error_code": exc.code}
    except (ValueError, TypeError, KeyError, RecursionError):
        output = {"error_code": "invalid_worker_request"}
    print(canonical(output))


if __name__ == "__main__":
    main()
