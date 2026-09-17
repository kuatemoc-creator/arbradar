"""Government ISDS registers - the treaty-transparency pages where States publish
the notices of intent and arbitrations brought against them.

This is the earliest public record of a dispute that exists: a notice of intent
appears here months before any case is registered anywhere. Canada and the
United States publish full case pages; Mexico's register sits behind a bot
challenge and is not reachable by a scheduled fetch (its press covers it).

Each register: an index page listing case pages. We take every case page linked
from the index, find the most recent dated event on it, and report it if it
falls inside the window. Case pages are cached for a day.
"""
import datetime as dt
import re
from typing import Dict, Iterator, List, Tuple

from selectolax.parser import HTMLParser

from ..fetch import get, HEADERS

BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/128 Safari/537.36"}

REGISTERS: List[Tuple[str, str, str, str]] = [
    # label, respondent State, index URL, link filter (regex on href)
    ("Canada - NAFTA/CUSMA register", "Canada",
     "https://www.international.gc.ca/trade-agreements-accords-commerciaux/topics-domaines/disp-diff/gov.aspx?lang=eng",
     r"disp-diff/(?!gov\.aspx)[A-Za-z0-9_\-]+\.aspx"),
    ("United States - USMCA register", "United States of America",
     "https://www.state.gov/office-of-international-claims-and-investment-disputes/usmca-investor-state-arbitrations",
     r"state\.gov/[a-z0-9\-]+-v-united-states"),
    ("United States - NAFTA register", "United States of America",
     "https://www.state.gov/nafta-investor-state-arbitrations",
     r"state\.gov/[a-z0-9\-]+-v-united-states"),
]

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(r"\b(?:%s) \d{1,2}, \d{4}\b" % MONTHS)
NOI_RE = re.compile(r"[^.]{0,160}Notice of (?:Intent|Arbitration)[^.]{0,160}\.", re.I)


def _text(html: str) -> str:
    tree = HTMLParser(html)
    for n in tree.css("script,style,nav,footer,header"):
        n.decompose()
    return " ".join(tree.body.text().split()) if tree.body else ""


def _latest_event(text: str) -> Tuple[dt.date, str]:
    """The most recent dated sentence on the page."""
    best, sentence = None, ""
    for m in DATE_RE.finditer(text):
        try:
            when = dt.datetime.strptime(m.group(0), "%B %d, %Y").date()
        except ValueError:
            continue
        if best is None or when > best:
            start = text.rfind(".", 0, m.start()) + 1
            end = text.find(".", m.end())
            best, sentence = when, text[start:(end if end > 0 else m.end() + 200)].strip()
    return best, sentence


def run(days: int = 7) -> Iterator[Dict]:
    cutoff = dt.date.today() - dt.timedelta(days=days)
    for label, state, index_url, link_re in REGISTERS:
        try:
            index = get(index_url, ttl=6 * 3600, headers=BROWSER_UA).text
        except Exception:                             # noqa: BLE001 - boundary
            continue
        tree = HTMLParser(index)
        seen = set()
        for a in tree.css("a"):
            href = a.attributes.get("href") or ""
            name = " ".join(a.text().split())
            if not re.search(link_re, href) or not name or name in ("Français", "English"):
                continue
            if href.startswith("/"):
                href = index_url.split("/", 3)[0] + "//" + index_url.split("/", 3)[2] + href
            if href in seen:
                continue
            seen.add(href)
            try:
                text = _text(get(href, ttl=24 * 3600, headers=BROWSER_UA).text)
            except Exception:                         # noqa: BLE001 - boundary
                continue
            when, sentence = _latest_event(text)
            if not when or when < cutoff:
                continue
            noi = NOI_RE.search(text)
            stage = "notice_of_intent" if (noi and "intent" in noi.group(0).lower()
                                           and when.year >= cutoff.year) else "new_case_filed"
            yield {
                "url": href,
                "source": label,
                "title": "{} v. {}: {}".format(name, state, sentence[:140]) if sentence else
                         "{} v. {}".format(name, state),
                "summary": "{} (register entry dated {}). {}".format(
                    sentence, when.isoformat(), noi.group(0) if noi else ""),
                "published_at": when.isoformat(),
                "event_type": stage,
                "respondents": [state],
                "states": [state],
                "claimants": [name],
            }
