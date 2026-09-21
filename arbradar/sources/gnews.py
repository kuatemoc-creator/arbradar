"""Google News RSS - the pre-dispute layer.

A treaty claim is announced months before it is registered: an AIM-listed miner
files an RNS saying it has served a notice of dispute, a wire carries a company
"considering all legal remedies" after a licence is pulled, a minister says a
concession will be "reviewed". Google News indexes all of that within the hour
and exposes it as RSS with a full query language, for free.

Two query families:
  * generic distress terms, worldwide
  * one query per watchlist State, so a country you care about is swept even
    when the story never uses the word "arbitration"
"""
import calendar
import datetime as dt
import html as _html
import re
import urllib.parse as up
from typing import Dict, Iterator, List

import feedparser

import time

from .. import config
from ..fetch import get
from .editions import EDITIONS, TERMS, MEASURES, MAJORS

ENDPOINT = "https://news.google.com/rss/search"

GENERIC: List[str] = [
    '"notice of dispute" (treaty OR ICSID OR arbitration)',
    '"notice of intent" (arbitration OR "investment treaty" OR ICSID)',
    '"notice of arbitration" (government OR republic OR state OR ministry)',
    '"investment treaty" (claim OR filed OR threatens OR "will pursue")',
    '"international arbitration" (government OR ministry) (threatens OR "legal action" OR "all remedies")',
    'expropriation (compensation OR arbitration OR "treaty claim")',
    '(nationalisation OR nationalization) (compensation OR investors OR arbitration)',
    '("licence revoked" OR "license revoked" OR "permit cancelled" OR "concession terminated") (mining OR energy OR company)',
    '"ICSID" (files OR registered OR claim OR "notice")',
    '"Energy Charter Treaty" (claim OR arbitration)',
    '("windfall tax" OR "export ban" OR "asset freeze") investors arbitration',
]

COMMERCIAL: List[str] = [
    '"request for arbitration" (ICC OR LCIA OR SIAC OR HKIAC OR SCC OR contractor OR "joint venture" OR supplier)',
    '(EPC OR contractor OR consortium OR FIDIC) (arbitration OR "dispute board" OR "adjudication board") (terminated OR delay OR claim)',
    '("power purchase agreement" OR PPA OR "gas supply" OR LNG OR "take-or-pay" OR "price review") arbitration',
    '(mining OR "joint venture" OR offtake OR royalty OR streaming) arbitration (ICC OR LCIA OR claim OR award)',
    '(pharma OR pharmaceutical OR biotech OR "licensing agreement" OR royalty OR milestone) arbitration (claim OR award OR tribunal)',
    '(shipping OR charterparty OR shipyard OR "shipbuilding contract") arbitration (award OR claim OR LMAA)',
    '(telecom OR spectrum OR "tower" OR "network sharing") arbitration (award OR claim OR tribunal)',
    '("arbitral award" OR "arbitration award") (million OR billion) (contractor OR supplier OR "joint venture" OR licensee OR operator)',
    '("force majeure" OR "notice of default" OR "termination notice") (arbitration OR "dispute resolution") (contract OR project)',
    '(insurer OR reinsurer OR "political risk") arbitration (claim OR award)',
]

# Who moved, who was appointed: the industry's own news, English editions only.
PEOPLE: List[str] = [
    '("international arbitration" OR "arbitration partner" OR "arbitration practice" OR "disputes partner") (joins OR hires OR hired OR "new partner" OR promoted OR appointed OR launches OR "opens office")',
    '("head of arbitration" OR "head of international arbitration" OR "arbitration head" OR "arbitration chair" OR "disputes head") (joins OR hires OR leaves OR moves OR appointed OR named)',
    '(arbitrator OR "ICC Court" OR "LCIA Court" OR ICSID OR "SIAC Court" OR HKIAC OR "PCA") (appointed OR elected OR named) (president OR "secretary general" OR "secretary-general" OR "vice president" OR member OR chair OR registrar)',
]

COUNTRY = '"{state}" (arbitration OR ICSID OR "investment treaty" OR expropriation OR "notice of dispute" OR nationalisation OR "licence revoked")'

_TRAIL = re.compile(r"\s+-\s+[^-]{2,60}$")     # "Headline - Outlet Name"


def _queries(states: List[str]) -> Iterator[str]:
    for q in GENERIC:
        yield q
    for s in states:
        yield COUNTRY.format(state=s)


def _published(entry) -> str:
    tm = entry.get("published_parsed")
    return dt.date.fromtimestamp(calendar.timegm(tm)).isoformat() if tm else ""


def _sweep(days: int):
    """(query, hl, gl, ceid, lang, country, family) for the global edition plus
    every configured local edition in its own language. Two families: dispute
    terms, and State measures against investors (no dispute word needed)."""
    settings = config.load()
    from .editions import COUNTRIES
    states = list((settings.states or {}).keys())
    states += sorted(set(COUNTRIES.values()) - set(states))     # every State the gazetteer knows
    for q in _queries(states):
        yield q, "en-GB", "GB", "GB:en", "en", "", "dispute"
    for q in MEASURES["en"]:
        yield q, "en-GB", "GB", "GB:en", "en", "", "measure"
    for q in COMMERCIAL:
        yield q, "en-GB", "GB", "GB:en", "en", "", "commercial"
    for q in PEOPLE:
        yield q, "en-GB", "GB", "GB:en", "en", "", "people"
    wanted = set(getattr(settings, "editions", None) or [])
    for label, hl, gl, ceid, lang in EDITIONS:
        if wanted and label not in wanted:
            continue
        for q in TERMS.get(lang, TERMS["en"]):
            yield q, hl, gl, ceid, lang, label, "dispute"
        for q in MEASURES.get(lang, []):
            yield q, hl, gl, ceid, lang, label, "measure"


