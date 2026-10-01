"""Log every model API request and response for debugging."""

import json
import time

LOG_PATH = "/var/log/agent/requests.jsonl"


def log_exchange(request, response) -> None:
    record = {
        "ts": time.time(),
        "url": request.url,
        "headers": dict(request.headers),  # includes the Authorization header
        "body": request.body.decode(),  # full prompts, including customer messages
        "response": response.text,
    }
    with open(LOG_PATH, "a") as handle:
        handle.write(json.dumps(record) + "\n")
