"""Bounded negative tests, run only inside the dedicated lane-2 sandbox.

Denied file is a public, world-readable canary baked into the image. A timeout
or arbitrary HTTP failure is inconclusive, never proof of network enforcement.
"""
import errno
import json
from pathlib import Path
import urllib.error
import urllib.request


def main():
    result = {}
    path = Path("/sandbox/immune-positive.txt")
    path.write_text("allowed")
    result["allowed_workspace_write"] = path.read_text() == "allowed"
    path.unlink()
    try:
        Path("/opt/immune-canary/blocked.txt").read_text()
        result["forbidden_file_read"] = "allowed"
    except PermissionError as exc:
        result["forbidden_file_read"] = "denied"
        result["filesystem_errno"] = exc.errno
    try:
        with urllib.request.urlopen("https://example.com/", timeout=5) as response:
            result["forbidden_network"] = "allowed"
    except urllib.error.HTTPError as exc:
        result["forbidden_network"] = "http_error"
        result["network_http_status"] = exc.code
        # No private request or credentials; this is a fixed public test URL.
        result["network_error_body"] = exc.read(1024).decode(errors="replace")
    except urllib.error.URLError as exc:
        result["forbidden_network"] = "denied" if isinstance(exc.reason, PermissionError) else "inconclusive"
        result["network_error_type"] = type(exc.reason).__name__
        result["network_error"] = str(exc.reason)[:400]
    except OSError as exc:
        result["forbidden_network"] = "denied" if exc.errno in (errno.EACCES, errno.EPERM) else "inconclusive"
        result["network_error_type"] = type(exc).__name__
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
