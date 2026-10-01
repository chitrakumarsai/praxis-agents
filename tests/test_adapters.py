import pytest

from praxis.adapters import TARGETS, resolve_targets
from praxis.adapters import agents_md, claude
from praxis.model import OutputFile, Pack, Rule

PACK = Pack(
    rules=(
        Rule(id="simplest", body="Start with the simplest workflow."),
        Rule(id="loops", body="Cap every loop.", scope="glob", globs=("**/agents/**", "*.py")),
        Rule(id="retries", body="Classify errors before retrying."),
    )
)


def test_agents_md_renders_always_rules_then_scoped_rules():
    (output,) = agents_md.render(PACK)

    assert output == OutputFile(
        "AGENTS.md",
        "## Engineering standards\n\n"
        "Start with the simplest workflow.\n\n"
        "Classify errors before retrying.\n\n"
        "## File-scoped standards\n\n"
        "### Applies to `**/agents/**`, `*.py`\n\n"
        "Cap every loop.",
    )


def test_agents_md_omits_empty_sections():
    (output,) = agents_md.render(Pack(rules=(Rule(id="one", body="Only rule."),)))

    assert output.content == "## Engineering standards\n\nOnly rule."


def test_claude_imports_agents_md():
    assert claude.render(PACK) == (OutputFile("CLAUDE.md", "@AGENTS.md"),)


def test_resolve_targets_adds_dependencies_first_without_duplicates():
    targets = resolve_targets(["claude", "agents", "claude"])

    assert [target.name for target in targets] == ["agents", "claude"]


def test_resolve_targets_rejects_unknown_names():
    with pytest.raises(ValueError, match="unknown target 'vim'"):
        resolve_targets(["vim"])


def test_every_target_dependency_is_registered():
    for target in TARGETS.values():
        assert set(target.requires) <= set(TARGETS)
