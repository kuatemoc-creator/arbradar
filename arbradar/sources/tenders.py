"""Public procurement - States and state enterprises buying arbitration counsel.

A tender for "legal representation in international arbitration" is a dispute
that has not been reported yet, published by the party that is about to be sued
or is about to sue. Nobody in the trade press reads procurement portals.

  * TED   - EU procurement, free JSON API, expert query syntax (TI~, FT~, PD>=)
  * Prozorro - Ukraine, one of the most-sued States; free full-text search
"""
import datetime as dt
import re
from typing import Dict, Iterator, List

import httpx

from ..fetch import HEADERS

TED = "https://api.ted.europa.eu/v3/notices/search"
TED_FIELDS = ["publication-number", "notice-title", "buyer-name", "publication-date",
              "buyer-country", "links"]
TED_QUERIES = [
    'TI~"arbitration and conciliation"',
    'TI~"legal services" AND (FT~"international arbitration" OR FT~"investment treaty" OR FT~"ICSID" OR FT~"UNCITRAL")',
    'TI~"legal" AND (FT~"arbitrage international" OR FT~"arbitraje internacional" OR FT~"CIRDI" OR FT~"CIADI")',
]

PROZORRO = "https://prozorro.gov.ua/api/search/tenders"
PROZORRO_QUERIES = ["міжнародний арбітраж", "інвестиційний арбітраж", "ICSID",
                    "арбітраж представництво інтересів", "international arbitration"]


def _first(v):
    """TED nests language maps inside lists inside maps; take the first leaf."""
    for _ in range(4):
        if isinstance(v, dict):
            v = v.get("eng") or v.get("ENG") or next(iter(v.values()), "")
        elif isinstance(v, list):
            v = v[0] if v else ""
        else:
            break
    return v if isinstance(v, str) else ""


INTERNATIONAL = ("international arbitration", "investment treaty", "investment arbitration",
                 "icsid", "uncitral", "bilateral investment", "arbitrage international",
                 "arbitraje internacional", "arbitrato internazionale", "investor-state",
                 "міжнародн", "інвестиційн")
LEGAL = ("legal", "juridique", "jurídic", "юридичн", "адвокат", "arbitr", "арбітраж", "представництв")
UAH_PER_USD = 41.5


def _ted(days: int) -> Iterator[Dict]:
    since = (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")
    seen = set()
    for q in TED_QUERIES:
        try:
            r = httpx.post(TED, headers={**HEADERS, "Content-Type": "application/json"},
                           json={"query": "{} AND PD>={}".format(q, since), "limit": 50,
                                 "fields": TED_FIELDS}, timeout=60)
            notices = r.json().get("notices", []) if r.status_code == 200 else []
        except Exception:                             # noqa: BLE001 - boundary
            continue
        for n in notices:
            pub = n.get("publication-number") or ""
            if not pub or pub in seen:
                continue
            seen.add(pub)
            links = (n.get("links") or {}).get("html") or {}
            url = _first(links) or "https://ted.europa.eu/en/notice/-/detail/{}".format(pub)
            title = _first(n.get("notice-title"))
            buyer = _first(n.get("buyer-name"))
            country = _first(n.get("buyer-country"))
            text = (title + " " + buyer).lower()
            if not any(k in text for k in LEGAL):
                continue
            yield {
                "url": url,
                "source": "TED procurement",
                "title": "{}: {}".format(buyer, title)[:300] if buyer else title[:300],
                "summary": "Tender published {} by {} ({}). {}".format(
                    str(n.get("publication-date", ""))[:10], buyer, country, title),
                "published_at": str(n.get("publication-date", ""))[:10] or None,
                # Domestic adjudication panels tender under the same CPV heading;
                # only an international marker earns the lead weight.
                "event_type": "counsel_tender" if any(k in text for k in INTERNATIONAL) else "commentary",
                "respondents": [buyer] if buyer else [],
                "states": [country] if country else [],
                "case_ref": pub,
            }


def _prozorro(days: int) -> Iterator[Dict]:
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    seen = set()
    for q in PROZORRO_QUERIES:
        try:
            r = httpx.post(PROZORRO, json={"text": q}, headers=HEADERS, timeout=60)
            rows = r.json().get("data", []) if r.status_code == 200 else []
        except Exception:                             # noqa: BLE001 - boundary
            continue
        for t in rows:
            tid = t.get("tenderID") or ""
            if not tid or tid in seen:
                continue
            seen.add(tid)
            # The enquiry period opens on publication; that is the tender's date.
            start = ""
            for period, key in ((t.get("enquiryPeriod"), "startDate"), (t.get("tenderPeriod"), "startDate"),
                                (t.get("enquiryPeriod"), "endDate"), (t.get("tenderPeriod"), "endDate")):
                if isinstance(period, dict) and period.get(key):
                    start = str(period[key])[:10]
                    break
            if not start:                            # the ID carries the publication date
                m = re.match(r"UA-(\d{4}-\d{2}-\d{2})", tid)
                start = m.group(1) if m else ""
            if not start or start < cutoff:
                continue                              # undated is not the same as new
            buyer = ((t.get("procuringEntity") or {}).get("identifier") or {}).get("legalName") \
                or (t.get("procuringEntity") or {}).get("name") or ""
            title = t.get("title") or ""
            if not any(k in (title + " " + buyer).lower() for k in LEGAL):
                continue                              # full-text search is loose; keep legal buys only
            value = t.get("value") or {}
            amount = value.get("amount")
            usd = (amount / UAH_PER_USD) if amount and (value.get("currency") == "UAH") else amount
            # A municipal utility's US$5k legal-aid contract matched "arbitration" somewhere
            # in its description. Keep a tender only if it says international, or is big
            # enough that international counsel is the plausible buyer.
            if not any(k in (title + " " + buyer).lower() for k in INTERNATIONAL) and (usd or 0) < 50000:
                continue
            yield {
                "url": "https://prozorro.gov.ua/tender/{}".format(tid),
                "source": "Prozorro procurement (Ukraine)",
                "title": "{}: {}".format(buyer, t.get("title") or "")[:300],
                "summary": "Ukrainian public tender {} ({}). Value {} {}. {}".format(
                    tid, t.get("status") or "status unknown",
                    "{:,.0f}".format(amount) if amount else "not stated", value.get("currency") or "",
                    t.get("title") or ""),
                "published_at": start or None,
                "event_type": "counsel_tender",
                "respondents": [buyer] if buyer else [],
                "states": ["Ukraine"],
                "case_ref": tid,
                "amount_usd": usd,
                "lang": "uk",
            }


def run(days: int = 7) -> Iterator[Dict]:
    yield from _ted(days)
    yield from _prozorro(days)
