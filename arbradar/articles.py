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
from .config import FALLBACK_BETA, OUT_DIR
from .taxonomy import EVENT_TYPES

SITE = os.path.join(OUT_DIR, "site")


class Article(BaseModel):
    headline: str = Field(description="At most 12 words. Lead with the commercial fact.")
    dek: str = Field(description="One sentence, at most 28 words, that says why a practitioner cares.")
    paragraphs: List[str] = Field(description="Two or three paragraphs, 130-180 words in total. "
                                              "Only facts present in the source. No hedging.")
    angle: str = Field(description="One sentence naming where the mandate is and who may still need counsel.")


ARTICLE_SYSTEM = """You write short standalone pieces for arbitration practitioners who are looking \
for cases to take. The reader is a partner. They know the law; they want the commercial fact, the \
procedural posture, and where the work is. Never invent a party, amount, treaty or firm that is not \
in the source. If counsel is on record, say so plainly - it tells the reader the seat is taken."""


def _slug(text: str, date: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:70]
    return "{}-{}".format(date, s)


def _facts(it: Dict[str, Any]) -> List[List[str]]:
    ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {})
    rows = [["Signal", ev.get("label", "")]]
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
    rows.append(["Published", str(it.get("published_at") or "")[:10]])
    return rows


def _template_article(it: Dict[str, Any]) -> Article:
    ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {})
    summary = re.sub(r"\s+", " ", it.get("summary") or "").strip()
    paras = [p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z])", summary) if p]
    body = [" ".join(paras[:2])] if paras else [it.get("title", "")]
    if len(paras) > 2:
        body.append(" ".join(paras[2:5]))
    counsel = it.get("counsel") or []
    angle = (it.get("why_it_matters") or ev.get("why", ""))
    if counsel:
        angle += " Counsel already on record: {}.".format(", ".join(counsel[:3]))
    elif (it.get("source_tier") or 2) == 1:
        angle += " No counsel is listed on the record yet."
    return Article(headline=it.get("title", "")[:120], dek=ev.get("why", ""),
                   paragraphs=body, angle=angle.strip())


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
:root{--blue-50:oklch(97% .015 270);--blue-500:#4D68F9;--blue-600:oklch(52% .21 270);
--n0:#fff;--n50:oklch(97.5% .005 270);--n100:oklch(95% .007 270);--n200:oklch(90.5% .011 270);
--n500:oklch(55% .02 270);--n600:oklch(46% .022 270);--n900:oklch(21% .03 272);
--page:oklch(98.4% .004 270);--card:var(--n0);--sunken:var(--n50);--soft:var(--blue-50);
--ink:var(--n900);--ink2:var(--n600);--mute:var(--n500);--link:var(--blue-600);
--hair:var(--n100);--line:var(--n200);--accent:var(--blue-500);
--display:"Source Serif 4",Georgia,"Times New Roman",serif;
--sans:"Hanken Grotesk",-apple-system,"Segoe UI",sans-serif;
--mono:"IBM Plex Mono","SF Mono",Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--page:oklch(15.5% .028 272);--card:oklch(19.5% .03 272);--sunken:oklch(23% .03 272);
--soft:oklch(26% .06 270);--ink:oklch(96% .008 270);--ink2:oklch(78% .02 270);
--mute:oklch(64% .022 270);--link:oklch(78% .115 270);--hair:oklch(26% .028 272);
--line:oklch(31% .03 272);--accent:#7d90ff}}
:root[data-theme="dark"]{--page:oklch(15.5% .028 272);--card:oklch(19.5% .03 272);
--sunken:oklch(23% .03 272);--soft:oklch(26% .06 270);--ink:oklch(96% .008 270);
--ink2:oklch(78% .02 270);--mute:oklch(64% .022 270);--link:oklch(78% .115 270);
--hair:oklch(26% .028 272);--line:oklch(31% .03 272);--accent:#7d90ff}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font-family:var(--sans);
font-size:1rem;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--link)}
.wrap{max-width:720px;margin:0 auto;padding:40px 24px 80px}
.mast{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap;
padding-bottom:14px;border-bottom:2px solid var(--ink);margin-bottom:28px}
.brand{font-size:.75rem;letter-spacing:.14em;text-transform:uppercase;font-weight:700;color:var(--ink);text-decoration:none}
.brand span{color:var(--mute);font-weight:500}
.mast .date{font-family:var(--mono);font-size:.75rem;color:var(--mute)}
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
            "<title>{t}</title><meta name=\"description\" content=\"{d}\">"
            "<meta property=\"og:title\" content=\"{t}\"><meta property=\"og:description\" content=\"{d}\">"
            "{f}<style>{c}</style></head><body><div class=\"wrap\">{b}</div></body></html>").format(
        t=html.escape(title), d=html.escape(desc[:200]), f=FONTS, c=CSS, b=body)


