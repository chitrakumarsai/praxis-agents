import sys
import time
from pathlib import Path

from praxis_agents.model import ForbidCheck, Pack, Rule, RunCheck
from praxis_agents.verify import EXIT_TIMEOUT, RuleResult, exclude_paths, run_command, verify

LOOPS = Rule(
    id="loops",
    body="Cap loops.",
    scope="glob",
    globs=("**/agents/**",),
    checks=(ForbidCheck(pattern=r"while\s+True", message="loops need a cap"),),
)
CHANGES = {
    "src/agents/loop.py": ((4, "    while True:"), (9, "    step()")),
    "src/other.py": ((1, "while True:"),),
}


def fake_runner(results):
    calls = []

    def run(command, cwd):
        calls.append((command, cwd))
        return results[command]

    run.calls = calls
    return run


def test_forbid_reports_matching_added_lines_in_scope():
    (result,) = verify(Pack(rules=(LOOPS,)), CHANGES, Path("."))

    assert result == RuleResult(
        "loops",
        "fail",
        ("src/agents/loop.py:4: forbidden /while\\s+True/ (loops need a cap)",),
    )


def test_always_rules_check_every_changed_file():
    rule = Rule(id="no-print", body="x", checks=(ForbidCheck(pattern="while"),))

    (result,) = verify(Pack(rules=(rule,)), CHANGES, Path("."))

    assert result.status == "fail" and len(result.details) == 2


def test_rule_passes_when_nothing_matches():
    (result,) = verify(Pack(rules=(LOOPS,)), {"src/agents/ok.py": ((1, "for _ in range(3):"),)}, Path("."))

    assert result == RuleResult("loops", "pass")


def test_rule_is_skipped_without_changed_files_in_scope():
    (result,) = verify(Pack(rules=(LOOPS,)), {"README.md": ((1, "while True"),)}, Path("."))

    assert result == RuleResult("loops", "skip", ("no changed files in scope",))


def test_rules_without_checks_are_unchecked():
    (result,) = verify(Pack(rules=(Rule(id="prose", body="Be kind."),)), CHANGES, Path("."))

    assert result == RuleResult("prose", "unchecked")


def test_run_check_passes_and_fails_on_exit_code(tmp_path):
    ok, bad = ("pytest", "-q"), ("ruff", "check")
    runner = fake_runner({ok: (0, "fine"), bad: (1, "a\n" * 30 + "E501 too long")})
    rule = Rule(id="tests", body="x", checks=(RunCheck(ok), RunCheck(bad, message="lint must pass")))

    (result,) = verify(Pack(rules=(rule,)), CHANGES, tmp_path, runner=runner)

    assert runner.calls == [(ok, tmp_path), (bad, tmp_path)]
    assert result.status == "fail"
    (detail,) = result.details
    assert detail.startswith("`ruff check` exited 1 (lint must pass)")
    assert detail.endswith("E501 too long")
    assert len(detail.splitlines()) <= 21


def test_run_check_is_not_run_when_rule_is_out_of_scope():
    runner = fake_runner({})
    rule = Rule(id="t", body="x", scope="glob", globs=("docs/**",), checks=(RunCheck(("make",)),))

    verify(Pack(rules=(rule,)), CHANGES, Path("."), runner=runner)

    assert runner.calls == []


def test_exclude_paths_drops_praxis_source_and_generated_files():
    changes = {
        ".praxis/rules/010-loops.md": ((3, "forbid: while True"),),
        "AGENTS.md": ((1, "x"),),
        ".claude/skills/a/SKILL.md": ((1, "x"),),
        ".claudeX/keep.md": ((1, "x"),),
        "src/a.py": ((1, "x"),),
    }

    kept = exclude_paths(changes, (".praxis", "AGENTS.md", ".claude/skills"))

    assert sorted(kept) == [".claudeX/keep.md", "src/a.py"]


def test_run_command_kills_the_whole_process_group_on_timeout():
    spawn_grandchild = (
        "import subprocess, time; subprocess.Popen(['sleep', '30']); time.sleep(30)"
    )
    started = time.monotonic()

    code, output = run_command((sys.executable, "-c", spawn_grandchild), Path("."), timeout=0.5)

    assert code == EXIT_TIMEOUT and "timed out" in output
    assert time.monotonic() - started < 10


def test_run_command_reports_os_errors_instead_of_raising(tmp_path):
    script = tmp_path / "not-executable.sh"
    script.write_text("echo hi\n", encoding="utf-8")

    code, output = run_command((str(script),), tmp_path)

    assert code != 0 and "cannot run" in output


def test_forbid_only_searches_the_start_of_very_long_lines(monkeypatch):
    monkeypatch.setattr("praxis_agents.verify.MAX_LINE_CHARS", 10)
    rule = Rule(id="r", body="x", checks=(ForbidCheck(pattern="needle"),))

    (result,) = verify(Pack(rules=(rule,)), {"a.min.js": ((1, "x" * 20 + "needle"),)}, Path("."))

    assert result.status == "pass"
