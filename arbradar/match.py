"""Same story or not.

Everything that decides whether two texts are about one matter lives here:
the identity of an item (its canonical URL, its title fingerprint), the stems
and the names a headline carries, the company names that make two headlines
two matters, the clustering that folds five outlets' copies of one
development into one story, and the measure-and-place rule that makes four
days of windfall-tax headlines one lead.

The rules are the cases that went wrong once; tests/test_matching.py keeps
them: Papel is not Mellat, the EU windfall tax is one lead under any headline,
a Czech one is another, a story keeps the copies it already has.
"""
import hashlib
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

from .sources.editions import states_in


TRACKING = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$)")

def canonical(url: str) -> str:
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    query = "&".join(q for q in parts.query.split("&")
                     if q and not TRACKING.match(q.split("=")[0]))
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       parts.path.rstrip("/"), query, ""))


def title_key(item: Dict[str, Any]) -> str:
    """Normalised-title identity, independent of which copy's link we hold."""
    norm = re.sub(r"[^a-z0-9]+", " ", (item.get("title") or "").lower()).strip()
    return hashlib.sha256(norm.encode()).hexdigest()


def fingerprint(item: Dict[str, Any]) -> str:
    """URL identity first; fall back to normalised title so the same story from
    two outlets collapses to one line."""
    url = canonical(item.get("url") or "")
    if url:
        return hashlib.sha256(url.encode()).hexdigest()
    norm = re.sub(r"[^a-z0-9]+", " ", (item.get("title") or "").lower()).strip()
    return hashlib.sha256(norm.encode()).hexdigest()


PAYWALL = ("you are not logged in", "subscribe to read", "please log in", "log in to read",
           "this content is for subscribers", "subscribers only", "sign in to continue",
           "the topic tool shows you", "case law discussion for 3000+ topics", "become a subscriber")


def is_paywall(text: str) -> bool:
    t = (text or "").strip().lower()
    return not t or any(t.startswith(p) or t == p.rstrip(".") for p in PAYWALL)


STOP = set("the a an of to in on for and or with by from at as is are was were be has have "
           "had its their this that over under against into after before amid says said new "
           "will could may how why who what when "
           # registry boilerplate - every ICSID headline carries these
           "icsid case registered arb republic kingdom state states united".split())
_SUFFIX = re.compile(r"(ments?|ations?|ings?|ies|es|ed|s)$")


def _stem(w: str) -> str:
    """Crude but sufficient: enforce / enforces / enforcement -> enforc."""
    if w.isdigit():
        return w
    if re.match(r"^\d+[mkb]n?$", w):          # 350m, 1bn -> 350, 1
        return re.sub(r"[a-z]+$", "", w)
    st = _SUFFIX.sub("", w)
    return st if len(st) >= 3 else w



_ALIAS = {"kremlin": "russia", "moscow": "russia", "putin": "russia", "beijing": "china", "ankara": "turkey",
          "erdogan": "turkey", "washington": "united", "kyiv": "ukraine", "tehran": "iran", "riyadh": "saudi"}


def _fold(text: str) -> str:
    """Nestlé and Nestle are the same word."""
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()


_SHORT_OK = {"eu", "us", "uk", "un"}


def _tokens(title: str) -> set:
    return {_stem(_ALIAS.get(w, w)) for w in re.findall(r"[a-z0-9]+", _fold(title).lower())
            if (len(w) >= 3 or w in _SHORT_OK) and w not in STOP}


def _bigrams(title: str) -> set:
    """Consecutive content words, stemmed: 'windfall tax', 'notice intent'."""
    words = [w for w in re.findall(r"[a-z0-9]+", _fold(title).lower()) if (len(w) >= 3 or w in _SHORT_OK) and w not in STOP]
    stems = [_stem(_ALIAS.get(w, w)) for w in words]
    return set(zip(stems, stems[1:]))


