# Extraction record and worked design

## Record shape

```json
{
  "field": "interest_rate",
  "status": "found",
  "candidates": [
    {
      "value": "SOFR + 2%",
      "scope": {"facility": "Revolver"},
      "evidence": {
        "document_id": "agreement-001",
        "document_version": "v1",
        "page_index": 9,
        "printed_page_label": "10",
        "quote": "The Revolving Loans bear interest at SOFR plus 2%."
      }
    }
  ],
  "validation_status": "pending"
}
```

`status` is one of `found`, `not_found`, `not_applicable`, `conflicting`, `extraction_failed`.

## Worked design: key terms from a long agreement with amendments

Scenario: a 200-page agreement plus amendments and schedules; extract 25 key terms with page-level
evidence, handle conflicts, support human review, and later compute a derived schedule.

1. **Define the terms** — meaning, units, applicability, relationships, review requirements.
2. **Ingest and version** — store originals, detect duplicates, link agreement, schedules, amendments.
3. **Parse and verify coverage** — preserve table structure and page references; flag unreadable areas.
4. **Build searchable evidence** — index clauses with document, section, effective date, scope, and access metadata.
5. **Retrieve per field or field group** — include definitions and applicable amendments; bound follow-up retrieval.
6. **Extract scoped candidates** — values with evidence and explicit missing/conflicting states.
7. **Resolve precedence carefully** — verified rules for amendment scope and effective dates; escalate the rest.
8. **Validate independently** — types, units, coverage, consistency, evidence support.
9. **Review consequential terms** — show conflicts and source pages; keep an audit trail.
10. **Compute derived values in deterministic code** — explicit assumptions (rates, day-count, calendars,
    rounding); flag missing inputs rather than inventing them.
11. **Evaluate and monitor** — per-field correctness, citation support, review effort, latency, cost.

## Release checklist

- [ ] Representative evaluation data and a held-out test set exist.
- [ ] Critical fields meet agreed release criteria.
- [ ] Missing, conflicting, and failed extraction states are distinguishable.
- [ ] Citations resolve to versioned sources and support the relevant claims.
- [ ] Access checks cover retrieval, caches, review, and export.
- [ ] Injection and unauthorized tool-use scenarios have been tested.
- [ ] Retries, duplicate jobs, crashes, and interruptions recover safely.
- [ ] Human review and escalation paths are usable.
