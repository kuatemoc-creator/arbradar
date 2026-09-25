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
from .match import (  # noqa: F401 - the matching rules live in match.py; re-exported for callers
    TRACKING, canonical, title_key, fingerprint, PAYWALL, is_paywall, STOP, _stem, _fold, _tokens, _bigrams, _state_stems, _propers, shared_propers, _entities, _CITIES, _in_english, _english, _JUR_WORDS, _STATE_STEMS, _GENERIC, _STAGES, _stage, cluster, _cite_best, _MEASURES, _CAPITALS, _REGION, _topics_of)
from . import fetch as fetch_mod

log = logging.getLogger(__name__)


# The day an issue is built for. Today unless a past day is being rebuilt, in
# which case nothing published after it may appear and only earlier days count
# as already shown.
AS_OF: Optional[dt.date] = None


def as_of() -> dt.date:
    return AS_OF or dt.date.today()


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


# A dry run of a day that already has an issue must see that day's own items:
# the build module lists the issue ids to treat as unassigned, without touching them.
FREE_ISSUES: set = set()


def _free() -> str:
    if not FREE_ISSUES:
        return "issue_id IS NULL"
    return "(issue_id IS NULL OR issue_id IN ({}))".format(",".join(str(int(i)) for i in FREE_ISSUES))


def select(conn, settings, extra_days: int = 0) -> List[Dict[str, Any]]:
    # Today is what was published in the last two days: a wire story three days
    # old that Google News surfaced late is not the lead of a daily.
    cutoff = (as_of() - dt.timedelta(days=getattr(settings, "today_days", 2) + extra_days)).isoformat()
    upto = as_of().isoformat() + "~"
    # Pinned items always make the cut; excluded ones never do. Everything else
    # competes on score within the window.
    rows = conn.execute(
        "SELECT * FROM items WHERE relevant=1 AND " + _free() + " "
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


def _track(conn, settings, taken, events, limit, floor, trade_ok, records_ok, business_gate) -> List[Dict[str, Any]]:
    from . import site as _site
    from .outlets import is_trade_press
    cutoff = (as_of() - dt.timedelta(days=settings.lookback_days)).isoformat()
    upto = as_of().isoformat() + "~"
    marks = ",".join("?" * len(events))
    sources = "" if records_ok else "AND source NOT LIKE 'Court:%' AND source NOT IN ('ICSID docket','SEC EDGAR','PCA case list') "
    rows = conn.execute(
        "SELECT * FROM items WHERE relevant=1 AND " + _free() + " AND COALESCE(excluded,0)=0 "
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
    # The clustering rewrites its inputs; the day's stories go in as copies so
    # their own "also" lists come out of this untouched.
    for rep in cluster(anchors + [dict(t) for t in taken] + cands):
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
