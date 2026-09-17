"""Short standalone articles, one per story, for resharing.

Each is a self-contained page in the CaseLens house style: a headline, a dek,
the facts as a definition list, three short paragraphs, and the angle. Written
by the editorial model when a key is set; assembled from the structured fields
otherwise. The output is a static site under out/site/ that can be hosted
anywhere - an Artifact, GitHub Pages, or your own domain.
"""
import datetime as dt
import html
import json
import os
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from . import db, llm
from .render import story_slug
from .config import FALLBACK_BETA, OUT_DIR
from .taxonomy import EVENT_TYPES

SITE = os.path.join(OUT_DIR, "site")


class Article(BaseModel):
    headline: str = Field(description="At most 12 words, sentence case, no colon. Lead with the "
                                      "commercial fact: who, against whom, over what.")
    dek: str = Field(description="One plain sentence, at most 28 words, on why a practitioner "
                                 "cares. Not a summary of the headline.")
    paragraphs: List[str] = Field(description="Two or three paragraphs, 130-180 words in total. "
                                              "Only facts present in the source. No hedging.")
    angle: str = Field("", description="Leave empty.")


ARTICLE_SYSTEM = """You write short standalone news pieces for international arbitration practitioners. \
The reader is a partner. Report the development: the commercial fact, the parties, the forum, the \
procedural posture, and who is on record. Do not explain why it matters to their practice or what \
they should do; they will see it. Never invent a party, amount, treaty or firm that is not in the source.

""" + llm.HOUSE_STYLE


def _slug(text: str, date: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:70]
    return "{}-{}".format(date, s)


def _facts(it: Dict[str, Any]) -> List[List[str]]:
    from .email_html import who, what, date_label
    ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {})
    when = str(it.get("published_at") or "")[:10]
    try:
        when_label = date_label(when)
    except ValueError:
        when_label = when
    rows = [["Who", who(it)], ["When", when_label], ["What", what(it)],
            ["Why flagged", it.get("flag_reason") or ""]]
    if it.get("institution"):
        rows.append(["Forum", it["institution"]])
    if it.get("case_ref"):
        rows.append(["Reference", it["case_ref"]])
    if it.get("treaty"):
        rows.append(["Instrument", it["treaty"]])
    if it.get("amount_usd"):
        rows.append(["Amount", "US${:,.0f}m".format(it["amount_usd"] / 1e6)])
    if it.get("claimants"):
        rows.append(["Claimant", "; ".join(it["claimants"][:3])])
    if it.get("respondents"):
        rows.append(["Respondent", "; ".join(it["respondents"][:3])])
    if it.get("counsel"):
        rows.append(["Counsel on record", "; ".join(it["counsel"][:4])])
    elif (it.get("source_tier") or 2) == 1:
        rows.append(["Counsel on record", "None listed"])
    return rows


def _template_article(it: Dict[str, Any]) -> Article:
    """No model available: assemble from the record, in plain professional English."""
    ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {})
    summary = re.sub(r"\s+", " ", it.get("summary_en") or it.get("summary") or "").strip()
    sentences = [p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z\u00c0-\u024f])", summary) if p]
    body = [" ".join(sentences[:2])] if sentences else [it.get("title", "")]
    if len(sentences) > 2:
        body.append(" ".join(sentences[2:5]))

    # A dek is one whole sentence or nothing. Never chop a sentence and stamp a
    # full stop on the stump - use the ranking reason instead.
    dek = sentences[0] if sentences else ""
    if len(dek.split()) > 80 or dek.lower().startswith(it.get("title", "").lower()[:30]):
        dek = ""

    return Article(headline=(it.get("title_en") or it.get("title", ""))[:120], dek=dek,
                   paragraphs=body, angle="")


def write_article(it: Dict[str, Any], model: str) -> Optional[Article]:
    src = json.dumps({k: it.get(k) for k in (
        "title", "summary", "source", "published_at", "event_type", "institution", "treaty",
        "case_ref", "claimants", "respondents", "states", "sectors", "amount_usd", "counsel",
        "arbitrators", "why_it_matters")}, ensure_ascii=False)
    kwargs = dict(model=model, max_tokens=3000, system=ARTICLE_SYSTEM,
                  output_config={"effort": "medium"},
                  messages=[{"role": "user", "content": "Source item:\n" + src}],
                  output_format=Article)
    if model.startswith("claude-fable") or model.startswith("claude-opus-5"):
        kwargs["betas"] = [FALLBACK_BETA]
        kwargs["fallbacks"] = "default"
    try:
        resp = llm.client().beta.messages.parse(**kwargs)
    except Exception:                                 # noqa: BLE001 - boundary
        return None
    if getattr(resp, "stop_reason", None) == "refusal":
        return None
    return resp.parsed_output


