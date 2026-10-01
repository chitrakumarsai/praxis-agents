# praxis-agents — Ideas and Plan

> Write engineering standards once, in Markdown. Compile them into every AI coding agent's native format.

## Core idea

praxis is a **compiler, not an agent runtime**. Markdown is the single source of truth; praxis parses it
into one intermediate model and renders it into the instruction files each tool already reads
(`AGENTS.md`, `CLAUDE.md`, Cursor rules, Copilot instructions, Agent Skills).

```
Markdown source (.praxis/)  ──load──▶  Pack (model)  ──render──▶  per-target files  ──sync──▶  project
                                                                                          │
                                                               praxis check (CI) ◀────────┘ drift?
```

## Problem

- Engineering guidance lives in long docs that agents never read.
- Tool-specific files (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, `.github/copilot-instructions.md`)
  are maintained by hand and drift out of sync.
- Long docs can't simply be pasted into those files: they're loaded on every request,
  and long instruction files get followed less reliably.

## Content tiers

| Tier | Size | Loaded | Example |
|---|---|---|---|
| **Rules** | ~100–150 lines total | Always | "Every agent loop has a max-iteration cap and a deterministic stop condition." |
| **Skills** | Short `SKILL.md` each | On demand, picked by description | `eval-design`, `harness-design`, `agent-architecture` |
| **References** | Long-form | Read by a skill when it needs depth | Full harness guide, checklists, kickoff templates |

## Source material triage

From `~/Desktop/AI Agent Learnings/`:

| File | Use |
|---|---|
| `Building-Effective-AI-Agents-Project-Agnostic.md` | Distill → rules + `agent-architecture` skill |
| `AI-Agent-Harness-Best-Practices.md` | Distill → rules + `harness-design`, `eval-design` skills; checklists/templates → references |
| `Senior_AI_Engineer_Best_Practices.md` | Distill → `rag-pipeline`, `structured-extraction` skills |
| `Building Effective AI Agents_Anthropic.md` | Reference only — link to the original, don't redistribute |
| `Demystifying evals for AI agents_Anthropic.md` | Reference only — link to the original, don't redistribute |
| `Senior_AI_Engineer_Interview_QA.md` | Excluded — Q&A isn't agent instruction |
| `*.pdf` | Duplicates of the `.md` files — ignored |

Distillation is a **one-time, human-reviewed** step (LLM-assisted is fine), not something praxis does on every run.

## Targets

| Target | Always-on | Scoped / on-demand | Status |
|---|---|---|---|
| `agents` (Codex, Cursor, Copilot, most others) | `AGENTS.md` | — | Phase 1 |
| `claude` | `CLAUDE.md` → `@AGENTS.md` import | `.claude/skills/` | Phase 1 (rules), Phase 2 (skills) |
| `cursor` | `.cursor/rules/*.mdc` (`alwaysApply`) | `.mdc` with `globs` / `description` | Phase 3 |
| `copilot` | `.github/copilot-instructions.md` | `.github/instructions/*.instructions.md` (`applyTo`) | Phase 3 |

Tool file paths change often. Each tool lives in its own adapter module; verify paths against
current docs when writing an adapter.

## Source format

```
.praxis/
└── rules/
    ├── 010-simplest-architecture.md
    └── 020-bounded-loops.md
```

```markdown
---
id: bounded-agent-loop        # optional, defaults to the file name
scope: glob                   # always (default) | glob
globs: ["**/agents/**"]       # required for scope: glob
---
Every agent loop must have a max-iteration cap, a cost/time budget,
and a deterministic stop condition.
```

Rules render in file-name order, so numeric prefixes control ordering.

## Design principles

- **Managed blocks.** praxis only writes between `<!-- praxis:begin -->` and `<!-- praxis:end -->`;
  user edits outside the block are preserved.
- **Drift detection.** `praxis check` exits 1 when generated files are stale — wire into CI / pre-commit.
- **Immutable model.** Frozen dataclasses; adapters are pure `Pack -> OutputFile[]` functions.
- **Fail fast.** Malformed source raises a clear error naming the file.
- **Minimal dependencies.** Only `pyyaml` for frontmatter.

## Phases

### Phase 1 — Core compiler (done)
- [x] Model: `Rule`, `Pack`, `OutputFile`
- [x] Loader: Markdown + YAML frontmatter → `Pack`, with validation
- [x] Adapters: `agents` (`AGENTS.md`), `claude` (`CLAUDE.md` importing `AGENTS.md`)
- [x] Sync engine: managed blocks, plan/apply
- [x] CLI: `praxis sync`, `praxis check`
- [x] Hardening from review: markers rejected in rule bodies, CRLF preserved, atomic writes
      (mode + symlinks kept), numeric prefix ordering, BOM-safe reads, hidden files skipped
- Known gaps (deferred): a marker quoted inside a code fence in a user's file still counts as a
  real marker; multi-file sync isn't transactional (each file is atomic on its own)

### Phase 2 — Skills and first pack
- [ ] Model + loader for skills (`SKILL.md` + `references/`), validated against the Agent Skills spec
- [ ] Skills output for each target that supports them
- [x] Draft `packs/agent-engineering/`: 14 rules (~130 lines in AGENTS.md) + 5 skills with references — **awaiting review**
- [ ] `praxis init --pack agent-engineering`: bundled starter pack distilled from the source material

### Phase 3 — Scoped adapters
- [ ] Cursor `.mdc` adapter (globs → `globs`, always → `alwaysApply`)
- [ ] Copilot adapter (globs → `applyTo`)

### Phase 4 — Verification
- [ ] Check agent output against rules: deterministic graders first, LLM-judge rubrics second
      (per the evals guide)

## Open decisions

1. **Config file.** Keep CLI flags only, or add `praxis.toml` (source dir, default targets)?
2. **Pack distribution.** Bundle packs in the wheel, or install them from git / separate packages?
3. **Distillation workflow.** Hand-written, or a `praxis distill` helper that drafts rules for review?
4. **Skill output paths.** Which skills directory per tool (verify current docs for Codex, Cursor, Copilot).
5. **Licensing.** Confirm shipped packs contain only original distilled text with links to sources.
6. **Generated-file policy.** Commit generated `AGENTS.md`/`CLAUDE.md`, or generate in CI only?
