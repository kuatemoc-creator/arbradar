"""ICSID docket, via the JSON API behind the case-database UI.

This is the single most valuable free source in the system. It is not a news
feed - it is the docket itself. For every pending case it returns the counsel
already on record, the tribunal, the treaty invoked, the economic sector, and
`lastproc`: the most recent procedural step with its date.

Two distinct signals come out of it:
  * dateregistered inside the window  -> a genuinely new case
  * lastproc date inside the window   -> a case that moved (award, annulment,
    tribunal change), which is where enforcement and annulment mandates come from

GAR reports a subset of these, days to weeks later.
"""
import datetime as dt
import re
import time
from typing import Dict, Iterator, List, Optional

from selectolax.parser import HTMLParser

from ..fetch import get

API = "https://icsid.worldbank.org/api/cases/{status}"
CASE_URL = "https://icsid.worldbank.org/cases/case-database/case-detail?CaseNo={}"
RESULT_KEY = "GetBulkCasesByStatusIdResult"

_DATE = re.compile(r"^\s*([A-Z][a-z]+ \d{1,2}, \d{4})\s*-\s*(.*)$", re.S)


def _clean(html: Optional[str]) -> str:
    if not html:
        return ""
    return " ".join(HTMLParser(html).text().split())


def _split_names(html: Optional[str]) -> List[str]:
    """Counsel and arbitrator fields are <br>-separated HTML."""
    if not html:
        return []
    parts = re.split(r"<br\s*/?>", html, flags=re.I)
    return [p for p in (_clean(x) for x in parts) if p]


def _parse_date(s: Optional[str]) -> Optional[dt.date]:
    if not s:
        return None
    try:
        return dt.datetime.strptime(s.strip(), "%B %d, %Y").date()
    except ValueError:
        return None


def _classify(text: str) -> str:
    t = text.lower()
    if "annul" in t or "ad hoc committee" in t:
        return "annulment_setaside"
    if "award" in t and ("render" in t or "issue" in t or "dispatch" in t):
        return "award_issued"
    if "tribunal is constituted" in t or "constituted" in t or "appoint" in t:
        return "tribunal_constituted"
    if "discontinu" in t or "settle" in t:
        return "award_issued"
    return "commentary"


def _emit(case: Dict, proc: Dict, event_type: str, when: dt.date,
          headline: str, detail: str) -> Dict:
    caseno = case.get("caseno") or case.get("caseid") or ""
    claimant_firms = _split_names(proc.get("claimant") or case.get("claimant"))
    respondent_firms = _split_names(proc.get("respondent") or case.get("respondent"))
    arbitrators = _split_names(proc.get("arbitrators")) + _split_names(proc.get("president"))
    treaty = " / ".join(x for x in (case.get("instrumentinvk1"),
                                    case.get("instrumentinvk2")) if x)
    return {
        "url": CASE_URL.format(caseno),
        "source": "ICSID docket",
        "title": headline,
        "summary": detail,
        "published_at": when.isoformat(),
        "event_type": event_type,
        "institution": "ICSID",
        "case_ref": caseno,
        "treaty": treaty or None,
        "sectors": [case["econsector"]] if case.get("econsector") else [],
        "claimants": [_clean(proc.get("clmnt_nationality"))] if proc.get("clmnt_nationality") else [],
        "respondents": [_clean(case.get("respondent_state") or case.get("partiessub") or "")] or [],
        "counsel": claimant_firms + respondent_firms,
        "arbitrators": [a for a in arbitrators if a],
    }


def run(days: int = 7, statuses=("pending", "concluded")) -> Iterator[Dict]:
    cutoff = dt.date.today() - dt.timedelta(days=days)
    for status in statuses:
        try:
            r = get(API.format(status=status),
                    params={"dt": int(time.time() * 1000)}, ttl=1800, timeout=90)
            cases = r.json()["data"][RESULT_KEY]
        except Exception:                             # noqa: BLE001 - boundary
            continue

        for case in cases:
            title = _clean(case.get("casetitle")) or case.get("caseno", "ICSID case")
            for proc in case.get("caseproceedings") or []:
                registered = _parse_date(proc.get("dateregistered"))
                if registered and registered >= cutoff:
                    yield _emit(
                        case, proc, "new_case_filed", registered,
                        "New ICSID case registered: {}".format(title),
                        "Registered {} under {}. Sector: {}. Subject: {}.".format(
                            proc.get("dateregistered"),
                            case.get("instrumentinvk1") or case.get("rulesapplied") or "ICSID rules",
                            case.get("econsector") or "unstated",
                            _clean(case.get("subject")) or "unstated"))

                m = _DATE.match(proc.get("lastproc") or "")
                if not m:
                    continue
                when = _parse_date(m.group(1))
                if not when or when < cutoff:
                    continue
                detail = _clean(m.group(2))
                if registered and when == registered:
                    continue                          # already emitted above
                yield _emit(
                    case, proc, _classify(detail), when,
                    "{}: {}".format(title, detail[:120]),
                    "Procedural step of {} in ICSID Case No. {}. {}".format(
                        m.group(1), case.get("caseno"), detail))
