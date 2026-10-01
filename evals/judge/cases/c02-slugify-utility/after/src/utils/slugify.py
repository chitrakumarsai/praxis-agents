"""Turn titles into URL slugs."""

import re
import unicodedata

_NON_WORD = re.compile(r"[^a-z0-9]+")


def slugify(title: str, max_length: int = 60) -> str:
    """Lowercase ASCII slug of ``title``, words joined by hyphens, at most ``max_length`` chars."""
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = _NON_WORD.sub("-", ascii_title.lower()).strip("-")
    return slug[:max_length].rstrip("-")
