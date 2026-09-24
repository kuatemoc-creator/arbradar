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
Accra Luxembourg TX NY CA FL IL MA DC PA CO GA WA Douala Abidjan Kinshasa Luanda Maputo Harare Lusaka
Khartoum Tripoli Baku Bishkek Dushanbe Ashgabat Ulaanbaatar Hanoi Jakarta Manila Bangkok Colombo Dhaka
Karachi Islamabad Lahore Jeddah Muscat Manama Tehran Baghdad Erbil Damascus Tegucigalpa Managua Kingston
Asunción Georgetown Paramaribo Libreville Conakry Bamako Niamey Ouagadougou Lomé Cotonou Kigali Kampala
Antananarivo Nouakchott Brazzaville Bujumbura Lilongwe Gaborone Windhoek Mbabane Maseru Praia""".split())
_GEO |= {"Dar es Salaam", "Addis Ababa", "Ho Chi Minh City", "Kuala Lumpur", "Kuwait City", "Panama City",
         "San José", "Guatemala City", "San Salvador", "Santo Domingo", "Port of Spain", "La Paz", "Port Louis"}
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
        m2 = re.match(r"^(?P<name>.+?)\s*\((?P<nat>[^)]*)\)\s*$", raw)
        if m2:
            return " ".join(w.capitalize() if w.isupper() else w for w in m2.group("name").split())
        return raw
    name = " ".join(w.capitalize() if w.isupper() else w for w in m.group("name").split())
    by = m.group("by").lower()
    who = ("claimant appointee" if "claimant" in by else "respondent appointee" if "respondent" in by
           else "appointed by the parties" if "parties" in by else "appointed by the Chairman" if "chairman" in by
           else "appointed")
    return "{} ({})".format(name, who.replace("appointee", "appointee"))


_SUFFIX = re.compile(r",?\s+(S\.?A\.?U?\.?|S\.?p\.?A\.?|S\.?A\.?R\.?L\.?|S\.?à\s?r\.?l\.?|B\.?V\.?|N\.?V\.?|GmbH|AG|"
                     r"Ltd\.?|Limited|LLC|L\.?P\.?|Inc\.?|Corp\.?|Corporation|plc|PLC|Co\.?|Company|Holdings?|"
                     r"International|Pte\.?|S\.?A\.?S\.?|S\.?L\.?|A\.?S\.?|Public Company Limited|and others|et al\.?)\b\.?", re.I)
_STATE = re.compile(r"^(The )?(Republic|Kingdom|State|Commonwealth|Federal Republic|Federative Republic|People's Democratic Republic|People's Republic|"
                    r"Oriental Republic|Bolivarian Republic|Plurinational State|Argentine Republic|Italian Republic|"
                    r"Hellenic Republic|United Mexican States|Union|Sultanate|Principality|Grand Duchy) (of )?", re.I)
_STATE_MAP = {"Argentine Republic": "Argentina", "Italian Republic": "Italy", "United Mexican States": "Mexico",
              "Hellenic Republic": "Greece", "Swiss Confederation": "Switzerland", "Kingdom of Spain": "Spain",
              "Republic of Türkiye": "Türkiye", "Russian Federation": "Russia", "Czech Republic": "Czechia",
              "Slovak Republic": "Slovakia", "Kyrgyz Republic": "Kyrgyzstan", "Lao People's Democratic Republic": "Laos",
              "Bolivarian Republic of Venezuela": "Venezuela", "Plurinational State of Bolivia": "Bolivia",
              "Oriental Republic of Uruguay": "Uruguay", "Federal Republic of Germany": "Germany",
              "Federal Republic of Nigeria": "Nigeria", "United Arab Emirates": "UAE", "United States of America": "United States"}


def short_party(name: str) -> str:
    name = _clean(name).replace("\u2019", "'")          # ICSID mixes curly and straight apostrophes
    for k, v in _STATE_MAP.items():
        if name.startswith(k):
            return v
    name = _STATE.sub("", name)
    first = re.split(r",| and ", name)[0].strip()
    first = _SUFFIX.sub("", first).strip(" ,.&")
    return first or name


def first_sentence(text: str, limit: int = 140) -> str:
    """The step for a headline: its first sentence, cut at a word if still too long."""
    text = " ".join((text or "").split())
    # Not at an initial or a title: "D. Brian King", "Prof. Dr. Sachs", "Mr. Kohen", "v. Ecuador".
    first = re.split(r"(?<!\b[A-Z]\.)(?<!\bMr\.)(?<!\bMs\.)(?<!\bDr\.)(?<!\bProf\.)(?<!\bNo\.)(?<!\bv\.)(?<!\bSt\.)"
                     r"(?<=[.!?])\s+", text, maxsplit=1)[0].rstrip(".:;, ")
    if len(first) <= limit:
        return first
    return first[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "\u2026"


def headline(case: Dict, step: str) -> str:
    title = _clean(case.get("casetitle"))
    left, _, right = title.partition(" v. ")
    right = re.sub(r"\s*\(ICSID Case No\..*$", "", right)
    if not right:
        return title
    return "{} v. {} \u2014 {}".format(short_party(left), short_party(right), step)


_NAT = {"Spanish": "Spanish", "Italian": "Italian", "French": "French", "German": "German", "Dutch": "Dutch",
        "British": "British", "U.S.": "US", "American": "US", "Canadian": "Canadian", "Swiss": "Swiss",
        "Chinese": "Chinese", "Turkish": "Turkish", "Cypriot": "Cypriot", "Luxembourg": "Luxembourg"}


def _nat(raw: str) -> str:
    """'Petersen Energía S.A.U. (Spanish)' -> ('Petersen Energía', 'Spanish')."""
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", raw or "")
    return (short_party(m.group(1)), m.group(2).split(",")[0].strip()) if m else (short_party(raw), "")


def _join(names: List[str]) -> str:
    names = list(dict.fromkeys(n for n in names if n))
    if not names:
        return ""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _date(raw: str) -> str:
    try:
        d = dt.datetime.strptime((raw or "").strip(), "%B %d, %Y").date()
        return "{} {} {}".format(d.day, d.strftime("%B"), d.year)
    except ValueError:
        return raw or ""


def describe(case: Dict, proc: Dict, when_label: str, step: str = "") -> str:
    """One paragraph a colleague could have written from the docket."""
    claimants = [c.strip() for c in re.split(r",\s*(?=[A-Z])", _clean(proc.get("clmnt_nationality"))) if c.strip()]
    claimants = [c for c in claimants if not re.fullmatch(r"(Claimant|Respondent)\(s\)", c)]
    if not claimants:
        claimants = [_clean(case.get("casetitle")).split(" v. ")[0].strip()]
    parts = [_nat(c) for c in claimants[:3]]
    names = _join([n for n, _ in parts])
    nats = list(dict.fromkeys(n for _, n in parts if n))
    if nats and len(nats) <= 2:
        nat = " and ".join(nats[:2])
        if len(parts) > 1:
            investor = "{}, {} investors,".format(names, nat)
        else:
            investor = "{}, {} {} investor,".format(names, "an" if nat[:1].lower() in "aeiou" else "a", nat)
    else:
        investor = names
    state = short_party(re.sub(r"\s*\([^)]*\)\s*$", "", _clean(proc.get("resp_nationality"))))
    if not state:
        state = short_party(_clean(case.get("casetitle")).split(" v. ")[-1].split(" (ICSID")[0])
    treaty = " and the ".join(" ".join(x.split()) for x in (case.get("instrumentinvk1"), case.get("instrumentinvk2")) if x)
    sector = (case.get("econsector") or "").lower().replace("&", "and")
    reg = _date(proc.get("dateregistered"))
    cf = _join([_firm(x) for x in _split_names(proc.get("claimant") or case.get("claimant"))][:5])
    rf = _join([_firm(x) for x in _split_names(proc.get("respondent") or case.get("respondent"))][:4])
    seats = [_seat(x) for x in _split_names(proc.get("president"))] + \
            [_seat(x) for x in _split_names(proc.get("arbitrators"))]

    out: List[str] = []
    if step:
        out.append("{} brought the claim against {}{}{}; it was registered on {}.".format(
            investor, state or "the State", " under the " + treaty if treaty else "",
            ", in the {} sector".format(sector) if sector else "", reg))
    else:
        out.append("{} {} registered a claim at ICSID against {}{}{}.".format(
            investor, "have" if len(parts) > 1 else "has", state or "the State",
            " under the " + treaty if treaty else "", ", in the {} sector".format(sector) if sector else ""))
    if cf:
        out.append("{} act{} for the claimant{}.".format(cf, "" if " and " in cf else "s", "s" if len(parts) > 1 else ""))
    if rf:
        out.append("{} for {}.".format(rf, state or "the State"))
    if seats:
        out.append("The tribunal is {}{}.".format(seats[0] + (", presiding" if len(seats) > 1 else ""),
                                                 ("; " + "; ".join(seats[1:])) if len(seats) > 1 else ""))
    else:
        out.append("The tribunal has not yet been constituted.")
    if step:
        out.append("On {}, {}.".format(when_label if not re.match(r"^[A-Z][a-z]+ \d", when_label) else _date(when_label),
                                       step[:1].lower() + step[1:].rstrip(".")))
    return " ".join(out)


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
                        headline(case, "new case registered at ICSID"),
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
                brief = first_sentence(detail)
                if brief.split(" ", 1)[0] in ("The", "A", "An"):
                    brief = brief[:1].lower() + brief[1:]   # 'the Tribunal renders', but 'Mitsui files'
                yield _emit(
                    case, proc, _classify(detail), when,
                    headline(case, brief),
                    describe(case, proc, m.group(1), detail))
