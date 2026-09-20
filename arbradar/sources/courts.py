"""Courts outside the United States: public judgment feeds and open search APIs.

A court list gives an arbitration practitioner the work that surrounds an
arbitration rather than the arbitration itself: applications to set an award
aside, enforcement of awards, stays of court proceedings in favour of
arbitration, anti-suit injunctions, challenges to arbitrators. The US federal
docket is read separately (courtlistener.py); this module covers the other
seats and enforcement jurisdictions whose courts publish in machine-readable
form.

Every source here is a public feed or an open API. Nothing is read from behind
a bot challenge (Ukraine's register, the Swiss Federal Tribunal, Indian Kanoon,
Brazil's STJ and the Australian federal judgments site all refuse scripts and
are left to a person). For England and Wales only the Find Case Law search
feed is used - the judgments themselves are not downloaded or analysed, which
keeps the use within the Open Justice Licence.
"""
import datetime as dt
import io
import json
import re
from typing import Dict, Iterator, List, Optional, Tuple

import feedparser

from ..fetch import get, Blocked
from .rss import _published

# ----------------------------------------------------------------------------
# shared helpers
# ----------------------------------------------------------------------------

_TAG = re.compile(r"<[^>]+>")


def _text(s: str) -> str:
    s = _TAG.sub(" ", s or "")
    s = s.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"').replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def _cutoff(days: int) -> str:
    return (dt.date.today() - dt.timedelta(days=days)).isoformat()


# What the judgment is about, in the order a practitioner would rank the work.
# Each entry: (regex over title + summary, event_type, plain description).
_KINDS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"set(?:ting)? aside|vacat|annul|section 6[789]\b|s\.? ?6[789]\b|serious irregularity|"
                r"recourse against|challenge to (?:the )?award|appeal (?:on a point of law )?(?:from|against) (?:the |an )?award|"
                r"vernietig|aufhebung|aufgehoben|aufhebungsantrag", re.I),
     "annulment_setaside", "challenge to an award"),
    (re.compile(r"enforc|recogni|exequatur|tenuitvoerlegging|erkenning|vollstreckbar|new york convention|"
                r"section (?:66|101)\b|homologation|registration of (?:the |an )?award", re.I),
     "enforcement_action", "enforcement of an award"),
    (re.compile(r"removal of (?:an |the )?arbitrator|section 24\b|apparent bias|impartial|"
                r"challenge to (?:an |the )?arbitrator|befangen|wraking", re.I),
     "tribunal_constituted", "challenge to an arbitrator"),
    (re.compile(r"anti-?suit|stay of (?:court )?proceedings|stay in favour|section 9\b|s\.? ?9\b|sursis|"
                r"refer(?:ral)? to arbitration|arbitration (?:agreement|clause)|kompetenz|"
                r"jurisdiction of (?:the )?(?:arbitral )?tribunal|schiedsvereinbarung|schiedsklausel|arbitrabil", re.I),
     "commercial_dispute", "arbitration agreement, stay or anti-suit relief"),
    (re.compile(r"section 44\b|interim (?:relief|measure|injunction)|freezing|in (?:aid|support) of (?:an )?arbitration", re.I),
     "commercial_dispute", "interim relief in support of arbitration"),
]


def _classify(text: str, default: str = "commercial_dispute", what: str = "arbitration-related judgment") -> Tuple[str, str]:
    for rx, event_type, label in _KINDS:
        if rx.search(text or ""):
            return event_type, label
    return default, what


_VS = re.compile(r"\s+(?:v\.?|vs\.?|c\.|contre|gegen|tegen)\s+", re.I)


def _parties(name: str) -> Tuple[List[str], List[str]]:
    parts = _VS.split(name or "", maxsplit=1)
    if len(parts) == 2:
        return [parts[0].strip(" ,;")], [parts[1].strip(" ,;")]
    return ([name.strip()] if name else []), []


