"""Load a praxis source directory (Markdown + YAML frontmatter) into a :class:`Pack`."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from praxis.model import BEGIN_MARKER, END_MARKER, SCOPES, Pack, Rule

FENCE = "---"
RULE_KEYS = frozenset({"id", "scope", "globs"})
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ORDER_PREFIX = re.compile(r"^(\d+)-")
FORBIDDEN_GLOB_CHARS = frozenset("`\r\n")


class PackError(ValueError):
    """Raised when praxis source files are malformed."""


def split_frontmatter(text: str, source: Path) -> tuple[dict[str, Any], str]:
    """Return ``(frontmatter, body)``; frontmatter is empty when the file has none."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != FENCE:
        return {}, text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FENCE:
            return _parse_yaml("".join(lines[1:index]), source), "".join(lines[index + 1 :])
    raise PackError(f"{source}: frontmatter is not closed with '{FENCE}'")


def _parse_yaml(raw: str, source: Path) -> dict[str, Any]:
    try:
        meta = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise PackError(f"{source}: invalid YAML frontmatter: {exc}") from exc
    if meta is None:
        return {}
    if not isinstance(meta, dict):
        raise PackError(f"{source}: frontmatter must be a mapping")
    return meta


def parse_rule(text: str, source: Path) -> Rule:
    """Parse one rule file. The id defaults to the file name minus any ``NNN-`` prefix."""
    meta, body = split_frontmatter(text, source)

    unknown = sorted((str(key) for key in meta if key not in RULE_KEYS))
    if unknown:
        raise PackError(f"{source}: unknown frontmatter key(s): {', '.join(unknown)}")

    rule_id = meta.get("id", ORDER_PREFIX.sub("", source.stem))
    if not isinstance(rule_id, str) or not ID_PATTERN.match(rule_id):
        raise PackError(f"{source}: invalid id {rule_id!r}; use lowercase words joined by hyphens")

    scope = meta.get("scope", "always")
    if scope not in SCOPES:
        raise PackError(f"{source}: invalid scope {scope!r}; expected one of {', '.join(SCOPES)}")

    globs = _parse_globs(meta.get("globs"), scope, source)

    body = body.strip()
    if not body:
        raise PackError(f"{source}: rule body is empty")
    if BEGIN_MARKER in body or END_MARKER in body:
        raise PackError(f"{source}: rule body must not contain praxis markers")

    return Rule(id=rule_id, body=body, scope=scope, globs=globs)


def _parse_globs(raw: Any, scope: str, source: Path) -> tuple[str, ...]:
    if raw is None:
        if scope == "glob":
            raise PackError(f"{source}: scope 'glob' requires a non-empty 'globs' list")
        return ()
    if scope != "glob":
        raise PackError(f"{source}: 'globs' is only allowed with scope 'glob'")
    if not isinstance(raw, list) or not all(_is_valid_glob(glob) for glob in raw):
        raise PackError(f"{source}: 'globs' must be a list of non-empty strings")
    if not raw:
        raise PackError(f"{source}: scope 'glob' requires a non-empty 'globs' list")
    return tuple(raw)


def _is_valid_glob(glob: Any) -> bool:
    return isinstance(glob, str) and bool(glob.strip()) and not FORBIDDEN_GLOB_CHARS & set(glob)


def _rule_order(path: Path) -> tuple[float, str]:
    """Numeric ``NNN-`` prefixes sort numerically; unprefixed files sort last, by name."""
    match = ORDER_PREFIX.match(path.name)
    return (int(match.group(1)) if match else float("inf"), path.name)


def load_pack(root: Path) -> Pack:
    """Load every visible ``rules/*.md`` file under ``root``, in prefix order."""
    rules_dir = root / "rules"
    if not rules_dir.is_dir():
        raise PackError(f"{rules_dir}: rules directory not found")

    paths = [
        path for path in rules_dir.glob("*.md") if path.is_file() and not path.name.startswith(".")
    ]
    rules = tuple(
        parse_rule(path.read_text(encoding="utf-8-sig"), path)
        for path in sorted(paths, key=_rule_order)
    )

    seen: set[str] = set()
    for rule in rules:
        if rule.id in seen:
            raise PackError(f"{rules_dir}: duplicate rule id {rule.id!r}")
        seen.add(rule.id)

    return Pack(rules=rules)
