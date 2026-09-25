"""Ingest -> dedupe -> enrich -> score. The LLM stages are optional."""
import datetime as dt
import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

from . import db, llm, score as scoring
from .sources import REGISTRY, TIERS
from .taxonomy import EVENT_PATTERNS, INSTITUTIONS, SECTORS
from .sources.editions import states_in
from . import fetch as fetch_mod

log = logging.getLogger(__name__)
TRACKING = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$)")

# The day an issue is built for. Today unless a past day is being rebuilt, in
# which case nothing published after it may appear and only earlier days count
# as already shown.
AS_OF: Optional[dt.date] = None


def as_of() -> dt.date:
    return AS_OF or dt.date.today()


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


_PEOPLE_CONTEXT = re.compile(r"partner|counsel\b|arbitrat|disputes|law firm|chambers|barrister|boutique|associate|"
                             r"\bkc\b|\bqc\b|practice|lawyer|attorney|solicitor|advocate|tribunal|\bicc\b|lcia|icsid|"
                             r"siac|hkiac|\bscc\b|institution|secretary|litigat")


def rule_classify(item: Dict[str, Any]) -> Dict[str, Any]:
    """Cheap first pass so the system is useful with no API key at all."""
    text = " {} {} ".format(item.get("title") or "", item.get("summary") or "").lower()
    out: Dict[str, Any] = {}

    treaty_context = re.search(r"icsid|investment treaty|bilateral investment|\bbit\b|investor-state|"
                               r"energy charter|expropriat|nationalis|nationaliz|uncitral", text) is not None
    if not item.get("event_type"):
        for event_type, phrases in EVENT_PATTERNS:
            if event_type == "commercial_dispute" and treaty_context:
                continue                              # treaty patterns decide those
            hit = next((p for p in phrases if p in text), None)
            if hit and event_type in ("lateral_move", "appointment", "counsel_instructed", "counsel_change") and not _PEOPLE_CONTEXT.search(text):
                continue
            if hit and event_type == "award_issued" and not re.search(
                    r"arbitra|tribunal|icsid|\bicc\b|lcia|siac|hkiac|uncitral|\bpca\b|annul|enforce", text):
                continue                              # a road contract "award" is procurement, not an award
            if hit and event_type == "state_measure" and not (
                    states_in(text) and re.search(r"compan|investor|group|corp|plc|inc\b|ltd|\bag\b|\bsa\b|subsidiar|"
                                                   r"operator|miner|developer|contractor|bank|firm|venture|plant|project|"
                                                   r"concession|licen[cs]e|mine\b|field|refiner|pipeline|terminal", text)):
                continue                              # a measure with no State or no business named is politics
            if hit and event_type == "notice_of_intent" and not re.search(
                    r"arbitra|treaty|icsid|dispute|claim|investor|\bbit\b|uncitral|cooling", text):
                continue                              # a NEPA or planning notice, not a treaty notice
            if hit:
                out["event_type"] = event_type
                out["flag_reason"] = "matched \u2018{}\u2019 in the text".format(hit.strip())
                break
        else:
            out["event_type"] = "commentary"
    if not item.get("states"):
        found = states_in((item.get("title") or "") + " " + (item.get("summary") or ""))
        if found:
            out["states"] = found[:3]

    if not item.get("institution"):
        for name, phrases in INSTITUTIONS.items():
            if any(p in text for p in phrases):
                out["institution"] = name
                break

    if not item.get("sectors"):
        found = [name for name, words in SECTORS.items() if any(w in text for w in words)]
        if found:
            out["sectors"] = found[:3]
    return out


