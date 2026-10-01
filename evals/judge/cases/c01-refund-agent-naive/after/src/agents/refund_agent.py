"""Refund agent: reads a support ticket and issues a refund when the model decides to."""

import json

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

client = anthropic.Anthropic()
MAX_TURNS = 8


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=20))
def call_model(messages):
    return client.messages.create(model="claude-opus-5-5", max_tokens=1024, messages=messages)


def run(ticket, issue_refund):
    messages = [{"role": "user", "content": ticket.body}]
    for _ in range(MAX_TURNS):
        reply = call_model(messages)
        plan = json.loads(reply.content[0].text)
        if plan.get("approved"):
            issue_refund(ticket.order_id, plan["amount"])
            return "completed"
        messages.append({"role": "assistant", "content": reply.content})
        messages.append({"role": "user", "content": "Continue."})
    return "budget_exhausted"
