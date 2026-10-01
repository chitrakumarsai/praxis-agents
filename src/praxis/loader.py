"""Load a praxis source directory (Markdown + YAML frontmatter) into a :class:`Pack`.

Layout: ``rules/*.md`` and, optionally, ``skills/<name>/SKILL.md`` with ``references/**/*.md``.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import yaml

from praxis.globs import compile_glob
from praxis.sync import MAX_TRACKED_BYTES
from praxis.model import (
    BEGIN_MARKER,
    END_MARKER,
    SCOPES,
    Check,
    ForbidCheck,
    Pack,
    Reference,
    Resource,
    Rule,
    RunCheck,
    Skill,
)

FENCE = "---"
RULE_KEYS = frozenset({"id", "scope", "globs", "checks", "judge"})
CHECK_KINDS = ("forbid", "run")
CHECK_KEYS = frozenset({*CHECK_KINDS, "message"})
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ORDER_PREFIX = re.compile(r"^(\d+)-")
# Cursor and Copilot join globs with commas, so a glob itself can't contain one. Cursor's `globs`
# value is unquoted YAML, so anything YAML would read as a comment, mapping, or tag is unsafe too.
FORBIDDEN_GLOB_CHARS = frozenset('`,"')
YAML_UNSAFE_GLOB_START = frozenset("#!&%@|>[{")
YAML_UNSAFE_GLOB_SUBSTRINGS = (" #", ": ")

SKILL_FILE = "SKILL.md"
SKILL_KEYS = frozenset({"name", "description"})
REFERENCES_DIR = "references"
RESOURCE_DIRS = ("scripts", "assets")  # any file type, copied byte for byte
MAX_RESOURCE_BYTES = MAX_TRACKED_BYTES
MAX_SKILL_NAME = 64  # limits from the Agent Skills format
MAX_DESCRIPTION = 1024


class PackError(ValueError):
    """Raised when praxis source files are malformed."""


def split_frontmatter(text: str, source: Path) -> tuple[dict[str, Any], str]:
    """Return ``(frontmatter, body)``; frontmatter is empty when the file has none."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip() != FENCE:
        return {}, text
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip() == FENCE:  # column 0 only; indented --- belongs to the YAML
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

    _reject_unknown_keys(meta, RULE_KEYS, source)

    rule_id = meta.get("id", ORDER_PREFIX.sub("", source.stem))
    if not isinstance(rule_id, str) or not ID_PATTERN.match(rule_id):
        raise PackError(f"{source}: invalid id {rule_id!r}; use lowercase words joined by hyphens")

    scope = meta.get("scope", "always")
    if scope not in SCOPES:
        raise PackError(f"{source}: invalid scope {scope!r}; expected one of {', '.join(SCOPES)}")

    globs = _parse_globs(meta.get("globs"), scope, source)

    judge = meta.get("judge", True)
    if not isinstance(judge, bool):
        raise PackError(f"{source}: 'judge' must be true or false")

    return Rule(
        id=rule_id,
        body=_clean_body(body, "rule", source),
        scope=scope,
        globs=globs,
        checks=_parse_checks(meta.get("checks"), source),
        judge=judge,
    )