def item_from_raw(name: str, raw: Dict[str, Any], now: str) -> Optional[Dict[str, Any]]:
    """An adapter's raw item as a classified row, whether it arrived live or relayed."""
    if not (raw.get("title") and raw.get("url")):
        return None
    item = {
        "fingerprint": fingerprint(raw),
        "url": raw["url"],
        "source": raw.get("source") or name,
        "source_tier": TIERS.get(name, 2),
        "title": raw["title"][:500],
        "summary": "" if is_paywall(raw.get("summary") or "") else (raw.get("summary") or "")[:4000],
        "body": (raw.get("body") or "")[:20000] or None,
        "published_at": raw.get("published_at"),
        "fetched_at": now,
        "event_type": raw.get("event_type"),
        "institution": raw.get("institution"),
        "treaty": raw.get("treaty"),
        "case_ref": raw.get("case_ref"),
        "sectors": raw.get("sectors") or [],
        "claimants": raw.get("claimants") or [],
        "respondents": raw.get("respondents") or [],
        "states": raw.get("states") or [],
        "counsel": raw.get("counsel") or [],
        "arbitrators": raw.get("arbitrators") or [],
        "amount_usd": raw.get("amount_usd"),
        "flag_reason": raw.get("flag_reason"),
        "lang": raw.get("lang") or "en",
        "country": raw.get("country") or None,
    }
    item.update(rule_classify(item))
    return item


def ingest(conn, settings, days: int, only: List[str] = None) -> Dict[str, int]:
    """Run every source adapter and store new items."""
    stats: Dict[str, int] = {}
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    for name, fn in REGISTRY.items():
        if only and name not in only:
            continue
        if settings.sources and settings.sources.get(name) is False:
            continue
        found = new = 0
        error = None
        snap = dict(fetch_mod.FAILURES)
        try:
            for raw in fn(days=days):
                found += 1
                item = item_from_raw(name, raw, now)
                if item and db.upsert_item(conn, item):
                    new += 1
        except Exception as exc:                      # noqa: BLE001 - boundary
            error = str(exc)[:300]
            log.warning("source %s failed: %s", name, exc)

        fails = {k: v - snap.get(k, 0) for k, v in fetch_mod.FAILURES.items() if v - snap.get(k, 0) > 0}
        if fails:
            top = ", ".join("{} x{}".format(k, v) for k, v in sorted(fails.items(), key=lambda kv: -kv[1])[:4])
            error = ((error + " | ") if error else "") + "fetch failures: " + top
        conn.execute("INSERT INTO fetch_log (source, ran_at, found, new_items, error) "
                     "VALUES (?,?,?,?,?)", (name, now, found, new, error))
        conn.commit()
        stats[name] = new
    return stats


def enrich(conn, settings) -> Dict[str, int]:
    """LLM triage then extraction. Skipped entirely when no API key is set."""
    counts = {"triaged": 0, "dropped": 0, "extracted": 0}
    if not settings.use_llm:
        conn.execute("UPDATE items SET llm_stage='skipped' WHERE llm_stage='none'")
        conn.commit()
        return counts

    batch = db.pending(conn, "none", limit=400)
    if batch:
        verdicts = llm.triage(batch, settings.triage_model)
        for item in batch:
            v = verdicts.get(item["id"])
            if v is None:
                db.update_item(conn, item["id"], llm_stage="triaged")
                continue
            counts["triaged"] += 1
            if not v.relevant:
                counts["dropped"] += 1
                db.update_item(conn, item["id"], relevant=0, llm_stage="triaged",
                               event_type=v.event_type)
            else:
                db.update_item(conn, item["id"], llm_stage="triaged",
                               event_type=v.event_type or item.get("event_type"))
        conn.commit()

    # Extract only where it can change the ranking: drop the obvious filler.
    rows = [r for r in db.pending(conn, "triaged", limit=120)
            if (r.get("event_type") or "commentary") != "commentary"]
    for item in rows:
        ex = llm.extract(item, settings.extract_model)
        if ex is None:
            db.update_item(conn, item["id"], llm_stage="extracted")
            continue
        counts["extracted"] += 1
        db.update_item(
            conn, item["id"], llm_stage="extracted",
            event_type=ex.event_type or item.get("event_type"),
            claimants=ex.claimants or item.get("claimants"),
            respondents=ex.respondents or item.get("respondents"),
            states=ex.states, institution=ex.institution or item.get("institution"),
            treaty=ex.treaty or item.get("treaty"),
            case_ref=ex.case_ref or item.get("case_ref"),
            sectors=ex.sectors or item.get("sectors"),
            amount_usd=ex.amount_usd,
            counsel=ex.counsel or item.get("counsel"),
            arbitrators=ex.arbitrators or item.get("arbitrators"),
            why_it_matters=ex.why_it_matters,
            title_en=ex.headline_en or None, summary_en=ex.summary_en or None)
    conn.commit()
    return counts


