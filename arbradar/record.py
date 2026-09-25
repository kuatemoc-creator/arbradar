"""The record behind a report.

GAR and IAReporter write from documents: a court's order, a docket entry, an
ICSID case page, a filing. The reader wants the document, not the write-up.
For each story from the press this looks for the primary record it reports -
the ICSID case page, the US federal docket on CourtListener, the English
judgment on Find Case Law, the PCA case - by the parties named in the
headline, within a month of the story, and attaches it as the entry's record.
The record is cited first on the source line; the report becomes the "also".
Nothing is attached on a guess: the party names must match.
"""
import datetime as dt
import re
import urllib.parse as up
from typing import Any, Dict, List, Optional

import feedparser

from . import db
from .fetch import get
from .match import _entities, _stem
from .sources.editions import states_in

CL = "https://www.courtlistener.com/api/rest/v4/search/"
CL_BASE = "https://www.courtlistener.com"
FCL = "https://caselaw.nationalarchives.gov.uk/atom.xml"

_PRESS_EVENTS = ("enforcement_action", "annulment_setaside", "award_issued", "new_case_filed", "s1782_application",
                 "interim_relief", "notice_of_intent", "counsel_instructed", "settlement")
_COURT_WORDS = re.compile(r"\b(court|judge|magistrate|tribunal confirms|confirm|vacat|enforc|set aside|annul|attach|garnish|"
                          r"immunity|petition|1782|discovery)\b", re.I)
_ENGLAND = re.compile(r"\b(English|England|UK|London|Commercial Court|High Court|Court of Appeal|Privy Council)\b")
_US = re.compile(r"\b(US|U\.S\.|American|federal|New York|Washington|Delaware|Texas|Florida|California)\s+(court|judge|magistrate|appeals|district|circuit|petition)|"
                 r"\b(district court|S\.D\.N\.Y\.|D\.D\.C\.|D\.C\. Circuit|Second Circuit|Fifth Circuit|Ninth Circuit|Southern District|Eastern District)\b", re.I)


def _names(it: Dict[str, Any]) -> List[str]:
    """The parties worth searching by: named parties on the record, then the
    entities and States in the headline."""
    out: List[str] = []
    for n in (it.get("claimants") or []) + (it.get("respondents") or []):
        if n and len(n) > 2 and n not in out:
            out.append(n)
    title = it.get("title_en") or it.get("title") or ""
    for s in states_in(title):
        # "US court", "UK judge": the forum, not a party. They join only when the record names them.
        if s in ("United States", "United Kingdom") and s not in (it.get("respondents") or []) + (it.get("claimants") or []):
            continue
        if s not in out:
            out.append(s)
    for w in re.findall(r"\b[A-Z][A-Za-z&'’.-]{2,}(?:\s+[A-Z][A-Za-z&'’.-]{2,}){0,3}", title):
        if _stem(w.split()[0].lower()) in _entities(title) and w not in out:
            out.append(w)
    return out[:4]


def _forms(name: str) -> List[str]:
    """A State under every name the gazetteer knows for it: Laos is 'Lao People's
    Democratic Republic' on a docket, Turkey is 'Türkiye' or 'Republic of Turkey'."""
    from .sources.editions import COUNTRIES
    canon = COUNTRIES.get(name)
    if not canon:
        return [name]
    forms = [f for f, c in COUNTRIES.items() if c == canon]
    stems = {f[:5].lower() for f in forms if len(f) >= 5}
    return forms + sorted(stems)


def _is_state(name: str) -> bool:
    from .sources.editions import COUNTRIES
    return name in COUNTRIES


def _overlap(names: List[str], text: str, need_party: bool = False, single_state_ok: bool = False) -> bool:
    """The names in the text. With need_party, a State alone is not enough: a
    docket or case page is matched on a party, not on the country it is against.
    single_state_ok lets one State carry the match when the caller has already
    tied the result to the story by date and court."""
    t = (text or "").lower()
    hit_party = any(n.lower() in t for n in names if len(n) > 3 and not _is_state(n))
    states_hit = sum(1 for n in names if _is_state(n) and any(f.lower() in t for f in _forms(n)))
    if need_party:
        # A single State carries the match only where the case name shows a
        # sovereign party ("Republic of", "Government of"), not a person called Laos.
        sovereign = bool(re.search(r"\b(republic|government|kingdom|state of|federation|ministry|emirate|sultanate|commonwealth|nation)\b", t))
        return hit_party or states_hit >= 2 or (single_state_ok and states_hit >= 1 and sovereign and not any(not _is_state(n) for n in names))
    return hit_party or states_hit >= 1


def _window(it: Dict[str, Any], days: int = 30):
    when = str(it.get("published_at") or dt.date.today().isoformat())[:10]
    try:
        base = dt.date.fromisoformat(when)
    except ValueError:
        base = dt.date.today()
    return (base - dt.timedelta(days=days)).isoformat(), (base + dt.timedelta(days=3)).isoformat()


