"""Story slugs: the one thing the email and the site must agree on."""
import re
from typing import Any, Dict


def _title(it: Dict[str, Any]) -> str:
    return it.get("title_en") or it.get("title") or ""


def story_slug(it: Dict[str, Any], date: str) -> str:
    """Shared with the article site so the email can deep-link each story."""
    s = re.sub(r"[^a-z0-9]+", "-", _title(it).lower()).strip("-")[:70]
    return "{}-{}.html".format(date, s)