# ----------------------------------------------------------------------------
# rendering - CaseLens tokens, light and dark
# ----------------------------------------------------------------------------
CSS = """
:root{color-scheme:light;--blue-50:oklch(97% .015 270);--blue-500:#4D68F9;--blue-600:oklch(52% .21 270);
--n0:#fff;--n50:oklch(97.5% .005 270);--n100:oklch(95% .007 270);--n200:oklch(90.5% .011 270);
--n500:oklch(55% .02 270);--n600:oklch(46% .022 270);--n900:oklch(21% .03 272);
--page:oklch(98.4% .004 270);--card:var(--n0);--sunken:var(--n50);--soft:var(--blue-50);
--ink:var(--n900);--ink2:var(--n600);--mute:var(--n500);--link:var(--blue-600);
--hair:var(--n100);--line:var(--n200);--accent:var(--blue-500);
--display:"Source Serif 4",Georgia,"Times New Roman",serif;
--sans:"Hanken Grotesk",-apple-system,"Segoe UI",sans-serif;
--mono:"IBM Plex Mono","SF Mono",Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font-family:var(--sans);
font-size:1rem;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--link)}
.wrap{max-width:720px;margin:0 auto;padding:40px 24px 80px}
.mast{display:flex;justify-content:flex-start;align-items:baseline;gap:0;flex-wrap:wrap;
padding-bottom:14px;border-bottom:2px solid var(--ink);margin-bottom:28px}
.brand{font-family:var(--display);font-size:1.375rem;font-weight:600;letter-spacing:-.01em;color:var(--ink);text-decoration:none}
.foot{margin-top:40px;padding-top:22px;border-top:1px solid var(--line)}
.pub{display:inline-flex;align-items:center;gap:12px;text-decoration:none;color:var(--ink)}
.pub span{display:flex;flex-direction:column;font-weight:700;font-size:1rem;line-height:1.2}
.pub small{font-size:.65rem;letter-spacing:.14em;text-transform:uppercase;color:var(--mute);font-weight:600;margin-bottom:2px}
.pub:hover{color:var(--link)}
.mast .date{font-family:var(--mono);font-size:.75rem;color:var(--mute);margin-left:auto}
.eyebrow{font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);font-weight:600}
h1{font-family:var(--display);font-size:2.125rem;line-height:1.15;letter-spacing:-.015em;
font-weight:600;margin:8px 0 12px;text-wrap:balance}
.dek{font-size:1.125rem;color:var(--ink2);margin:0 0 26px;max-width:60ch;line-height:1.5}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px 24px;
background:var(--sunken);border:1px solid var(--hair);border-radius:12px;padding:18px 20px;margin:0 0 28px}
.facts div{min-width:0}
.facts dt{font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);font-weight:600;margin-bottom:2px}
.facts dd{margin:0;font-size:.875rem;font-weight:500;overflow-wrap:anywhere}
.body p{margin:0 0 16px;max-width:65ch}
.angle{border-left:3px solid var(--accent);background:var(--soft);padding:14px 18px;
border-radius:0 10px 10px 0;margin:28px 0}
.angle b{display:block;font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin-bottom:4px}
.src{font-size:.8125rem;color:var(--mute);border-top:1px solid var(--line);padding-top:14px;margin-top:32px}
.src a{margin-right:12px}
.list{display:flex;flex-direction:column;gap:0}
.item{display:grid;grid-template-columns:110px 1fr;gap:16px;padding:18px 0;border-bottom:1px solid var(--hair)}
.item .d{font-family:var(--mono);font-size:.75rem;color:var(--mute);padding-top:5px}
.item a.h{font-family:var(--display);font-size:1.25rem;font-weight:600;color:var(--ink);text-decoration:none;line-height:1.3}
.item a.h:hover{color:var(--link)}
.item p{margin:6px 0 0;color:var(--ink2);font-size:.9375rem;max-width:62ch}
.pill{display:inline-block;font-size:.7rem;font-weight:600;letter-spacing:.04em;padding:1px 8px;
border-radius:999px;background:var(--soft);color:var(--link);margin-top:8px}
@media (max-width:560px){.item{grid-template-columns:1fr;gap:4px}h1{font-size:1.625rem}}
"""
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:'
         'opsz,wght@8..60,400;8..60,600&family=Hanken+Grotesk:wght@400;500;600;700&family='
         'IBM+Plex+Mono:wght@400;500&display=swap">')