def _item(*, url: str, country: str, court: str, title: str, ref: str, published: Optional[str],
          summary: str, what: Optional[str] = None, event_type: Optional[str] = None,
          lang: str = "en", counsel: Optional[List[str]] = None) -> Dict:
    if not event_type:
        event_type, what = _classify(title + " " + summary)
    what = what or "arbitration-related judgment"
    claimants, respondents = _parties(title)
    return {
        "url": url,
        "source": "Court: " + country,
        "title": title[:300],
        "summary": summary[:2000],
        "published_at": published,
        "event_type": event_type,
        "case_ref": ref or None,
        "claimants": claimants,
        "respondents": respondents,
        "counsel": counsel or [],
        "flag_reason": "{}: {}".format(court, what),
        "lang": lang,
        "country": country,
    }


# ----------------------------------------------------------------------------
# England and Wales - Find Case Law (The National Archives), Atom search feed
# ----------------------------------------------------------------------------

FCL = "https://caselaw.nationalarchives.gov.uk/atom.xml"

# Exact phrases the judgments themselves use; the site's own search does the
# matching. Order is priority: the first phrase a judgment matches labels it.
FCL_QUERIES: List[Tuple[str, str, str]] = [
    ('"section 67 of the Arbitration Act 1996"', "annulment_setaside", "challenge to the tribunal's jurisdiction (s.67)"),
    ('"section 68 of the Arbitration Act 1996"', "annulment_setaside", "serious-irregularity challenge to an award (s.68)"),
    ('"section 69 of the Arbitration Act 1996"', "annulment_setaside", "appeal on a point of law from an award (s.69)"),
    ('"section 24 of the Arbitration Act 1996"', "tribunal_constituted", "application to remove an arbitrator (s.24)"),
    ('"section 101 of the Arbitration Act 1996"', "enforcement_action", "enforcement of a New York Convention award (s.101)"),
    ('"section 66 of the Arbitration Act 1996"', "enforcement_action", "enforcement of an award (s.66)"),
    ('"investment treaty"', "enforcement_action", "investment-treaty matter before the English courts"),
    ('"anti-suit injunction"', "commercial_dispute", "anti-suit injunction"),
    ('"section 9 of the Arbitration Act 1996"', "commercial_dispute", "stay of court proceedings in favour of arbitration (s.9)"),
    ('"section 44 of the Arbitration Act 1996"', "commercial_dispute", "interim relief in support of arbitration (s.44)"),
    ('"Arbitration Act 1996"', "commercial_dispute", "judgment under the Arbitration Act 1996"),
]

_FCL_COURTS = {
    "uksc": "UKSC", "ukpc": "UKPC", "ewca/civ": "EWCA Civ", "ewca/crim": "EWCA Crim",
    "ewhc/comm": "EWHC (Comm)", "ewhc/tcc": "EWHC (TCC)", "ewhc/ch": "EWHC (Ch)", "ewhc/kb": "EWHC (KB)",
    "ewhc/qb": "EWHC (QB)", "ewhc/admlty": "EWHC (Admlty)", "ewhc/admin": "EWHC (Admin)",
    "ewhc/fam": "EWHC (Fam)", "ewhc/pat": "EWHC (Pat)", "ewhc/ipec": "EWHC (IPEC)", "ewhc/scco": "EWHC (SCCO)",
}


def _fcl_citation(link: str) -> str:
    m = re.search(r"caselaw\.nationalarchives\.gov\.uk/([a-z]+(?:/[a-z]+)?)/(\d{4})/(\d+)", link)
    if not m:
        return ""
    court, year, num = m.groups()
    code = _FCL_COURTS.get(court, court.upper().replace("/", " "))
    if "(" in code:                       # EWHC divisions cite as [2026] EWHC 123 (Comm)
        base, div = code.split(" ", 1)
        return "[{}] {} {} {}".format(year, base, num, div)
    return "[{}] {} {}".format(year, code, num)


def _fcl(days: int) -> Iterator[Dict]:
    cutoff = _cutoff(days)
    seen = set()
    for q, event_type, what in FCL_QUERIES:
        try:
            raw = get(FCL, params={"query": q, "order": "-date", "per_page": 30}, ttl=1800).content
        except (Blocked, Exception):                  # noqa: BLE001 - boundary
            continue
        for e in feedparser.parse(raw).entries:
            link = e.get("link") or ""
            published = _published(e)
            if not link or link in seen or (published and published < cutoff):
                continue
            seen.add(link)
            court = (e.get("author") or "Court").strip()
            if re.search(r"Family|Crim|Tribunal|Administrative|Immigration|Employment|Magistrates", court):
                continue
            title = _text(e.get("title") or "")
            citation = _fcl_citation(link)
            summary = "Judgment of the {} handed down on {}{}. Found by the Find Case Law search for {}.".format(
                court, _nice(published), (", " + citation) if citation else "", q.replace('"', "‘", 1).replace('"', "’"))
            yield _item(url=link, country="England and Wales", court=court, title=title, ref=citation,
                        published=published, summary=summary, what=what, event_type=event_type)


