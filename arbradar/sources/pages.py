"""Registers, gazettes, regulators, exchanges, courts and tender portals that
publish a page but no feed.

A hundred-odd State pages on the map answer to a script and offer no RSS:
the government's decrees, the mining cadastre's notices, the exchange's
announcements, a court's judgment list, a treasury's page on the disputes it
defends. Each is read the way a person skims it: the headline links on the
page, kept when they speak of a licence or concession being revoked, an
expropriation, a tax demand, an arbitration or a tender for counsel. No
article page is fetched here. A page that only offers a search box yields
nothing, honestly.

The list is docs/sources.json, written by tools/sourcemap.py --probe: every
non-press candidate whose status is `html`.
"""
import concurrent.futures as cf
import json
import os
import re
from typing import Dict, Iterator, List

from ..config import ROOT
from ..fetch import get, Blocked
from .frontpage import headlines
from .rss import _STRONG, _ASSET, _ACTION, relevant

# Words that make a headline on a court list an arbitration matter.
_COURT = re.compile(r"arbitra|arbitral award|set aside|annul|enforc|exequatur|arbitral tribunal|new york convention|anti-suit|stay of proceedings|"
                    r"schieds|sentence arbitrale|laudo|lodo|арбитраж|арбітраж|tahkim|hakem|تحكيم", re.I)
# A tender for the State's lawyers.
_TENDER = re.compile(r"legal (services|advis|counsel|representation)|law firm|attorney|counsel|arbitration|litigation|"
                     r"servicios (legales|jurídicos)|asesor[ií]a (legal|jurídica)|representaci[óo]n (legal|judicial)|"
                     r"services juridiques|conseil juridique|cabinet d'avocats|юридическ|адвокат|юридичн|hukuk|avukat", re.I)
# A listed company telling the market about a dispute.
_DISCLOSE = re.compile(r"arbitra|dispute|claim|litigation|award|tribunal|notice of|expropriat|licen[cs]e|concession|"
                       r"terminat|revok|settlement|lawsuit|court", re.I)
# A State act against an asset: the gazette is the State, so no actor word is needed.
_TAX = re.compile(r"windfall|back tax|tax (assessment|demand|claim|reassessment)|royalt(?:y|ies) (?:increase|hike|rise|dispute)|export (ban|duty)|price cap|"
                  r"nationali|expropri|confiscat|seiz|temporary (management|administration)|external management|"
                  r"national[ií]za|expropia|incaut|embarg|национализ|экспроприац|конфиск|изъят|kamulaştır|el koy", re.I)


def candidates() -> List[Dict[str, str]]:
    path = os.path.join(ROOT, "docs", "sources.json")
    if not os.path.exists(path):
        return []
    try:
        rows = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out, seen = [], set()
    for country, kind, name, url, note, status, detail in rows:
        if kind == "press" or status != "html" or not url or url in seen:
            continue
        seen.add(url)
        out.append({"country": country, "kind": kind, "name": name, "url": url})
    return out


def keep(kind: str, title: str) -> bool:
    if relevant(title):
        return True
    if kind == "courts":
        return bool(_COURT.search(title))
    if kind == "tenders":
        return bool(_TENDER.search(title))
    if kind == "exchange":
        return bool(_DISCLOSE.search(title)) and bool(_STRONG.search(title) or _ASSET.search(title) or _TAX.search(title))
    # gazette, regulator, register: the page's owner is the State
    return bool(_STRONG.search(title) or _TAX.search(title) or (_ASSET.search(title) and _ACTION.search(title)))


# The link on an institution's home page that leads to what it publishes:
# its news, decisions, decrees, notices, judgments, announcements.
_SECTION = re.compile(r"\b(news|press[- ]?releases?|announcements?|notices?|decisions?|decrees?|resolutions?|judgments?|judgements?|"
                      r"rulings?|circulars?|publications?|bulletins?|gazette|latest|actualit[eé]s?|communiqu[eé]s?|d[eé]cisions?|"
                      r"d[eé]crets?|arr[eê]t[eé]s?|noticias|comunicados|resoluciones|decretos|sentencias|boletines?|novedades|"
                      r"not[ií]cias|decis[oõ]es|atos|haberler|duyurular|kararlar|basın|новости|пресс-центр|решения|постановления|"
                      r"указы|новини|рішення|постанови|укази|yangiliklar|qarorlar|xəbərlər|qərarlar|жаңалықтар|шешімдер|"
                      r"լուրեր|որոշումներ|სიახლეები|გადაწყვეტილებები|мэдээ|шийдвэр|berita|keputusan|pengumuman|"
                      r"أخبار|قرارات|بيانات|events?|what's new|media cent(er|re)|disputes?|arbitration|cases)\b", re.I)
