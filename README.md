# praxis-agents

> Put your engineering best practices into practice, across every AI coding agent.

**praxis-agents** is a Python library that takes your Markdown files of best practices, conventions, and engineering standards and applies them to AI coding tools such as Claude Code, Codex, and others.

Write your standards once. Every agent follows them.

## Why

Engineering guidance usually sits in docs that agents never read, or in tool-specific files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`) that drift out of sync. praxis-agents makes your Markdown the single source of truth.

## Features

- **Single source of truth:** author rules in plain Markdown
- **Multi-tool adapters:** compile and sync to Claude, Codex, and more
- **Verification:** check that agent output follows your rules
- **Extensible:** add an adapter for any tool

## Install

    uv tool install praxis-agents    # not yet published to PyPI

## Quick start

Start from a bundled pack, or write your own source in `.praxis/`:

    praxis packs                        # list bundled packs
    praxis init agent-engineering       # copy a pack into .praxis/
    praxis sync                         # write AGENTS.md, CLAUDE.md, and skills

### Rules

Always-on rules live in `.praxis/rules/*.md`, ordered by their numeric file-name prefix:

```markdown
---
scope: glob                # always (default) | glob
globs: ["**/agents/**"]    # required when scope is glob; no commas (write *.{ts,tsx} as two globs)
---
Every agent loop has a max-iteration cap and a deterministic stop condition.
```

### Skills

On-demand skills use the [Agent Skills](https://agentskills.io) format:
`.praxis/skills/<name>/SKILL.md` (frontmatter `name` and `description`) plus optional
`references/**/*.md`.

### Targets

| Target | Writes | Read by |
|---|---|---|
| `agents` | `AGENTS.md`, `.agents/skills/` | Codex, Cursor, GitHub Copilot, and others |
| `claude` | `CLAUDE.md` (imports `AGENTS.md`), `.claude/skills/` | Claude Code |
| `cursor` (opt-in) | `.cursor/rules/praxis-<id>.mdc` per glob-scoped rule | Cursor |
| `copilot` (opt-in) | `.github/copilot-instructions.md`, `.github/instructions/praxis-<id>.instructions.md` per glob-scoped rule | GitHub Copilot Chat, code review, cloud agent |

Cursor and Copilot already read `AGENTS.md` and `.agents/skills/`, so the default is `agents,claude`.
Add `cursor` or `copilot` when you want glob-scoped rules to load only for matching files.
Glob-scoped rules also stay in `AGENTS.md` for tools without scoping, and Copilot's coding agent
reads both `AGENTS.md` and `copilot-instructions.md`, so some rules reach it twice.

    praxis sync                     # default targets: agents, claude
    praxis sync --target agents,claude,cursor,copilot
    praxis sync --target agents     # only AGENTS.md
    praxis check                    # exit 1 if generated files are stale (for CI)

In `AGENTS.md` and `CLAUDE.md`, praxis only edits the section between `<!-- praxis:begin -->` and
`<!-- praxis:end -->`; anything you write outside it is kept. Skill, Cursor, and Copilot instruction
files are owned by praxis and marked with a generated-file comment; praxis refuses to overwrite a
file it didn't write.

When you remove a rule or skill from the source, `praxis sync` deletes the files it generated for it
(and `praxis check` reports them as stale). Only the targets you sync are cleaned: if you stop using
a target, delete its files yourself.

## Verify

Rules can carry deterministic checks that `praxis verify` runs against the lines your change added
since it diverged from a base branch (commits, uncommitted edits, and untracked files):

```markdown
---
scope: glob
globs: ["**/agents/**"]
checks:
  - forbid: 'while\s+True'          # Python regex, matched against added lines
    message: loops need an iteration cap
  - run: uv run pytest -q tests/agents   # runs without a shell when the change touches the scope
---
Agent loops read their iteration cap from config.
```

    praxis verify                 # compare with main
    praxis verify --base HEAD~1

    FAIL agent-loops
      src/agents/loop.py:2: forbidden /while\s+True/ (loops need an iteration cap)
    1 failed, 0 passed, 0 skipped, 14 unchecked

It exits 1 when a check fails, so it can gate CI or a pre-commit hook. Rules without checks are
counted as unchecked. The praxis source and generated files are never checked.

- `run` checks execute commands from the rule files on the branch being verified, the same trust
  level as a Makefile. Review rule changes like code, and don't run `praxis verify` on untrusted
  pull requests in CI with secrets available.
- `forbid` patterns are Python regexes from your rule files; only the first 10,000 characters of each
  line are searched, and untracked files over 1 MB are skipped.

### LLM judge (optional)

Most rules are principles a regex can't check. `--judge` has an LLM grade the change against each
rule without checks that touches a changed file. Two providers are supported:

| Provider | Install | Credentials | Default model |
|---|---|---|---|
| `anthropic` (default) | `praxis-agents[judge]` | `ANTHROPIC_API_KEY` or an `ant auth login` profile | `claude-opus-5-5` |
| `openai` | `praxis-agents[judge-openai]` | `OPENAI_API_KEY` | `gpt-6.1-sol` |

    praxis verify --judge
    praxis verify --judge --judge-model claude-sonnet-5-5
    praxis verify --judge --judge-provider openai --judge-model gpt-6-astra

praxis doesn't load `.env` files itself. Copy `.env.example` to `.env` (it's git-ignored), fill it
in, and export it into the shell first: `set -a; . ./.env; set +a`.

    JUDGE FAIL human-handoff
      Approval is read from the model's own output instead of a recorded approval.
      src/agents/approve.py:14: if plan.approved:
    judge (claude-opus-5-5, advisory): 1 failed, 2 passed, 0 unknown, 8 not applicable

- Costs one request per graded rule; the diff is a shared prefix that both providers cache.
- Add `judge: false` to a rule's frontmatter to skip it: process rules (planning, measurement,
  evaluation practice) can't be seen in a diff. The bundled pack marks four rules this way.
- The judge fails only what the change itself introduces; practices that belong to the wider system
  (tracing, metrics, planning) count as not applicable rather than failures of a small change.
- Verdicts are `pass`, `fail` (with `path:line` evidence), `not_applicable`, or `unknown`.
  Refusals, cut-off answers, and malformed output count as `unknown`, never `pass`.
- Judge results are advisory by default and don't change the exit code. Add `--judge-strict` to
  make a judge `fail` exit 1 like a failed check; `unknown` and `not_applicable` never fail the run,
  so a refusal or a cut-off answer can't block a merge.
- Calibration (`evals/judge/`, 16 reviewed cases): Claude caught 96% of violations with no false
  fails; OpenAI caught 98% with 11% false fails. Prefer `--judge-strict` with Claude, or expect
  about one false failure in ten non-violations with OpenAI. See `evals/judge/RESULTS.md`.
- Diffs over 200k tokens are refused rather than truncated.
- The diff is sent to the provider's API; the praxis source and generated files are left out.

## Development

This project uses [uv](https://docs.astral.sh/uv/):

    uv sync --extra dev        # includes the judge's SDK so its tests run
    uv run pytest

See [ideas.md](ideas.md) for the roadmap and open decisions.