def rescore(conn, settings) -> int:
    rows = conn.execute("SELECT * FROM items WHERE relevant=1").fetchall()
    n = 0
    for row in rows:
        item = db.row_to_dict(row)
        value, detail = scoring.score_item(item, settings)
        db.update_item(conn, item["id"], score=value,
                       score_detail=json.dumps(detail, ensure_ascii=False))
        n += 1
    conn.commit()
    return n


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


import unicodedata

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
            it["also"] = []
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


_PEOPLE = re.compile(r"\b(hires?|hired|hiring|joins?|joined|leaves?|left|departs?|exits?|appoint(?:s|ed)?\s+(?:as|to|of)|named\s+(?:as|to)|"
                     r"names?\s+\w+\s+(?:as|to|head|chair|partner)|promot\w*|elected|re-?elected|becomes|takes over|steps? down|"
                     r"new\s+(?:partner|head|chair|president|secretary|director|co-chair)|partner hires|lateral|moves? to|returns? to|"
                     r"launches\s+\w*\s*practice|adds?\s+\w+\s+partner|bolsters|strengthens)\b", re.I)


def record_extras(conn, settings, featured: List[Dict[str, Any]], days: int = 14) -> Dict[str, List[Dict[str, Any]]]:
    """Primary-record lists for the issue: docket movements, disclosures, court filings.
    Excludes anything already featured. Rule-based; the records are the story."""
    cutoff = (as_of() - dt.timedelta(days=days)).isoformat()
    upto = as_of().isoformat() + "~"
    skip = {it["id"] for it in featured} | {a.get("url") for it in featured for a in (it.get("also") or [])}
    skip_titles = ({fingerprint(it) for it in featured} | {fingerprint(a) for it in featured for a in (it.get("also") or [])}
                   | {title_key(it) for it in featured} | {title_key(a) for it in featured for a in (it.get("also") or [])})
    # ...and nothing an earlier day already carried, in any list.
    from . import site
    shown_urls, shown_fps = site.shown_before(as_of().isoformat())
    skip |= shown_urls
    skip_titles |= shown_fps

    muted = [m.lower() for m in (getattr(settings, "mute", None) or [])]

    def take(sql, params, limit, key=None):
        out, seen = [], set()
        for r in conn.execute(sql, params):
            it = db.row_to_dict(r)
            if it["id"] in skip or it["url"] in skip or fingerprint(it) in skip_titles or title_key(it) in skip_titles:
                continue
            text = ((it.get("title") or "") + " " + (it.get("summary") or "")).lower()
            if any(m in text for m in muted):
                continue                              # muted terms keep an item out of every list
            k = key(it) if key else it["url"]
            if k in seen:
                continue
            seen.add(k)
            out.append(it)
            if len(out) >= limit:
                break
        return out

    docket = take(
        "SELECT * FROM items WHERE source='ICSID docket' AND relevant=1 AND published_at>=? AND published_at<=? "
        "AND (event_type IN ('new_case_filed','award_issued') "
        "     OR (event_type='annulment_setaside' AND (title LIKE '%application for annulment%' "
        "         OR title LIKE '%decision on annulment%' OR title LIKE '%issues its decision%' "
        "         OR title LIKE '%Committee is constituted%')) "
        "     OR title LIKE '%resignation%' OR title LIKE '%disqualif%') "
        "ORDER BY published_at DESC", (cutoff, upto), 8)
    disclosures = take(
        "SELECT * FROM items WHERE source='SEC EDGAR' AND relevant=1 AND published_at>=? AND published_at<=? "
        "AND url NOT LIKE '%ex10%' AND url NOT LIKE '%ex2-%' AND url NOT LIKE '%ex4%' AND url NOT LIKE '%ex3%' "
        "ORDER BY published_at DESC", (cutoff, upto), 6,
        key=lambda it: (it.get("title") or "").split(" discloses")[0])
    court_rows = take(
        "SELECT * FROM items WHERE relevant=1 AND COALESCE(score,0)>0 AND published_at>=? AND published_at<=? "
        "AND (source LIKE 'Court:%' OR (source LIKE 'US federal docket%' "
        "     AND (source LIKE '%sovereign%' OR title LIKE 'In re%' OR title LIKE 'In Re%' "
        "          OR title LIKE 'IN RE%' OR summary LIKE '%foreign%'))) "
        "ORDER BY published_at DESC", (cutoff, upto), 30)
    # One list, many jurisdictions: at most two rows per country, so that a busy
    # registry cannot crowd out the rest.
    per: Dict[str, int] = {}
    courts: List[Dict[str, Any]] = []
    for allowance in (1, 2):                      # every jurisdiction once, then seconds
        for it in court_rows:
            c = it.get("country") or "United States"
            if it in courts or per.get(c, 0) >= allowance:
                continue
            per[c] = per.get(c, 0) + 1
            courts.append(it)
            if len(courts) >= 8:
                break
        if len(courts) >= 8:
            break
    courts.sort(key=lambda it: it.get("published_at") or "", reverse=True)
    # People: firm moves and institutional appointments from the press, and the
    # tribunal appointments the ICSID docket records - who appointed whom.
    people_rows = take(
        "SELECT * FROM items WHERE relevant=1 AND COALESCE(score,0)>0 AND published_at>=? AND published_at<=? AND ("
        "  event_type IN ('lateral_move','appointment') "
        "  OR (source='ICSID docket' AND event_type='tribunal_constituted' "
        "      AND (title LIKE '%appoint%' OR title LIKE '%constituted%' OR title LIKE '%President%'))) "
        "ORDER BY score DESC, published_at DESC", (cutoff, upto), 40)
    # A headline in the People list must be about a person's move or an
    # appointment; "High Court's location doesn't become the seat because the
    # HC appointed the arbitrator" is a judgment, whatever the classifier said.
    people_rows = [it for it in people_rows if it.get("source") == "ICSID docket"
                   or _PEOPLE.search(it.get("title_en") or it.get("title") or "")]
    people = drop_repeats(people_rows, site.people_before(as_of().isoformat()))
    moves = sorted((it for it in people if it.get("source") != "ICSID docket"),
                   key=lambda it: it.get("published_at") or "", reverse=True)
    seats = sorted((it for it in people if it.get("source") == "ICSID docket"),
                   key=lambda it: it.get("published_at") or "", reverse=True)
    return {"docket": docket, "disclosures": disclosures, "courts": courts, "people": moves[:6] + seats[:6]}


