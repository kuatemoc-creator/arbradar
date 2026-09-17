"""Public procurement - States and state enterprises buying arbitration counsel.

A tender for "legal representation in international arbitration" is a dispute
that has not been reported yet, published by the party that is about to be sued
or is about to sue. Nobody in the trade press reads procurement portals.

  * TED   - EU procurement, free JSON API, expert query syntax (TI~, FT~, PD>=)
  * Prozorro - Ukraine, one of the most-sued States; free full-text search
"""
import datetime as dt
from typing import Dict, Iterator, List

import httpx

from ..fetch import HEADERS

TED = "https://api.ted.europa.eu/v3/notices/search"
TED_FIELDS = ["publication-number", "notice-title", "buyer-name", "publication-date",
              "buyer-country", "links"]
TED_QUERIES = [
    '(TI~"arbitration" OR TI~"arbitrage" OR TI~"arbitraje" OR TI~"Schiedsverfahren" OR TI~"arbitrato")',
    '(FT~"investment treaty" OR FT~"investment arbitration" OR FT~"ICSID") AND TI~"legal services"',
]

PROZORRO = "https://prozorro.gov.ua/api/search/tenders"
PROZORRO_QUERIES = ["міжнародний арбітраж", "інвестиційний арбітраж", "ICSID",
                    "арбітраж представництво інтересів", "international arbitration"]


def _first(v):
    if isinstance(v, dict):
        return v.get("eng") or v.get("ENG") or next(iter(v.values()), "")
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""


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
            yield {
                "url": url,
                "source": "TED procurement",
                "title": "{}: {}".format(buyer, title)[:300] if buyer else title[:300],
                "summary": "Tender published {} by {} ({}). {}".format(
                    str(n.get("publication-date", ""))[:10], buyer, country, title),
                "published_at": str(n.get("publication-date", ""))[:10] or None,
                "event_type": "counsel_tender",
                "respondents": [buyer] if buyer else [],
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
            period = t.get("tenderPeriod") or t.get("enquiryPeriod") or {}
            start = str(period.get("startDate") or "")[:10]
            if start and start < cutoff:
                continue
            buyer = ((t.get("procuringEntity") or {}).get("identifier") or {}).get("legalName") \
                or (t.get("procuringEntity") or {}).get("name") or ""
            value = t.get("value") or {}
            amount = value.get("amount")
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
                "lang": "uk",
            }


def run(days: int = 7) -> Iterator[Dict]:
    yield from _ted(days)
    yield from _prozorro(days)
