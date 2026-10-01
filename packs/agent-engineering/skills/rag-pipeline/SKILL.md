---
name: rag-pipeline
description: Build, debug, or review a retrieval-augmented generation (RAG) pipeline over documents - ingestion and parsing (PDFs, scans, tables), structure-aware chunking, lexical/dense/hybrid retrieval, reranking, access control, caching, and per-layer evaluation. Use when working on document ingestion, embeddings, search indexes, retrieval quality, or answers that cite sources.
---

# RAG pipeline

```text
Upload -> object storage -> durable queue -> parse/OCR -> quality checks
       -> structure-aware chunks -> metadata + search indexes

Request -> authn + authz -> retrieval -> optional reranking -> evidence selection
        -> generation/extraction -> validation -> human review if required -> answer + citations
```

Keep ingestion, parsing, retrieval, generation, validation, and presentation behind explicit
interfaces so each can be replaced and evaluated independently. Keep original documents immutable;
store parsed and derived outputs separately, linked to source versions. Run document processing in
workers with durable job state, separate from interactive APIs.

## Ingestion and parsing

- Route by document type: native text, scans, tables, forms, mixed layouts, handwriting. Evaluate
  text, Markdown, OCR, and multimodal parsing on representative samples — none is universally best.
- Preserve headings, reading order, table headers, footnotes, units, and cell relationships.
- Keep both physical page index and printed page label; they differ.
- Content hashes for exact duplicates. Semantic similarity is a review signal, not proof two versions
  are interchangeable.
- Link amendments to the agreement and clauses they modify, with effective dates and scope. A later
  document doesn't automatically override every earlier term.
- Quarantine or flag extraction failures. Never index empty or corrupted content as success.

Metadata and trace field lists: `references/fields-and-diagnostics.md`.

## Chunking and retrieval

- Chunk on document structure first (sections, clauses, definitions, schedules, tables), then apply
  size limits without breaking those boundaries. Keep parent-child links for context expansion.
- Compare lexical, dense, and hybrid retrieval on labeled queries; exact identifiers and conceptual
  questions behave differently.
- Tune chunk size, overlap, candidate count, and context limits from downstream results, not defaults.
- Add a reranker only when evidence is retrieved but poorly ordered, and confirm it pays for its latency.
- Expand queries carefully: related terms (e.g., "net income" vs. "operating profit") are not interchangeable.
- Add multi-step retrieval only for questions that need linked definitions, amendments, or cross-document evidence.
- **Enforce access control before candidates reach the model**, including during expansion and reranking.

## Diagnose retrieval vs. generation

Feed known-correct evidence directly to generation. If the answer improves, investigate retrieval and
context assembly; if it stays wrong, investigate interpretation and generation. Both can fail on the
same request — evaluate them separately:

| Layer | Measure | Inspect |
|---|---|---|
| Parsing | Text/table fidelity, page coverage | Missing rows, reading order, units |
| Retrieval | Recall@K, MRR or NDCG | Is required evidence found and ranked? |
| Generation | Correctness, support, completeness | Unsupported or incomplete claims |
| Citations | Reference validity, claim support | Right page vs. genuinely supporting text |
| Operations | p50/p95 latency, errors, cost per successful task | Outliers, retry overhead |

Re-evaluate after any change to parsers, chunking, indexes, embeddings, prompts, or models. When
changing embeddings, build and validate a new compatible index and keep a rollback path.

## Caching

Key caches on every dependency: document versions, parser, chunker, prompt, model, retrieval config,
and authorization scope. Re-check authorization on cache hits. Invalidate when documents, permissions,
or config change. Treat semantic caching with suspicion — similar questions can need different answers,
dates, or access rights.

## Security

Prompt injection arrives through retrieved documents; RAG doesn't prevent it. Derive tenant identity
from authenticated context, never a request field. Enforce tenant and document permissions across
storage, retrieval, caches, exports, and review UIs. Test cross-tenant retrieval and malicious documents.