# A commercial-sweep hit with no arbitration word in the headline or the snippet is
# an article that mentions arbitration somewhere down the page, not a dispute story.
_COMMERCIAL_SIGNAL = re.compile(r"arbitra|\bICC\b|\bLCIA\b|\bSIAC\b|\bHKIAC\b|\bSCC\b|\bLMAA\b|\bICSID\b|award|"
                                r"tribunal|dispute board|adjudicat|\bDAB\b|FIDIC|\bclaim\b", re.I)

_MAJOR_RE = [(m, re.compile(r"(?<![\w-])" + re.escape(m) + r"(?![\w-])",
                              0 if len(m) <= 5 else re.I)) for m in MAJORS]


_ADVERSE = re.compile(
    r"revok|cancel|terminat|seiz|nationali[sz]|expropriat|confiscat|suspend|halt|freez|\bban(s|ned)?\b|block|"
    r"windfall|back tax|tax (assessment|demand|claim|bill)|reassess|takes? (control|over)|temporary administration|"
    r"forced|arrest|raid|strip|annul|withdr|scrap|overturn|reject|refus|impos|fine[sd]?\b|penalt|"
    r"revoc|cancel|rescind|caduc|expropi|nacionaliz|incaut|embarg|suspend|prohíb|bloque|congel|"
    r"аннулир|отозв|отзыв|расторг|национализ|экспроприац|арест|изъят|заморо|приостанов|запрет|"
    r"анулю|скасув|розірв|націоналізац|експропріац|iptal|fesh|kamulaştır|millileştir|el koy|askıya|"
    r"retir|annul|résili|nationalis|exproprie|saisi|gel[ée]|interdi|suspend", re.I)


def _majors(text: str) -> List[str]:
    """Whole-word matches only. A five-letter-or-shorter name must also match case,
    or "Eni" is found inside "opening" and "Citi" inside "citing"."""
    return [m for m, rx in _MAJOR_RE if rx.search(text)]


def run(days: int = 7) -> Iterator[Dict]:
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    seen = set()

    for q, hl, gl, ceid, lang, country, family in _sweep(days):
        full = "{} when:{}d".format(q, max(1, days))
        url = "{}?q={}&hl={}&gl={}&ceid={}".format(ENDPOINT, up.quote(full), hl, gl, ceid)
        try:
            raw = get(url, ttl=1800).content
        except Exception:                             # noqa: BLE001 - boundary
            continue
        time.sleep(0.3)                               # polite; ~100 feeds a run
        for e in feedparser.parse(raw).entries:
            title = (e.get("title") or "").strip()
            published = _published(e)
            if not title or (published and published < cutoff):
                continue
            # The same story syndicates across outlets under near-identical
            # headlines; collapse on the headline minus the outlet suffix.
            key = re.sub(r"[^a-z0-9]+", " ", _TRAIL.sub("", title).lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            outlet = (e.get("source") or {}).get("title") or ""
            clean_title = _html.unescape(_TRAIL.sub("", title)[:300])
            summary = re.sub(r"<[^>]+>", " ", e.get("summary") or "")[:1500]
            majors = _majors(clean_title + " " + summary)
            item = {
                "url": e.get("link") or "",
                "source": "Google News" + (" / " + outlet if outlet else ""),
                "title": clean_title,
                "summary": summary,
                "published_at": published or None,
                "lang": lang,
                "country": country,            # the edition it came through, not the subject
                "claimants": majors[:3],       # the investor of means, if one is named
            }
            if family == "commercial":
                if _COMMERCIAL_SIGNAL.search(clean_title + " " + summary):
                    item["event_type"] = "commercial_dispute"
                    item["flag_reason"] = "commercial-arbitration sweep"
                else:
                    item["event_type"] = "commentary"
                    item["flag_reason"] = "commercial sweep; no arbitration term in the headline or snippet"
            if family == "people":
                item["flag_reason"] = "people-and-appointments sweep"   # the rules label it a move or an appointment
            if family == "measure":
                # A measure story needs an adverse act in the headline - a contract award,
                # an import policy, a deal is not a measure - and only earns the lead
                # weight when it names an investor who can pay.
                if not _ADVERSE.search(clean_title) or re.search(r"\bseiz(?:e|es|ed|ing) (?:on|upon)\b", clean_title, re.I):
                    item["event_type"] = "commentary"
                else:
                    item["event_type"] = "state_measure" if majors else "distress_event"
                item["flag_reason"] = ("State-measure sweep ({} edition); investor of means named: {}".format(
                    country or "global", ", ".join(majors[:2])) if majors else
                    "State-measure sweep ({} edition); no listed investor named".format(country or "global"))
            yield item
