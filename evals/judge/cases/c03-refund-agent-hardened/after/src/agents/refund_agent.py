"""Refund agent with a bounded tool loop, human approval, and verified outcomes."""

import time
import uuid
from dataclasses import dataclass, field

from agents.approvals import request_approval
from agents.llm import propose_next_action
from agents.tools import TOOLS, validate_args
from billing import get_refund, issue_refund
from telemetry import trace

MAX_TURNS = 8
MAX_TOOL_CALLS = 12
DEADLINE_S = 120
MAX_COST_USD = 0.50
MAX_REPEATS = 2


@dataclass
class RunState:
    ticket_id: str
    goal: str
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    evidence: list = field(default_factory=list)  # (tool, args, result_ref)
    tool_calls: int = 0
    cost_usd: float = 0.0
    seen_actions: dict = field(default_factory=dict)
    uncertain_effects: list = field(default_factory=list)


def run(ticket, checkpoint) -> dict:
    state = RunState(ticket_id=ticket.id, goal=f"Resolve refund request on order {ticket.order_id}")
    started = time.monotonic()
    for _ in range(MAX_TURNS):
        if time.monotonic() - started > DEADLINE_S or state.cost_usd > MAX_COST_USD:
            return finish(state, "budget_exhausted", checkpoint)
        action = propose_next_action(state)  # builds context from state.goal and state.evidence
        state.cost_usd += action.cost_usd
        trace(state.run_id, "proposal", kind=action.kind, model=action.model, tokens=action.tokens)
        signature = (action.kind, action.tool, repr(action.args))
        state.seen_actions[signature] = state.seen_actions.get(signature, 0) + 1
        if state.seen_actions[signature] > MAX_REPEATS:
            return finish(state, "failed", checkpoint, reason="no progress: repeated action")
        if action.kind == "tool":
            if state.tool_calls >= MAX_TOOL_CALLS:
                return finish(state, "budget_exhausted", checkpoint)
            args = validate_args(action.tool, action.args)  # raises on invalid or unauthorized
            result = TOOLS[action.tool](**args)
            state.tool_calls += 1
            state.evidence.append((action.tool, args, result.ref))
            trace(state.run_id, "tool", tool=action.tool, status=result.status)
        elif action.kind == "refund":
            amount = action.args["amount"]
            approval = request_approval(
                run_id=state.run_id,
                action="refund",
                params={"order_id": ticket.order_id, "amount": amount},
                evidence=state.evidence,
                timeout_s=3600,
            )
            trace(state.run_id, "approval", status=approval.status, approver=approval.approver)
            if approval.status != "approved":  # timeout and silence are not consent
                return finish(state, "needs_human", checkpoint, reason=approval.status)
            refund_id = issue_refund(ticket.order_id, amount, idempotency_key=state.run_id)
            refund = get_refund(refund_id)  # authoritative state, not the model's word
            if refund is None or refund.status != "succeeded":
                state.uncertain_effects.append(refund_id)
                return finish(state, "partial", checkpoint, reason="refund not confirmed")
            return finish(state, "completed", checkpoint)
    return finish(state, "budget_exhausted", checkpoint)


def finish(state: RunState, status: str, checkpoint, reason: str = "") -> dict:
    checkpoint(state)
    trace(state.run_id, "stop", status=status, reason=reason, cost_usd=state.cost_usd)
    return {"status": status, "reason": reason, "uncertain_effects": state.uncertain_effects}
