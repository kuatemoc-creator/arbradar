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
    # Petitions to confirm or enforce an award against a State under the FSIA -
    # every one of these is an enforcement mandate with a sovereign counterparty.
    "enforcement_action:sovereign": '"Foreign Sovereign Immunities Act" AND ("arbitral award" OR "arbitration award") AND (confirm OR enforce OR recognition)',
    "s1782_application": '"28 U.S.C. 1782" OR "section 1782" OR "discovery in aid of a foreign"',
    "enforcement_action": '"petition to confirm arbitration award" OR "recognition and enforcement of a foreign arbitral award"',
    "annulment_setaside": '"vacate the arbitration award" OR "motion to vacate arbitral"',
    # Execution against a sovereign's property: the stage after confirmation,
    # where the assets and the immunity fights are.
    "enforcement_action:execution": '("writ of execution" OR "turnover order" OR "writ of attachment" OR "post-judgment discovery") AND ("arbitral award" OR "arbitration award") AND (Republic OR Kingdom OR "sovereign" OR "Bolivarian" OR "Federation" OR "State of")',
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
            # Government prosecutions and domestic labour matters use the same
            # statutory language; neither is an arbitration lead.
            joined = " | ".join(parties).upper()
            if joined.startswith("UNITED STATES") or " UNION" in joined or "LOCAL " in joined:
                continue
            firms = [f for f in (res.get("firm") or []) if f]
            desc = ""
            docs = res.get("recap_documents") or []
            if docs:
                desc = (docs[0].get("description") or "")[:300]
            yield {
                "url": BASE + (res.get("docket_absolute_url") or ""),
                "source": "US federal docket" + (" (sovereign)" if event_type.endswith(":sovereign") else ""),
                "title": "{} ({} {})".format(
                    res.get("caseName") or "Docket",
                    res.get("court_citation_string") or res.get("court") or "",
                    res.get("docketNumber") or ""),
                "summary": "{} Parties: {}.{}".format(
                    desc, "; ".join(parties[:6]) or "not listed",
                    " Counsel on record: " + "; ".join(firms[:4]) + "." if firms else
                    " No counsel listed yet."),
                "published_at": res.get("dateFiled"),
                "event_type": event_type.split(":")[0],
                "case_ref": res.get("docketNumber"),
                "claimants": parties[:1],
                "respondents": parties[1:3],
                "counsel": firms[:5],
                "flag_reason": ("US federal docket: petition to confirm or enforce an award against a State (FSIA)"
                                if event_type.endswith(":sovereign") else
                                "US federal docket: \u00a71782 application" if event_type.startswith("s1782") else
                                "US federal docket: petition to confirm or vacate an award"),
            }