def _state_stems() -> set:
    from .sources.editions import COUNTRIES
    out = set(_stem(v) for v in _ALIAS.values())
    names = list(COUNTRIES.keys()) if isinstance(COUNTRIES, dict) else list(COUNTRIES)
    for n in names:
        for w in re.findall(r"[a-z0-9]+", _fold(str(n)).lower()):
            if len(w) >= 3:
                out.add(_stem(w))
    return out


def _propers(title: str) -> set:
    """Capitalised words after the first, minus stop words - the names in a headline."""
    words = re.findall(r"[A-Za-z][A-Za-z'\u00c0-\u024f]+", title or "")
    return {_stem(_ALIAS.get(_fold(w).lower(), _fold(w).lower())) for w in words[1:]
            if w[0].isupper() and len(w) >= 4 and w.lower() not in STOP}


def shared_propers(a: str, b: str) -> set:
    """Capitalised words two headlines share, minus the words of the trade
    (court, tribunal, award) and the first word of each. 'Devas', 'Iraq',
    'Turkey' count; 'Court', 'Appeal', 'Award' do not."""
    def props(t):
        words = re.findall(r"[A-Za-z][A-Za-z'\u00c0-\u024f]+", (t or "").replace("-", " "))
        return {_stem(_fold(w).lower()) for w in words[1:] if w[:1].isupper() and len(w) >= 3 and w.lower() not in STOP}
    # A State in common is the subject of a hundred stories a week, not a
    # signature - unless the headline names nothing but States (Iraq v Turkey,
    # Laos' enforcement bid), in which case the States are all there is.
    noise = {"us", "uk", "new", "high", "supreme", "state", "federal", "district", "national"}
    pa, pb = props(a), props(b)
    named = (pa & pb) - _GENERIC - _STATE_STEMS() - noise
    if named:
        return named
    if not (pa - _GENERIC - _STATE_STEMS() - noise):          # the headline has no other name to match on
        return (pa & pb) & _STATE_STEMS()
    return set()


def _entities(title: str) -> set:
    """The names in a headline that are neither a State nor an ordinary word
    capitalised by Title Case: 'Papel', 'Mellat', 'Yukos', not 'Bank' or 'Court'."""
    from .style import _is_common
    from .sources.editions import states_in
    english = _english()
    state_words = {w.lower() for s in states_in(title or "") for w in re.findall(r"[A-Za-z]+", s)}
    state_words |= {w.lower() for w in re.findall(r"[A-Za-z]+", title or "") if w in _JUR_WORDS}
    words = re.findall(r"[A-Za-z][A-Za-z'\u00c0-\u024f]+", title or "")
    out = set()
    for w in words[1:]:
        lw = _fold(w).lower().split("'")[0].split("\u2019")[0]
        if w[0].isupper() and len(lw) >= 4 and lw not in STOP and lw not in state_words and not _is_common(lw) \
                and not _in_english(lw, english) and lw not in _CITIES and _stem(lw) not in _STATE_STEMS():
            out.add(_stem(lw))
    return out


_ENGLISH: Optional[set] = None
# Capitals and financial centres: a place in a headline is not a party.
_CITIES = set("""london paris moscow beijing delhi mumbai dubai abu dhabi geneva zurich frankfurt madrid rome berlin vienna
brussels amsterdam hague stockholm oslo copenhagen helsinki warsaw prague budapest bucharest sofia athens istanbul ankara
cairo riyadh jeddah doha kuwait tehran baghdad erbil beirut amman damascus kyiv minsk chisinau tbilisi yerevan baku astana
almaty tashkent bishkek dushanbe ashgabat ulaanbaatar tokyo seoul shanghai shenzhen jakarta bangkok manila hanoi kuala
lumpur lagos abuja nairobi accra johannesburg pretoria cape town lusaka harare luanda maputo kinshasa dakar abidjan
casablanca rabat tunis algiers tripoli khartoum addis ababa kigali kampala dodoma mexico bogota lima santiago buenos aires
brasilia paulo caracas quito paz montevideo asuncion panama washington york houston miami toronto ottawa vancouver
calgary sydney melbourne perth canberra wellington delaware luxembourg belgrade zagreb ljubljana skopje tirana sarajevo
podgorica pristina riga vilnius tallinn nicosia valletta lisbon dublin edinburgh manchester milan munich hamburg""".split())


