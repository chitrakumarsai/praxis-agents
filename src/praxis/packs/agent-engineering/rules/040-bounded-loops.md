### Bound every loop

- Every agent, correction, or evaluator-optimizer loop needs limits on iterations, wall-clock time,
  tokens/cost, tool calls, and correction attempts, plus a no-progress rule.
- Detect repeated action/error signatures without state change and stop.
- End runs with an explicit status: `completed`, `partial`, `needs_human`, `failed`, `cancelled`,
  or `budget_exhausted`. A budget stop is not success.
- On every terminal path, checkpoint known state, list uncertain external effects, and report
  completed and unfinished work honestly.
