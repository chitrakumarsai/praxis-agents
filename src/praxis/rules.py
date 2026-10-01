"""Parse Markdown best-practice files into a structured rules model.

A rules file is plain Markdown:

    ---
    name: acme-standards
    version: 1
    ---

    # Acme engineering standards

    Optional intro paragraph.

    ## Testing

    Why this section matters.

    - Write a test for every bug fix.
      Indented lines continue the rule.
      - Nested items become details of the rule.
    - Keep unit tests under one second.

Headings become sections (nested by level), top-level list items become
rules, and other prose becomes a section's description. Content inside
fenced code blocks is kept verbatim in descriptions and never parsed as rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_FRONTMATTER_LINE = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$")


class RulesParseError(ValueError):
    """Raised when a rules file cannot be parsed."""


@dataclass
class Rule:
    """A single best practice, taken from a top-level list item."""

    text: str
    id: str
    line: int
    details: list[str] = field(default_factory=list)


@dataclass
class Section:
    """A heading and everything under it up to the next heading of equal or higher level."""

    title: str
    level: int
    line: int
    description: str = ""
    rules: list[Rule] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)

    def all_rules(self) -> list[Rule]:
        """Rules in this section and all nested sections, in document order."""
        out = list(self.rules)
        for child in self.sections:
            out.extend(child.all_rules())
        return out


@dataclass
class RuleSet:
    """A parsed rules file."""

    title: str = ""
    description: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    source: Path | None = None

    def all_rules(self) -> list[Rule]:
        """Every rule in the file, in document order."""
        out = list(self.rules)
        for section in self.sections:
            out.extend(section.all_rules())
        return out


def slugify(text: str) -> str:
    """Lowercase, hyphen-separated slug of ``text`` with Markdown punctuation removed."""
    text = re.sub(r"[`*_~\[\]()]", "", text.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "rule"


def parse_file(path: str | Path) -> RuleSet:
    """Read and parse the rules file at ``path``."""
    path = Path(path)
    ruleset = parse(path.read_text(encoding="utf-8"))
    ruleset.source = path
    return ruleset


def parse(text: str) -> RuleSet:
    """Parse Markdown ``text`` into a :class:`RuleSet`."""
    lines = text.splitlines()
    ruleset = RuleSet()
    start = _parse_frontmatter(lines, ruleset.metadata)

    # Stack of open sections; the RuleSet itself acts as the level-0 root.
    stack: list[Section] = []
    used_ids: dict[str, int] = {}
    prose: list[str] = []
    current_rule: Rule | None = None
    rule_indent = 0
    in_fence = False
    fence_marker = ""

    def container_rules() -> list[Rule]:
        return stack[-1].rules if stack else ruleset.rules

    def flush_prose() -> None:
        body = "\n".join(prose).strip()
        prose.clear()
        if not body:
            return
        if stack:
            target = stack[-1]
            target.description = f"{target.description}\n\n{body}" if target.description else body
        else:
            ruleset.description = (
                f"{ruleset.description}\n\n{body}" if ruleset.description else body
            )

    def new_rule(item_text: str, lineno: int) -> Rule:
        base = slugify(item_text)[:60].rstrip("-") or "rule"
        prefix = slugify(stack[-1].title) if stack else ""
        rid = f"{prefix}/{base}" if prefix else base
        count = used_ids.get(rid, 0) + 1
        used_ids[rid] = count
        if count > 1:
            rid = f"{rid}-{count}"
        return Rule(text=item_text, id=rid, line=lineno)

    for index in range(start, len(lines)):
        raw = lines[index]
        lineno = index + 1

        fence = _FENCE.match(raw)
        if in_fence:
            prose.append(raw)
            if fence and fence.group(1) == fence_marker:
                in_fence = False
            continue
        if fence:
            current_rule = None
            in_fence = True
            fence_marker = fence.group(1)
            prose.append(raw)
            continue

        heading = _HEADING.match(raw)
        if heading:
            flush_prose()
            current_rule = None
            level = len(heading.group(1))
            title = heading.group(2).strip()
            if level == 1 and not ruleset.title and not stack:
                ruleset.title = title
                continue
            while stack and stack[-1].level >= level:
                stack.pop()
            section = Section(title=title, level=level, line=lineno)
            (stack[-1].sections if stack else ruleset.sections).append(section)
            stack.append(section)
            continue

        item = _LIST_ITEM.match(raw)
        if item:
            indent = len(item.group(1).expandtabs(4))
            content = item.group(2).strip()
            if current_rule is not None and indent > rule_indent:
                current_rule.details.append(content)
                continue
            flush_prose()
            current_rule = new_rule(content, lineno)
            rule_indent = indent
            container_rules().append(current_rule)
            continue

        if not raw.strip():
            if current_rule is None:
                prose.append(raw)
            continue

        indent = len(raw) - len(raw.lstrip())
        if current_rule is not None and indent > rule_indent:
            # Continuation of a rule's text or of its last detail.
            if current_rule.details:
                current_rule.details[-1] += " " + raw.strip()
            else:
                current_rule.text += " " + raw.strip()
            continue

        current_rule = None
        prose.append(raw)

    if in_fence:
        raise RulesParseError("unterminated code fence")
    flush_prose()
    return ruleset


def _parse_frontmatter(lines: list[str], metadata: dict[str, str]) -> int:
    """Read simple ``key: value`` frontmatter; return the index of the first body line."""
    if not lines or lines[0].strip() != "---":
        return 0
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            return index + 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _FRONTMATTER_LINE.match(line)
        if not match:
            raise RulesParseError(f"line {index + 1}: invalid frontmatter: {line.strip()!r}")
        metadata[match.group(1)] = match.group(2).strip().strip("\"'")
    raise RulesParseError("frontmatter is missing its closing '---'")
