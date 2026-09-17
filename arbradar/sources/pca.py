"""PCA news.

The PCA case list itself is client-rendered and not exposed over its WordPress
REST API, so we take the news feed. Case-level PCA detail is a known gap - the
UNCITRAL Transparency Registry is the better route and is a later addition.
"""
import datetime as dt
from typing import Dict, Iterator

from selectolax.parser import HTMLParser

from ..fetch import get

NEWS = "https://pca-cpa.org/en/news/"


def run(days: int = 7) -> Iterator[Dict]:
    try:
        html = get(NEWS, ttl=3600).text
    except Exception:                                 # noqa: BLE001 - boundary
        return
    tree = HTMLParser(html)
    for node in tree.css("script,style,nav,header,footer"):
        node.decompose()
    seen = set()
    for a in tree.css("a"):
        href = a.attributes.get("href") or ""
        text = " ".join(a.text().split())
        if len(text) < 25 or "/news" not in href or href in seen:
            continue
        seen.add(href)
        if href.startswith("/"):
            href = "https://pca-cpa.org" + href
        yield {
            "url": href,
            "source": "PCA",
            "title": text[:300],
            "summary": text[:600],
            "published_at": None,
            "institution": "PCA",
        }