def icsid(conn, it: Dict[str, Any], names: List[str]) -> Optional[Dict[str, str]]:
    lo, hi = _window(it, 45)
    rows = conn.execute("SELECT title, url, published_at, summary FROM items WHERE source='ICSID docket' "
                        "AND published_at BETWEEN ? AND ? ORDER BY published_at DESC", (lo, hi)).fetchall()
    for r in rows:
        if _overlap(names, r["title"], need_party=True):
            return {"source": "ICSID docket", "url": r["url"], "title": r["title"], "snippet": r["summary"] or ""}
    return None


def pca(conn, it: Dict[str, Any], names: List[str]) -> Optional[Dict[str, str]]:
    lo, hi = _window(it, 60)
    rows = conn.execute("SELECT title, url, published_at, summary FROM items WHERE source LIKE 'PCA%' "
                        "AND COALESCE(published_at, substr(fetched_at,1,10)) BETWEEN ? AND ?", (lo, hi)).fetchall()
    for r in rows:
        if _overlap(names, r["title"], need_party=True):
            return {"source": "PCA case list", "url": r["url"], "title": r["title"], "snippet": r["summary"] or ""}
    return None


def courtlistener(it: Dict[str, Any], names: List[str]) -> Optional[Dict[str, str]]:
    """The docket whose case name carries the parties: one fielded query, the
    States under every form the gazetteer knows, a company by its name."""
    import os
    headers = {}
    if os.environ.get("COURTLISTENER_TOKEN"):
        headers["Authorization"] = "Token " + os.environ["COURTLISTENER_TOKEN"]
    clauses = []
    for n in names[:3]:
        if _is_state(n):
            clauses.append("caseName:({})".format(" OR ".join('"{}"'.format(f) for f in _forms(n)[:3] if len(f) >= 3)))
        else:
            clauses.append('caseName:"{}"'.format(n.replace('"', "")))
    if not clauses:
        return None
    q = " AND ".join(clauses)
    try:
        r = get(CL, params={"q": q, "type": "r", "order_by": "dateFiled desc"}, ttl=6 * 3600, headers=headers)
        results = r.json().get("results", [])
    except Exception:                                 # noqa: BLE001 - boundary
        return None
    lo, hi = _window(it, 4 * 365)
    for res in results[:8]:
        case = res.get("caseName") or ""
        if not _overlap(names, case, need_party=True):
            continue
        filed = str(res.get("dateFiled") or "")[:10]
        if filed and not (lo <= filed <= hi):
            continue                                  # a docket from another decade is another matter
        parties = res.get("party") or []
        docs = res.get("recap_documents") or []
        desc = (docs[0].get("description") or "") if docs else ""
        return {"source": "US federal docket", "url": CL_BASE + (res.get("docket_absolute_url") or ""),
                "title": "{} ({} {})".format(case, res.get("court_citation_string") or "", res.get("docketNumber") or "").strip(),
                "snippet": "{} Parties: {}.".format(desc, "; ".join(parties[:4]))}
    return None


def opinion(it: Dict[str, Any], names: List[str]) -> Optional[Dict[str, str]]:
    """A US court's own opinion, order or report on CourtListener: the case name
    carries the parties, the text is the court's, and the date is within a
    month of the story. Better than a docket: it is the decision itself."""
    import os
    headers = {}
    if os.environ.get("COURTLISTENER_TOKEN"):
        headers["Authorization"] = "Token " + os.environ["COURTLISTENER_TOKEN"]
    clauses = []
    for n in names[:3]:
        if _is_state(n):
            clauses.append("caseName:({})".format(" OR ".join('"{}"'.format(f) for f in _forms(n)[:3] if len(f) >= 3)))
        else:
            clauses.append('caseName:"{}"'.format(n.replace('"', "")))
    if not clauses:
        return None
    lo, hi = _window(it, 45)
    try:
        r = get(CL, params={"q": " AND ".join(clauses), "type": "o", "order_by": "dateFiled desc"}, ttl=6 * 3600, headers=headers)
        results = r.json().get("results", [])
    except Exception:                                 # noqa: BLE001 - boundary
        return None
    lo14, hi14 = _window(it, 14)
    for res in results[:6]:
        case = res.get("caseName") or ""
        filed = str(res.get("dateFiled") or "")[:10]
        tight = bool(filed and lo14 <= filed <= hi14)
        if not _overlap(names, case, need_party=True, single_state_ok=tight) or (filed and not (lo <= filed <= hi)):
            continue
        snippet = ""
        for op in res.get("opinions") or []:
            snippet = _opinion_paragraph(op.get("id"), headers, CL_BASE + (res.get("absolute_url") or "")) or re.sub(r"<[^>]+>", " ", op.get("snippet") or "")
            if snippet.strip():
                break
        return {"source": "US court opinion", "url": CL_BASE + (res.get("absolute_url") or ""),
                "title": "{} ({}, {})".format(case, res.get("court") or "", filed).strip(),
                "snippet": re.sub(r"\s+", " ", snippet).strip()}
    return None


