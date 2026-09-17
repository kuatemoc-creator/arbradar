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
            why_it_matters=ex.why_it_matters)
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


def select(conn, settings) -> List[Dict[str, Any]]:
    cutoff = (dt.date.today() - dt.timedelta(days=settings.lookback_days)).isoformat()
    rows = conn.execute(
        "SELECT * FROM items WHERE relevant=1 AND issue_id IS NULL "
        "AND score >= ? AND COALESCE(published_at, substr(fetched_at,1,10)) >= ? "
        "ORDER BY score DESC LIMIT ?",
        (settings.min_score, cutoff, settings.max_items_per_issue)).fetchall()
    return [db.row_to_dict(r) for r in rows]