def _nice(iso: Optional[str]) -> str:
    try:
        return dt.date.fromisoformat((iso or "")[:10]).strftime("%-d %B %Y")
    except ValueError:
        return "an unrecorded date"


# ----------------------------------------------------------------------------
# Singapore - Singapore Law Watch judgments feed (SGHC, SGHC(I), SGCA), catchwords
# ----------------------------------------------------------------------------

SLW = "https://www.singaporelawwatch.sg/Portals/0/RSS/Judgments.xml"
_SG_COURTS = {
    "SGHC": "High Court of Singapore", "SGHC(I)": "Singapore International Commercial Court",
    "SGCA": "Court of Appeal of Singapore", "SGCA(I)": "Court of Appeal of Singapore (SICC appeal)",
    "SGHCR": "High Court of Singapore (Registrar)", "SGHC(A)": "Appellate Division of the High Court",
}
_SG_TITLE = re.compile(r"^(?P<name>.+?)\s+\[(?P<year>\d{4})\]\s+(?P<court>SG[A-Z]+(?:\([A-Z]\))?)\s+(?P<num>\d+)\s*$")


def _slw(days: int) -> Iterator[Dict]:
    cutoff = _cutoff(days)
    try:
        raw = get(SLW, ttl=1800).content
    except (Blocked, Exception):                      # noqa: BLE001 - boundary
        return
    for e in feedparser.parse(raw).entries:
        summary = _text(e.get("summary") or "")
        catchwords, _, tail = summary.partition("| Decision Date:")
        groups = [g.strip() for g in catchwords.split(";")]
        if not any(g.lower().startswith("arbitration") for g in groups):
            continue
        published = None
        m = re.search(r"(\d{1,2} \w{3} \d{4})", tail)
        if m:
            try:
                published = dt.datetime.strptime(m.group(1), "%d %b %Y").date().isoformat()
            except ValueError:
                published = None
        published = published or _published(e)
        if published and published < cutoff:
            continue
        title = _text(e.get("title") or "")
        tm = _SG_TITLE.match(title)
        name, citation, court = title, "", "Singapore courts"
        if tm:
            name = tm.group("name")
            citation = "[{}] {} {}".format(tm.group("year"), tm.group("court"), tm.group("num"))
            court = _SG_COURTS.get(tm.group("court"), tm.group("court"))
        event_type, what = _classify(catchwords, default="annulment_setaside", what="recourse against an award")
        text = "{} decided on {}{}. Catchwords: {}.".format(
            court, _nice(published), (", " + citation) if citation else "", "; ".join(groups))
        yield _item(url=(e.get("link") or "").replace(" ", "%20"), country="Singapore", court=court, title=name, ref=citation,
                    published=published, summary=text, what=what, event_type=event_type)


# ----------------------------------------------------------------------------
# Canada - CanLII per-court feeds (20 most recent decisions each, with catchwords)
# ----------------------------------------------------------------------------

CANLII = [
    ("en/ca/scc", "Supreme Court of Canada", "en"),
    ("en/ca/fca", "Federal Court of Appeal", "en"),
    ("en/ca/fct", "Federal Court", "en"),
    ("en/on/onca", "Court of Appeal for Ontario", "en"),
    ("en/on/onsc", "Ontario Superior Court of Justice", "en"),
    ("en/bc/bcca", "Court of Appeal for British Columbia", "en"),
    ("en/bc/bcsc", "Supreme Court of British Columbia", "en"),
    ("en/ab/abca", "Court of Appeal of Alberta", "en"),
    ("en/ab/abkb", "Court of King's Bench of Alberta", "en"),
    ("fr/qc/qcca", "Cour d'appel du Québec", "fr"),
    ("fr/qc/qccs", "Cour supérieure du Québec", "fr"),
]
_CA_ARB = re.compile(r"arbitra", re.I)
_CA_DOMESTIC = re.compile(r"grievance|griefs?\b|collective agreement|convention collective|labou?r relations|"
                          r"family|famil|spousal|child support|custody|parenting|employment standards|"
                          r"wrongful dismissal|condominium|strata|residential tenanc|insurance — accident|"
                          r"statutory accident benefits|automobile insurance|assurance automobile|"
                          r"droit administratif|administrative law|arbitrage obligatoire|r\u00e9gie des march|"
                          r"survivorship|estate|succession|\bwill\b|divorce|matrimonial|testament", re.I)
