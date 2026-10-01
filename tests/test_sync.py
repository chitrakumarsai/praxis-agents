from dataclasses import dataclass, field

import pytest

from praxis.adapters import (
    GENERATED_NOTICE,
    Adapter,
    available_targets,
    get_adapter,
    register_adapter,
)
from praxis.sync import parse_targets, sync


@dataclass
class FakeRule:
    title: str
    body: str


@dataclass
class FakeRuleSet:
    rules: list = field(default_factory=list)


@pytest.fixture
def ruleset():
    return FakeRuleSet(
        [
            FakeRule("Testing", "Write a test for every bug fix.\n"),
            FakeRule("  Style ", "- Use type hints.\n- Keep functions short."),
        ]
    )


def test_builtin_targets_registered():
    assert {"claude", "codex"} <= set(available_targets())
    assert get_adapter("claude").filename == "CLAUDE.md"
    assert get_adapter("codex").filename == "AGENTS.md"


def test_unknown_target_lists_available():
    with pytest.raises(ValueError, match="Unknown target 'cursor'.*claude"):
        get_adapter("cursor")


@pytest.mark.parametrize(
    "value, expected",
    [
        ("claude,codex", ["claude", "codex"]),
        (" Claude , codex,claude ", ["claude", "codex"]),
        (["claude", "codex"], ["claude", "codex"]),
        (["codex,claude"], ["codex", "claude"]),
    ],
)
def test_parse_targets(value, expected):
    assert parse_targets(value) == expected


def test_parse_targets_rejects_empty_and_unknown():
    with pytest.raises(ValueError, match="No sync targets"):
        parse_targets(" , ")
    with pytest.raises(ValueError, match="Unknown target"):
        parse_targets("claude,nope")


def test_render_markdown(ruleset):
    text = get_adapter("claude").render(ruleset)
    assert text.startswith(GENERATED_NOTICE + "\n")
    assert "# CLAUDE.md" in text
    assert "## Testing\n\nWrite a test for every bug fix.\n" in text
    assert "## Style\n\n- Use type hints.\n- Keep functions short.\n" in text
    assert text.index("## Testing") < text.index("## Style")
    assert text.endswith("short.\n")


def test_render_empty_ruleset():
    text = get_adapter("codex").render(FakeRuleSet())
    assert text == f"{GENERATED_NOTICE}\n\n# AGENTS.md\n\n" \
        "Follow these project rules when working in this repository.\n"


def test_sync_writes_both_files(tmp_path, ruleset):
    results = sync(ruleset, "claude,codex", tmp_path)

    assert [(r.target, r.path.name, r.changed) for r in results] == [
        ("claude", "CLAUDE.md", True),
        ("codex", "AGENTS.md", True),
    ]
    for name in ("CLAUDE.md", "AGENTS.md"):
        text = (tmp_path / name).read_text()
        assert "## Testing" in text and "## Style" in text


def test_sync_is_idempotent(tmp_path, ruleset):
    sync(ruleset, "claude", tmp_path)
    mtime = (tmp_path / "CLAUDE.md").stat().st_mtime_ns

    results = sync(ruleset, "claude", tmp_path)

    assert results[0].changed is False
    assert (tmp_path / "CLAUDE.md").stat().st_mtime_ns == mtime


def test_sync_overwrites_stale_file(tmp_path, ruleset):
    (tmp_path / "AGENTS.md").write_text("old\n")
    [result] = sync(ruleset, "codex", tmp_path)
    assert result.changed is True
    assert "## Testing" in (tmp_path / "AGENTS.md").read_text()


def test_sync_dry_run_writes_nothing(tmp_path, ruleset):
    results = sync(ruleset, "claude,codex", tmp_path, dry_run=True)
    assert all(r.changed for r in results)
    assert list(tmp_path.iterdir()) == []


def test_sync_only_selected_target(tmp_path, ruleset):
    sync(ruleset, "codex", tmp_path)
    assert (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()


def test_custom_adapter_plugs_in(tmp_path, ruleset):
    class CursorAdapter(Adapter):
        name = "test-cursor"
        filename = ".cursorrules"

        def render(self, rs):
            return "\n".join(r.title.strip() for r in rs.rules) + "\n"

    register_adapter(CursorAdapter)
    try:
        sync(ruleset, "test-cursor", tmp_path)
        assert (tmp_path / ".cursorrules").read_text() == "Testing\nStyle\n"
    finally:
        from praxis import adapters

        adapters._REGISTRY.pop("test-cursor")
