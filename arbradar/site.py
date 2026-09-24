"""The newsletter on the web: one page per day, with a day switcher.

Every build saves its day to out/site/data/<date>.json - the stories and the
four record lists. The site is rendered from those files, so each day that was
ever built stays reachable, the root page is always the latest day, and the
pipeline can look back at what earlier days carried so that a story or a
record row is never repeated on a later day.
"""
import datetime as dt
import glob
import html
import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import OUT_DIR

SITE = os.path.join(OUT_DIR, "site")
DATA = os.path.join(SITE, "data")

STORY_FIELDS = ("id", "title", "title_en", "summary", "summary_en", "url", "source", "source_tier",
                "event_type", "published_at", "institution", "treaty", "case_ref", "claimants",
                "respondents", "states", "sectors", "counsel", "arbitrators", "amount_usd",
                "flag_reason", "why_it_matters", "also", "lang", "country", "corroboration", "story")
RECORD_HEADINGS = (("docket", "From the ICSID docket"), ("disclosures", "Company disclosures"),
                   ("courts", "In the courts"), ("people", "People and appointments"))


def day_file(date: str) -> str:
    return os.path.join(DATA, date + ".json")


def day_page(date: str) -> str:
    return date + ".html"


def date_label(date: str) -> str:
    d = dt.date.fromisoformat(date[:10])
    return "{} {} {}".format(d.day, d.strftime("%B"), d.year)


def short_label(date: str) -> str:
    d = dt.date.fromisoformat(date[:10])
    return "{} {} {}".format(d.strftime("%a"), d.day, d.strftime("%b"))


# ----------------------------------------------------------------------------
# saving a day
# ----------------------------------------------------------------------------

def write_day(date: str, items: List[Dict[str, Any]], extras: Dict[str, List[Dict[str, Any]]],
              settings, subject: str = "") -> str:
    from .render import story_slug
    from .email_html import SHORT, record_parts
    stories = []
    for i, it in enumerate(items):
        d = {k: it.get(k) for k in STORY_FIELDS}
        d["tier"] = "brief" if it.get("brief_only") else "lead" if i == 0 else "development" if i < 7 else "brief"
        d["slug"] = story_slug(it, date)
        d["event"] = SHORT.get(it.get("event_type") or "commentary", "Note")
        stories.append(d)
    leads = []
    for it in (extras or {}).get("leads") or []:
        d = {k: it.get(k) for k in STORY_FIELDS}
        d["tier"] = "signal"
        d["slug"] = story_slug(it, date)
        d["event"] = SHORT.get(it.get("event_type") or "commentary", "Note")
        leads.append(d)
    records: Dict[str, List[Dict[str, Any]]] = {}
    for key, _ in RECORD_HEADINGS:
        rows = []
        for it in (extras or {}).get(key) or []:
            main, step, tail = record_parts(key, it)
            rows.append({"date": str(it.get("published_at") or "")[:10], "title": it.get("title") or "",
                         "main": main, "step": step, "tail": tail, "url": it.get("url") or ""})
        records[key] = rows
    os.makedirs(DATA, exist_ok=True)
    with open(day_file(date), "w", encoding="utf-8") as fh:
        json.dump({"date": date, "subject": subject, "stories": stories, "leads": leads, "records": records},
                  fh, ensure_ascii=False, indent=1)
    return day_file(date)