def _in_english(w: str, english: set) -> bool:
    """The word or its base form: 'Meets', 'Spreads', 'Granting' are English."""
    if w in english:
        return True
    for suffix in ("s", "es", "ed", "d", "ing", "ies"):
        if w.endswith(suffix) and len(w) - len(suffix) >= (5 if suffix == "s" else 3):
            base = w[: -len(suffix)] + ("y" if suffix == "ies" else "")
            if base in english or base + "e" in english:
                return True                           # 'Devas' is not the plural of a deva; a five-letter base is
    return False


def _english() -> set:
    """Ordinary English words, so that a Title Case headline's 'Anger', 'Crack'
    and 'Sterling' are not taken for company names."""
    global _ENGLISH
    if _ENGLISH is None:
        import gzip
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "english-words.txt.gz")
        try:
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                _ENGLISH = {w.strip() for w in fh if w.strip()}
        except OSError:
            _ENGLISH = set()
    return _ENGLISH


_JUR_WORDS = {"EU", "UK", "US", "UN", "USA"}
_STATE_STEMS_CACHE: Optional[set] = None


def _STATE_STEMS() -> set:
    global _STATE_STEMS_CACHE
    if _STATE_STEMS_CACHE is None:
        _STATE_STEMS_CACHE = _state_stems()
    return _STATE_STEMS_CACHE


# Words of the trade that pair up in any headline: "high court", "court grants",
# "interim relief". A phrase made only of these is not the signature of a story.
_GENERIC = {_stem(w) for w in """court courts high supreme appeal appeals tribunal arbitral arbitration award awards judge judges
ruling rules dispute disputes claim claims relief interim injunction case cases bench division commercial grants granted order
orders decision holds held enforcement enforce set aside annul annulment application petition hearing judgment judgments
international investor investors treaty state government ministry minister law legal firm partner partners""".split()}


_STAGES = {"award": ("award_issued", "enforcement_action", "annulment_setaside"),
           "filing": ("new_case_filed", "notice_of_intent"),
           "measure": ("state_measure", "distress_event")}


def _stage(it: Dict[str, Any]):
    """The stage of a matter an item reports, coarser than the event type: an
    award confirmed and an award enforced are the same stage."""
    e = it.get("event_type") or ""
    for name, kinds in _STAGES.items():
        if e in kinds:
            return name
    return None


