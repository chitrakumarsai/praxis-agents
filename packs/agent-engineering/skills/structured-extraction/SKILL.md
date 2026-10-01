---
name: structured-extraction
description: Design or review LLM-based structured extraction from documents into typed fields - field specifications, structured outputs and schema validation, explicit missing/conflicting states, evidence and citations, per-field evaluation, and human review. Use when extracting fields, entities, or terms from documents into JSON or a database, or when building review workflows for extracted values.
---

# Structured extraction

## Specify fields before prompting

For every field define: meaning, units, allowed formats, applicability, relationships to other
fields, missing-value behavior, evidence requirements, and whether it needs human review. Vague
field definitions produce disagreement that no model can fix.

## Extract with explicit states and evidence

- Separate instructions from quoted document content. Documents are evidence, never authority.
- Use the provider's structured-output mechanism for machine-consumed results, **then validate in
  application code**. Schema validity and factual correctness are separate checks.
- Distinguish `found`, `not_found`, `not_applicable`, `conflicting`, and `extraction_failed`.
  Never collapse them into an unexplained null.
- Keep multiple candidates when values vary by scope (facility, currency, date) instead of picking one.
- Attach evidence to every candidate: document ID and version, page index, printed page label, quote.
- Check field coverage explicitly; retry only failed or unresolved fields.
- Model-reported confidence is an uncalibrated signal. Set automation thresholds from observed
  error rates on labeled data.

Example record shape: `references/extraction-record.md`.

## Validate independently

Check types, units, required coverage, cross-field consistency, and evidence support in code.
Resolve precedence (e.g., amendments vs. original terms) only with verified rules for scope and
effective dates; escalate unresolved interpretation. Do downstream calculations (schedules, totals,
conversions) in deterministic code from approved values, with explicit assumptions — flag missing
inputs instead of inventing them.

## Human review

- Show the candidate beside its source page, surrounding context, competing candidates, and the
  review reason.
- Store the original extraction and the reviewer's decision separately, with actor, timestamp, rationale.
- Route review by field criticality, ambiguity, validation failures, and measured reliability.
- Reviewer corrections aren't automatically ground truth; adjudicate disagreements before adding labels.

## Evaluate per field

- Evaluate critical fields individually; a weighted average must not hide failures on important terms.
- Normalize dates, numbers, currencies, and units before comparing; use explicit tolerances.
- Measure per-field precision/recall, citation support, review rate, reviewer changes, accepted-error rate.
- Track abstentions alongside accuracy so a system that answers almost nothing isn't rewarded.
- Include scans, complex tables, amendments, ambiguous terms, missing fields, and contradictory sources.
- Keep related document versions in the same split to avoid leakage.

A worked end-to-end design (multi-document agreement extraction) is in `references/extraction-record.md`.