_CA_TITLE = re.compile(r"^(?P<name>.+?),\s+(?P<cite>\d{4} [A-Z]+ \d+)(?: \(CanLII\))?\s*$")


def _canlii(days: int) -> Iterator[Dict]:
    cutoff = _cutoff(days)
    for path, court, lang in CANLII:
        try:
            raw = get("https://www.canlii.org/{}/rss_new.xml".format(path), ttl=1800).content
        except (Blocked, Exception):                  # noqa: BLE001 - boundary
            continue
        for e in feedparser.parse(raw).entries:
            title = _text(e.get("title") or "")
            summary = _text(e.get("summary") or "")
            blob = title + " " + summary
            if not _CA_ARB.search(blob) or _CA_DOMESTIC.search(blob):
                continue
            published = _published(e)
            if published and published < cutoff:
                continue
            tm = _CA_TITLE.match(title)
            name, cite = (tm.group("name"), tm.group("cite")) if tm else (title, "")
            event_type, what = _classify(summary)
            text = "{} decided on {}{}. Catchwords: {}.".format(court, _nice(published), (", " + cite) if cite else "", summary)
            yield _item(url=e.get("link") or "", country="Canada", court=court, title=name, ref=cite,
                        published=published, summary=text, what=what, event_type=event_type, lang=lang)


# ----------------------------------------------------------------------------
# Netherlands - rechtspraak.nl open data (every published decision in the window,
# filtered on the court's own summary, the inhoudsindicatie)
# ----------------------------------------------------------------------------

RECHTSPRAAK = "https://data.rechtspraak.nl/uitspraken/zoeken"
_NL_ARB = re.compile(r"arbitr|scheidsgerecht|scheidsrechter|arbitraal|arbitrage", re.I)
_NL_TITLE = re.compile(r"^(?P<ecli>ECLI:NL:[A-Z]+:\d{4}:\d+),\s*(?P<court>[^,]+),\s*(?P<date>\d{2}-\d{2}-\d{4})(?:,\s*(?P<ref>.+))?$")


def _rechtspraak(days: int) -> Iterator[Dict]:
    cutoff = _cutoff(days)
    params = {"date": [cutoff, dt.date.today().isoformat()], "return": "DOC", "max": 1000, "sort": "DESC",
              "subject": "http://psi.rechtspraak.nl/rechtsgebied#civielRecht"}
    entries = []
    for start in (0, 1000, 2000):
        try:
            raw = get(RECHTSPRAAK, params=dict(params, **{"from": start}), ttl=3600, timeout=60).content
        except (Blocked, Exception):                  # noqa: BLE001 - boundary
            break
        page = feedparser.parse(raw).entries
        entries += page
        if len(page) < 1000 or (page[-1].get("updated") or "")[:10] < cutoff:
            break
    for e in entries:
        title = _text(e.get("title") or "")
        summary = _text(e.get("summary") or "")
        if not _NL_ARB.search(title + " " + summary):
            continue
        tm = _NL_TITLE.match(title)
        court, ecli, ref, decided = "Dutch court", "", "", None
        if tm:
            court, ecli, ref = tm.group("court"), tm.group("ecli"), tm.group("ref") or ""
            try:
                decided = dt.datetime.strptime(tm.group("date"), "%d-%m-%Y").date().isoformat()
            except ValueError:
                decided = None
        published = _published(e) or decided
        event_type, what = _classify(summary)
        text = "{}, uitspraak van {}{}. {}".format(court, _nice(decided or published), (" (" + ecli + ")") if ecli else "", summary)
        yield _item(url=e.get("link") or "", country="Netherlands", court=court, title=court + (" · " + ref if ref else ""),
                    ref=ecli, published=published, summary=text, what=what, event_type=event_type, lang="nl")


