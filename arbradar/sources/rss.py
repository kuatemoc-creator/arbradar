"""Generic RSS/Atom adapter.

Covers the trade press, the institutions that publish feeds, and law firm press
rooms. Firm press releases matter more than they look: a firm announcing it has
been instructed tells you the mandate is gone, which is just as useful as knowing
one is open - it stops you chasing dead leads.
"""
import calendar
import re
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


# A national business feed is mostly not about disputes. Keep an item only if it
# says so, in any of the sweep's languages: a forum or treaty word, or an
# expropriation/nationalisation word, or a licence/concession/contract word next to
# a revoke/cancel/terminate word.
_STRONG = re.compile(
    r"arbitra|арбитраж|арбітраж|tahkim|arbitraj|արբիտրաժ|არბიტრაჟ|تحكيم|arbitrase|tr\u1ecdng t\u00e0i|"
    r"\bICSID\b|CIADI|CIRDI|МЦУИС|UNCITRAL|ЮНСИТРАЛ|"
    r"expropri|экспроприац|експропріац|kamula\u015ft\u0131r|nacionaliz|nationalis|nationaliz|национализ|націоналізац|"
    r"milliləşdir|ազգայնաց|ნაციონალიზ|تأميم|مصادرة|nasionalisasi|"
    r"investment treaty|bilateral investment|tratado bilateral|trait\u00e9 bilat|инвестиционн[а-я]+ (спор|соглашен)|"
    r"інвестиційн[а-я]+ (спір|угод)|yat\u0131r\u0131m anla\u015fmas|notice of (dispute|intent|arbitration)|"
    r"notificaci\u00f3n de (controversia|disputa)|уведомлени[ея] о споре", re.I)
_ASSET = re.compile(r"licen[cs]e|licence|лиценз|ліценз|lisans|licencia|licença|concession|concesi|конц|"
                    r"imtiyaz|contrat|контракт|contract|permit|разрешени|permiso|ruhsat", re.I)
_ACTION = re.compile(r"revok|cancel|terminat|annul|withdr|suspend|аннулир|отозв|отзыв|расторг|приостанов|"
                     r"скасув|анулю|розірв|iptal|fesh|askıya|revoc|cancel|rescind|caduc|résili|retir|suspend", re.I)


def relevant(text: str) -> bool:
    return bool(_STRONG.search(text) or (_ASSET.search(text) and _ACTION.search(text)))


def _configured() -> List[Dict[str, str]]:
    """sources.yaml wins over the built-in list, so the feeds are editable."""
    import os
    import yaml
    from ..config import ROOT
    path = os.path.join(ROOT, "sources.yaml")
    if not os.path.exists(path):
        return FEEDS
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    feeds = [f for f in (cfg.get("rss") or []) if f.get("url") and f.get("enabled", True)]
    for f in (cfg.get("national_press") or []):
        if f.get("url") and f.get("enabled", True):
            feeds.append({"name": "{} ({})".format(f["name"], f["country"]), "url": f["url"],
                          "lang": f.get("lang", "en"), "country": f["country"], "filter": True})
    return feeds or FEEDS


def run(days: int = 7, feeds: List[Dict[str, str]] = None) -> Iterator[Dict]:
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    for feed in (feeds or _configured()):
        try:
            raw = get(feed["url"], ttl=1800).content
        except (Blocked, Exception):                  # noqa: BLE001 - boundary
            continue
        parsed = feedparser.parse(raw)
        for entry in parsed.entries:
            published = _published(entry)
            if published and published < cutoff:
                continue
            summary = re.sub(r"<[^>]+>", " ", entry.get("summary", "") or "")
            title = (entry.get("title") or "").strip()
            if feed.get("filter") and not relevant(title + " " + summary):
                continue
            yield {
                "url": entry.get("link") or "",
                "source": feed["name"],
                "title": title,
                "summary": summary[:2000],
                "published_at": published or None,
                "lang": feed.get("lang", "en"),
                "country": feed.get("country"),
            }
