import shutil
from pathlib import Path

import pytest
from conftest import git

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


def test_sync_cursor_and_copilot_targets(project):
    rules = project / ".praxis" / "rules"
    (rules / "020-loops.md").write_text(
        "---\nscope: glob\nglobs: ['**/agents/**']\n---\nCap every loop.\n", encoding="utf-8"
    )

    assert run(project, "sync", "--target", "cursor,copilot") == 0

    assert (project / "AGENTS.md").is_file()
    assert (project / ".cursor/rules/praxis-loops.mdc").is_file()
    assert (project / ".github/instructions/praxis-loops.instructions.md").is_file()
    assert "simplest workflow" in (project / ".github/copilot-instructions.md").read_text()
    assert not (project / "CLAUDE.md").exists()
    assert run(project, "check", "--target", "cursor,copilot") == 0


def test_removed_skill_is_reported_stale_then_deleted(tmp_path, capsys):
    main(["init", "agent-engineering", "--root", str(tmp_path)])
    run(tmp_path, "sync")
    shutil.rmtree(tmp_path / ".praxis" / "skills" / "rag-pipeline")
    capsys.readouterr()

    assert run(tmp_path, "check") == 1
    assert "stale: .agents/skills/rag-pipeline/SKILL.md" in capsys.readouterr().out

    assert run(tmp_path, "sync") == 0
    out = capsys.readouterr().out
    assert "removed .claude/skills/rag-pipeline/references/fields-and-diagnostics.md" in out
    assert not (tmp_path / ".agents/skills/rag-pipeline").exists()
    assert not (tmp_path / ".claude/skills/rag-pipeline").exists()
    assert run(tmp_path, "check") == 0


def test_removed_glob_rule_deletes_cursor_and_copilot_files(project):
    rule = project / ".praxis" / "rules" / "020-loops.md"
    rule.write_text("---\nscope: glob\nglobs: ['*.py']\n---\nCap.\n", encoding="utf-8")
    run(project, "sync", "--target", "cursor,copilot")

    rule.unlink()
    (project / ".praxis" / "rules" / "010-simplest.md").unlink()
    (project / ".praxis" / "skills").mkdir()
    assert run(project, "sync", "--target", "cursor,copilot") == 0

    assert not (project / ".cursor/rules/praxis-loops.mdc").exists()
    assert not (project / ".github/instructions/praxis-loops.instructions.md").exists()
    assert not (project / ".github/copilot-instructions.md").exists()


LOOP_RULE = """---
scope: glob
globs: ["**/agents/**"]
checks:
  - forbid: 'while True:'
    message: loops need an iteration cap
---
Cap every loop.
"""


@pytest.fixture
def verify_repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "feature")
    rules = tmp_path / ".praxis" / "rules"
    rules.mkdir(parents=True)
    (rules / "010-loops.md").write_text(LOOP_RULE, encoding="utf-8")
    (rules / "020-prose.md").write_text("Be kind.\n", encoding="utf-8")
    return tmp_path


def test_verify_fails_on_forbidden_added_line(verify_repo, capsys):
    agents = verify_repo / "src" / "agents"
    agents.mkdir(parents=True)
    (agents / "loop.py").write_text("def run():\n    while True:\n        pass\n", encoding="utf-8")

    assert run(verify_repo, "verify") == 1

    out = capsys.readouterr().out
    assert "FAIL loops" in out
    assert "src/agents/loop.py:2: forbidden /while True:/ (loops need an iteration cap)" in out
    assert "1 failed, 0 passed, 0 skipped, 1 unchecked" in out


def test_verify_passes_and_ignores_praxis_source_and_generated_files(verify_repo, capsys):
    run(verify_repo, "sync")  # AGENTS.md now contains rule text, but generated files are excluded
    (verify_repo / "src" / "agents").mkdir(parents=True)
    (verify_repo / "src" / "agents" / "loop.py").write_text("for _ in range(3):\n    pass\n")

    assert run(verify_repo, "verify") == 0

    out = capsys.readouterr().out
    assert "PASS loops" in out
    assert "0 failed, 1 passed, 0 skipped, 1 unchecked" in out


def test_verify_skips_rules_without_changes_in_scope(verify_repo, capsys):
    assert run(verify_repo, "verify") == 0

    assert "SKIP loops (no changed files in scope)" in capsys.readouterr().out


def test_verify_unknown_base_exits_2(verify_repo, capsys):
    assert run(verify_repo, "verify", "--base", "nope") == 2

    assert "unknown base 'nope'" in capsys.readouterr().err


def test_verify_judge_grades_unchecked_rules_and_stays_advisory(verify_repo, monkeypatch, capsys):
    from test_judge import FakeClient, reply

    client = FakeClient(
        {"prose": reply({"status": "fail", "explanation": "rude\x1b[31m", "evidence": ["notes.md:1: you are wrong"]})}
    )
    monkeypatch.setattr("praxis.judge.anthropic_backend._default_client", lambda: client)
    (verify_repo / "notes.md").write_text("you are wrong\n", encoding="utf-8")

    assert run(verify_repo, "verify", "--judge", "--judge-model", "claude-sonnet-5-5") == 0

    out = capsys.readouterr().out
    assert "JUDGE FAIL prose" in out and "notes.md:1: you are wrong" in out
    assert "\x1b" not in out  # model text is printed without control characters
    assert "judge (anthropic claude-sonnet-5-5, advisory): 1 failed, 0 passed, 0 unknown, 0 not applicable" in out
    (call,) = client.calls  # only the rule without checks, and only with files in scope
    assert call["model"] == "claude-sonnet-5-5"
    assert "you are wrong" in call["messages"][0]["content"][0]["text"]
    assert "Be kind." not in call["messages"][0]["content"][0]["text"]  # .praxis is excluded


def test_verify_without_judge_never_builds_a_client(verify_repo, monkeypatch):
    def fail():
        raise AssertionError("client built")

    monkeypatch.setattr("praxis.judge.anthropic_backend._default_client", fail)

    assert run(verify_repo, "verify") == 0


def test_judge_model_requires_judge(verify_repo):
    with pytest.raises(SystemExit) as exc:
        run(verify_repo, "verify", "--judge-model", "claude-sonnet-5-5")

    assert exc.value.code == 2


def test_verify_judge_with_openai_provider(verify_repo, monkeypatch, capsys):
    from test_judge_openai import FakeOpenAI, response

    client = FakeOpenAI(
        response({"status": "fail", "explanation": "rude", "evidence": ["notes.md:1: you are wrong"]})
    )
    monkeypatch.setattr("praxis.judge.openai_backend._default_client", lambda: client)
    (verify_repo / "notes.md").write_text("you are wrong\n", encoding="utf-8")

    assert run(verify_repo, "verify", "--judge", "--judge-provider", "openai") == 0

    out = capsys.readouterr().out
    assert "JUDGE FAIL prose" in out
    assert "judge (openai gpt-6.1-sol, advisory): 1 failed" in out


def test_judge_provider_requires_judge(verify_repo):
    with pytest.raises(SystemExit) as exc:
        run(verify_repo, "verify", "--judge-provider", "openai")

    assert exc.value.code == 2
