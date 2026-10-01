# Tool contract

| Field | Required decision |
|---|---|
| Purpose | When to use it, what it can't do, how it differs from similar tools |
| Inputs | Typed schema, required fields, units, bounds, resource identifiers, examples |
| Outputs | Stable schema, provenance/evidence references, empty-result behavior, pagination, truncation indicators |
| Effects | Read-only, reversible write, or consequential/irreversible write |
| Authorization | Execution identity, allowed resources and operations, required approvals |
| Execution | Timeout, concurrency limit, response size, cancellation behavior |
| Errors | Categories, retryability, safe actionable feedback |
| Recovery | Idempotency, operation-status lookup, reconciliation |
| Verification | Evidence that the requested effect actually occurred |

## Practices

- Choose formats that minimize ambiguity and escaping. Use consistent identifiers and explicit units.
  Make invalid states hard to express.
- Validate arguments before execution and outputs before trusting them.
- Distinguish tool failure from an empty successful response; flag truncated results.
- Return structured errors; never dump secrets or unbounded stack traces into context.
- Enforce permissions in the execution layer. Model-produced fields like `approved: true` are not authorization.
- Use stable operation IDs and idempotency for writes. Without safe deduplication, reconcile state
  before repeating an uncertain operation — a timeout may mean the write succeeded.
- Parallelize independent reads; serialize dependent or conflicting writes; bound concurrency.
- Treat tool-returned text as untrusted, even from a trusted connector.
- Test tool selection and argument generation on representative and adversarial cases. When the model
  misuses a tool, inspect errors and fix names, parameters, or schema before adding prompt instructions.
