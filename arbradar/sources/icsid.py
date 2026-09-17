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


_GEO = set("""U.S.A. U.K. D.C. France Spain Italy Germany Switzerland Austria Belgium Netherlands Luxembourg
Sweden Norway Denmark Finland Portugal Ireland Canada Mexico Brazil Argentina Chile Peru Colombia Uruguay
Venezuela Ecuador Bolivia Panama Australia Singapore Japan Korea China India Türkiye Turkey Egypt Nigeria Kenya
Ukraine Russia Kazakhstan Uzbekistan Armenia Georgia Azerbaijan Malta Cyprus Greece Poland Romania Hungary Czechia
Croatia Serbia Israel Lebanon Jordan Qatar Bahrain Kuwait Oman Morocco Algeria Tunisia Senegal Cameroon Ghana
London Paris Washington Madrid Barcelona Houston Dallas Miami Chicago Boston Denver Philadelphia Geneva Zurich
Zürich Frankfurt Munich Berlin Vienna Brussels Amsterdam Rotterdam Stockholm Oslo Copenhagen Helsinki Lisbon
Dublin Milan Rome Toronto Vancouver Montreal Ottawa Sydney Melbourne Perth Tokyo Seoul Beijing Shanghai
Delhi Mumbai Dubai Doha Riyadh Cairo Lagos Nairobi Johannesburg Istanbul Ankara Kyiv Moscow Yerevan Tbilisi
Almaty Astana Tashkent Lima Bogotá Bogota Santiago Quito Caracas Montevideo Panamá Valletta Nicosia Athens
Warsaw Bucharest Budapest Prague Zagreb Belgrade Beirut Amman Rabat Casablanca Algiers Tunis Dakar Yaoundé
Accra Luxembourg TX NY CA FL IL MA DC PA CO GA WA""".split())
_GEO |= {"New York", "Los Angeles", "San Francisco", "Hong Kong", "The Hague", "Mexico City", "Buenos Aires",
         "Washington, D.C.", "United Kingdom", "United States", "Hong Kong SAR", "Abu Dhabi", "Tel Aviv"}


def _firm(raw: str) -> str:
    """ICSID lists counsel as 'Firm, City, Country [and City, Country]'. Multi-name
    firms contain commas too, so strip trailing geography rather than cutting at
    the first comma: 'Kellogg, Hansen, Todd, Figel & Frederick, Washington, D.C., U.S.A.'
    must come back whole."""
    raw = re.split(r",?\s+and\s+(?=[A-Z][a-z]+,)", raw)[0]     # drop second offices
    parts = [x.strip() for x in raw.split(",") if x.strip()]
    geo = re.compile(r"^(Republic|Kingdom|State|Commonwealth|Federal|Federation|United|People|Principality|"
                     r"Grand Duchy|Sultanate|Emirate|Union) ", re.I)
    while len(parts) > 1 and (parts[-1] in _GEO or re.fullmatch(r"[A-Z]{2}", parts[-1])
                              or geo.match(parts[-1]) or parts[-1].endswith(("U.S.A.", "U.K."))):
        parts.pop()
    return ", ".join(parts).strip()


def _seat(raw: str) -> str:
    """'Jane DOE (British) - Appointed by the Claimant(s)' -> 'Jane Doe (claimant appointee)'."""
    m = re.match(r"^(?P<name>.+?)\s*\((?P<nat>[^)]*)\)\s*-\s*Appointed by (?P<by>.+)$", raw)
    if not m:
        return raw
    name = " ".join(w.capitalize() if w.isupper() else w for w in m.group("name").split())
    by = m.group("by").lower()
    who = ("claimant appointee" if "claimant" in by else "respondent appointee" if "respondent" in by
           else "appointed by the parties" if "parties" in by else "appointed by the Chairman" if "chairman" in by
           else "appointed")
    return "{} ({})".format(name, who)


def describe(case: Dict, proc: Dict, when_label: str, step: str = "") -> str:
    """The facts a practitioner reads first, in one paragraph, from the record."""
    parts: List[str] = []
    claimant = _clean(proc.get("clmnt_nationality"))
    if not claimant or re.fullmatch(r"(Claimant|Respondent)\(s\)", claimant):
        claimant = _clean(case.get("casetitle")).split(" v. ")[0].strip()   # the record's own placeholder
    state = _clean(proc.get("resp_nationality"))
    treaty = " and ".join(x for x in (case.get("instrumentinvk1"), case.get("instrumentinvk2")) if x)
    reg = proc.get("dateregistered")
    if claimant or state:
        parts.append("{} against {}.".format(claimant or "The claimant", state or "the State"))
    if reg or treaty:
        parts.append("Registered {}{}.".format(reg or "", (" under the " + treaty) if treaty else ""))
    if case.get("econsector"):
        parts.append("Sector: {}.".format(case["econsector"].lower()))
    cf = [_firm(x) for x in _split_names(proc.get("claimant") or case.get("claimant"))]
    rf = [_firm(x) for x in _split_names(proc.get("respondent") or case.get("respondent"))]
    if cf:
        parts.append("For the claimant: {}.".format(", ".join(list(dict.fromkeys(cf))[:6])))
    if rf:
        parts.append("For the State: {}.".format(", ".join(list(dict.fromkeys(rf))[:6])))
    seats = [_seat(x) for x in _split_names(proc.get("president"))] + \
            [_seat(x) for x in _split_names(proc.get("arbitrators"))]
    if seats:
        parts.append("Tribunal: {}{}.".format(seats[0] + " presiding" if len(seats) > 1 else seats[0],
                                              ("; " + "; ".join(seats[1:])) if len(seats) > 1 else ""))
    elif proc.get("dateconstituted") is None or not proc.get("dateconstituted"):
        parts.append("Tribunal not yet constituted.")
    if step:
        parts.append("Latest step, {}: {}.".format(when_label, step.rstrip(".")))
    return " ".join(parts)


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
        "claimants": [c.strip() for c in re.split(r",\s*(?=[A-Z])", _clean(proc.get("clmnt_nationality")))
                      if c.strip() and not re.fullmatch(r"(Claimant|Respondent)\(s\)", c.strip())]
                     or [_clean(case.get("casetitle")).split(" v. ")[0].strip()],
        "respondents": [re.sub(r"\s*\([^)]*\)\s*$", "", _clean(proc.get("resp_nationality")))]
                       if proc.get("resp_nationality") else [],
        "states": [re.sub(r"\s*\([^)]*\)\s*$", "", _clean(proc.get("resp_nationality")))]
                  if proc.get("resp_nationality") else [],
        "counsel": claimant_firms + respondent_firms,
        "arbitrators": [a for a in arbitrators if a],
        "flag_reason": "ICSID docket: " + ("case registered" if event_type == "new_case_filed" else
                                           "award rendered" if event_type == "award_issued" else
                                           "annulment step" if event_type == "annulment_setaside" else
                                           "tribunal change" if event_type == "tribunal_constituted" else
                                           "procedural step"),
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
                        describe(case, proc, proc.get("dateregistered") or ""))

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
                    describe(case, proc, m.group(1), detail))
