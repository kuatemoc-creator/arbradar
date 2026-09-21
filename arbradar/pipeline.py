"""Ingest -> dedupe -> enrich -> score. The LLM stages are optional."""
import datetime as dt
import hashlib
import json
import logging
import re
from typing import Any, Dict, List
from urllib.parse import urlsplit, urlunsplit

from . import db, llm, score as scoring
from .sources import REGISTRY, TIERS
from .taxonomy import EVENT_PATTERNS, INSTITUTIONS, SECTORS
from .sources.editions import states_in
from . import fetch as fetch_mod

log = logging.getLogger(__name__)
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
            if hit and event_type in ("lateral_move", "appointment") and not _PEOPLE_CONTEXT.search(text):
                continue
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
                if not (raw.get("title") and raw.get("url")):
                    continue
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
                if db.upsert_item(conn, item):
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
           "this content is for subscribers", "subscribers only", "sign in to continue")


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
        """State names in the headline, plus EU/UK/US: a UK windfall tax and an EU
        windfall tax are two stories however alike the phrasing."""
        title = it.get("title_en") or it["title"]
        found = {_fold(s).lower() for s in states_in(title)}
        found |= {w for w in re.findall(r"[A-Za-z]+", title) if w.lower() in _JUR_EXTRA and w.isupper()}
        return {w.lower() for w in found}

    for it in items:
        toks = _tokens(it.get("title_en") or it["title"])
        names = _propers(it.get("title_en") or it["title"])
        bg = it.pop("_bg")
        home = None
        for rep in reps:
            # Two different case numbers are two different matters, full stop.
            if it.get("case_ref") and rep.get("case_ref") and it["case_ref"] != rep["case_ref"]:
                continue
            # The same investor against the same State, in the same window, is one story
            # whatever the headline says.
            same_parties = ((_fold_set(it.get("claimants")) | _fold_set(it.get("respondents")))
                            & (_fold_set(rep.get("claimants")) | _fold_set(rep.get("respondents")))
                            and _fold_set(it.get("states")) & _fold_set(rep.get("states")))
            shared_phrase = {b for b in bg & rep["_bg"]
                             if df.get(b, 0) <= rare_max and b[0] not in states and b[1] not in states}
            # A rare name in common - a project, a company, a person - plus the same
            # State is the same matter under two headlines ("Mambilla").
            rare_name = {n for n in names & rep["_names"] if dfn.get(n, 0) <= rare_max and n not in states}
            same_state = bool(_fold_set(it.get("states")) & _fold_set(rep.get("states")))
            ja, jb = _jurisdictions(it), _jurisdictions(rep)
            if ja and jb and not (ja & jb):
                shared_phrase, rare_name = set(), set()   # different jurisdictions named: not one story
            inter = len(toks & rep["_toks"])
            if not inter and not same_parties:
                continue
            jac = inter / max(1, len(toks | rep["_toks"]))
            shared_names = len(names & rep["_names"])
            if (same_parties or shared_phrase or (rare_name and (same_state or inter >= 2))
                    or jac >= 0.5 or (inter >= 3 and jac >= 0.22) or shared_names >= 2):
                home = rep
                break
        if home is None:
            it["_toks"] = set(toks)
            it["_names"] = set(names)
            it["_bg"] = set(bg)
            it["also"] = []
            reps.append(it)
            continue
        if (home.get("lang") or "en") != "en" and (it.get("lang") or "en") == "en":
            # The English version tells the story; the foreign-language one hangs off it.
            it["_toks"] = home["_toks"] | toks
            it["_names"] = home["_names"] | names
            it["_bg"] = home["_bg"] | bg
            it["also"] = home["also"] + [{"source": home.get("source"), "url": home.get("url"), "title": home.get("title")}]
            for f in ("counsel", "claimants", "respondents", "states", "sectors",
                      "arbitrators", "treaty", "amount_usd", "case_ref"):
                if not it.get(f) and home.get(f):
                    it[f] = home[f]
            for k in ("_toks", "_names", "_bg", "also"):
                home.pop(k, None)
            reps[reps.index(home)] = it
            continue
        home["_toks"] |= toks
        home["_names"] |= names
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
    best = min(also, key=lambda a: rank(a.get("source"), a.get("url")))
    if rank(best.get("source"), best.get("url")) < rank(rep.get("source"), rep.get("url")) and best.get("url"):
        old = {"source": rep.get("source"), "url": rep.get("url"), "title": rep.get("title")}
        rep["source"], rep["url"] = best.get("source"), best.get("url")
        if best.get("title") and (rep.get("lang") or "en") == "en":
            rep["title"] = best["title"]
        rep["also"] = [old] + [a for a in also if a is not best]


