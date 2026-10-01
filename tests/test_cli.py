from pathlib import Path

import pytest

from praxis.cli import main


@pytest.fixture
def project(tmp_path: Path) -> Path:
    rules = tmp_path / ".praxis" / "rules"
    rules.mkdir(parents=True)
    (rules / "010-simplest.md").write_text("Start with the simplest workflow.\n", encoding="utf-8")
    return tmp_path


def run(project: Path, *args: str) -> int:
    return main([*args, "--root", str(project)])


def test_sync_writes_agents_and_claude_files(project, capsys):
    assert run(project, "sync") == 0

    assert "Start with the simplest workflow." in (project / "AGENTS.md").read_text()
    assert "@AGENTS.md" in (project / "CLAUDE.md").read_text()
    assert capsys.readouterr().out.splitlines() == ["wrote AGENTS.md", "wrote CLAUDE.md"]


def test_sync_twice_reports_up_to_date(project, capsys):
    run(project, "sync")
    capsys.readouterr()

    assert run(project, "sync") == 0
    assert capsys.readouterr().out.strip() == "already up to date"


def test_sync_respects_target_selection(project):
    assert run(project, "sync", "--target", "agents") == 0

    assert (project / "AGENTS.md").exists()
    assert not (project / "CLAUDE.md").exists()


def test_check_passes_after_sync_and_fails_after_source_edit(project, capsys):
    run(project, "sync")
    assert run(project, "check") == 0

    (project / ".praxis" / "rules" / "020-loops.md").write_text("Cap every loop.\n", encoding="utf-8")
    capsys.readouterr()

    assert run(project, "check") == 1
    out = capsys.readouterr().out
    assert "out of date: AGENTS.md" in out
    assert "CLAUDE.md" not in out


def test_check_does_not_write_files(project):
    assert run(project, "check") == 1

    assert not (project / "AGENTS.md").exists()


def test_errors_exit_2_with_message(tmp_path, capsys):
    assert run(tmp_path, "sync") == 2

    assert "praxis: error:" in capsys.readouterr().err


def test_unknown_target_exits_2(project, capsys):
    assert run(project, "sync", "--target", "vim") == 2

    assert "unknown target 'vim'" in capsys.readouterr().err


def test_empty_target_list_exits_2(project, capsys):
    assert run(project, "sync", "--target", " , ") == 2

    assert "no targets selected" in capsys.readouterr().err


def test_packs_lists_bundled_packs(capsys):
    assert main(["packs"]) == 0

    assert "agent-engineering" in capsys.readouterr().out.split()


def test_init_copies_pack_then_sync_writes_rules_and_skills(tmp_path, capsys):
    assert main(["init", "agent-engineering", "--root", str(tmp_path)]) == 0
    assert (tmp_path / ".praxis" / "rules").is_dir()

    assert run(tmp_path, "sync") == 0

    assert "Bound every loop" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    for base in (".agents/skills", ".claude/skills"):
        assert (tmp_path / base / "eval-design" / "SKILL.md").is_file()
        assert (tmp_path / base / "harness-design" / "references" / "tool-contract.md").is_file()
    assert run(tmp_path, "check") == 0


def test_init_refuses_existing_source(project, capsys):
    assert main(["init", "agent-engineering", "--root", str(project)]) == 2

    assert "already exists" in capsys.readouterr().err


def test_init_unknown_pack_exits_2(tmp_path, capsys):
    assert main(["init", "nope", "--root", str(tmp_path)]) == 2

    assert "unknown pack 'nope'" in capsys.readouterr().err


def test_init_failure_leaves_no_partial_source(tmp_path, monkeypatch, capsys):
    import praxis.bundled

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr(praxis.bundled.Path, "write_bytes", fail)

    assert main(["init", "agent-engineering", "--root", str(tmp_path)]) == 2
    assert not (tmp_path / ".praxis").exists()
    assert list(tmp_path.iterdir()) == []
