"""Company disclosures on the newswires.

A listed company that receives or serves a notice of dispute says so on the
wire the same day, because its exchange makes it: "ATOME PLC: Notice of Dispute
and Intent to Submit Claim to Arbitration under the UK-Paraguay BIT". That is
the earliest public record of a treaty claim, days to weeks before the trade
press, and it names the parties, the treaty and the counsel.

The wires (PR Newswire, Business Wire, GlobeNewswire, Newsfile, Accesswire,
CNW) and the exchange announcement services are read through the Google News
search feed, which indexes them within minutes and answers to a site: query.
Nothing is decoded; the feed's own link and outlet name are kept.
"""
import datetime as dt
import html as _html
import re
import time
import urllib.parse as up
from typing import Dict, Iterator

import feedparser

from ..fetch import get

ENDPOINT = "https://news.google.com/rss/search"
SITES = ("prnewswire.com", "businesswire.com", "globenewswire.com", "newsfilecorp.com", "accesswire.com",
         "newswire.ca", "londonstockexchange.com", "asx.com.au", "investegate.co.uk",
         "sedarplus.ca", "hkexnews.hk", "euronext.com", "oslobors.no", "tase.co.il", "jse.co.za")
PHRASES = ('"notice of dispute"', '"notice of arbitration"', '"request for arbitration"', '"notice of intent" arbitration',
           '"arbitration proceedings" (commenced OR initiated OR filed OR received)', '"arbitral award" OR "arbitration award"',
           '"investment treaty" OR "bilateral investment treaty" OR ICSID', '"emergency arbitrator" OR "interim measures"',
           '"expropriation" OR "expropriated"', '"licence revoked" OR "license revoked" OR "concession terminated"',
           '"tax assessment" (arbitration OR treaty OR dispute)', '"settlement agreement" arbitration',
           '"enforcement of the award" OR "enforce the award" OR "recognition and enforcement" OR "petition to confirm" OR "award creditor"')
_TRAIL = re.compile(r"\s+[-|–—]\s+[^-|–—]{2,60}$")
# Only a wire or an exchange service is a company's own disclosure. Anything
# else the unrestricted queries bring back is press, and the sweep has it.
_WIRE = re.compile(r"prnewswire|pr newswire|businesswire|business wire|globenewswire|newsfile|accesswire|newswire\.ca|\bcnw\b|"
                   r"london stock exchange|londonstockexchange|\basx\b|investegate|sedar|hkexnews|euronext|oslobors|tase\.co|jse\.co|"
                   r"\btmx\b|\brns\b|\bsens\b|marketwired|nasdaq\.com|otcmarkets|einpresswire|prweb", re.I)


def _queries():
    # Few, broad queries: each is one feed fetch. The site list is split in
    # halves so the query stays under Google's length limit.
    halves = (SITES[: len(SITES) // 2], SITES[len(SITES) // 2:])
    for phrase in PHRASES:
        for part in halves:
            yield "({}) ({})".format(" OR ".join("site:" + s for s in part), phrase)
    # The same phrases with no site restriction, tied to the words a company
    # announcement uses: a wire the list does not name still surfaces.
    for phrase in PHRASES[:6]:
        yield "({}) (plc OR limited OR corp OR inc OR announces OR announced OR ASX OR TSX OR AIM)".format(phrase)


def _published(e) -> str:
    for k in ("published_parsed", "updated_parsed"):
        if e.get(k):
            return dt.date(*e[k][:3]).isoformat()
    return ""


def run(days: int = 7) -> Iterator[Dict]:
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    seen = set()
    for q in _queries():
        url = "{}?q={}&hl=en-US&gl=US&ceid=US:en".format(ENDPOINT, up.quote("{} when:{}d".format(q, max(1, days))))
        try:
            raw = get(url, ttl=1800).content
        except Exception:                             # noqa: BLE001 - boundary
            continue
        time.sleep(0.3)
        for e in feedparser.parse(raw).entries:
            title = _html.unescape((e.get("title") or "").strip())
            published = _published(e)
            if not title or (published and published < cutoff):
                continue
            key = re.sub(r"[^a-z0-9]+", " ", _TRAIL.sub("", title).lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            outlet = (e.get("source") or {}).get("title") or ""
            src_url = (e.get("source") or {}).get("href") or ""
            if not _WIRE.search(outlet + " " + src_url + " " + (e.get("link") or "")):
                continue
            summary = re.sub(r"<[^>]+>", " ", e.get("summary") or "")[:1500]
            text = (title + " " + summary).lower()
            if not re.search(r"arbitra|treaty|icsid|expropriat|revoked|terminated|tribunal|\bbit\b|settlement", text):
                continue                              # the wire also carries earnings; those are not disclosures of a dispute
            # The disclosure's own words say what it is; the classifier only
            # sees "arbitration" and would file it as commentary.
            low = title.lower()
            if re.search(r"notice of dispute|notice of intent|intent to submit|trigger letter", low):
                kind = "notice_of_intent"
            elif re.search(r"notice of arbitration|request for arbitration|commence[sd]?|initiat|files?\b|filed|lodge[sd]?|launch|brings?\b|submits?\b", low) and re.search(r"arbitra|icsid|claim", low):
                kind = "new_case_filed"
            elif re.search(r"award", low):
                kind = "award_issued"
            elif re.search(r"settle", low):
                kind = "settlement"
            elif re.search(r"arbitra|tribunal|icsid", low):
                kind = "commercial_dispute"
            else:
                kind = None
            yield {
                "url": e.get("link") or "",
                "source": "Wire / " + (outlet or "newswire"),
                "event_type": kind,
                "title": _TRAIL.sub("", title)[:300],
                "summary": summary,
                "published_at": published or None,
                "lang": "en",
                "flag_reason": "company disclosure on the wire",
            }
