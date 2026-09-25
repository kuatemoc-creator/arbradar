"""The one build: from the database to a day's issue, in named steps.

    build_issue(conn, settings, date=None)            today's issue, recorded
    build_issue(conn, settings, date, dry_run=True)   the same issue, written to
                                                      out/test-issue-<date>.html,
                                                      nothing recorded
    rebuild_range(conn, settings, first, last)        past days rebuilt in order,
                                                      the range cleared first

Every entry point - the daily run, `cli build`, `cli test`, the review UI - comes
through here, so there is one pipeline and one place to read it:

    prepare -> select (today, leads, enforcement) -> texts -> chase -> records
            -> edit (partner's pass, copy desk, grounding) -> render -> record
"""
import datetime as dt
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional

from . import copydesk, email_html, enrich, followup, grounding, llm, pipeline, record, site
from .config import OUT_DIR, live_site_url
from .outlets import is_trade_press, rank as outlet_rank
from .render import story_slug

RECORD_SOURCES = ("ICSID docket", "US federal docket", "US court opinion", "Find Case Law (England and Wales)", "PCA case list")
DOCKET_SOURCES = ("US federal docket", "ICSID docket", "SEC EDGAR", "Court:", "PCA")
CHASE_LIMIT = 14


class Refused(Exception):
    """The build is not allowed as asked: a sent day without --force."""


# ----------------------------------------------------------------------------
# steps
# ----------------------------------------------------------------------------

def prepare(conn, settings, date: Optional[str], force: bool, dry_run: bool) -> str:
    """Pin the day, refuse to rebuild a sent one without force, release the
    day's earlier issue so the second build sees the same pool as the first."""
    if date:
        pipeline.AS_OF = dt.date.fromisoformat(date)
        sent = conn.execute("SELECT sent_at FROM issues WHERE html_path LIKE ? AND sent_at IS NOT NULL",
                            ("%issue-{}.%".format(date),)).fetchone()
        if sent and not force and not dry_run:
            raise Refused("the issue of {} was sent on {}; pass --force to rebuild it anyway".format(date, sent[0][:16]))
        # Scores carry a recency term; a past day is rebuilt with the scores it had then.
        pipeline.reclassify(conn, settings, days=settings.lookback_days + 7)
    today = pipeline.as_of().isoformat()
    prior = [r[0] for r in conn.execute("SELECT id FROM issues WHERE substr(created_at,1,10)=?", (today,))]
    pipeline.FREE_ISSUES = set()
    if prior and dry_run:
        pipeline.FREE_ISSUES = set(prior)             # the day's own items are candidates again, on paper only
    elif prior:
        marks = ",".join("?" * len(prior))
        conn.execute("UPDATE items SET issue_id=NULL WHERE issue_id IN ({})".format(marks), prior)
        conn.execute("DELETE FROM issues WHERE id IN ({})".format(marks), prior)
        conn.commit()
    pipeline.rescore(conn, settings)
    return today


def fill_summaries(conn, rows: List[Dict[str, Any]]) -> int:
    """A story whose copy arrived cut short ("... after the Congolese") takes the
    fullest text our own database holds for the same article or the same headline."""
    n = 0
    for it in rows:
        cur = (it.get("summary") or "").strip()
        if cur and len(cur) >= 200 and not cur.endswith(("…", "...")):
            continue
        urls = [u for u in [it.get("url")] + [a.get("url") for a in it.get("also") or []] if u]
        q = "SELECT summary FROM items WHERE summary IS NOT NULL AND (url IN ({}) OR title=?)".format(",".join("?" * len(urls)) or "''")
        best = ""
        for (txt,) in conn.execute(q, (*urls, it.get("title") or "")):
            plain = re.sub(r"<[^>]+>", " ", txt or "").strip()
            if plain.endswith(("…", "...")) or plain.lower().startswith((it.get("title") or "").lower()[:40]):
                continue
            if len(plain) > len(best):
                best = txt
        if best and len(best) > len(cur) + 20:
            it["summary"] = best
            n += 1
    return n


