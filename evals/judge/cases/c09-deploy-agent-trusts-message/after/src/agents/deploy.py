"""Deploy assistant: asks the model to run the deploy tool and reports its result."""

from agents.llm import run_with_tools
from agents.tools import deploy_tool


def deploy(service: str, version: str) -> dict:
    reply = run_with_tools(
        f"Deploy {service} at version {version}.", tools=[deploy_tool], max_tool_calls=3
    )
    if "deployment complete" in reply.text.lower():
        return {"status": "completed", "service": service, "version": version}
    return {"status": "failed", "detail": reply.text}