# ----------------------------------------------------------------------------
# Austria - RIS Judikatur open-data API (OGH, OLG, LG decision texts)
# ----------------------------------------------------------------------------

RIS = "https://data.bka.gv.at/ris/api/v2.6/Judikatur"
_RIS_TERMS = "Schiedsspruch OR Schiedsgericht OR Schiedsverfahren OR Schiedsvereinbarung OR Schiedsklausel"
_AT_COURTS = {"OGH": "Oberster Gerichtshof", "OLG": "Oberlandesgericht", "LG": "Landesgericht"}


def _ris_summary(url: str) -> str:
    try:
        html = get(url, ttl=86400, timeout=40).text
    except (Blocked, Exception):                      # noqa: BLE001 - boundary
        return ""
    text = _text(html)
    m = re.search(r"\bSpruch\b(.{40,700}?)(?:\bText\b|\bBegründung\b|\bRechtliche Beurteilung\b)", text)
    if m:
        return m.group(1).strip()
    k = text.find("Kopf")
    return text[k + 4:k + 500].strip() if k >= 0 else text[:400]


def _ris(days: int) -> Iterator[Dict]:
    cutoff = _cutoff(days)
    try:
        r = get(RIS, params={"Applikation": "Justiz", "Suchworte": _RIS_TERMS,
                             "Dokumenttyp.SucheInEntscheidungstexten": "true",
                             "Dokumenttyp.SucheInRechtssaetzen": "false",
                             "ImRisSeitVonDatum": cutoff, "DokumenteProSeite": "Fifty"}, ttl=3600, timeout=60)
        res = r.json()["OgdSearchResult"].get("OgdDocumentResults") or {}
    except (Blocked, Exception):                      # noqa: BLE001 - boundary
        return
    refs = res.get("OgdDocumentReference") or []
    if isinstance(refs, dict):
        refs = [refs]
    for x in refs:
        try:
            data = x["Data"]
            meta = data["Metadaten"]
            ju = meta.get("Judikatur") or {}
            jz = ju.get("Justiz") or {}
            gz = ju.get("Geschaeftszahl") or {}
            gz = gz.get("item") if isinstance(gz, dict) else gz
            if isinstance(gz, list):
                gz = gz[0]
            decided = (ju.get("Entscheidungsdatum") or "")[:10]
            published = (meta.get("Allgemein") or {}).get("Veroeffentlicht") or decided
            court_code = jz.get("Gericht") or "OGH"
            court = _AT_COURTS.get(court_code, court_code)
            html_url = ""
            for ref in (data.get("Dokumentliste") or {}).get("ContentReference", []) if isinstance((data.get("Dokumentliste") or {}).get("ContentReference"), list) else [(data.get("Dokumentliste") or {}).get("ContentReference") or {}]:
                for u in (ref.get("Urls") or {}).get("ContentUrl", []):
                    if u.get("DataType") == "Html":
                        html_url = u.get("Url") or ""
            url = html_url or (meta.get("Allgemein") or {}).get("DokumentUrl") or ""
        except (KeyError, TypeError, AttributeError):
            continue
        if not url or not gz:
            continue
        # A decision re-imported years later is not news; keep the window on the decision itself.
        if decided and decided < (dt.date.today() - dt.timedelta(days=max(days, 120))).isoformat():
            continue
        spruch = _ris_summary(url)
        event_type, what = _classify(spruch, what="decision in an arbitration matter")
        text = "{}, Entscheidung vom {} ({}), im RIS veröffentlicht am {}. {}".format(
            court, _nice(decided), gz, _nice(published), spruch)
        yield _item(url=url, country="Austria", court=court, title="{} {}".format(court_code, gz), ref=gz,
                    published=published, summary=text, what=what, event_type=event_type, lang="de")


# ----------------------------------------------------------------------------
# Germany - Bundesgerichtshof decisions feed; the I. Zivilsenat hears arbitration
# matters under docket letters "I ZB", confirmed against the decision's own text
# ----------------------------------------------------------------------------

BGH = "https://www.bundesgerichtshof.de/DE/Service/RSSFeed/Function/RSS_EN.xml"
_BGH_DOCKET = re.compile(r"^(?P<ref>I ZB \d+/\d+),\s*Entscheidung vom (?P<date>\d{2}\.\d{2}\.\d{4})")