def _has_text(it: Dict[str, Any]) -> bool:
    return bool(enrich.relevant_summary(it.get("title_en") or it.get("title") or "", email_html.summary_of(it)))


def with_text(rows: List[Dict[str, Any]], log: Callable[[str], None]) -> List[Dict[str, Any]]:
    """Every printed headline carries an explanation. A story that is still only
    a headline after enrichment is left out; the records (tier 1) and the trade
    press (read in full) always have prose or stand alone by the brief."""
    gone = [it for it in rows if (it.get("source_tier") or 2) != 1
            and not is_trade_press(it.get("source") or "", it.get("url") or "") and not _has_text(it)]
    if gone:
        log("left out {} headline-only stories: {}".format(len(gone), "; ".join((it.get("title") or "")[:50] for it in gone)))
    return [it for it in rows if it not in gone]


def _docket_text(text: str) -> bool:
    """"MISCELLANEOUS CASE INITIATING DOCUMENT - MOTION": a docket entry, not an explanation."""
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(1 for c in letters if c.isupper()) > 0.35 * len(letters)


def select_today(conn, settings, log: Callable[[str], None]) -> List[Dict[str, Any]]:
    items = pipeline.select(conn, settings)
    if not items:
        return []
    fill_summaries(conn, items)
    filled = enrich.enrich(conn, items)
    if filled:
        log("filled in text for {} headline-only stories".format(filled))
    items = with_text(items, log)
    if len(items) < 3:
        # A thin day: as an exception, reach one day further back for stories that
        # were never printed, and give them the same enrichment.
        have = {it["id"] for it in items}
        more = [it for it in pipeline.select(conn, settings, extra_days=1) if it["id"] not in have]
        if more:
            enrich.enrich(conn, more)
            more = with_text(more, log)
            for it in more:
                it["flag_reason"] = ((it.get("flag_reason") or "") + " | held over from the previous day").strip(" |")
            log("thin day: held over {} stories from the previous day".format(len(more)))
            items = (items + more)[:settings.max_items_per_issue]
    # A trade-press headline that still has no text goes after every story that
    # can be explained; it is never the lead.
    for it in items:
        text = email_html.summary_of(it)
        it["brief_only"] = not _has_text(it) or _docket_text(text[:200])
    return [it for it in items if not it["brief_only"]] + [it for it in items if it["brief_only"]]


def select_tracks(conn, settings, items: List[Dict[str, Any]]):
    """The leads (pre-dispute hints from outside the trade press) and the
    enforcement track (awards enforced, resisted and undone), each with its own slots."""
    leads = pipeline.select_leads(conn, settings, items, limit=5)
    if leads:
        enrich.enrich(conn, leads)
        leads = [it for it in leads if _has_text(it) or followup.load(it.get("corroboration"))]
    enforcement = pipeline.select_enforcement(conn, settings, items + leads, limit=6)
    if enforcement:
        enrich.enrich(conn, enforcement)
    fill_summaries(conn, leads + enforcement)
    return leads, enforcement


def chase(conn, rows: List[Dict[str, Any]], dry_run: bool) -> int:
    """Every story is chased into other outlets and its explanation built from
    what they add; a wire's headline replaces a minor outlet's when it is plainly
    the same story. What is found is kept on the row for the next build."""
    chased = 0
    for it in rows:
        stored = followup.load(it.get("corroboration"))
        if stored or chased >= CHASE_LIMIT:
            it["corroboration"] = stored
            continue
        found = followup.corroborate(it)
        chased += 1
        it["corroboration"] = found["sources"]
        if outlet_rank(it.get("source") or "", it.get("url") or "") >= 3 and not (it.get("title_en") or "").strip() \
                and not (it.get("source") or "").startswith(DOCKET_SOURCES):
            better = next((s for s in found["sources"] if outlet_rank(s.get("source") or "", s.get("url") or "") <= 2
                           and 5 <= len((s.get("title") or "").split()) <= 16), None)
            if better:
                it["title_en"] = better["title"]
                if not dry_run:
                    conn.execute("UPDATE items SET title_en=? WHERE id=?", (better["title"], it["id"]))
        if found["story"] and len(found["story"]) > len(email_html.summary_of(it) or ""):
            it["story"] = found["story"]
        if not dry_run:
            conn.execute("UPDATE items SET corroboration=?, story=? WHERE id=?",
                         (json.dumps(found["sources"], ensure_ascii=False), it.get("story") or None, it["id"]))
    if not dry_run:
        conn.commit()
    return chased


