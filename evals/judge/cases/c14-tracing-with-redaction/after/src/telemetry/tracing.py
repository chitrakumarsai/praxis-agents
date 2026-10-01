"""Trace agent runs: one correlation id per run, versions, timings, and redacted payloads."""

import json
import re
import time
import uuid

SECRET = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|Bearer\s+\S+)")
RETENTION_DAYS = 30


def redact(text: str) -> str:
    return SECRET.sub("[REDACTED]", text)


class RunTrace:
    def __init__(self, sink, model: str, prompt_version: str, tool_schema_version: str):
        self.run_id = uuid.uuid4().hex
        self.sink = sink
        self.versions = {"model": model, "prompt": prompt_version, "tools": tool_schema_version}
        self.started = time.monotonic()

    def event(self, kind: str, **fields) -> None:
        payload = {k: redact(v) if isinstance(v, str) else v for k, v in fields.items()}
        self.sink.write(
            json.dumps(
                {
                    "run_id": self.run_id,
                    "kind": kind,
                    "elapsed_s": round(time.monotonic() - self.started, 3),
                    "versions": self.versions,
                    "retention_days": RETENTION_DAYS,
                    **payload,
                }
            )
        )
