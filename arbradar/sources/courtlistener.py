"""CourtListener / RECAP - US federal dockets, free API.

Two high-value docket shapes for a practitioner:
  * s.1782 applications - discovery in aid of a foreign proceeding. Frequently
    filed before or at the very start of an arbitration.
  * petitions to confirm / vacate an award - enforcement work, and each one
    implies counsel needed wherever assets sit.

The API returns party, attorney and firm names, which is exactly the BD payload:
you can see who is already instructed and who is not.
"""
import datetime as dt
from typing import Dict, Iterator
import os

from ..fetch import get

ENDPOINT = "https://www.courtlistener.com/api/rest/v4/search/"
BASE = "https://www.courtlistener.com"

QUERIES = {
    "s1782_application": '"28 U.S.C. 1782" OR "section 1782" OR "discovery in aid of a foreign"',
    "enforcement_action": '"petition to confirm arbitration award" OR "recognition and enforcement of a foreign arbitral award"',
    "annulment_setaside": '"vacate the arbitration award" OR "motion to vacate arbitral"',
}


def run(days: int = 7) -> Iterator[Dict]:
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    headers = {}
    token = os.environ.get("COURTLISTENER_TOKEN")
    if token:                       # optional - raises the rate limit
        headers["Authorization"] = "Token " + token

    for event_type, q in QUERIES.items():
        try:
            r = get(ENDPOINT, params={
                "q": q, "type": "r",
                "filed_after": since,
                "order_by": "dateFiled desc",
            }, ttl=1800, headers=headers)
        except Exception:                             # noqa: BLE001 - boundary
            continue
        for res in r.json().get("results", []):
            parties = res.get("party") or []
            firms = [f for f in (res.get("firm") or []) if f]
            desc = ""
            docs = res.get("recap_documents") or []
            if docs:
                desc = (docs[0].get("description") or "")[:300]
            yield {
                "url": BASE + (res.get("docket_absolute_url") or ""),
                "source": "CourtListener / RECAP",
                "title": "{} ({} {})".format(
                    res.get("caseName") or "Docket",
                    res.get("court_citation_string") or res.get("court") or "",
                    res.get("docketNumber") or ""),
                "summary": "{} Parties: {}.{}".format(
                    desc, "; ".join(parties[:6]) or "not listed",
                    " Counsel on record: " + "; ".join(firms[:4]) + "." if firms else
                    " No counsel listed yet."),
                "published_at": res.get("dateFiled"),
                "event_type": event_type,
                "case_ref": res.get("docketNumber"),
                "claimants": parties[:1],
                "respondents": parties[1:3],
                "counsel": firms[:5],
            }
