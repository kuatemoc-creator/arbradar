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


def fingerprint(item: Dict[str, Any]) -> str:
    """URL identity first; fall back to normalised title so the same story from
    two outlets collapses to one line."""
    url = canonical(item.get("url") or "")
    if url:
        return hashlib.sha256(url.encode()).hexdigest()
    norm = re.sub(r"[^a-z0-9]+", " ", (item.get("title") or "").lower()).strip()
    return hashlib.sha256(norm.encode()).hexdigest()


def rule_classify(item: Dict[str, Any]) -> Dict[str, Any]:
    """Cheap first pass so the system is useful with no API key at all."""
    text = " {} {} ".format(item.get("title") or "", item.get("summary") or "").lower()
    out: Dict[str, Any] = {}

    if not item.get("event_type"):
        for event_type, phrases in EVENT_PATTERNS:
            if any(p in text for p in phrases):
                out["event_type"] = event_type
                break
        else:
            out["event_type"] = "commentary"

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
                    "summary": (raw.get("summary") or "")[:4000],
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
                    "lang": raw.get("lang") or "en",
                    "country": raw.get("country") or None,
                }
                item.update(rule_classify(item))
                if db.upsert_item(conn, item):
                    new += 1
        except Exception as exc:                      # noqa: BLE001 - boundary
            error = str(exc)[:300]
            log.warning("source %s failed: %s", name, exc)

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


def _tokens(title: str) -> set:
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", (title or "").lower())
            if len(w) >= 3 and w not in STOP}


def cluster(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Greedy story clustering on headline overlap.

    Google News brings the same development in from five outlets under five
    headlines. Items arrive score-descending, so the best-scored version becomes
    the story and the others hang off it as "also reported by". A cluster is
    compared on the union of its members' tokens, so a terse trade-press
    headline and a long wire headline still find each other.
    """
    reps: List[Dict[str, Any]] = []
    for it in items:
        toks = _tokens(it.get("title_en") or it["title"])
        home = None
        for rep in reps:
            # Two different case numbers are two different matters, full stop.
            if it.get("case_ref") and rep.get("case_ref") and it["case_ref"] != rep["case_ref"]:
                continue
            inter = len(toks & rep["_toks"])
            if not inter:
                continue
            jac = inter / len(toks | rep["_toks"])
            if jac >= 0.5 or (inter >= 3 and jac >= 0.22):
                home = rep
                break
        if home is None:
            it["_toks"] = set(toks)
            it["also"] = []
            reps.append(it)
            continue
        home["_toks"] |= toks
        home["also"].append({"source": it.get("source"), "url": it.get("url"),
                             "title": it.get("title")})
        # A duplicate from a primary record can carry evidence the lead lacks.
        for f in ("counsel", "claimants", "respondents", "states", "sectors",
                  "arbitrators", "treaty", "amount_usd", "case_ref"):
            if not home.get(f) and it.get(f):
                home[f] = it[f]
    for r in reps:
        r.pop("_toks", None)
    return reps


def select(conn, settings) -> List[Dict[str, Any]]:
    cutoff = (dt.date.today() - dt.timedelta(days=settings.lookback_days)).isoformat()
    # Pinned items always make the cut; excluded ones never do. Everything else
    # competes on score within the window.
    rows = conn.execute(
        "SELECT * FROM items WHERE relevant=1 AND issue_id IS NULL "
        "AND COALESCE(excluded,0)=0 "
        "AND (COALESCE(pinned,0)=1 OR (score >= ? "
        "     AND COALESCE(published_at, substr(fetched_at,1,10)) >= ?)) "
        "ORDER BY COALESCE(pinned,0) DESC, score DESC LIMIT ?",
        (settings.min_score, cutoff, settings.max_items_per_issue * 4)).fetchall()
    stories = cluster([db.row_to_dict(r) for r in rows])
    return stories[:settings.max_items_per_issue]