def attach_records(conn, rows: List[Dict[str, Any]], dry_run: bool) -> int:
    """The record behind the report: the docket, the case page, the judgment the
    press wrote from. Cited first when found; the report becomes the "also"."""
    for it in rows:
        stored = followup.load(it.get("corroboration"))
        rec = next((c for c in stored if isinstance(c, dict) and c.get("source") in RECORD_SOURCES), None)
        if rec:
            it["record"] = rec
    found = record.attach(conn, rows)
    if found and not dry_run:
        for it in rows:
            if it.get("record"):
                conn.execute("UPDATE items SET corroboration=? WHERE id=?",
                             (json.dumps(it.get("corroboration") or [], ensure_ascii=False), it["id"]))
        conn.commit()
    return found


def edit(rows: List[Dict[str, Any]], settings, date: str, use_llm: bool, log: Callable[[str], None]) -> bool:
    """The partner's edit when the editorial tier is on and a key is present; the
    copy desk on every build; then the grounding check, which keeps both honest."""
    llm_pass = False
    if use_llm and settings.use_llm and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            n = llm.edit_entries(rows, settings.editor_model)
            llm_pass = n > 0
            log("editor pass: {} entries edited".format(n))
        except Exception as exc:                      # noqa: BLE001 - boundary
            log("editor pass skipped ({})".format(exc))
    desk = copydesk.apply(rows, date, OUT_DIR, llm_pass)
    log("copy desk: {} entries, {} need a person; see out/editor-{}.json".format(len(desk["entries"]), desk["needs_person"], date))
    report = grounding.apply(rows, date, OUT_DIR)
    if report["dropped"]:
        log("grounding: dropped {} sentence(s) no cited source carries; see out/grounding-{}.json".format(report["dropped"], date))
    return llm_pass


def render(conn, settings, items, leads, enforcement, date: str) -> Dict[str, Any]:
    extras = pipeline.record_extras(conn, settings, items + leads + enforcement)
    extras["leads"] = leads
    extras["enforcement"] = enforcement
    built = email_html.build(items, extras, settings, date)
    built["extras"] = extras
    return built


def record_issue(conn, settings, items, leads, enforcement, extras, subject: str, html_path: str, today: str) -> int:
    """The day the web site shows, and the issue row the send command reads."""
    site.write_day(today, items, extras, settings, subject)
    cur = conn.execute(
        "INSERT INTO issues (number, created_at, subject, html_path, md_path, item_count) "
        "VALUES ((SELECT COALESCE(MAX(number),0)+1 FROM issues),?,?,?,?,?)",
        (today + dt.datetime.now().isoformat(timespec="seconds")[10:], subject, html_path, None, len(items)))
    issue_id = cur.lastrowid
    conn.executemany("UPDATE items SET issue_id=? WHERE url=? OR id=?",
                     [(issue_id, a["url"], it["id"]) for it in items + leads + enforcement
                      for a in ([{"url": it["url"]}] + (it.get("also") or []))])
    conn.commit()
    return issue_id


# ----------------------------------------------------------------------------
# entry points
# ----------------------------------------------------------------------------

