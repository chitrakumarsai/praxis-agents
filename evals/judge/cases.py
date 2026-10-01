"""Load the judge calibration cases: a diff per case and the expected verdict per judged rule."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from praxis.bundled import pack_source
from praxis.judge import STATUSES
from praxis.loader import load_pack
from praxis.model import Rule

EVAL_DIR = Path(__file__).resolve().parent
CASES_DIR = EVAL_DIR / "cases"
LABELS_FILE = EVAL_DIR / "cases.yaml"
PACK = "agent-engineering"
DEFAULT_VERDICT = "not_applicable"
LABEL_NOTE = re.compile(r"^\s{4}(?P<rule>[a-z0-9-]+):\s*(?P<label>.+?)\s*#\s*(?P<why>.+)$")


@dataclass(frozen=True)
class Case:
    id: str
    title: str
    tags: tuple[str, ...]
    diff: str
    paths: tuple[str, ...]
    expected: dict[str, frozenset[str]]  # rule id -> acceptable verdicts
    notes: dict[str, str]  # rule id -> why, from the label comments


def judged_rules() -> tuple[Rule, ...]:
    """The rules `praxis verify --judge` grades in the bundled pack."""
    with pack_source(PACK) as source:
        return tuple(rule for rule in load_pack(source).rules if rule.judge and not rule.checks)


def load_cases() -> list[Case]:
    rules = {rule.id for rule in judged_rules()}
    entries = yaml.safe_load(LABELS_FILE.read_text(encoding="utf-8"))
    notes = _label_notes()
    cases = []
    for entry in entries:
        case_id = entry["id"]
        labels = entry.get("expected") or {}
        unknown = set(labels) - rules
        if unknown:
            raise ValueError(f"{case_id}: labels for rules the judge doesn't grade: {unknown}")
        expected = {rule: frozenset(_as_list(labels.get(rule, DEFAULT_VERDICT))) for rule in rules}
        for rule, verdicts in expected.items():
            if not verdicts <= set(STATUSES) - {"unknown"}:
                raise ValueError(f"{case_id}: invalid verdicts for {rule}: {sorted(verdicts)}")
        diff, paths = build_diff(CASES_DIR / case_id)
        cases.append(
            Case(
                id=case_id,
                title=entry["title"],
                tags=tuple(entry.get("tags", ())),
                diff=diff,
                paths=paths,
                expected=expected,
                notes=notes.get(case_id, {}),
            )
        )
    return cases


def build_diff(case_dir: Path) -> tuple[str, tuple[str, ...]]:
    """A git-style unified diff from ``before/`` to ``after/`` (3 lines of context)."""
    before, after = _files(case_dir / "before"), _files(case_dir / "after")
    if not after:
        raise ValueError(f"{case_dir}: no files under after/")
    sections = []
    for path in sorted(set(before) | set(after)):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        header = f"diff --git a/{path} b/{path}\n" + ("new file mode 100644\n" if old is None else "")
        lines = difflib.unified_diff(
            (old or "").splitlines(keepends=True),
            (new or "").splitlines(keepends=True),
            fromfile="/dev/null" if old is None else f"a/{path}",
            tofile=f"b/{path}",
        )
        sections.append(header + "".join(lines))
    changed = tuple(sorted(path for path in after if before.get(path) != after[path]))
    return "".join(sections), changed


def _files(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _as_list(value: str | list[str]) -> list[str]:
    return value if isinstance(value, list) else [value]


def _label_notes() -> dict[str, dict[str, str]]:
    """Rationale comments next to labels in cases.yaml, keyed by case and rule."""
    notes: dict[str, dict[str, str]] = {}
    case_id = None
    for line in LABELS_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("- id: "):
            case_id = line.removeprefix("- id: ").strip()
        elif case_id and (match := LABEL_NOTE.match(line)):
            notes.setdefault(case_id, {})[match["rule"]] = match["why"]
    return notes
