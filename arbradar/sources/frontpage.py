"""The front page of a paper that publishes no feed.

For the outlets whose site answers but offers no RSS, the home page itself is
the feed: its headline links are read, and those that speak of a dispute, a
treaty, an expropriation or a revoked licence - in the paper's own language -
become items. No article page is fetched here; the headline is the item, and
the page is read later only if the story is chosen.

Nothing is done to a site that refuses scripts: those are left to the
Google News site: sweep.
"""
import concurrent.futures as cf
import html as _html
import json
import os
import re
from typing import Dict, Iterator, List
from urllib.parse import urljoin, urlsplit

from ..config import ROOT
from ..fetch import get, Blocked
from .rss import relevant

_A = re.compile(r'<a\s[^>]*?href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_SKIP = re.compile(r"/(tag|tags|category|categories|author|authors|topic|topics|search|login|signup|subscribe|newsletter|"
                   r"about|contact|privacy|terms|advertis|rss|feed|page/\d|video|videos|photo|photos|gallery|live)\b|"
                   r"\.(jpg|png|gif|pdf|mp4)$|^(mailto|tel|javascript):", re.I)


def answering() -> List[Dict[str, str]]:
    """Outlets whose home page answered but carried no feed, from docs/press.json."""
    path = os.path.join(ROOT, "docs", "press.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh).get("results") or []
    except (OSError, ValueError):
        return []
    out, seen = [], set()
    for r in rows:
        if r.get("status") != "none" or not str(r.get("detail", "")).startswith("not a feed"):
            continue
        host = urlsplit(r["url"]).netloc.lower()
        if host in seen:
            continue
        seen.add(host)
        out.append({"country": r.get("country") or "", "name": r.get("name") or host, "url": r["url"], "lang": r.get("lang") or "en"})
    return out


def headlines(page_url: str, text: str) -> Iterator[Dict[str, str]]:
    host = urlsplit(page_url).netloc.lower().replace("www.", "")
    seen = set()
    for href, inner in _A.findall(text):
        title = _html.unescape(re.sub(r"\s+", " ", _TAG.sub(" ", inner))).strip()
        words = title.split()
        if not (5 <= len(words) <= 30) or title.isupper():
            continue
        url = urljoin(page_url, _html.unescape(href.strip()))
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or host not in parts.netloc.lower():
            continue
        if _SKIP.search(parts.path) or len(parts.path) < 12:
            continue
        if url in seen:
            continue
        seen.add(url)
        yield {"url": url, "title": title}


def _read(outlet: Dict[str, str]):
    try:
        r = get(outlet["url"], ttl=1800, timeout=15)
    except (Blocked, Exception):                      # noqa: BLE001 - boundary
        return outlet, ""
    ctype = r.headers.get("content-type", "") if hasattr(r, "headers") else ""
    if "html" not in ctype and "<html" not in r.text[:2000].lower():
        return outlet, ""
    return outlet, r.text


def run(days: int = 7) -> Iterator[Dict]:
    outlets = answering()
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        pages = list(ex.map(_read, outlets))
    for outlet, text in pages:
        if not text:
            continue
        for h in headlines(outlet["url"], text):
            if not relevant(h["title"]):
                continue
            yield {
                "url": h["url"],
                "source": "{} ({})".format(outlet["name"], outlet["country"]) if outlet["country"] else outlet["name"],
                "title": h["title"][:300],
                "summary": "",
                "published_at": None,                 # the front page carries no date; the fetch date stands in
                "lang": outlet["lang"],
                "country": outlet["country"],
                "flag_reason": "front page of a paper with no feed",
            }