def load_days() -> List[Dict[str, Any]]:
    days = []
    for path in glob.glob(os.path.join(DATA, "*.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        if d.get("date"):
            days.append(d)
    return sorted(days, key=lambda d: d["date"], reverse=True)


def shown_before(date: str, days: int = 30) -> Tuple[Set[str], Set[str]]:
    """URLs and title fingerprints of everything carried by earlier days."""
    from .pipeline import fingerprint, title_key
    cutoff = (dt.date.fromisoformat(date) - dt.timedelta(days=days)).isoformat()
    urls: Set[str] = set()
    fps: Set[str] = set()
    for d in load_days():
        if not (cutoff <= d["date"] < date):
            continue
        for s in (d.get("stories") or []) + (d.get("leads") or []):
            urls.add(s.get("url") or "")
            fps.add(fingerprint(s)); fps.add(title_key(s))
            for a in s.get("also") or []:
                urls.add(a.get("url") or "")
                fps.add(fingerprint(a)); fps.add(title_key(a))
        for rows in (d.get("records") or {}).values():
            for r in rows:
                urls.add(r.get("url") or "")
                fps.add(fingerprint(r)); fps.add(title_key(r))
    urls.discard("")
    return urls, fps


def anchors_before(date: str, days: int = 21) -> List[Dict[str, Any]]:
    """Stories from earlier days, as items the clustering can merge new candidates into."""
    cutoff = (dt.date.fromisoformat(date) - dt.timedelta(days=days)).isoformat()
    out = []
    for d in load_days():
        if not (cutoff <= d["date"] < date):
            continue
        for s in (d.get("stories") or []) + (d.get("leads") or []):
            out.append({"title": s.get("title") or "", "title_en": s.get("title_en"), "url": s.get("url") or "",
                        "claimants": s.get("claimants") or [], "respondents": s.get("respondents") or [],
                        "states": s.get("states") or [], "case_ref": s.get("case_ref"),
                        "lang": s.get("lang") or "en", "also": []})
    return out


def people_before(date: str, days: int = 21) -> List[Dict[str, Any]]:
    """Earlier days' people rows, as items the clustering can merge new copies into."""
    cutoff = (dt.date.fromisoformat(date) - dt.timedelta(days=days)).isoformat()
    out = []
    for d in load_days():
        if not (cutoff <= d["date"] < date):
            continue
        for r in (d.get("records") or {}).get("people") or []:
            out.append({"title": r.get("title") or "", "url": r.get("url") or "", "also": [], "lang": "en"})
    return out


# ----------------------------------------------------------------------------
# rendering
# ----------------------------------------------------------------------------

def _clip(text: str, words: int = 55) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).replace("\xa0", " ").strip()
    parts = text.split(" ")
    if len(parts) <= words:
        return text
    return " ".join(parts[:words]).rstrip(",;:") + "…"


def _switcher(days: List[Dict[str, Any]], current: str) -> str:
    links = []
    for d in days[:14]:
        cur = ' aria-current="page"' if d["date"] == current else ""
        links.append('<a class="day" href="{}"{}>{}</a>'.format(day_page(d["date"]), cur, short_label(d["date"])))
    return '<nav class="days" aria-label="Issues by day">{}</nav>'.format("".join(links))


def _story_row(s: Dict[str, Any], lead: bool = False) -> str:
    """Headline, explanation, source and date - the same shape as the email."""
    from .email_html import summary_of
    from .style import headline, sentences
    when = str(s.get("published_at") or "")[:10]
    try:
        d = dt.date.fromisoformat(when)
        when_label = "{} {}".format(d.day, d.strftime("%B"))
    except ValueError:
        when_label = ""
    outlet = (s.get("source") or "").replace("Google News / ", "")
    outlet = re.sub(r"\s*\((?:Global|Sector: [^)]*)\)\s*$", "", outlet)
    body = sentences(s.get("story") or summary_of(s), 70 if s.get("story") else 45)
    tail = '<span class="tail">&mdash; <a href="{}" rel="noopener">{}</a>{}</span>'.format(
        html.escape(s.get("url") or "#"), html.escape(outlet or "source"), (", " + html.escape(when_label)) if when_label else "")
    cites = [c for c in (s.get("corroboration") or [])[:3] if c.get("url")]
    if cites:
        tail += '<span class="tail"> &middot; also ' + ", ".join(
            '<a href="{}" rel="noopener">{}</a>'.format(html.escape(c["url"]), html.escape(c.get("source") or "source")) for c in cites) + "</span>"
    return ('<article class="story{lead}"><h2><a href="{slug}">{h}</a></h2>'
            '<p>{p}{sp}{tail}</p></article>').format(
        lead=" lead" if lead else "", slug=html.escape(s.get("slug") or "#"),
        h=html.escape(headline(s.get("title_en") or s.get("title") or "",
                               list(s.get("claimants") or []) + list(s.get("respondents") or []) + list(s.get("counsel") or []))),
        p=html.escape(body), sp=" " if body else "", tail=tail)


def _record_rows(rows: List[Dict[str, Any]]) -> str:
    """A record is an entry like any other: name as the headline, the step as
    the explanation, the court or reference and the date as the source line."""
    out = []
    for r in rows:
        try:
            d = short_label(r.get("date") or "")
        except ValueError:
            d = ""
        url = html.escape(r.get("url") or "#")
        tail = '<span class="tail">&mdash; <a href="{}" rel="noopener">{}</a>{}</span>'.format(
            url, html.escape(r.get("tail") or "record"), (", " + html.escape(d)) if d else "")
        body = html.escape(r.get("step") or "")
        out.append('<article class="story"><h2><a href="{}" rel="noopener">{}</a></h2><p>{}{}{}</p></article>'.format(
            url, html.escape(r.get("main") or r.get("title") or ""), body, " " if body else "", tail))
    return '<div class="stories">{}</div>'.format("".join(out))


def render_day(day: Dict[str, Any], days: List[Dict[str, Any]], settings) -> str:
    from .articles import _page, _signup, FOOTER
    date = day["date"]
    stories = day.get("stories") or []
    main = stories
    briefs = []
    parts = [
        '<header class="mast"><a class="brand" href="index.html">{}</a><span class="date">{}</span></header>'.format(
            html.escape(settings.newsletter_name), html.escape(date_label(date))),
        _switcher(days, date),
        "<h1>{}</h1>".format(html.escape(settings.tagline)),
        _signup(settings),
        '<h2 class="sec">Today</h2><div class="stories">{}</div>'.format("".join(_story_row(s, lead=(i == 0)) for i, s in enumerate(main))),
    ]
    leads = day.get("leads") or []
    if leads:
        parts.append('<h2 class="sec">Leads</h2><p class="lede">Measures and disputes in the making, from outside the trade press.</p>'
                     '<div class="stories">{}</div>'.format("".join(_story_row(s) for s in leads)))
    if briefs:
        parts.append('<h2 class="sec">In brief</h2><div class="stories">{}</div>'.format("".join(
            _story_row(dict(s, summary="", summary_en="", story="")) for s in briefs)))
    for key, heading in RECORD_HEADINGS:
        rows = (day.get("records") or {}).get(key) or []
        if rows:
            parts.append('<h2 class="sec">{}</h2>{}'.format(html.escape(heading), _record_rows(rows)))
    parts.append(FOOTER)
    title = "{} · {}".format(settings.newsletter_name, date_label(date))
    return _page(title, "\n".join(parts), day.get("subject") or settings.tagline, settings.newsletter_name)


def build(settings, use_llm: bool = True) -> Dict[str, Any]:
    from .articles import write_article, _template_article, render_article
    days = load_days()
    if not days:
        raise RuntimeError("no day data yet - build an issue first")
    os.makedirs(SITE, exist_ok=True)
    # The custom domain goes on the site only once it resolves. With the CNAME
    # file in place before the DNS record exists, GitHub redirects the github.io
    # address to a host that does not answer and every visitor gets a warning.
    from .config import live_site_url
    host = re.sub(r"^https?://", "", (settings.site_url or "").strip()).split("/")[0]
    cname = os.path.join(SITE, "CNAME")
    if host and not host.endswith("github.io") and live_site_url(settings):
        with open(cname, "w", encoding="utf-8") as fh:
            fh.write(host + "\n")
    elif os.path.exists(cname):
        os.remove(cname)
    with open(os.path.join(SITE, ".nojekyll"), "w", encoding="utf-8") as fh:
        fh.write("")
    # The full list of sources, verified weekly, is part of the product.
    src_map = os.path.join(os.path.dirname(OUT_DIR), "docs", "sources.html")
    if os.path.exists(src_map):
        with open(src_map, encoding="utf-8") as fh, open(os.path.join(SITE, "sources.html"), "w", encoding="utf-8") as out:
            out.write(fh.read())

    keep: Set[str] = set()
    written = 0
    for day in days:
        date = day["date"]
        for s in (day.get("stories") or []) + (day.get("leads") or []):
            fname = s.get("slug") or ""
            if not fname:
                continue
            path = os.path.join(SITE, fname)
            keep.add(fname)
            art = None
            if use_llm and settings.use_llm and not os.path.exists(path):
                art = write_article(s, settings.editor_model)
            art = art or _template_article(s)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(render_article(art, s, settings, date, day_href=day_page(date)))
            written += 1
        page = render_day(day, days, settings)
        with open(os.path.join(SITE, day_page(date)), "w", encoding="utf-8") as fh:
            fh.write(page)
        keep.add(day_page(date))
    # The root is the latest day.
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_day(days[0], days, settings))
    # Story pages no day refers to any more are dead weight.
    for path in glob.glob(os.path.join(SITE, "20*.html")):
        if os.path.basename(path) not in keep:
            os.remove(path)
    stale = os.path.join(SITE, "manifest.json")
    if os.path.exists(stale):
        os.remove(stale)
    return {"site": SITE, "days": [d["date"] for d in days], "written": written}
