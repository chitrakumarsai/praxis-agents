"""Payment assistant: the model drafts a payment; a human approves the exact payment."""

import hashlib
import json

from agents.llm import ask
from approvals import request_approval
from banking import send_wire


def handle_invoice(invoice) -> str:
    draft = json.loads(ask("Extract the payee account and amount as JSON.", invoice.text))
    params = {"account": draft["account"], "amount": draft["amount"], "invoice": invoice.id}
    digest = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    approval = request_approval(
        action="send_wire",
        params=params,
        params_digest=digest,
        evidence=[invoice.id],
        timeout_s=86_400,
    )
    if approval.status != "approved" or approval.params_digest != digest:
        return "needs_human"  # rejection, timeout, or changed parameters: no payment
    send_wire(params["account"], params["amount"])
    return "paid"
