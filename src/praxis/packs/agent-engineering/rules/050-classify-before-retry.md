### Classify failures before retrying

- Transient/rate-limit errors on safe operations: bounded exponential backoff with jitter,
  drawn from a shared retry budget.
- Invalid arguments or schema: return precise validation feedback and repair only the failed part.
  Never resend the identical bad request.
- Missing prerequisite: acquire it if authorized, otherwise report or escalate. Never invent inputs.
- Timeout after a write: query status and reconcile before retrying. A lost response does not
  mean the write failed.
- Keep infrastructure retries separate from model correction attempts; both count against one
  global run budget, including nested workers.