def _opinion_paragraph(op_id, headers, page_url: str = "") -> str:
    """The first substantive paragraph of the court's text: not the caption, not
    the counsel list, a paragraph of sentences that says what the court did.
    The API needs a token; without one the public page carries the same text."""
    text = ""
    if op_id:
        try:
            r = get(CL_BASE + "/api/rest/v4/opinions/{}/".format(op_id), ttl=7 * 24 * 3600, headers=headers)
            j = r.json()
            text = j.get("plain_text") or re.sub(r"<[^>]+>", " ", j.get("html_with_citations") or j.get("html") or "")
        except Exception:                             # noqa: BLE001 - boundary
            text = ""
    if not text and page_url:
        try:
            html_page = get(page_url, ttl=7 * 24 * 3600).text
            body = re.search(r'<(?:article|div)[^>]+(?:id="opinion-content"|class="[^"]*opinion[^"]*")[^>]*>(.*?)</(?:article|div)>', html_page, re.S)
            chunk = body.group(1) if body else html_page
            chunk = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", chunk, flags=re.S)
            chunk = re.sub(r"</p>|<br\s*/?>", "\n\n", chunk)
            text = re.sub(r"<[^>]+>", " ", chunk)
            text = __import__("html").unescape(text)
        except Exception:                             # noqa: BLE001 - boundary
            text = ""
    if re.search(r"not a robot|enable javascript|verify that you", text or "", re.I):
        return ""                                     # a bot check is not the court's text, and is not worked around
    for para in re.split(r"\n\s*\n", text or ""):
        p = re.sub(r"\s+", " ", para).strip()
        words = p.split()
        if len(words) < 25 or len(words) > 220:
            continue
        letters = [c for c in p if c.isalpha()]
        if letters and sum(1 for c in letters if c.isupper()) / len(letters) > 0.3:
            continue                                  # a caption or a heading
        if re.search(r"\b(Petitioner|Respondent|Plaintiff|Defendant)s?,\s+v\.", p) or p.count("v.") > 1 and len(words) < 40:
            continue
        if "." not in p:
            continue
        return p
    return ""


def find_case_law(it: Dict[str, Any], names: List[str]) -> Optional[Dict[str, str]]:
    lo, hi = _window(it, 30)
    for n in names[:3]:
        url = "{}?{}".format(FCL, up.urlencode({"query": n, "order": "-date"}))
        try:
            raw = get(url, ttl=6 * 3600).content
        except Exception:                             # noqa: BLE001 - boundary
            continue
        for e in feedparser.parse(raw).entries[:8]:
            title = e.get("title") or ""
            pub = ""
            for k in ("published_parsed", "updated_parsed"):
                if e.get(k):
                    pub = dt.date(*e[k][:3]).isoformat()
                    break
            if pub and not (lo <= pub <= hi):
                continue
            if _overlap(names, title, need_party=True):
                return {"source": "Find Case Law (England and Wales)", "url": e.get("link") or "", "title": title,
                        "snippet": re.sub(r"<[^>]+>", " ", e.get("summary") or "")[:400]}
    return None


def find(conn, it: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """The primary record a press report is about, or None."""
    src = it.get("source") or ""
    if src.startswith(("ICSID docket", "US federal docket", "Court:", "PCA", "SEC EDGAR", "Wire /")):
        return None                                   # already a record
    names = _names(it)
    if not names:
        return None
    title = it.get("title_en") or it.get("title") or ""
    text = title + " " + (it.get("summary") or "")
    for finder in (lambda: icsid(conn, it, names) if re.search(r"ICSID|treaty|BIT\b|annulment|ad hoc committee", text, re.I) else None,
                   lambda: opinion(it, names) if (_US.search(text) or _COURT_WORDS.search(text)) else None,
                   lambda: courtlistener(it, names) if (_US.search(text) or _COURT_WORDS.search(text)) else None,
                   lambda: find_case_law(it, names) if _ENGLAND.search(text) else None,
                   lambda: pca(conn, it, names) if re.search(r"PCA|UNCITRAL|Permanent Court", text) else None):
        try:
            rec = finder()
        except Exception:                             # noqa: BLE001 - boundary
            rec = None
        if rec and rec.get("url"):
            return rec
    return None


def attach(conn, items: List[Dict[str, Any]]) -> int:
    n = 0
    for it in items:
        stored = it.get("record")
        if stored:
            continue
        rec = find(conn, it)
        if rec:
            it["record"] = rec
            it["corroboration"] = [rec] + [c for c in (it.get("corroboration") or []) if c.get("url") != rec["url"]]
            n += 1
    return n