def _parse_checks(raw: Any, source: Path) -> tuple[Check, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise PackError(f"{source}: 'checks' must be a list")
    return tuple(
        _parse_check(item, f"{source}: check {index}") for index, item in enumerate(raw, 1)
    )


def _parse_check(item: Any, where: str) -> Check:
    if not isinstance(item, dict):
        raise PackError(f"{where} must be a mapping")
    unknown = sorted(str(key) for key in item if key not in CHECK_KEYS)
    if unknown:
        raise PackError(f"{where} has unknown key(s): {', '.join(unknown)}")
    kinds = [kind for kind in CHECK_KINDS if kind in item]
    if len(kinds) != 1:
        raise PackError(f"{where} needs exactly one of 'forbid' or 'run'")
    message = item.get("message", "")
    if not isinstance(message, str):
        raise PackError(f"{where} 'message' must be a string")

    (kind,) = kinds
    value = item[kind]
    if not isinstance(value, str) or not value.strip():
        raise PackError(f"{where} '{kind}' must be a non-empty string")
    if kind == "forbid":
        try:
            re.compile(value)
        except re.error as exc:
            raise PackError(f"{where} has an invalid regex: {exc}") from exc
        return ForbidCheck(pattern=value, message=message)
    try:
        command = tuple(shlex.split(value))
    except ValueError as exc:
        raise PackError(f"{where} 'run' can't be parsed: {exc}") from exc
    return RunCheck(command=command, message=message)


def _reject_unknown_keys(meta: dict[str, Any], allowed: frozenset[str], source: Path) -> None:
    unknown = sorted(str(key) for key in meta if key not in allowed)
    if unknown:
        raise PackError(f"{source}: unknown frontmatter key(s): {', '.join(unknown)}")


def _clean_body(body: str, kind: str, source: Path) -> str:
    body = body.strip()
    if not body:
        raise PackError(f"{source}: {kind} body is empty")
    if BEGIN_MARKER in body or END_MARKER in body:
        raise PackError(f"{source}: {kind} body must not contain praxis markers")
    return body


def _parse_globs(raw: Any, scope: str, source: Path) -> tuple[str, ...]:
    if raw is None:
        if scope == "glob":
            raise PackError(f"{source}: scope 'glob' requires a non-empty 'globs' list")
        return ()
    if scope != "glob":
        raise PackError(f"{source}: 'globs' is only allowed with scope 'glob'")
    if not isinstance(raw, list) or not all(_is_valid_glob(glob) for glob in raw):
        raise PackError(
            f"{source}: 'globs' must be a list of plain glob strings: no surrounding spaces, "
            "commas, quotes, backticks, control characters, ' #' or ': ', and no leading "
            "#!&%@|>[{ (write '*.{ts,tsx}' as two globs)"
        )
    if not raw:
        raise PackError(f"{source}: scope 'glob' requires a non-empty 'globs' list")
    for glob in raw:
        try:
            compile_glob(glob)
        except re.error as exc:
            raise PackError(f"{source}: invalid glob {glob!r}: {exc}") from exc
    return tuple(raw)


def _is_valid_glob(glob: Any) -> bool:
    return (
        isinstance(glob, str)
        and bool(glob)
        and glob == glob.strip()
        and glob[0] not in YAML_UNSAFE_GLOB_START
        and not any(part in glob for part in YAML_UNSAFE_GLOB_SUBSTRINGS)
        and all(char.isprintable() and char not in FORBIDDEN_GLOB_CHARS for char in glob)
    )


def _rule_order(path: Path) -> tuple[float, str]:
    """Numeric ``NNN-`` prefixes sort numerically; unprefixed files sort last, by name."""
    match = ORDER_PREFIX.match(path.name)
    return (int(match.group(1)) if match else float("inf"), path.name)


def parse_skill(skill_dir: Path) -> Skill:
    """Parse ``skill_dir/SKILL.md`` and its ``references/`` files."""
    source = skill_dir / SKILL_FILE
    if not source.is_file():
        raise PackError(f"{source}: {SKILL_FILE} not found")
    meta, body = split_frontmatter(source.read_text(encoding="utf-8-sig"), source)
    _reject_unknown_keys(meta, SKILL_KEYS, source)

    name = meta.get("name")
    if not isinstance(name, str) or len(name) > MAX_SKILL_NAME or not ID_PATTERN.match(name):
        raise PackError(
            f"{source}: invalid skill name {name!r}; use up to {MAX_SKILL_NAME} "
            "lowercase characters joined by hyphens"
        )
    if name != skill_dir.name:
        raise PackError(f"{source}: name {name!r} must match its directory {skill_dir.name!r}")

    description = meta.get("description")
    if not isinstance(description, str) or not 0 < len(description.strip()) <= MAX_DESCRIPTION:
        raise PackError(
            f"{source}: 'description' must be a string of 1-{MAX_DESCRIPTION} characters"
        )

    return Skill(
        name=name,
        description=" ".join(description.split()),
        body=_clean_body(body, "skill", source),
        references=_load_references(skill_dir),
        resources=_load_resources(skill_dir),
    )


def _load_references(skill_dir: Path) -> tuple[Reference, ...]:
    references = []
    for path in skill_dir.rglob("*"):
        relative = path.relative_to(skill_dir)
        relpath = relative.as_posix()
        if any(part.startswith(".") for part in relative.parts):
            continue
        if path.is_symlink():
            raise PackError(f"{skill_dir}: {relpath!r}: symlinks are not allowed in skills")
        if not path.is_file() or relpath == SKILL_FILE or relative.parts[0] in RESOURCE_DIRS:
            continue
        if relative.parts[0] != REFERENCES_DIR or path.suffix != ".md":
            raise PackError(
                f"{skill_dir}: unsupported file {relpath!r}; a skill may contain only "
                f"{SKILL_FILE}, {REFERENCES_DIR}/**/*.md, "
                f"and files under {' or '.join(f'{d}/' for d in RESOURCE_DIRS)}"
            )
        references.append(Reference(relpath, path.read_text(encoding="utf-8-sig").strip()))
    return tuple(sorted(references, key=lambda reference: reference.path))


def _load_resources(skill_dir: Path) -> tuple[Resource, ...]:
    """Scripts and assets, byte for byte (symlinks were rejected by ``_load_references``)."""
    resources = []
    for directory in RESOURCE_DIRS:
        if (skill_dir / directory).is_file():
            raise PackError(f"{skill_dir}: {directory!r} must be a directory")
        for path in sorted((skill_dir / directory).rglob("*")):
            relative = path.relative_to(skill_dir)
            if any(part.startswith(".") for part in relative.parts) or not path.is_file():
                continue
            relpath = relative.as_posix()
            if not relpath.isprintable():  # names are written into the manifest, one per line
                raise PackError(f"{skill_dir}: {relpath!r} has control characters in its name")
            if path.stat().st_size > MAX_RESOURCE_BYTES:
                raise PackError(
                    f"{skill_dir}: {relpath!r} is larger than {MAX_RESOURCE_BYTES:,} bytes"
                )
            data = path.read_bytes()
            # A shebang marks a script as executable; file modes don't survive packaging.
            resources.append(Resource(relpath, data, executable=data.startswith(b"#!")))
    return tuple(sorted(resources, key=lambda resource: resource.path))


def load_pack(root: Path) -> Pack:
    """Load visible rules in prefix order, then skills in name order."""
    rules_dir, skills_dir = root / "rules", root / "skills"
    if not rules_dir.is_dir() and not skills_dir.is_dir():
        raise PackError(f"{root}: no rules/ or skills/ directory found")

    paths = [
        path
        for path in (rules_dir.glob("*.md") if rules_dir.is_dir() else ())
        if path.is_file() and not path.name.startswith(".")
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

    skill_dirs = (
        sorted(
            path
            for path in skills_dir.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )
        if skills_dir.is_dir()
        else []
    )
    return Pack(rules=rules, skills=tuple(parse_skill(path) for path in skill_dirs))
