### Design tools as narrow, explicit contracts

- Every tool states its purpose, typed inputs (units, bounds, identifiers), stable output schema,
  effects (read-only, reversible, consequential), authorization scope, timeout, and error categories.
- Distinguish an empty successful result from a failure, and mark truncated or paginated output.
- Return structured, actionable errors. Never put secrets or unbounded stack traces in model context.
- Use stable operation IDs and idempotency for writes. Serialize dependent or conflicting writes.
- When a model misuses a tool, fix the interface (names, parameters, schema) before adding prompt text.
