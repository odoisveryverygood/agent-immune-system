"""Host-owned append-only JSONL evidence with a verifiable hash chain.

The chain detects edits/truncation when its head is retained by the caller; it is
not a signature and cannot defend against a malicious host rewriting all history.
"""
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
from .policy import canonical, digest, TargetError


class EvidenceLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _read(file):
        file.seek(0)
        rows = []
        head = "0" * 64
        try:
            for line in file:
                row = json.loads(line)
                if (set(row) != {"seq", "previous", "payload", "hash"}
                        or row["seq"] != len(rows) + 1 or row["previous"] != head
                        or row["hash"] != digest({k: row[k] for k in ("seq", "previous", "payload")})):
                    raise TargetError("evidence_corrupted")
                head = row["hash"]
                rows.append(row)
        except (ValueError, TypeError, KeyError) as exc:
            if isinstance(exc, TargetError):
                raise
            raise TargetError("evidence_corrupted") from None
        return rows

    def append(self, payload):
        with self.path.open("a+", encoding="utf-8") as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            rows = self._read(file)
            row = {"seq": len(rows) + 1, "previous": rows[-1]["hash"] if rows else "0" * 64,
                   "payload": deepcopy(payload)}
            row["hash"] = digest(row)
            file.seek(0, 2)
            file.write(canonical(row) + "\n")
            file.flush()
            os.fsync(file.fileno())
            return deepcopy(row)

    def read(self):
        with self.path.open(encoding="utf-8") as file:
            fcntl.flock(file, fcntl.LOCK_SH)
            return self._read(file)
