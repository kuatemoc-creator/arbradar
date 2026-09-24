"""The national press that publishes no feed, read through Google News.

Of the outlets on the map, half publish no RSS. Google News indexes nearly all
of them within minutes, and its search feed answers to a `site:` clause. So the
feedless outlets are swept in batches of eight, per language, with the dispute
terms of that language: one query reads eight papers, and the answer names
the outlet each article came from. Nothing is decoded; the feed's own link and
outlet name are kept, as in the other sweeps.

The outlet list is docs/press.json, written by tools/discover.py: every outlet
whose feed check did not pass.
"""
import datetime as dt
import html as _html
import json
import os
import re
import time
import urllib.parse as up
from typing import Dict, Iterator, List, Tuple
from urllib.parse import urlsplit

import feedparser

from ..config import ROOT
from ..fetch import get
from .editions import EDITIONS
from .rss import relevant

ENDPOINT = "https://news.google.com/rss/search"
BATCH = 8
_TRAIL = re.compile(r"\s+[-|\u2013\u2014]\s+[^-|\u2013\u2014]{2,60}$")     # "Headline - Outlet Name"

# Compact dispute terms per language; a site: query has little room. English
# is the fallback: most national papers carry English loanwords in their
# international pages, and Google matches across languages loosely.
TERMS: Dict[str, str] = {
    "en": '(arbitration OR ICSID OR "investment treaty" OR expropriation OR nationalisation OR nationalization OR "licence revoked" OR "license revoked" OR "arbitral award" OR "arbitral tribunal")',
    "es": '(arbitraje OR CIADI OR laudo OR expropiación OR nacionalización OR "tratado bilateral" OR "revocación de licencia" OR "revoca la licencia")',
    "pt": '(arbitragem OR CIRDI OR "sentença arbitral" OR expropriação OR desapropriação OR nacionalização OR "tratado bilateral")',
    "fr": '(arbitrage OR CIRDI OR "sentence arbitrale" OR expropriation OR nationalisation OR "traité bilatéral" OR "retrait de licence" OR "retrait du permis")',
    "de": '(Schiedsverfahren OR Schiedsgericht OR ICSID OR Schiedsspruch OR Enteignung OR Verstaatlichung OR Investitionsschutz)',
    "it": '(arbitrato OR ICSID OR "lodo arbitrale" OR espropriazione OR nazionalizzazione OR "trattato bilaterale")',
    "nl": '(arbitrage OR ICSID OR "arbitraal vonnis" OR onteigening OR nationalisatie OR investeringsverdrag)',
    "ru": '(арбитраж OR МЦУИС OR "арбитражное решение" OR экспроприация OR национализация OR "инвестиционный спор" OR "отозвал лицензию" OR "аннулировал лицензию")',
    "uk": '(арбітраж OR МЦУІС OR "арбітражне рішення" OR експропріація OR націоналізація OR "інвестиційний спір" OR "анулював ліцензію")',
    "tr": '(tahkim OR ICSID OR "hakem kararı" OR kamulaştırma OR millileştirme OR "yatırım anlaşması" OR "lisansı iptal")',
    "ar": '(تحكيم OR "حكم تحكيم" OR مصادرة OR تأميم OR "معاهدة استثمار" OR "إلغاء الترخيص" OR إكسيد)',
    "fa": '(داوری OR "رای داوری" OR مصادره OR "ملی شدن" OR "لغو مجوز" OR ایکسید)',
    "id": '(arbitrase OR ICSID OR "putusan arbitrase" OR nasionalisasi OR pencabutan izin OR "perjanjian investasi")',
    "vi": '("trọng tài" OR ICSID OR "phán quyết trọng tài" OR "quốc hữu hóa" OR "thu hồi giấy phép" OR "hiệp định đầu tư")',
    "th": '(อนุญาโตตุลาการ OR ICSID OR "คำชี้ขาด" OR "ยึดกิจการ" OR "เพิกถอนใบอนุญาต")',
    "ms": '(timbang tara OR ICSID OR "award timbang tara" OR pemilik negara OR "lesen dibatalkan")',
    "hi": '(मध्यस्थता OR ICSID OR "मध्यस्थता निर्णय" OR राष्ट्रीयकरण OR "लाइसेंस रद्द")',
    "bn": '(সালিশ OR ICSID OR "সালিশি রায়" OR জাতীয়করণ OR "লাইসেন্স বাতিল")',
    "ja": '(仲裁 OR ICSID OR 仲裁判断 OR 国有化 OR 収用 OR 投資協定)',
    "ko": '(중재 OR ICSID OR 중재판정 OR 국유화 OR 수용 OR 투자협정)',
    "zh": '(仲裁 OR ICSID OR 仲裁裁决 OR 国有化 OR 征收 OR 投资协定)',
    "pl": '(arbitraż OR ICSID OR "wyrok arbitrażowy" OR wywłaszczenie OR nacjonalizacja OR "umowa inwestycyjna" OR "cofnięcie koncesji")',
    "cs": '(arbitráž OR ICSID OR "rozhodčí nález" OR vyvlastnění OR znárodnění OR "investiční dohoda")',
    "sk": '(arbitráž OR ICSID OR "rozhodcovský rozsudok" OR vyvlastnenie OR znárodnenie OR "investičná dohoda")',
    "hu": '(választottbíróság OR ICSID OR "választottbírósági ítélet" OR kisajátítás OR államosítás OR "beruházásvédelmi")',
    "ro": '(arbitraj OR ICSID OR "hotărâre arbitrală" OR expropriere OR naționalizare OR "tratat bilateral" OR "retragerea licenței")',
    "bg": '(арбитраж OR ICSID OR "арбитражно решение" OR отчуждаване OR национализация OR "инвестиционен спор")',
    "el": '(διαιτησία OR ICSID OR "διαιτητική απόφαση" OR απαλλοτρίωση OR εθνικοποίηση OR "επενδυτική συμφωνία")',
    "sr": '(arbitraža OR ICSID OR "arbitražna odluka" OR eksproprijacija OR nacionalizacija OR "investicioni spor" OR арбитража)',
    "hr": '(arbitraža OR ICSID OR "arbitražna odluka" OR izvlaštenje OR nacionalizacija OR "investicijski spor")',
    "bs": '(arbitraža OR ICSID OR "arbitražna odluka" OR eksproprijacija OR nacionalizacija OR "investicioni spor")',
    "sl": '(arbitraža OR ICSID OR "arbitražna odločba" OR razlastitev OR nacionalizacija OR "investicijski spor")',
    "mk": '(арбитража OR ICSID OR "арбитражна одлука" OR експропријација OR национализација OR "инвестициски спор")',
    "sq": '(arbitrazh OR ICSID OR "vendim arbitrazhi" OR shpronësim OR shtetëzim OR "marrëveshje investimi")',
    "lv": '(arbitrāža OR ICSID OR "šķīrējtiesas nolēmums" OR ekspropriācija OR nacionalizācija OR "ieguldījumu līgums")',
    "lt": '(arbitražas OR ICSID OR "arbitražo sprendimas" OR ekspropriacija OR nacionalizacija OR "investicijų sutartis")',
    "et": '(vahekohus OR ICSID OR "vahekohtu otsus" OR sundvõõrandamine OR natsionaliseerimine OR "investeeringute leping")',
    "fi": '(välimiesmenettely OR ICSID OR välitystuomio OR pakkolunastus OR kansallistaminen OR investointisuoja)',
    "sv": '(skiljeförfarande OR ICSID OR skiljedom OR expropriation OR förstatligande OR investeringsskydd)',
    "no": '(voldgift OR ICSID OR voldgiftsdom OR ekspropriasjon OR nasjonalisering OR investeringsavtale)',
    "da": '(voldgift OR ICSID OR voldgiftskendelse OR ekspropriation OR nationalisering OR investeringsaftale)',
    "is": '(gerðardómur OR ICSID OR eignarnám OR þjóðnýting OR fjárfestingarsamningur)',
    "he": '(בוררות OR ICSID OR "פסק בוררות" OR הפקעה OR הלאמה OR "הסכם השקעות")',
    "sw": '(usuluhishi OR ICSID OR "uamuzi wa usuluhishi" OR kutaifisha OR "leseni imefutwa" OR mkataba wa uwekezaji)',
    "am": '(ግልግል OR ICSID OR "የግልግል ውሳኔ" OR መወረስ OR "ፈቃድ መሰረዝ")',
    "mn": '(арбитр OR ICSID OR "арбитрын шийдвэр" OR улсын мэдэлд OR "тусгай зөвшөөрөл хүчингүй")',
    "hy": '(արբիտրաժ OR ICSID OR "արբիտրաժային վճիռ" OR ազգայնացում OR բռնագրավում OR "ներդրումային վեճ")',
    "ka": '(არბიტრაჟი OR ICSID OR "საარბიტრაჟო გადაწყვეტილება" OR ნაციონალიზაცია OR ექსპროპრიაცია OR "საინვესტიციო დავა")',
    "az": '(arbitraj OR ICSID OR "arbitraj qərarı" OR milliləşdirmə OR "lisenziya ləğv" OR "investisiya mübahisəsi")',
    "uz": '(arbitraj OR ICSID OR "arbitraj qarori" OR milliylashtirish OR "litsenziya bekor" OR "investitsiya nizosi")',
}