def _page(title: str, body: str, desc: str, name: str) -> str:
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"color-scheme\" content=\"light\">"
            "<title>{t}</title><meta name=\"description\" content=\"{d}\">"
            "<meta property=\"og:title\" content=\"{t}\"><meta property=\"og:description\" content=\"{d}\">"
            "{f}<style>{c}</style></head><body><div class=\"wrap\">{b}</div></body></html>").format(
        t=html.escape(title), d=html.escape(desc[:200]), f=FONTS, c=CSS, b=body)


def render_article(a: Article, it: Dict[str, Any], settings, date: str) -> str:
    from .email_html import SHORT
    ev = {"label": SHORT.get(it.get("event_type") or "commentary", "Note")
                    + (" \u00b7 " + it["institution"] if it.get("institution") else "")}
    paras = "".join("<p>{}</p>".format(html.escape(p)) for p in a.paragraphs)
    srcs = [(it.get("source") or "source", it.get("url"))] + [
        ((x.get("source") or "source").replace("Google News / ", ""), x.get("url"))
        for x in (it.get("also") or [])[:4]]
    src_html = "".join('<a href="{}" rel="noopener">{}</a>'.format(html.escape(u or "#"), html.escape(s))
                       for s, u in srcs if u)
    body = """<header class="mast"><a class="brand" href="index.html">{name}</a>
<span class="date">{date}</span></header>
<div class="eyebrow">{ev}</div>
<h1>{h}</h1>
{dek}
<div class="body">{paras}</div>
<div class="src">{src}</div>
<footer class="foot"><a href="https://caselens.tech" class="pub"><svg width="32" height="32" style="display:block;border-radius:7px" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 32 32"><g transform="translate(0.4 0.209)"><path d="M 24.514 0 L 6.686 0 C 2.993 0 0 2.993 0 6.686 L 0 24.514 C 0 28.207 2.993 31.2 6.686 31.2 L 24.514 31.2 C 28.207 31.2 31.2 28.207 31.2 24.514 L 31.2 6.686 C 31.2 2.993 28.207 0 24.514 0 Z" fill="rgb(77,104,249)"></path><path d="M 24.149 9.951 C 22.329 7.625 19.624 6.31 16.667 6.31 C 11.56 6.31 7.363 10.481 7.363 15.563 C 7.363 17.242 7.815 18.81 8.605 20.16 L 8.581 20.137 L 7.26 24.892 L 11.952 23.495 C 13.361 24.318 15.009 24.79 16.768 24.79 C 19.776 24.79 22.506 23.323 24.2 21.099 L 20.231 18.04 C 19.422 19.203 18.107 19.835 16.692 19.835 C 14.315 19.835 12.369 17.913 12.369 15.563 C 12.369 13.161 14.341 11.265 16.742 11.265 C 18.183 11.265 19.447 11.973 20.231 13.06 Z" fill="rgb(255,255,255)"></path></g></svg><span><small>Published by</small>CaseLens</span></a></footer>""".format(
        name=html.escape(settings.newsletter_name), date=html.escape(date),
        ev=html.escape(ev.get("label", "")), h=html.escape(a.headline),
        dek='<p class="dek">{}</p>'.format(html.escape(a.dek)) if (a.dek and a.dek not in " ".join(a.paragraphs)) else "",
        paras=paras, src=src_html)
    return _page(a.headline, body, a.dek, settings.newsletter_name)


