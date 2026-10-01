### Keep state explicit; build context from it

- State is the authoritative structured record of a run; conversation text is not a database.
  Track goal, constraints, completed work, evidence references, attempt counts, and remaining budgets.
- Context is a selected view of state plus evidence. Reference large artifacts instead of re-embedding
  them, and reserve room for tool results and finalization.
- Summaries keep provenance and uncertainty; never turn guesses into facts.
- Add cross-run memory only with a defined purpose, access scope, correction path, and retention policy.
- Isolate users and tenants across state, retrieval, memory, caches, and telemetry.