def _edition(lang: str) -> Tuple[str, str, str]:
    for label, hl, gl, ceid, l in EDITIONS:
        if l == lang:
            return hl, gl, ceid
    return "en-GB", "GB", "GB:en"


def _host(url: str) -> str:
    return re.sub(r"^(www|amp|m|en|fr|es|ru)\.", "", urlsplit(url).netloc.lower())


def feedless() -> List[Dict[str, str]]:
    """Outlets on the map whose feed check did not pass, from docs/press.json."""
    path = os.path.join(ROOT, "docs", "press.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh).get("results") or []
    except (OSError, ValueError):
        return []
    out, seen = [], set()
    for r in rows:
        if r.get("status") == "ok" or not r.get("url"):
            continue
        host = _host(r["url"])
        if not host or host in seen:
            continue
        seen.add(host)
        out.append({"country": r.get("country") or "", "name": r.get("name") or host, "host": host, "lang": r.get("lang") or "en"})
    return out


def _batches(outlets: List[Dict[str, str]]) -> Iterator[Tuple[str, List[Dict[str, str]]]]:
    by_lang: Dict[str, List[Dict[str, str]]] = {}
    for o in outlets:
        by_lang.setdefault(o["lang"] if o["lang"] in TERMS else "en", []).append(o)
    for lang, rows in by_lang.items():
        for i in range(0, len(rows), BATCH):
            yield lang, rows[i:i + BATCH]


def _published(e) -> str:
    for k in ("published_parsed", "updated_parsed"):
        if e.get(k):
            return dt.date(*e[k][:3]).isoformat()
    return ""


def run(days: int = 7) -> Iterator[Dict]:
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    seen = set()
    for lang, batch in _batches(feedless()):
        hl, gl, ceid = _edition(lang)
        q = "({}) {} when:{}d".format(" OR ".join("site:" + o["host"] for o in batch), TERMS.get(lang, TERMS["en"]), max(1, days))
        url = "{}?q={}&hl={}&gl={}&ceid={}".format(ENDPOINT, up.quote(q), hl, gl, ceid)
        try:
            raw = get(url, ttl=1800).content
        except Exception:                             # noqa: BLE001 - boundary
            continue
        time.sleep(0.3)
        by_host = {o["host"]: o for o in batch}
        for e in feedparser.parse(raw).entries:
            title = _TRAIL.sub("", _html.unescape((e.get("title") or "").strip()))
            published = _published(e)
            if not title or (published and published < cutoff):
                continue
            src = e.get("source") or {}
            host = _host(src.get("href") or "")
            outlet = by_host.get(host)
            if outlet is None:
                # the batch's hosts by suffix: "news.example.com" for "example.com"
                outlet = next((o for h, o in by_host.items() if host.endswith(h)), None)
            key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            summary = re.sub(r"<[^>]+>", " ", e.get("summary") or "")[:1500]
            if not relevant(title + " " + summary):
                continue
            name = outlet["name"] if outlet else (src.get("title") or host)
            country = outlet["country"] if outlet else ""
            yield {
                "url": e.get("link") or "",
                "source": "{} ({})".format(name, country) if country else name,
                "title": title[:300],
                "summary": summary,
                "published_at": published or None,
                "lang": lang,
                "country": country,
                "flag_reason": "national press with no feed, read through a Google News site: query",
            }
