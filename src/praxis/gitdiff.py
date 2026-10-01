"""Lines added by a change: git diff from the merge-base with a base ref, plus untracked files."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

AddedLines = dict[str, tuple[tuple[int, str], ...]]  # root-relative path -> (line number, text)

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
DIFF_ARGS = ("--no-color", "--no-ext-diff", "--no-renames", "--unified=0", "--diff-filter=d")
# Untracked files above this size (build output, bundles) are skipped rather than scanned.
MAX_UNTRACKED_BYTES = 1_000_000
# Escapes git uses in C-quoted paths, besides \ooo octal bytes.
C_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


class GitError(ValueError):
    """Raised when the change set can't be read from git."""


def added_lines(root: Path, base: str) -> AddedLines:
    """Lines added under ``root`` since ``base`` diverged: commits, edits, and untracked files.

    Paths are relative to ``root``, which may be below the git top level.
    """
    merge_base = _merge_base(root, base)
    # --relative limits the diff to ``root`` and makes its paths relative to it.
    diff = _git(root, "-c", "core.quotePath=false", "diff", "--relative", *DIFF_ARGS, merge_base)
    changes = parse_diff(diff)
    for relpath in _untracked(root):
        lines = _text_lines(root / relpath)
        if lines:
            changes[relpath] = tuple(enumerate(lines, start=1))
    return changes


def unified_diff(root: Path, base: str, exclude: Iterable[str] = ()) -> str:
    """The change as a readable unified diff with context, for review; untracked files included.

    Paths under any ``exclude`` prefix (praxis source, generated files) are left out.
    """
    prefixes = tuple(exclude)
    merge_base = _merge_base(root, base)
    pathspec = [".", *(f":(exclude,literal){prefix}" for prefix in prefixes)]
    tracked = _git(
        root, "-c", "core.quotePath=false", "diff", "--relative", "--no-color", "--no-ext-diff",
        "--no-renames", merge_base, "--", *pathspec,
    )
    sections = [tracked.rstrip("\n")] if tracked.strip() else []
    for relpath in _untracked(root):
        lines = [] if is_excluded(relpath, prefixes) else _text_lines(root / relpath)
        if lines:
            body = "\n".join(f"+{line}" for line in lines)
            sections.append(
                f"diff --git a/{relpath} b/{relpath}\nnew file (untracked)\n--- /dev/null\n"
                f"+++ b/{relpath}\n@@ -0,0 +1,{len(lines)} @@\n{body}"
            )
    return "\n".join(sections) + "\n" if sections else ""


def is_excluded(path: str, prefixes: Iterable[str]) -> bool:
    """True if ``path`` is one of ``prefixes`` or lies under one of them."""
    return any(
        path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")
        for prefix in prefixes
    )


def _merge_base(root: Path, base: str) -> str:
    _git(root, "rev-parse", "--is-inside-work-tree", error="not a git repository")
    commit = f"{base}^{{commit}}"
    _git(root, "rev-parse", "--verify", "--quiet", commit, error=f"unknown base {base!r}")
    return _git(
        root, "merge-base", base, "HEAD", error=f"no common history with {base!r}"
    ).strip()


def _untracked(root: Path) -> list[str]:
    output = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    return [relpath for relpath in output.split("\0") if relpath]


def parse_diff(text: str) -> AddedLines:
    """Map each file in a ``--unified=0`` diff to its added lines, numbered as in the new file."""
    added: dict[str, list[tuple[int, str]]] = {}
    path: str | None = None
    in_header = False
    line_number = 0
    # Split on "\n" only: str.splitlines() also breaks on \f, \x85,  ... inside a line.
    for raw in text.split("\n"):
        line = raw.removesuffix("\r")
        if line.startswith("diff --git "):
            path, in_header = None, True
        elif in_header and line.startswith("+++ "):
            path = _diff_path(line[4:])
        elif hunk := HUNK_HEADER.match(line):
            in_header = False
            line_number = int(hunk.group(1))
        elif path is not None and not in_header and line.startswith("+"):
            added.setdefault(path, []).append((line_number, line[1:]))
            line_number += 1
    return {path: tuple(lines) for path, lines in added.items()}


def _diff_path(target: str) -> str | None:
    """Path from a ``+++`` header; git adds a tab after names with spaces and C-quotes others."""
    target = target.removesuffix("\t")
    if len(target) > 1 and target.startswith('"') and target.endswith('"'):
        target = _unquote(target[1:-1])
    return target[2:] if target.startswith("b/") else None


def _unquote(inner: str) -> str:
    data = bytearray()
    index = 0
    while index < len(inner):
        char = inner[index]
        if char == "\\" and index + 1 < len(inner):
            escape = inner[index + 1]
            if escape in "01234567":
                data.append(int(inner[index + 1 : index + 4], 8))
                index += 4
                continue
            data.append(C_ESCAPES.get(escape, ord(escape)))
            index += 2
            continue
        data += char.encode("utf-8")
        index += 1
    return data.decode("utf-8", errors="replace")


def _git(cwd: Path, *args: str, error: str = "git command failed") -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, encoding="utf-8", errors="replace"
        )
    except FileNotFoundError as exc:
        raise GitError("git is not installed or not on PATH") from exc
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        raise GitError(f"{cwd}: {error}" + (f" ({detail[-1]})" if detail else ""))
    return result.stdout


def _text_lines(path: Path) -> list[str]:
    """Lines of a text file; empty for binary, oversized, unreadable, or non-regular files."""
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_UNTRACKED_BYTES:
            return []
        data = path.read_bytes()
    except OSError:
        return []
    if b"\0" in data:
        return []
    lines = data.decode("utf-8", errors="replace").split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line.removesuffix("\r") for line in lines]
