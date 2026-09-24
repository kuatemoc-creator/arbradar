"""Which copy of a story to cite.

Google News and the feeds bring the same story in from many outlets. The copy
we cite should be the most authoritative one on hand, not the first one seen:
a wire or a major paper first, then the trade and legal press, then national
business papers, then everything else.
"""
import re
from typing import Optional
from urllib.parse import urlsplit

_TIERS = {
    1: ("reuters", "bloomberg", "ft.com", "financial times", "wsj", "wall street journal", "apnews", "associated press",
        "afp", "economist", "nytimes", "new york times", "theguardian", "guardian", "bbc", "cnbc", "politico",
        "handelsblatt", "lemonde", "le monde", "elpais", "el país", "el pais", "nikkei", "thetimes", "the times",
        "washingtonpost", "washington post", "telegraph", "lesechos", "les echos", "faz.net", "frankfurter allgemeine"),
    2: ("globalarbitrationreview", "global arbitration review", "gar", "iareporter", "law360", "lexology", "jusmundi",
        "kluwerarbitration", "kluwer arbitration blog", "legalbusiness", "legal business", "thelawyer", "the lawyer",
        "globallegalpost", "global legal post", "latinlawyer", "latin lawyer", "legalbusinessonline", "asian legal business",
        "law.com", "lawgazette", "law gazette", "mining.com", "upstreamonline", "upstream", "energyvoice", "spglobal",
        "s&p global", "argusmedia", "lloydslist", "lloyd's list", "tradewindsnews", "tradewinds", "seatrade-maritime",
        "seatrade maritime", "miningweekly", "mining weekly", "northernminer", "the northern miner", "livelaw", "bar & bench",
        "barandbench", "iisd", "investment treaty news", "ciarb", "jdsupra"),
    3: ("hurriyetdailynews", "hürriyet daily news", "hurriyet daily news", "dailysabah", "daily sabah", "thehindu", "the hindu",
        "economictimes", "the economic times", "livemint", "mint", "business-standard", "business standard", "kommersant",
        "vedomosti", "rbc.ru", "interfax", "tass", "lanacion", "la nación", "la nacion", "elfinanciero", "el financiero",
        "expansion.com", "expansión", "folha", "valor", "businessday", "business day", "theeastafrican", "the east african",
        "nation.africa", "premiumtimesng", "premium times", "thecable", "punchng", "vanguardngr", "businesslive",
        "moneycontrol", "hindustantimes", "hindustan times", "indianexpress", "indian express", "scmp", "south china morning post",
        "straitstimes", "the straits times", "businesstimes", "the business times", "theedgemalaysia", "the edge",
        "jakartapost", "bangkokpost", "bangkok post", "khaleejtimes", "khaleej times", "thenationalnews", "the national",
        "arabnews", "arab news", "timesofisrael", "haaretz", "kyivindependent", "kyiv independent", "pravda.com.ua",
        "ukrinform", "news.am", "civilnet", "hetq", "azernews", "report.az", "trend.az", "agenda.ge", "interpressnews",
        "kursiv", "tengrinews", "zakon.kz", "gazeta.uz", "kun.uz", "dailynewsegypt", "daily news egypt", "ahram",
        "aljazeera", "al jazeera", "africanews", "theafricareport", "the africa report", "ecofin", "jeuneafrique", "jeune afrique"),
}


# The arbitration trade press. A headline from these is arbitration news whatever
# words it uses, and gets a floor weight when the rules see only commentary.
TRADE_PRESS = ("gar", "global arbitration review", "globalarbitrationreview", "iareporter", "law360 international arbitration",
               "latin lawyer", "latinlawyer", "kluwer arbitration blog", "jus mundi", "jusmundi", "ciarb", "arbitration blog")


def is_trade_press(source: str, url: str = "") -> bool:
    text = " ".join(x for x in ((source or "").replace("Google News / ", ""), _host(url or "")) if x).lower()
    return any(k in text for k in TRADE_PRESS)


def _host(url: str) -> str:
    try:
        h = urlsplit(url).netloc.lower()
    except ValueError:
        return ""
    return re.sub(r"^(www|amp|m)\.", "", h)


def rank(source: Optional[str] = None, url: Optional[str] = None) -> int:
    """1 = wires and majors, 2 = trade and legal press, 3 = national business press, 4 = the rest."""
    text = " ".join(x for x in ((source or "").replace("Google News / ", ""), _host(url or "")) if x).lower()
    if not text:
        return 4
    for tier in (1, 2, 3):
        for key in _TIERS[tier]:
            k = key.lower()
            if len(k) <= 4:                    # "gar", "afp", "bbc", "wsj", "tass", "mint": whole word only
                if re.search(r"(?<![\w.])" + re.escape(k) + r"(?![\w])", text):
                    return tier
            elif k in text:
                return tier
    return 4


def label(url: str, fallback: str = "") -> str:
    """A readable outlet name from a URL when the feed gave none: 'dailysabah.com'."""
    host = _host(url or "")
    return host or fallback
