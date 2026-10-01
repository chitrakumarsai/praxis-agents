### Trace every run

- Use one correlation ID across model calls, tools, workers, approvals, and external operations.
- Record model, prompt, tool-schema, and config versions; state transitions; validation verdicts;
  retry and stop reasons; tokens, cost, and per-stage latency.
- Redact sensitive values before persistence and apply retention limits to traces.
- Replay traces only in isolated environments; a replay must never repeat real side effects.
