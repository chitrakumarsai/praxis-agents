"""Route support tickets with one model call and deterministic routing."""

import json

import anthropic

client = anthropic.Anthropic()
QUEUES = {"billing": "queue-billing", "bug": "queue-eng", "account": "queue-accounts"}
SCHEMA = {
    "type": "object",
    "properties": {"category": {"type": "string", "enum": sorted(QUEUES)}},
    "required": ["category"],
    "additionalProperties": False,
}


def route(ticket_text: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        messages=[{"role": "user", "content": f"Classify this support ticket:\n{ticket_text}"}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    category = json.loads(response.content[0].text)["category"]
    return QUEUES.get(category, "queue-triage")