def cluster(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Greedy story clustering on headline overlap.

    Google News brings the same development in from five outlets under five
    headlines. Items arrive score-descending, so the best-scored version becomes
    the story and the others hang off it as "also reported by". A cluster is
    compared on the union of its members' tokens, so a terse trade-press
    headline and a long wire headline still find each other.
    """
    reps: List[Dict[str, Any]] = []
    # A phrase two headlines share, and few others in the pool do, is one story:
    # "windfall tax" in a week with one windfall-tax row. State names are excluded
    # so "Russia seizes" does not glue every seizure together.
    df: Dict[tuple, int] = {}
    for it in items:
        it["_bg"] = _bigrams(it.get("title_en") or it["title"])
        for b in it["_bg"]:
            df[b] = df.get(b, 0) + 1
    dfn: Dict[str, int] = {}
    for it in items:
        for n in _propers(it.get("title_en") or it["title"]):
            dfn[n] = dfn.get(n, 0) + 1
    rare_max = max(3, len(items) // 8)
    states = _state_stems()

    def _fold_set(values) -> set:
        return {_fold(v).lower() for v in (values or []) if v}

    _JUR_EXTRA = {"eu", "uk", "us", "un"}

    def _jurisdictions(it) -> set:
        """State names in the headline or on the record, plus EU/UK/US: a UK
        windfall tax and an EU windfall tax are two stories however alike the
        phrasing, and so are Bulgaria's and the EU's."""
        title = it.get("title_en") or it["title"]
        found = {_fold(s).lower() for s in states_in(title)}
        found |= {_fold(s).lower() for s in (it.get("states") or []) if s}
        found |= {w for w in re.findall(r"[A-Za-z]+", title) if w.lower() in _JUR_EXTRA and w.isupper()}
        return {w.lower() for w in found}

    for it in items:
        toks = _tokens(it.get("title_en") or it["title"])
        names = _propers(it.get("title_en") or it["title"])
        ents = _entities(it.get("title_en") or it["title"])
        bg = it.pop("_bg")
        home = None
        for rep in reps:
            # Two headlines each naming a company the other does not are two
            # matters, whatever else they share: Turkey revoking Papel's licence
            # is not Turkey revoking Bank Mellat's, four days earlier.
            conflict = bool(ents and rep["_ents"] and not (ents & rep["_ents"]))
            # Two different case numbers are two different matters, full stop.
            if it.get("case_ref") and rep.get("case_ref") and it["case_ref"] != rep["case_ref"]:
                continue
            # The same investor against the same State, in the same window, is one story
            # whatever the headline says.
            same_parties = ((_fold_set(it.get("claimants")) | _fold_set(it.get("respondents")))
                            & (_fold_set(rep.get("claimants")) | _fold_set(rep.get("respondents")))
                            and _fold_set(it.get("states")) & _fold_set(rep.get("states")))
            shared_phrase = {b for b in bg & rep["_bg"]
                             if df.get(b, 0) <= rare_max and b[0] not in states and b[1] not in states
                             and not (b[0] in _GENERIC and b[1] in _GENERIC)}
            # A rare name in common - a project, a company, a person - plus the same
            # State is the same matter under two headlines ("Mambilla").
            rare_name = {n for n in names & rep["_names"] if dfn.get(n, 0) <= rare_max and n not in states}
            same_state = bool(_fold_set(it.get("states")) & _fold_set(rep.get("states")))
            ja, jb = _jurisdictions(it), _jurisdictions(rep)
            if ja and jb and not (ja & jb):
                shared_phrase, rare_name = set(), set()   # different jurisdictions named: not one story
            if conflict:
                shared_phrase, rare_name = set(), set()
            inter = len(toks & rep["_toks"])
            if not inter and not same_parties:
                continue
            # Overlap is judged against the closest member, not the union of the
            # cluster: a union grows with every member and would let a chain of
            # loosely related headlines swallow anything with three words in common.
            jac = max(len(toks & m) / max(1, len(toks | m)) for m in rep["_members"])
            shared_names = len(names & rep["_names"])
            # The same State and the same kind of event, with three words in
            # common, is one story told twice: "Malaysian investor threatens
            # India over enforcement delays" and "Malaysian road developer puts
            # India on notice of treaty dispute over enforcement proceedings".
            same_kind = bool((toks & rep["_toks"]) & states) and inter >= 3 and jac >= 0.15 \
                and (it.get("event_type") or "") == (rep.get("event_type") or "") and it.get("event_type") not in (None, "", "commentary")
            # Two States named on both sides, the same stage of the same matter, no
            # other company in either headline: "US judge backs Iraq as net creditor
            # in oil dispute with Turkey" and "US court recommends confirmation of
            # award in Iraq-Türkiye pipeline arbitration" are one story.
            pair_a, pair_b = ja - _JUR_EXTRA, jb - _JUR_EXTRA
            same_pair = len(pair_a) >= 2 and pair_a == pair_b and inter >= 2 and not ents and not rep["_ents"] \
                and _stage(it) == _stage(rep) and _stage(it) is not None
            if conflict and not same_parties:
                continue
            if ja and jb and not (ja & jb) and not (same_parties or jac >= 0.5):
                continue
            if (same_parties or shared_phrase or (rare_name and (same_state or inter >= 2))
                    or jac >= 0.5 or (inter >= 3 and jac >= 0.22) or shared_names >= 2 or same_kind or same_pair):
                home = rep
                break
        if home is None:
            it["_toks"] = set(toks)
            it["_names"] = set(names)
            it["_ents"] = set(ents)
            it["_members"] = [set(toks)]
            it["_bg"] = set(bg)
            it["also"] = list(it.get("also") or [])   # a story clustered once keeps the copies it already has
            reps.append(it)
            continue
        if (home.get("lang") or "en") != "en" and (it.get("lang") or "en") == "en":
            # The English version tells the story; the foreign-language one hangs off it.
            it["_toks"] = home["_toks"] | toks
            it["_names"] = home["_names"] | names
            it["_ents"] = home["_ents"] | ents
            it["_members"] = home["_members"] + [set(toks)]
            it["_bg"] = home["_bg"] | bg
            it["also"] = home["also"] + [{"source": home.get("source"), "url": home.get("url"), "title": home.get("title")}]
            for f in ("counsel", "claimants", "respondents", "states", "sectors",
                      "arbitrators", "treaty", "amount_usd", "case_ref"):
                if not it.get(f) and home.get(f):
                    it[f] = home[f]
            for k in ("_toks", "_names", "_ents", "_members", "_bg", "also"):
                home.pop(k, None)
            reps[reps.index(home)] = it
            continue
        home["_toks"] |= toks
        home["_names"] |= names
        home["_ents"] |= ents
        home["_members"].append(set(toks))
        home["_bg"] |= bg
        home["also"].append({"source": it.get("source"), "url": it.get("url"),
                             "title": it.get("title")})
        # A wire headline outscores a trade-press write-up on recency and reach;
        # the write-up still has the better text. Keep the fullest summary.
        def _real(txt, title):
            txt = (txt or "").strip()
            if is_paywall(txt) or txt.lower().startswith((title or "").lower()[:40]):
                return ""
            return txt
        if len(_real(it.get("summary"), it.get("title"))) > len(_real(home.get("summary"), home.get("title"))):
            home["summary"] = it["summary"]
        # A duplicate from a primary record can carry evidence the lead lacks.
        for f in ("counsel", "claimants", "respondents", "states", "sectors",
                  "arbitrators", "treaty", "amount_usd", "case_ref"):
            if not home.get(f) and it.get(f):
                home[f] = it[f]
    for r in reps:
        r.pop("_toks", None)
        r.pop("_names", None)
        r.pop("_bg", None)
        r.pop("_ents", None)
        r.pop("_members", None)
        _cite_best(r)
    return reps


def _cite_best(rep: Dict[str, Any]) -> None:
    """Cite the most authoritative copy of the story: a wire or a major paper over
    the syndicated copy that happened to arrive first. The headline and link
    follow the cited copy; the summary and the evidence stay with the story."""
    from .outlets import rank
    also = rep.get("also") or []
    if not also:
        return
    # A Google News link is a detour; the outlet's own link is the citation.
    def _r(x):
        return rank(x.get("source"), x.get("url")) + (0.5 if "news.google." in (x.get("url") or "") else 0)
    best = min(also, key=_r)
    if _r(best) < _r(rep) and best.get("url"):
        old = {"source": rep.get("source"), "url": rep.get("url"), "title": rep.get("title")}
        rep["source"], rep["url"] = best.get("source"), best.get("url")
        if best.get("title") and (rep.get("lang") or "en") == "en":
            rep["title"] = best["title"]
        rep["also"] = [old] + [a for a in also if a is not best]


# A lead is a measure against investors in a place. Four days of headlines on
# the EU windfall tax are one lead, whatever each outlet called it.
_MEASURES = [("windfall tax", re.compile(r"windfall[ -](?:tax|profit|charge|levy)", re.I)),
             ("nationalisation", re.compile(r"nationali[sz]", re.I)),
             ("expropriation", re.compile(r"expropriat", re.I)),
             ("licence revoked", re.compile(r"licen[cs]e\w*.{0,40}\b(?:revok|suspend|cancel|withdr|strip)|(?:revok|suspend|cancel|withdr|strip)\w*.{0,40}licen[cs]e", re.I)),
             ("price cap", re.compile(r"price caps?|caps? (?:on )?(?:fuel|energy|electricity|gas|margin)|margin caps?", re.I)),
             ("export ban", re.compile(r"export (?:ban|curb|restriction|halt)|bans? (?:the )?exports?", re.I)),
             ("concession terminated", re.compile(r"concession\w*.{0,40}\b(?:terminat|cancel|revok|annul)|(?:terminat|cancel|revok|annul)\w*.{0,40}concession", re.I)),
             ("moratorium", re.compile(r"moratori", re.I)),
             ("mining halt", re.compile(r"mining (?:ban|halt|suspen|permit)", re.I)),
             ("asset seizure", re.compile(r"seiz\w*.{0,30}\b(?:asset|plant|refiner|mine|stake|shares)|(?:asset|plant|refiner|mine|stake|shares)\w*.{0,30}\bseiz", re.I))]
_CAPITALS = {"prague": "czechia", "warsaw": "poland", "budapest": "hungary", "bucharest": "romania", "sofia": "bulgaria",
             "athens": "greece", "ankara": "turkey", "istanbul": "turkey", "cairo": "egypt", "riyadh": "saudi arabia",
             "doha": "qatar", "tehran": "iran", "baghdad": "iraq", "kyiv": "ukraine", "moscow": "russia", "delhi": "india",
             "mumbai": "india", "beijing": "china", "abuja": "nigeria", "lagos": "nigeria", "nairobi": "kenya",
             "accra": "ghana", "kinshasa": "congo (drc)", "caracas": "venezuela", "bogota": "colombia", "lima": "peru",
             "quito": "ecuador", "santiago": "chile", "buenos aires": "argentina", "mexico city": "mexico",
             "jakarta": "indonesia", "manila": "philippines", "hanoi": "vietnam", "bangkok": "thailand",
             "islamabad": "pakistan", "dhaka": "bangladesh", "colombo": "sri lanka", "harare": "zimbabwe",
             "lusaka": "zambia", "maputo": "mozambique", "luanda": "angola", "addis ababa": "ethiopia",
             "algiers": "algeria", "tunis": "tunisia", "rabat": "morocco", "tripoli": "libya", "khartoum": "sudan",
             "astana": "kazakhstan", "tashkent": "uzbekistan", "baku": "azerbaijan", "tbilisi": "georgia",
             "yerevan": "armenia", "bishkek": "kyrgyzstan", "dushanbe": "tajikistan", "ashgabat": "turkmenistan",
             "berlin": "germany", "paris": "france", "madrid": "spain", "rome": "italy", "lisbon": "portugal",
             "dublin": "ireland", "london": "united kingdom", "washington": "united states", "ottawa": "canada",
             "brasilia": "brazil", "canberra": "australia", "tokyo": "japan", "seoul": "korea"}
_REGION = re.compile(r"\b(?:EU|E\.U\.|European Union|Europe|Brussels|Eurogroup|European Commission|eurozone)\b", re.I)


def _topics_of(items: List[Dict[str, Any]]) -> set:
    """(measure, place) pairs a set of items is about; empty when a text names neither."""
    out = set()
    for it in items:
        text = " ".join([it.get("title_en") or it.get("title") or "", (it.get("summary_en") or it.get("summary") or "")[:400]])
        measures = [name for name, rx in _MEASURES if rx.search(text)]
        if not measures:
            continue
        places = {_fold(s).lower() for s in states_in(text)}
        low = _fold(text).lower()
        places.update(state for city, state in _CAPITALS.items() if re.search(r"\b" + city + r"\b", low))
        if _REGION.search(text):
            places.add("eu")
        out.update((m, p) for m in measures for p in places)
    return out
