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
| `agents` (Codex, Cursor, Copilot, most others) | `AGENTS.md` | `.agents/skills/` | Done (default) |
| `claude` | `CLAUDE.md` → `@AGENTS.md` import | `.claude/skills/` | Done (default) |
| `cursor` | via `AGENTS.md` | `.cursor/rules/praxis-<id>.mdc` (`globs`) | Done (opt-in) |
| `copilot` | `.github/copilot-instructions.md` | `.github/instructions/praxis-<id>.instructions.md` (`applyTo`) | Done (opt-in) |

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

### Phase 2 — Skills and first pack (done)
- [x] Model + loader for skills (`SKILL.md` + `references/`), validated against the Agent Skills spec
- [x] Skills output: `agents` → `.agents/skills/` (Codex, Cursor, Copilot), `claude` → `.claude/skills/`
- [x] `agent-engineering` pack: 14 rules (~130 lines in AGENTS.md) + 5 skills with references
- [x] Packs bundled in the wheel (`src/praxis/packs/`); `praxis packs` and `praxis init <pack>`
- Known gap (deferred): skills support only `references/**/*.md` (no `scripts/` or `assets/` yet)

### Phase 3 — Scoped adapters (done)
- [x] Cursor adapter: glob rules → `.cursor/rules/praxis-<id>.mdc` (`globs`, `alwaysApply: false`);
      always-on rules reach Cursor through `AGENTS.md`
- [x] Copilot adapter: always-on rules → `.github/copilot-instructions.md` (managed block);
      glob rules → `.github/instructions/praxis-<id>.instructions.md` (`applyTo`)
- [x] Default targets are `agents,claude`; `cursor` and `copilot` are opt-in
- Trade-off: glob-scoped rules also appear in `AGENTS.md` (for tools without scoping), so Cursor and
  Copilot see them both always-on and scoped
- [x] Stale cleanup: `sync` deletes owned files (marked with the generated notice) that are no longer
      produced, prunes empty folders, and removes managed blocks no longer produced; `check` reports them
- Known gap: only the targets being synced are cleaned; dropping a target leaves its files behind

### Phase 4 — Verification (deterministic checks done)
- [x] `checks:` in rule frontmatter: `forbid` (regex on added lines) and `run` (command, no shell)
- [x] `praxis verify [--base main]`: git diff from the merge-base plus untracked files; glob-scoped
      rules see only matching files; praxis source and generated files excluded; exit 1 on failure
- [x] Bundled pack checks: `forbid` checks on 3 rules (bare retry, swallowed errors, secrets, and
      shell execution), each tested against known-bad and known-good lines like any grader
- [x] LLM judge (`praxis verify --judge`, `judge` extra): one request per unchecked rule in scope,
      shared cached diff prefix, pass/fail/not_applicable/unknown with `path:line` evidence,
      refusal and malformed output -> unknown, token limit refuses instead of truncating; advisory
- [x] OpenAI provider (`--judge-provider openai`, `judge-openai` extra): Responses API with a strict
      JSON schema; same nonce tags, grounding, and size limit as the Anthropic backend
- [x] Judge precision: `judge: false` frontmatter skips process rules (4 in the bundled pack); the
      rubric fails only what a change introduces. Live check: a harmless change got 0 failures from
      both providers; the flawed demo kept its real violations (6 failures with OpenAI, 7 with Claude)
- [x] Calibrate the judge (`evals/judge/`): 16 human-reviewed cases × 7 judged rules, 2 reps.
      Claude: 96% of violations caught, 0% false fails. OpenAI: 98% caught, 11% false fails.
      Labels were revised once after the first run (17 pairs, marked in `cases.yaml`)
- [ ] Decide whether judge failures may gate the exit code (Claude's numbers support an opt-in
      `--judge-strict`; OpenAI's 11% false-fail rate argues for keeping it advisory there)
- [ ] Grow the calibration set with real diffs from projects that use praxis
- Known limits: project root must be the git top level; `run` checks trust the rule files

## Open decisions

1. **Config file.** Keep CLI flags only, or add `praxis.toml` (source dir, default targets)?
2. ~~**Pack distribution.**~~ Decided: bundled in the wheel.
3. **Distillation workflow.** Hand-written, or a `praxis distill` helper that drafts rules for review?
4. ~~**Skill output paths.**~~ Decided: `.agents/skills/` (Codex, Cursor, Copilot) and `.claude/skills/` (Claude Code).
5. **Licensing.** Confirm shipped packs contain only original distilled text with links to sources.
6. **Generated-file policy.** Commit generated `AGENTS.md`/`CLAUDE.md`, or generate in CI only?