def _pdf_text(content: bytes, pages: int = 4) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        return " ".join((p.extract_text() or "") for p in reader.pages[:pages])
    except Exception:                                 # noqa: BLE001 - optional dependency, bad PDFs
        return ""


def _bgh(days: int) -> Iterator[Dict]:
    cutoff = _cutoff(days)
    try:
        raw = get(BGH, ttl=1800).content
    except (Blocked, Exception):                      # noqa: BLE001 - boundary
        return
    for e in feedparser.parse(raw).entries:
        m = _BGH_DOCKET.match(_text(e.get("title") or ""))
        if not m:
            continue
        published = _published(e)
        if published and published < cutoff:
            continue
        link = e.get("link") or ""
        try:
            page = get(link, ttl=86400).text
        except (Blocked, Exception):                  # noqa: BLE001 - boundary
            continue
        pm = re.search(r'href="([^"]+\.pdf[^"]*)"', page)
        if not pm:
            continue
        pdf_url = pm.group(1).replace("&amp;", "&")
        if pdf_url.startswith("/"):
            pdf_url = "https://www.bundesgerichtshof.de" + pdf_url
        try:
            text = _pdf_text(get(pdf_url, ttl=86400, timeout=40).content)
        except (Blocked, Exception):                  # noqa: BLE001 - boundary
            continue
        if len(re.findall(r"schieds", text, re.I)) < 3:
            continue                                  # I ZB also covers trade-mark appeals
        text = re.sub(r"\s+", " ", text)
        op = re.search(r"(?:beschlossen|für Recht erkannt):\s*(.{40,500}?)(?:Gründe:|$)", text)
        spruch = op.group(1).strip() if op else text[:400]
        try:
            decided = dt.datetime.strptime(m.group("date"), "%d.%m.%Y").date().isoformat()
        except ValueError:
            decided = published
        event_type, what = _classify(spruch + " " + text[:3000], what="decision in an arbitration matter (§§ 1025 ff. ZPO)")
        summary = "Bundesgerichtshof, I. Zivilsenat, Beschluss vom {} ({}). {}".format(_nice(decided), m.group("ref"), spruch)
        yield _item(url=link, country="Germany", court="Bundesgerichtshof", title="BGH " + m.group("ref"), ref=m.group("ref"),
                    published=published or decided, summary=summary, what=what, event_type=event_type, lang="de")


# ----------------------------------------------------------------------------
# DIFC Courts (Dubai) - arbitration and enforcement lists
# ----------------------------------------------------------------------------

DIFC = "https://www.difccourts.ae/rules-decisions/judgments-orders/{}"
_DIFC_BLOCK = re.compile(r'<div class="each_result[^"]*">\s*<h4><a href="([^"]+)"[^>]*>(.*?)</a></h4>\s*'
                         r'<p class="label_small">(.*?)</p>\s*<p class="content_desc">(.*?)</p>', re.S)
_DIFC_TITLE = re.compile(r"^(?P<ref>(?:ARB|ENF|CFI|CA|SCT|CFI-)\s*[\d/]+)\s+(?P<name>.+)$")


def _difc(days: int) -> Iterator[Dict]:
    cutoff = _cutoff(days)
    for cat in ("arbitration", "enforcement"):
        try:
            html = get(DIFC.format(cat), ttl=3600, timeout=40).text
        except (Blocked, Exception):                  # noqa: BLE001 - boundary
            continue
        for url, title, label, desc in _DIFC_BLOCK.findall(html):
            title, label, desc = _text(title), _text(label), _text(desc)
            if cat == "enforcement" and not re.search(r"arbitra|award", desc, re.I):
                continue
            dm = re.match(r"([A-Z][a-z]+ \d{1,2}, \d{4})", label)
            published = None
            if dm:
                try:
                    published = dt.datetime.strptime(dm.group(1), "%B %d, %Y").date().isoformat()
                except ValueError:
                    published = None
            if published and published < cutoff:
                continue
            tm = _DIFC_TITLE.match(title)
            ref, name = (tm.group("ref"), tm.group("name")) if tm else ("", title)
            court = "DIFC Court of Appeal" if "COURT OF APPEAL" in desc.upper() else "DIFC Court of First Instance"
            k = desc.find("UPON")
            body = desc[k:] if k >= 0 else desc
            body = body.replace("Continue Reading »", "").strip()
            event_type, what = _classify(body, default=("enforcement_action" if cat == "enforcement" else "commercial_dispute"),
                                         what=("enforcement of an award" if cat == "enforcement" else "arbitration claim before the DIFC Courts"))
            kind = (label[dm.end():] if dm else label).strip(" -")
            summary = "{} ({}), {}, {}. {}".format(court, ref, kind or "judgment", _nice(published), body)
            yield _item(url=url, country="United Arab Emirates (DIFC)", court=court, title=name, ref=ref,
                        published=published, summary=summary, what=what, event_type=event_type)