_SECTION_PATH = re.compile(r"/(news|press|media|announcements?|notices?|decisions?|decrees?|judgments?|judgements?|rulings?|"
                           r"actualites?|communiques?|noticias|comunicados|resoluciones|decretos|sentencias|novedades|"
                           r"noticias|decisoes|haberler|duyurular|kararlar|novosti|news-and|newsroom|press-releases?|"
                           r"publications?|bulletin|latest|events|cases|disputes?|arbitration)(/|$|\?)", re.I)


def _sections(page_url: str, text: str, limit: int = 2) -> List[str]:
    from .frontpage import _A, _TAG
    host = re.sub(r"^www\.", "", __import__("urllib.parse").parse.urlsplit(page_url).netloc.lower())
    from urllib.parse import urljoin, urlsplit
    found: List[str] = []
    for href, inner in _A.findall(text):
        label = re.sub(r"\s+", " ", _TAG.sub(" ", inner)).strip()
        url = urljoin(page_url, href.strip())
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or host not in parts.netloc.lower():
            continue
        if (len(label.split()) <= 4 and _SECTION.search(label)) or _SECTION_PATH.search(parts.path):
            if url.rstrip("/") != page_url.rstrip("/") and url not in found:
                found.append(url)
        if len(found) >= limit * 3:
            break
    # prefer the shortest paths: "/news" over "/news/2019/archive"
    found.sort(key=lambda u: len(urlsplit(u).path))
    return found[:limit]


def _read(src: Dict[str, str]):
    """The page and, one click further, its news or decisions section."""
    try:
        r = get(src["url"], ttl=1800, timeout=20)
    except (Blocked, Exception):                      # noqa: BLE001 - boundary
        return src, []
    text = r.text or ""
    if "<html" not in text[:3000].lower() and "<a " not in text[:20000].lower():
        return src, []
    pages = [(src["url"], text)]
    for sec in _sections(src["url"], text):
        try:
            t = get(sec, ttl=1800, timeout=20).text or ""
        except (Blocked, Exception):                  # noqa: BLE001 - boundary
            continue
        if "<a " in t.lower():
            pages.append((sec, t))
    return src, pages


def run(days: int = 7) -> Iterator[Dict]:
    srcs = candidates()
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        pages = list(ex.map(_read, srcs))
    for src, found in pages:
        seen = set()
        for page_url, text in found:
            for h in headlines(page_url, text):
                if h["url"] in seen or not keep(src["kind"], h["title"]):
                    continue
                seen.add(h["url"])
                yield {
                    "url": h["url"],
                    "source": "{} ({})".format(src["name"], src["country"]) if src["country"] != "Global" else src["name"],
                    "title": h["title"][:300],
                    "summary": "",
                    "published_at": None,
                    "lang": "en",
                    "country": src["country"] if src["country"] != "Global" else None,
                    "flag_reason": "{} page: {}".format(src["kind"], src["name"]),
                }


def probe(out_path: str = None) -> Dict[str, Dict[str, int]]:
    """How much each page gives: section pages followed and headlines read.
    Written to docs/pages.json so the source map can say which pages are
    script-rendered or search-only and yield nothing to a script."""
    srcs = candidates()
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(_read, srcs))
    stats = {}
    for src, found in res:
        stats[src["url"]] = {"sections": max(0, len(found) - 1),
                             "headlines": sum(len(list(headlines(u, t))) for u, t in found)}
    out_path = out_path or os.path.join(ROOT, "docs", "pages.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=1)
    return stats


if __name__ == "__main__":
    st = probe()
    print(len(st), "pages;", sum(1 for v in st.values() if v["headlines"]), "readable;",
          sum(v["headlines"] for v in st.values()), "headlines")
