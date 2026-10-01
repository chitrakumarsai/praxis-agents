"""Deploy assistant: runs the deploy tool, then checks the service before reporting success."""

import time

from agents.llm import run_with_tools
from agents.tools import deploy_tool
from infra import get_service_status

VERIFY_DEADLINE_S = 300


def deploy(service: str, version: str) -> dict:
    run_with_tools(f"Deploy {service} at version {version}.", tools=[deploy_tool], max_tool_calls=3)
    deadline = time.monotonic() + VERIFY_DEADLINE_S
    while time.monotonic() < deadline:
        status = get_service_status(service)
        if status.healthy and status.version == version:
            return {"status": "completed", "service": service, "version": version}
        time.sleep(10)
    return {"status": "partial", "detail": "deploy requested but not verified", "uncertain": [service]}