# ----------------------------------------------------------------------------
# AIFC Court (Astana) - judgments list
# ----------------------------------------------------------------------------

AIFC = "https://court.aifc.kz/judgments/"
_AIFC_BLOCK = re.compile(r'<div class="block_jud">(.*?)<div class="view_more_list">', re.S)


def _aifc(days: int) -> Iterator[Dict]:
    cutoff = _cutoff(days)
    try:
        html = get(AIFC, ttl=3600, timeout=40).text
    except (Blocked, Exception):                      # noqa: BLE001 - boundary
        return
    for block in _AIFC_BLOCK.findall(html):
        tm = re.search(r'<a class="list_jud_title_block" href="([^"]+)">(.*?)</a>', block, re.S)
        if not tm:
            continue
        url, title = tm.group(1), _text(tm.group(2))
        ref = _text((re.search(r'class="case_page">(.*?)</div>', block, re.S) or [None, ""])[1]).replace("CASE No:", "").strip()
        dm = re.search(r'class="date_page">(\d{2})\.(\d{2})\.(\d{4})', block)
        published = "{}-{}-{}".format(dm.group(3), dm.group(2), dm.group(1)) if dm else None
        summary = _text((re.search(r'class="summary_block">(.*?)</div>', block, re.S) or [None, ""])[1])
        judges = _text((re.search(r'class="judges_name">(.*?)</div>', block, re.S) or [None, ""])[1])
        if not re.search(r"arbitra|\bIAC\b", title + " " + summary, re.I):
            continue
        if published and published < cutoff:
            continue
        court = "AIFC Court of Appeal" if "/CA/" in ref else "AIFC Court of First Instance"
        event_type, what = _classify(summary)
        text = "{} ({}), {}{}. {}".format(court, ref, _nice(published), (", before " + judges) if judges else "", summary)
        yield _item(url=url, country="Kazakhstan (AIFC)", court=court, title=title.title() if title.isupper() else title,
                    ref=ref, published=published, summary=text, what=what, event_type=event_type)


# ----------------------------------------------------------------------------
# African law reports on the Peachjam platform (Laws.Africa) - open search API
# ----------------------------------------------------------------------------

PEACHJAM = [
    ("Kenya", "https://new.kenyalaw.org"),
    ("Nigeria", "https://nigerialii.org"),
    ("Uganda", "https://ulii.org"),
    ("Tanzania", "https://tanzlii.org"),
    ("Zambia", "https://zambialii.org"),
    ("Malawi", "https://malawilii.org"),
    ("South Africa", "https://lawlibrary.org.za"),
    ("Namibia", "https://namiblii.org"),
    ("Zimbabwe", "https://zimlii.org"),
    ("Sierra Leone", "https://sierralii.gov.sl"),
    ("Eswatini", "https://eswatinilii.org"),
]
PEACHJAM_QUERIES = ['"arbitral award"', '"arbitration clause"', '"arbitration agreement"']
_PJ_PARTIES = re.compile(r"\s+\((?=[^)]*\b(?:No\.?|of)\s?\d)|\s+\[\d{4}\]")
_PJ_CITE = re.compile(r"\[\d{4}\] [A-Z]+ \d+(?: \([A-Z]+\))?")
_PJ_HTML = re.compile(r'<li class="mb-4 hit[^"]*"[^>]*>(.*?)</li>', re.S)
# The docket type in the case name says what the court was asked to do. Arbitration
# causes and miscellaneous or commercial applications are where set-aside and
# enforcement live; petitions, land and employment matters mention awards in passing.
_PJ_KIND = re.compile(r"\([^()]*\b(?:Arbitration|Miscellaneous|Misc\.?|Commercial)\b[^()]*\d[^()]*\)", re.I)
_PJ_NOISE_COURT = re.compile(r"\] (?:KEMC|KEELC|KEELRC|KEET|KESRTC|KEHAT|KECA)\b")