def render_article(a: Article, it: Dict[str, Any], settings, date: str) -> str:
    ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {})
    facts = "".join("<div><dt>{}</dt><dd>{}</dd></div>".format(html.escape(k), html.escape(v))
                    for k, v in _facts(it) if v)
    paras = "".join("<p>{}</p>".format(html.escape(p)) for p in a.paragraphs)
    srcs = [(it.get("source") or "source", it.get("url"))] + [
        ((x.get("source") or "source").replace("Google News / ", ""), x.get("url"))
        for x in (it.get("also") or [])[:4]]
    src_html = "".join('<a href="{}" rel="noopener">{}</a>'.format(html.escape(u or "#"), html.escape(s))
                       for s, u in srcs if u)
    body = """<header class="mast"><a class="brand" href="index.html">{name} <span>· by CaseLens</span></a>
<span class="date">{date}</span></header>
<div class="eyebrow">{ev}</div>
<h1>{h}</h1>
<p class="dek">{dek}</p>
<dl class="facts">{facts}</dl>
<div class="body">{paras}</div>
<div class="angle"><b>The angle</b>{angle}</div>
<div class="src">Sources: {src}</div>""".format(
        name=html.escape(settings.newsletter_name), date=html.escape(date),
        ev=html.escape(ev.get("label", "")), h=html.escape(a.headline), dek=html.escape(a.dek),
        facts=facts, paras=paras, angle=html.escape(a.angle), src=src_html)
    return _page(a.headline, body, a.dek, settings.newsletter_name)


def render_index(entries: List[Dict[str, Any]], settings) -> str:
    items = "".join("""<div class="item"><div class="d">{d}</div><div>
<a class="h" href="{f}">{h}</a><p>{dek}</p><span class="pill">{ev}</span></div></div>""".format(
        d=html.escape(e["date"]), f=html.escape(e["file"]), h=html.escape(e["headline"]),
        dek=html.escape(e["dek"]), ev=html.escape(e["event"]))
        for e in entries)
    body = """<header class="mast"><a class="brand" href="index.html">{name} <span>· by CaseLens</span></a>
<span class="date">{n} pieces</span></header>
<h1>{tag}</h1>
<p class="dek">Short, sourced pieces on where arbitration work is opening up. Each stands alone and can be shared.</p>
<div class="list">{items}</div>""".format(name=html.escape(settings.newsletter_name), n=len(entries),
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
    stories = pipeline.cluster([db.row_to_dict(r) for r in rows])[:limit]

    os.makedirs(SITE, exist_ok=True)
    manifest_path = os.path.join(SITE, "manifest.json")
    manifest: List[Dict[str, Any]] = []
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path, encoding="utf-8"))
    known = {e["file"] for e in manifest}

    written = []
    fresh: List[Dict[str, Any]] = []
    for it in stories:
        art = write_article(it, settings.editor_model) if (use_llm and settings.use_llm) else None
        art = art or _template_article(it)
        fname = _slug(art.headline, date) + ".html"
        with open(os.path.join(SITE, fname), "w", encoding="utf-8") as fh:
            fh.write(render_article(art, it, settings, date))
        entry = {"file": fname, "date": date, "headline": art.headline, "dek": art.dek,
                 "event": EVENT_TYPES.get(it.get("event_type") or "commentary", {}).get("label", "")}
        if fname not in known:
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
