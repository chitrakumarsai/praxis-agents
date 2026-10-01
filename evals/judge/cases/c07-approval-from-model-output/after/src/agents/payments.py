"""Payment assistant: lets the model decide whether a vendor payment is approved."""

import json

from agents.llm import ask
from banking import send_wire


def handle_invoice(invoice) -> str:
    decision = json.loads(
        ask(
            "You review invoices. Reply with JSON: {\"approved\": bool, \"amount\": number}.",
            invoice.text,
        )
    )
    if decision["approved"]:
        send_wire(invoice.vendor_account, decision["amount"])
        return "paid"
    return "rejected"