def drop_repeats(candidates: List[Dict[str, Any]], anchors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Cluster candidates against earlier days' items; keep only what is new."""
    if not anchors:
        return cluster(candidates)
    for a in anchors:
        a["_anchor"] = True
    anchor_urls = {a.get("url") for a in anchors} - {None, ""}
    out = []
    for rep in cluster(anchors + candidates):
        if rep.get("_anchor") or rep.get("url") in anchor_urls:
            continue
        if any((a.get("url") in anchor_urls) for a in rep.get("also") or []):
            continue
        out.append(rep)
    return out


def reclassify(conn, settings, days: int = 21) -> int:
    """Re-run the rule classifier over rule-classified items in the window. Used
    after a taxonomy change; items a model has judged are left alone."""
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    n = 0
    from .sources.gnews import measure_label
    for r in conn.execute("SELECT * FROM items WHERE COALESCE(llm_stage,'none')='none' "
                          "AND COALESCE(published_at, substr(fetched_at,1,10))>=? "
                          "AND source NOT LIKE 'Court:%' AND source<>'ICSID docket'", (cutoff,)).fetchall():
        it = db.row_to_dict(r)
        before = it.get("event_type")
        if (it.get("flag_reason") or "").startswith("State-measure sweep"):
            ev, why = measure_label(it.get("title") or "", it.get("claimants") or [])
            if ev != before:
                db.update_item(conn, it["id"], event_type=ev, flag_reason=why)
                n += 1
            continue
        probe = dict(it, event_type=None)
        out = rule_classify(probe)
        # Source adapters that set their own type (sweeps, dockets) keep it unless the
        # rules now see a people story, which the adapters never label.
        new = out.get("event_type") or "commentary"
        if new == before or (new not in ("lateral_move", "appointment") and (it.get("flag_reason") or "").startswith(
                ("commercial-arbitration sweep", "State-measure sweep", "US federal docket", "SEC", "ICSID"))):
            continue
        db.update_item(conn, it["id"], event_type=new, flag_reason=out.get("flag_reason") or it.get("flag_reason"))
        n += 1
    conn.commit()
    rescore(conn, settings)
    return n


_ON_TOPIC = re.compile(r"arbitra|\baward\b|tribunal|ICSID|\bICC\b|LCIA|SIAC|HKIAC|\bPCA\b|UNCITRAL|annul|set aside|"
                       r"enforce|treaty claim|investor-state|\bISDS\b|investment treaty|expropriat|nationali[sz]|"
                       r"notice of dispute|notice of intent|emergency arbitrator|\bseat\b|"
                       r"seiz|confiscat|revok|licen[cs]e|concession|asset freez|frozen assets|windfall[- ]tax|"
                       r"tak(?:es|en|ing) control|under (?:temporary |state |external )?(?:management|administration)|"
                       r"tax (?:demand|reassessment|bill|claim)|back taxes|royalt|export ban|price cap|forced (?:sale|to sell)|"
                       r"cancel|terminat|renegotiat|nationali|sanction|fine[ds]?\b|penalt|moratorium|blocked the", re.I)


# The two titles that are read cover to cover: every GAR and IAReporter headline
# of the day is carried. Law360's arbitration feed mixes in US domestic and
# opinion pieces and stays on the scored path.
_FULL_READ = re.compile(r"globalarbitrationreview|global arbitration review|(?<![\w.])gar(?![\w])|iareporter", re.I)


def _read_in_full(it: Dict[str, Any]) -> bool:
    text = " ".join([(it.get("source") or "").replace("Google News / ", ""), it.get("url") or ""]
                    + [(a.get("source") or "") + " " + (a.get("url") or "") for a in (it.get("also") or [])])
    return bool(_FULL_READ.search(text))


def select(conn, settings, extra_days: int = 0) -> List[Dict[str, Any]]:
    cutoff = (as_of() - dt.timedelta(days=settings.lookback_days + extra_days)).isoformat()
    upto = as_of().isoformat() + "~"
    # Pinned items always make the cut; excluded ones never do. Everything else
    # competes on score within the window.
    rows = conn.execute(
        "SELECT * FROM items WHERE relevant=1 AND issue_id IS NULL "
        "AND COALESCE(excluded,0)=0 "
        "AND source NOT LIKE 'Court:%' "          # judgments belong to the court list, not the stories
        "AND COALESCE(event_type,'') NOT IN ('lateral_move','appointment') "
        "AND (COALESCE(pinned,0)=1 OR (score >= ? "
        "     AND COALESCE(published_at, substr(fetched_at,1,10)) >= ? "
        "     AND COALESCE(published_at, substr(fetched_at,1,10)) <= ?)) "
        "ORDER BY COALESCE(pinned,0) DESC, score DESC LIMIT ?",
        (settings.min_score, cutoff, upto, settings.max_items_per_issue * 12)).fetchall()
    # What earlier days carried is not a candidate, and must not crowd the pool either.
    from . import site as _site
    shown_urls, shown_keys = _site.shown_before(as_of().isoformat())
    rows = [r for r in rows if r["url"] not in shown_urls and title_key(dict(r)) not in shown_keys]
    # A story carried on an earlier day is not news on a later one. Earlier
    # days' stories go into the clustering first, so a new copy of an old story
    # merges into them and drops out.
    from . import site
    today = as_of().isoformat()
    since = (as_of() - dt.timedelta(days=21)).isoformat()
    anchors: List[Dict[str, Any]] = []
    for r in conn.execute("SELECT i.* FROM items i JOIN issues s ON s.id=i.issue_id "
                          "WHERE substr(s.created_at,1,10) < ? AND COALESCE(i.published_at,'') >= ?", (today, since)):
        anchors.append(db.row_to_dict(r))
    anchors += site.anchors_before(today)
    for a in anchors:
        a["_anchor"] = True
    anchor_urls = {a.get("url") for a in anchors} - {None, ""}
    anchor_topics = _topics_of(anchors)
    reps = cluster(anchors + [db.row_to_dict(r) for r in rows])
    from .outlets import is_trade_press
    stories = []
    floor = float(getattr(settings, "min_story_score", 0) or 0)
    for rep in reps:
        if rep.get("_anchor") or rep.get("url") in anchor_urls:
            continue
        if any((a.get("url") in anchor_urls) for a in rep.get("also") or []):
            continue
        if rep.get("event_type") in ("state_measure", "distress_event") and not rep.get("pinned") \
                and _topics_of([rep]) & anchor_topics:
            continue                              # the same measure in the same place as an earlier day's story
        if (rep.get("score") or 0) < floor and not rep.get("pinned"):
            continue                              # below the floor: leave it out rather than pad the day
        head = rep.get("title_en") or rep.get("title") or ""
        body = " ".join([head, rep.get("summary_en") or rep.get("summary") or ""])
        if not rep.get("pinned") and _NOT_NEWS.search(head) and not (rep.get("source") or "").startswith(("ICSID docket", "Court:", "US federal docket")):
            continue                              # an awards night, a report, a survey: not a development
        if not rep.get("pinned") and rep.get("event_type") == "commercial_dispute" \
                and not is_trade_press(rep.get("source") or "", rep.get("url") or "") and not _DISPUTE_WORD.search(body):
            continue                              # "terminates contracts of two soldiers" is not a commercial dispute
        if not rep.get("pinned") and rep.get("event_type") in ("state_measure", "distress_event") \
                and not is_trade_press(rep.get("source") or "", rep.get("url") or "") \
                and not (rep.get("claimants") or rep.get("amount_usd") or _BUSINESS.search(body)):
            continue                              # a measure that lands on no named business is politics, not a story
        # A firm's newsletter piece or a trade story with no arbitration in it is
        # not a story here, however well it scores on the watchlist.
        # The same test for a sweep item of any kind: "airlines cancel flights as
        # sanctions bite" names no measure against an investor and is not a story.
        if not rep.get("pinned") and (rep.get("source_tier") or 2) != 1 \
                and not is_trade_press(rep.get("source") or "", rep.get("url") or "") \
                and not _ON_TOPIC.search(" ".join([rep.get("title_en") or rep.get("title") or "",
                                                   rep.get("summary_en") or rep.get("summary") or ""])):
            continue
        stories.append(rep)
    # The trade press is read in full: every GAR, IAReporter or Law360 headline
    # of the day is carried, whatever its score, so the reader never has to
    # wonder what was left out. It joins after the scored stories.
    day_lo = (as_of() - dt.timedelta(days=1)).isoformat()
    have = {id(s) for s in stories}
    for rep in reps:
        if id(rep) in have or rep.get("_anchor") or rep.get("url") in anchor_urls:
            continue
        if any((a.get("url") in anchor_urls) for a in rep.get("also") or []):
            continue
        if not _read_in_full(rep):
            continue
        if str(rep.get("published_at") or "")[:10] < day_lo:
            continue
        head = rep.get("title_en") or rep.get("title") or ""
        if _NOT_NEWS.search(head):
            continue
        stories.append(rep)
        have.add(id(rep))
    if len(stories) < 3:
        # A quiet day: items just under the floor still go in 'In brief' when the
        # headline itself is about an arbitration, never on the sweep's say-so alone.
        on_topic = _ON_TOPIC
        seen = {id(s) for s in stories}
        for rep in reps:
            if id(rep) in seen or rep.get("_anchor") or rep.get("url") in anchor_urls:
                continue
            if (rep.get("score") or 0) >= floor - 12 and on_topic.search(rep.get("title_en") or rep["title"]):
                stories.append(rep)
            if len(stories) >= 6:
                break
    # The cap falls on the sweep, never on the trade press of the day.
    trade = [s for s in stories if _read_in_full(s) and str(s.get("published_at") or "")[:10] >= day_lo]
    others = [s for s in stories if s not in trade]
    room = max(0, settings.max_items_per_issue - len(trade))
    keep = trade + others[:room]
    return sorted(keep, key=lambda s: (s.get("score") or 0), reverse=True)

# The events a rainmaker watches for before any tribunal exists. A lead is a
# sweep or feed item of one of these kinds; it never competes with the trade
# press for the story slots and has its own floor.
LEAD_EVENTS = ("state_measure", "distress_event", "notice_of_intent", "counsel_tender", "commercial_dispute",
               "interim_relief", "funding", "counsel_change", "settlement", "s1782_application")


_BUSINESS = re.compile(r"\b(?:Inc|Ltd|Limited|Plc|LLC|LLP|GmbH|AG|SA|SpA|NV|BV|Pty|Corp|Corporation|Holdings|Group|"
                       r"Co\b|Company|Industries|Energy|Mining|Resources|Petroleum|Oil|Gas|Power|Bank|Telecom|Airlines|"
                       r"Airways|Cement|Steel|Motors|Pharma|Capital|Partners|Ventures)\b(?!\s+of\s+Ministers)")


ENFORCEMENT_EVENTS = ("enforcement_action", "s1782_application", "annulment_setaside")


def select_leads(conn, settings, taken: List[Dict[str, Any]], limit: int = 5, floor: float = 45.0) -> List[Dict[str, Any]]:
    """The best pre-dispute hints from outside the trade press and the records,
    not already carried as a story today or on an earlier day."""
    return _track(conn, settings, taken, LEAD_EVENTS, limit, floor, trade_ok=False, records_ok=False, business_gate=True)


def select_enforcement(conn, settings, taken: List[Dict[str, Any]], limit: int = 6, floor: float = 40.0) -> List[Dict[str, Any]]:
    """The award after the award: enforcement, execution against assets,
    immunity rulings, set-aside and s.1782 applications, from the press, the
    court feeds and the US dockets alike. Each is a mandate somewhere: the
    creditor needs counsel where the assets are, the debtor where the fight is."""
    return _track(conn, settings, taken, ENFORCEMENT_EVENTS, limit, floor, trade_ok=True, records_ok=True, business_gate=False)


_DISPUTE_WORD = re.compile(r"arbitra|\bICC\b|\bLCIA\b|\bSIAC\b|\bHKIAC\b|\bSCC\b|\bICSID\b|\baward\b|tribunal|\bclaim(s|ed)?\b|"
                           r"\bdispute|lawsuit|litigation|\bsues?\b|\bsued\b|damages|breach of contract|notice of|"
                           r"arbitraje|laudo|litigio|demanda|arbitragem|sentença arbitral|arbitrage|sentence arbitrale|litige|"
                           r"арбитраж|иск|спор|арбітраж|позов|спір|tahkim|dava|uyuşmazlık", re.I)
_ARBITRAL = re.compile(r"arbitra|arbitral|\baward\b|ICSID|exequatur|new york convention|seat of|\bLCIA\b|\bICC\b|\bSIAC\b|UNCITRAL|"
                       r"laudo|sentença arbitral|sentence arbitrale|Schiedsspruch|lodo|арбитраж|арбітраж|tahkim|hakem", re.I)
_NOT_NEWS = re.compile(r"\b(report|survey|study|guide|webinar|conference|podcast|roundtable|symposium|summit|masterclass|"
                       r"awards? \d{4}|awards (night|ceremony|shortlist)|shortlist|nominations?|rankings?|directory|"
                       r"publishes|launches its|annual review|year in review|in numbers|statistics|celebrates|anniversary)\b", re.I)


def _foreign_docket(d: Dict[str, Any]) -> bool:
    """A US federal docket row with a foreign or sovereign element: an FSIA or
    execution petition, a s.1782 application ("In re"), or a foreign party."""
    src = (d.get("source") or "").lower()
    title = d.get("title") or ""
    text = (title + " " + (d.get("summary") or "")).lower()
    return ("sovereign" in src or "execution" in src or title.lower().startswith("in re")
            or bool(re.search(r"foreign|republic of|kingdom of|federation|\bS\.?A\.?\b|\bLtd\b|\bPLC\b|\bGmbH\b|\bB\.?V\.?\b|\bAG\b|"
                              r"international|new york convention|1782", text)) or bool(states_in(title)))


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
        if _REGION.search(text):
            places.add("eu")
        out.update((m, p) for m in measures for p in places)
    return out


def _track(conn, settings, taken, events, limit, floor, trade_ok, records_ok, business_gate) -> List[Dict[str, Any]]:
    from . import site as _site
    from .outlets import is_trade_press
    cutoff = (as_of() - dt.timedelta(days=settings.lookback_days)).isoformat()
    upto = as_of().isoformat() + "~"
    marks = ",".join("?" * len(events))
    sources = "" if records_ok else "AND source NOT LIKE 'Court:%' AND source NOT IN ('ICSID docket','SEC EDGAR','PCA case list') "
    rows = conn.execute(
        "SELECT * FROM items WHERE relevant=1 AND issue_id IS NULL AND COALESCE(excluded,0)=0 "
        + sources +
        "AND event_type IN ({}) AND score >= ? "
        "AND COALESCE(published_at, substr(fetched_at,1,10)) >= ? "
        "AND COALESCE(published_at, substr(fetched_at,1,10)) <= ? "
        "ORDER BY score DESC LIMIT 120".format(marks), (*events, floor, cutoff, upto)).fetchall()
    shown_urls, shown_keys = _site.shown_before(as_of().isoformat())
    taken_urls = {t.get("url") for t in taken} | {a.get("url") for t in taken for a in (t.get("also") or [])}
    taken_keys = {title_key(t) for t in taken} | {fingerprint(t) for t in taken}
    cands = []
    for r in rows:
        d = db.row_to_dict(r)
        if d["url"] in shown_urls or d["url"] in taken_urls:
            continue
        if title_key(d) in shown_keys or title_key(d) in taken_keys or fingerprint(d) in taken_keys:
            continue
        if not trade_ok and is_trade_press(d.get("source") or "", d.get("url") or ""):
            continue                                  # the trade press is a story, not a hint
        if (d.get("source") or "").startswith("US federal docket") and not _foreign_docket(d):
            continue                                  # a domestic consumer or FINRA petition is not this newsletter's work
        text = " ".join([d.get("title_en") or d.get("title") or "", d.get("summary_en") or d.get("summary") or ""])
        if not _ON_TOPIC.search(text) and not (d.get("source") or "").startswith(("Court:", "US federal docket")):
            continue
        if business_gate and d.get("event_type") in ("state_measure", "distress_event") and not (
                d.get("claimants") or d.get("amount_usd") or _BUSINESS.search(text)):
            continue                                  # a measure that lands on no named business is politics
        if business_gate and d.get("event_type") == "commercial_dispute" and not _DISPUTE_WORD.search(text):
            continue                                  # "terminates contracts of two soldiers" is not a commercial dispute
        if _NOT_NEWS.search(d.get("title_en") or d.get("title") or ""):
            continue                                  # a report, survey or event notice is not a lead
        if events is ENFORCEMENT_EVENTS and not (d.get("source") or "").startswith(("Court:", "US federal docket", "ICSID docket", "PCA")) \
                and not _ARBITRAL.search(text):
            continue                                  # an "annulment" with no award in sight is another kind of law
        cands.append(d)
    anchors = _site.anchors_before(as_of().isoformat())
    for a in anchors:
        a["_anchor"] = True
    anchor_urls = {a.get("url") for a in anchors} - {None, ""}
    seen_topics = _topics_of(anchors + taken)
    out = []
    for rep in cluster(anchors + taken + cands):
        if rep.get("_anchor") or rep.get("url") in anchor_urls or rep.get("url") in taken_urls:
            continue
        if any(a.get("url") in anchor_urls or a.get("url") in taken_urls for a in rep.get("also") or []):
            continue
        if _topics_of([rep]) & seen_topics:
            continue                                  # the same measure in the same place: a lead already carried
        out.append(rep)
        seen_topics |= _topics_of([rep])
        if len(out) >= limit:
            break
    return out