def _pj_clean_title(title: str) -> Tuple[str, str]:
    name = _PJ_PARTIES.split(title, maxsplit=1)[0].strip()
    cm = _PJ_CITE.search(title)
    return name or title, (cm.group(0) if cm else "")


def _peachjam(days: int) -> Iterator[Dict]:
    cutoff = _cutoff(days)
    seen = set()
    for country, host in PEACHJAM:
        for q in PEACHJAM_QUERIES:
            try:
                r = get(host + "/search/api/documents/", params={"search": q, "ordering": "-date", "page_size": 10},
                        ttl=3600, timeout=40)
                j = r.json()
            except (Blocked, Exception):              # noqa: BLE001 - boundary
                continue
            rows: List[Dict] = []
            for res in j.get("results") or []:
                if (res.get("doc_type") or "judgment").lower() != "judgment":
                    continue
                snippets = []
                for pg in res.get("pages") or []:
                    for frag in (pg.get("highlight") or {}).get("pages.body", []):
                        snippets.append(_text(frag))
                rows.append({"url": host + (res.get("expression_frbr_uri") or ""), "title": res.get("title") or "",
                             "date": res.get("date") or "", "court": res.get("court") or "", "snippet": " … ".join(snippets[:2])})
            if not rows and j.get("results_html"):
                for hit in _PJ_HTML.findall(j["results_html"]):
                    am = re.search(r'<a class="h5[^"]*"\s+href="([^"]+)"[^>]*>(.*?)</a>', hit, re.S)
                    spans = [_text(s) for s in re.findall(r'<span class="me-3">(.*?)</span>', hit, re.S)]
                    marks = [_text(x) for x in re.findall(r"([^<>]{0,120}<mark>.*?</mark>[^<>]{0,120})", hit, re.S)]
                    if not am or re.search(r"gazette|act\b|regulations", _text(am.group(2)), re.I):
                        continue
                    date = ""
                    for s in spans:
                        try:
                            date = dt.datetime.strptime(s, "%d %B %Y").date().isoformat()
                            break
                        except ValueError:
                            continue
                    court = next((s for s in spans if re.search(r"court|tribunal", s, re.I)), "")
                    rows.append({"url": host + am.group(1), "title": _text(am.group(2)), "date": date, "court": court,
                                 "snippet": " … ".join(marks[:2])})
            for row in rows:
                if not row["date"] or row["date"] < cutoff or row["url"] in seen:
                    continue
                if _PJ_NOISE_COURT.search(row["title"]) or not (
                        re.search(r"arbitra", row["title"], re.I) or _PJ_KIND.search(row["title"])):
                    continue
                seen.add(row["url"])
                name, cite = _pj_clean_title(row["title"])
                court = row["court"] or "{} courts".format(country)
                default_what = ("application under the Arbitration Act" if re.search(r"arbitration cause", row["title"], re.I)
                                else "arbitration-related judgment")
                event_type, what = _classify(row["title"] + " " + row["snippet"], what=default_what)
                summary = "{}, {}{}. Matched the phrase {}.{}".format(
                    court, _nice(row["date"]), (", " + cite) if cite else "", q.replace('"', "‘", 1).replace('"', "’"),
                    (" “" + row["snippet"] + "”") if row["snippet"] else "")
                yield _item(url=row["url"], country=country, court=court, title=name, ref=cite,
                            published=row["date"], summary=summary, what=what, event_type=event_type)


# ----------------------------------------------------------------------------

READERS = [_fcl, _slw, _canlii, _rechtspraak, _ris, _bgh, _difc, _aifc, _peachjam]


def run(days: int = 7) -> Iterator[Dict]:
    for reader in READERS:
        try:
            for item in reader(days):
                if item.get("url") and item.get("title"):
                    yield item
        except Exception:                             # noqa: BLE001 - one court must not stop the rest
            continue