def build_issue(conn, settings, date: Optional[str] = None, force: bool = False, use_llm: bool = True,
                dry_run: bool = False, log: Callable[[str], None] = print) -> Dict[str, Any]:
    """Build one day's issue. Returns what was built; raises Refused when the
    day was sent and force is not given. With dry_run nothing is recorded: no
    issue row, no day file, no item marked - the HTML goes to out/test-issue-<date>.html."""
    today = prepare(conn, settings, date, force, dry_run)
    items = select_today(conn, settings, log)
    if not items:
        log("Nothing with an explanation to print on {}.".format(today))
        return {"date": today, "items": [], "leads": [], "enforcement": [], "html": "", "subject": "", "paths": {}}
    base = live_site_url(settings)
    if settings.site_url and not base:
        log("site host does not resolve yet; email links go to the sources")
    for it in items:
        it["site_link"] = "{}/{}".format(base, story_slug(it, today)) if base else None
    leads, enforcement = select_tracks(conn, settings, items)
    rows = items + leads + enforcement
    chased = chase(conn, rows, dry_run)
    found = attach_records(conn, rows, dry_run)
    if found:
        log("records attached: {}".format(found))
    leads = [it for it in leads if email_html.summary_of(it) or it.get("story")]
    if chased:
        log("chased {} stories into other outlets; {} leads; {} enforcement".format(chased, len(leads), len(enforcement)))
    edit(items + leads + enforcement, settings, today, use_llm, log)
    built = render(conn, settings, items, leads, enforcement, today)
    os.makedirs(OUT_DIR, exist_ok=True)
    name = ("test-issue-{}" if dry_run else "issue-{}").format(today)
    html_path = os.path.join(OUT_DIR, name + ".html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(built["html"])
    out = {"date": today, "items": items, "leads": leads, "enforcement": enforcement, "html": built["html"],
           "subject": built["subject"], "paths": {"html": html_path}, "extras": built["extras"]}
    pipeline.FREE_ISSUES = set()
    if not dry_run:
        out["issue_id"] = record_issue(conn, settings, items, leads, enforcement, built["extras"], built["subject"], html_path, today)
    return out


def clear_range(conn, first: str, last: str) -> List[str]:
    """Forget the issues of a date range - day files and issue rows - so a rebuild
    starts from the same pool the original runs had, in order."""
    dates = []
    d = dt.date.fromisoformat(first)
    end = dt.date.fromisoformat(last)
    while d <= end:
        date = d.isoformat()
        dates.append(date)
        path = site.day_file(date)
        if os.path.exists(path):
            os.remove(path)
        ids = [r[0] for r in conn.execute("SELECT id FROM issues WHERE html_path LIKE ?", ("%issue-{}.html".format(date),))]
        if ids:
            marks = ",".join("?" * len(ids))
            conn.execute("UPDATE items SET issue_id=NULL WHERE issue_id IN ({})".format(marks), ids)
            conn.execute("DELETE FROM issues WHERE id IN ({})".format(marks), ids)
        d += dt.timedelta(days=1)
    conn.commit()
    return dates


def rebuild_range(conn, settings, first: str, last: str, force: bool = False, use_llm: bool = False,
                  log: Callable[[str], None] = print) -> List[Dict[str, Any]]:
    """Past days rebuilt in order after the range is cleared, so that no stale
    later day steers an earlier one and each day sees only what came before it."""
    sent = [r[0] for r in conn.execute("SELECT html_path FROM issues WHERE sent_at IS NOT NULL")]
    dates = clear_range(conn, first, last) if force or not any(("issue-{}.html".format(x) in (p or "")) for p in sent for x in _dates(first, last)) else None
    if dates is None:
        raise Refused("a day in {}..{} was sent; pass --force to rebuild the range".format(first, last))
    out = []
    for date in dates:
        log("== {}".format(date))
        out.append(build_issue(conn, settings, date=date, force=force, use_llm=use_llm, log=log))
    return out


def _dates(first: str, last: str) -> List[str]:
    d, end, out = dt.date.fromisoformat(first), dt.date.fromisoformat(last), []
    while d <= end:
        out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out