def render_index(entries: List[Dict[str, Any]], settings) -> str:
    items = "".join("""<div class="item"><div class="d">{d}</div><div>
<a class="h" href="{f}">{h}</a>{dek}<span class="pill">{ev}</span></div></div>""".format(
        d=html.escape(e["date"]), f=html.escape(e["file"]), h=html.escape(e["headline"]),
        dek="<p>{}</p>".format(html.escape(e["dek"])) if e.get("dek") else "", ev=html.escape(e["event"]))
        for e in entries)
    body = """<header class="mast"><a class="brand" href="index.html">{name}</a>
<span class="date">{n} pieces</span></header>
<h1>{tag}</h1>
<p class="dek">One page per story, with sources.</p>
<div class="list">{items}</div>
<footer class="foot"><a href="https://caselens.tech" class="pub"><svg width="32" height="32" style="display:block;border-radius:7px" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 32 32"><g transform="translate(0.4 0.209)"><path d="M 24.514 0 L 6.686 0 C 2.993 0 0 2.993 0 6.686 L 0 24.514 C 0 28.207 2.993 31.2 6.686 31.2 L 24.514 31.2 C 28.207 31.2 31.2 28.207 31.2 24.514 L 31.2 6.686 C 31.2 2.993 28.207 0 24.514 0 Z" fill="rgb(77,104,249)"></path><path d="M 24.149 9.951 C 22.329 7.625 19.624 6.31 16.667 6.31 C 11.56 6.31 7.363 10.481 7.363 15.563 C 7.363 17.242 7.815 18.81 8.605 20.16 L 8.581 20.137 L 7.26 24.892 L 11.952 23.495 C 13.361 24.318 15.009 24.79 16.768 24.79 C 19.776 24.79 22.506 23.323 24.2 21.099 L 20.231 18.04 C 19.422 19.203 18.107 19.835 16.692 19.835 C 14.315 19.835 12.369 17.913 12.369 15.563 C 12.369 13.161 14.341 11.265 16.742 11.265 C 18.183 11.265 19.447 11.973 20.231 13.06 Z" fill="rgb(255,255,255)"></path></g></svg><span><small>Published by</small>CaseLens</span></a></footer>""".format(name=html.escape(settings.newsletter_name), n=len(entries),
                                           tag=html.escape(settings.tagline), items=items)
    return _page(settings.newsletter_name, body, settings.tagline, settings.newsletter_name)


def build(conn, settings, limit: int = 6, use_llm: bool = True) -> Dict[str, Any]:
    from . import pipeline
    row = conn.execute("SELECT * FROM issues ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        raise RuntimeError("no issue built yet")
    date = str(row["created_at"])[:10]
    rows = conn.execute("SELECT * FROM items WHERE issue_id=? AND relevant=1 ORDER BY score DESC",
                        (row["id"],)).fetchall()
    stories = pipeline.cluster([db.row_to_dict(r) for r in rows])
    starters = ("notice_of_intent", "new_case_filed", "counsel_tender", "s1782_application", "state_measure")
    lead = next((it for it in stories[:5] if it.get("event_type") in starters), stories[0] if stories else None)
    if lead is not None:
        stories = [lead] + [it for it in stories if it is not lead]
    stories = stories[:limit]

    os.makedirs(SITE, exist_ok=True)
    manifest_path = os.path.join(SITE, "manifest.json")
    manifest: List[Dict[str, Any]] = []
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path, encoding="utf-8"))
        # an entry whose page was removed is a dead link on the index
        manifest = [e for e in manifest if os.path.exists(os.path.join(SITE, e["file"]))]
    known = {e["file"] for e in manifest}

    written = []
    fresh: List[Dict[str, Any]] = []
    for it in stories:
        art = write_article(it, settings.editor_model) if (use_llm and settings.use_llm) else None
        art = art or _template_article(it)
        fname = story_slug(it, date)
        with open(os.path.join(SITE, fname), "w", encoding="utf-8") as fh:
            fh.write(render_article(art, it, settings, date))
        from .email_html import SHORT
        entry = {"file": fname, "date": date, "headline": art.headline, "dek": art.dek,
                 "event": SHORT.get(it.get("event_type") or "commentary", "Note")}
        if fname in known:
            # Regenerated page: refresh its entry rather than keep the old copy.
            manifest = [entry if e["file"] == fname else e for e in manifest]
        else:
            fresh.append(entry)
            known.add(fname)
        written.append(fname)
    # Newest issue on top, and within it the strongest story first.
    manifest = fresh + manifest

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_index(manifest, settings))
    return {"site": SITE, "written": written, "total": len(manifest)}
