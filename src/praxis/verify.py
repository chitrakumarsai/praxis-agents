"""Run each rule's deterministic checks against the lines a change added."""

from __future__ import annotations

import os
import re
import shlex
import signal
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from praxis.gitdiff import AddedLines
from praxis.globs import matches
from praxis.model import ForbidCheck, Pack, Rule, RunCheck

Status = Literal["pass", "fail", "skip", "unchecked"]
Runner = Callable[[tuple[str, ...], Path], tuple[int, str]]  # (argv, cwd) -> (exit code, output)

RUN_TIMEOUT_SECONDS = 600
OUTPUT_TAIL_LINES = 20
EXIT_CANNOT_RUN, EXIT_NOT_FOUND, EXIT_TIMEOUT = 126, 127, 124
# Forbid patterns only see the start of each line, bounding the cost of a pathological regex.
MAX_LINE_CHARS = 10_000


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    status: Status
    details: tuple[str, ...] = ()


def run_command(
    command: tuple[str, ...], cwd: Path, timeout: float = RUN_TIMEOUT_SECONDS
) -> tuple[int, str]:
    """Run ``command`` without a shell; return its exit code and combined output."""
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,  # own process group, so a timeout can stop its children too
        )
    except FileNotFoundError:
        return EXIT_NOT_FOUND, f"command not found: {command[0]}"
    except OSError as exc:
        return EXIT_CANNOT_RUN, f"cannot run {command[0]}: {exc}"
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(process)
        process.communicate()
        return EXIT_TIMEOUT, f"timed out after {timeout}s"
    return process.returncode, output


def _kill_group(process: subprocess.Popen[str]) -> None:
    if hasattr(os, "killpg"):
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
    process.kill()


def exclude_paths(changes: AddedLines, prefixes: Iterable[str]) -> AddedLines:
    """Drop changes under any of ``prefixes`` (praxis source and generated files)."""
    roots = tuple(prefix.rstrip("/") for prefix in prefixes)
    return {
        path: lines
        for path, lines in changes.items()
        if not any(path == root or path.startswith(f"{root}/") for root in roots)
    }


def verify(
    pack: Pack, changes: AddedLines, root: Path, runner: Runner = run_command
) -> tuple[RuleResult, ...]:
    return tuple(_verify_rule(rule, changes, root, runner) for rule in pack.rules)


def _verify_rule(rule: Rule, changes: AddedLines, root: Path, runner: Runner) -> RuleResult:
    if not rule.checks:
        return RuleResult(rule.id, "unchecked")
    in_scope = {
        path: lines
        for path, lines in sorted(changes.items())
        if rule.scope == "always" or matches(path, rule.globs)
    }
    if not in_scope:
        return RuleResult(rule.id, "skip", ("no changed files in scope",))

    failures = []
    for check in rule.checks:
        if isinstance(check, ForbidCheck):
            failures.extend(_forbidden_lines(check, in_scope))
        else:
            failures.extend(_failed_run(check, root, runner))
    return RuleResult(rule.id, "fail" if failures else "pass", tuple(failures))


def _forbidden_lines(check: ForbidCheck, changes: AddedLines) -> list[str]:
    pattern = re.compile(check.pattern)
    note = f" ({check.message})" if check.message else ""
    return [
        f"{path}:{number}: forbidden /{check.pattern}/{note}"
        for path, lines in changes.items()
        for number, text in lines
        if pattern.search(text[:MAX_LINE_CHARS])
    ]


def _failed_run(check: RunCheck, root: Path, runner: Runner) -> list[str]:
    code, output = runner(check.command, root)
    if code == 0:
        return []
    note = f" ({check.message})" if check.message else ""
    tail = "\n".join(output.strip().splitlines()[-OUTPUT_TAIL_LINES:])
    return [f"`{shlex.join(check.command)}` exited {code}{note}" + (f"\n{tail}" if tail else "")]