def record_extras(conn, settings, featured: List[Dict[str, Any]], days: int = 14) -> Dict[str, List[Dict[str, Any]]]:
    """Primary-record lists for the issue: docket movements, disclosures, court filings.
    Excludes anything already featured. Rule-based; the records are the story."""
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    skip = {it["id"] for it in featured} | {a.get("url") for it in featured for a in (it.get("also") or [])}
    skip_titles = ({fingerprint(it) for it in featured} | {fingerprint(a) for it in featured for a in (it.get("also") or [])}
                   | {title_key(it) for it in featured} | {title_key(a) for it in featured for a in (it.get("also") or [])})
    # ...and nothing an earlier day already carried, in any list.
    from . import site
    shown_urls, shown_fps = site.shown_before(dt.date.today().isoformat())
    skip |= shown_urls
    skip_titles |= shown_fps

    def take(sql, params, limit, key=None):
        out, seen = [], set()
        for r in conn.execute(sql, params):
            it = db.row_to_dict(r)
            if it["id"] in skip or it["url"] in skip or fingerprint(it) in skip_titles or title_key(it) in skip_titles:
                continue
            k = key(it) if key else it["url"]
            if k in seen:
                continue
            seen.add(k)
            out.append(it)
            if len(out) >= limit:
                break
        return out

    docket = take(
        "SELECT * FROM items WHERE source='ICSID docket' AND relevant=1 AND published_at>=? "
        "AND (event_type IN ('new_case_filed','award_issued') "
        "     OR (event_type='annulment_setaside' AND (title LIKE '%application for annulment%' "
        "         OR title LIKE '%decision on annulment%' OR title LIKE '%issues its decision%' "
        "         OR title LIKE '%Committee is constituted%')) "
        "     OR title LIKE '%resignation%' OR title LIKE '%disqualif%') "
        "ORDER BY published_at DESC", (cutoff,), 8)
    disclosures = take(
        "SELECT * FROM items WHERE source='SEC EDGAR' AND relevant=1 AND published_at>=? "
        "AND url NOT LIKE '%ex10%' AND url NOT LIKE '%ex2-%' AND url NOT LIKE '%ex4%' AND url NOT LIKE '%ex3%' "
        "ORDER BY published_at DESC", (cutoff,), 6,
        key=lambda it: (it.get("title") or "").split(" discloses")[0])
    court_rows = take(
        "SELECT * FROM items WHERE relevant=1 AND published_at>=? "
        "AND (source LIKE 'Court:%' OR (source LIKE 'US federal docket%' "
        "     AND (source LIKE '%sovereign%' OR title LIKE 'In re%' OR title LIKE 'In Re%' "
        "          OR title LIKE 'IN RE%' OR summary LIKE '%foreign%'))) "
        "ORDER BY published_at DESC", (cutoff,), 30)
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
        "SELECT * FROM items WHERE relevant=1 AND published_at>=? AND ("
        "  event_type IN ('lateral_move','appointment') "
        "  OR (source='ICSID docket' AND event_type='tribunal_constituted' "
        "      AND (title LIKE '%appoint%' OR title LIKE '%constituted%' OR title LIKE '%President%'))) "
        "ORDER BY score DESC, published_at DESC", (cutoff,), 40)
    people = drop_repeats(people_rows, site.people_before(dt.date.today().isoformat()))
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
    for r in conn.execute("SELECT * FROM items WHERE COALESCE(llm_stage,'none')='none' AND published_at>=? "
                          "AND source NOT LIKE 'Court:%' AND source<>'ICSID docket'", (cutoff,)).fetchall():
        it = db.row_to_dict(r)
        before = it.get("event_type")
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


def select(conn, settings) -> List[Dict[str, Any]]:
    cutoff = (dt.date.today() - dt.timedelta(days=settings.lookback_days)).isoformat()
    # Pinned items always make the cut; excluded ones never do. Everything else
    # competes on score within the window.
    rows = conn.execute(
        "SELECT * FROM items WHERE relevant=1 AND issue_id IS NULL "
        "AND COALESCE(excluded,0)=0 "
        "AND source NOT LIKE 'Court:%' "          # judgments belong to the court list, not the stories
        "AND COALESCE(event_type,'') NOT IN ('lateral_move','appointment') "
        "AND (COALESCE(pinned,0)=1 OR (score >= ? "
        "     AND COALESCE(published_at, substr(fetched_at,1,10)) >= ?)) "
        "ORDER BY COALESCE(pinned,0) DESC, score DESC LIMIT ?",
        (settings.min_score, cutoff, settings.max_items_per_issue * 4)).fetchall()
    # A story carried on an earlier day is not news on a later one. Earlier
    # days' stories go into the clustering first, so a new copy of an old story
    # merges into them and drops out.
    from . import site
    today = dt.date.today().isoformat()
    since = (dt.date.today() - dt.timedelta(days=21)).isoformat()
    anchors: List[Dict[str, Any]] = []
    for r in conn.execute("SELECT i.* FROM items i JOIN issues s ON s.id=i.issue_id "
                          "WHERE substr(s.created_at,1,10) < ? AND COALESCE(i.published_at,'') >= ?", (today, since)):
        anchors.append(db.row_to_dict(r))
    anchors += site.anchors_before(today)
    for a in anchors:
        a["_anchor"] = True
    anchor_urls = {a.get("url") for a in anchors} - {None, ""}
    reps = cluster(anchors + [db.row_to_dict(r) for r in rows])
    stories = []
    floor = float(getattr(settings, "min_story_score", 0) or 0)
    for rep in reps:
        if rep.get("_anchor") or rep.get("url") in anchor_urls:
            continue
        if any((a.get("url") in anchor_urls) for a in rep.get("also") or []):
            continue
        if (rep.get("score") or 0) < floor and not rep.get("pinned"):
            continue                              # below the floor: leave it out rather than pad the day
        stories.append(rep)
    return stories[:settings.max_items_per_issue]
