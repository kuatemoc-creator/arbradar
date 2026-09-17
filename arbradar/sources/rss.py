"""Generic RSS/Atom adapter.

Covers the trade press, the institutions that publish feeds, and law firm press
rooms. Firm press releases matter more than they look: a firm announcing it has
been instructed tells you the mandate is gone, which is just as useful as knowing
one is open - it stops you chasing dead leads.
"""
import calendar
import datetime as dt
from typing import Dict, Iterator, List

import feedparser

from ..fetch import get, Blocked

FEEDS: List[Dict[str, str]] = [
    # trade press (headlines are free even where the article is paywalled)
    {"name": "GAR", "url": "https://globalarbitrationreview.com/rss"},
    {"name": "IAReporter", "url": "https://www.iareporter.com/feed/"},
    {"name": "Kluwer Arbitration Blog", "url": "http://arbitrationblog.kluwerarbitration.com/feed/"},
    {"name": "Jus Mundi", "url": "https://blog.jusmundi.com/rss/"},
    # institutions
    {"name": "PCA", "url": "https://pca-cpa.org/feed/"},
    {"name": "SCC", "url": "https://sccarbitrationinstitute.se/en/feed"},
    {"name": "HKIAC", "url": "https://www.hkiac.org/rss.xml"},
    {"name": "SIAC", "url": "https://siac.org.sg/feed"},
    # policy / treaty
    {"name": "IISD ITN", "url": "https://www.iisd.org/itn/feed/"},
    # enforcement & funding
    {"name": "Burford Quarterly", "url": "https://www.burfordcapital.com/insights/rss/"},
    # general business wire, filtered hard downstream
    {"name": "Reuters Legal", "url": "https://www.reuters.com/arc/outboundfeeds/rss/category/legal/?outputType=xml"},
]


def _published(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        tm = entry.get(key)
        if tm:
            return dt.date.fromtimestamp(calendar.timegm(tm)).isoformat()
    return ""


def run(days: int = 7, feeds: List[Dict[str, str]] = None) -> Iterator[Dict]:
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    for feed in (feeds or FEEDS):
        try:
            raw = get(feed["url"], ttl=1800).content
        except (Blocked, Exception):                  # noqa: BLE001 - boundary
            continue
        parsed = feedparser.parse(raw)
        for entry in parsed.entries:
            published = _published(entry)
            if published and published < cutoff:
                continue
            summary = entry.get("summary", "") or ""
            yield {
                "url": entry.get("link") or "",
                "source": feed["name"],
                "title": (entry.get("title") or "").strip(),
                "summary": summary[:2000],
                "published_at": published or None,
            }
