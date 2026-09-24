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


def _nice(date: str) -> str:
    try:
        d = dt.date.fromisoformat(date[:10])
        return "{} {} {}".format(d.day, d.strftime("%B"), d.year)
    except ValueError:
        return date


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
    summary = html.unescape(re.sub(r"<[^>]+>", " ", it.get("story") or it.get("summary_en") or it.get("summary") or ""))
    summary = re.sub(r"\s+", " ", summary).replace("\xa0", " ").strip()
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
.brand{font-family:var(--sans);font-size:1.375rem;font-weight:700;letter-spacing:-.01em;color:var(--ink);text-decoration:none}
.foot{margin-top:40px;padding-top:22px;border-top:1px solid var(--line)}
.footnav{font-size:.8125rem;margin:0 0 16px}.footnav a{color:var(--mute);text-decoration:none;margin-right:16px}.footnav a:hover{color:var(--link)}
.pub{display:inline-flex;align-items:center;gap:12px;text-decoration:none;color:var(--ink)}
.pub span{display:flex;flex-direction:column;font-weight:700;font-size:1rem;line-height:1.2}
.pub small{font-size:.65rem;letter-spacing:.14em;text-transform:uppercase;color:var(--mute);font-weight:600;margin-bottom:2px}
.pub:hover{color:var(--link)}
.mast .date{font-size:.8125rem;color:var(--mute);margin-left:auto;text-decoration:none}
.mast a.date:hover{color:var(--link)}
.eyebrow{font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);font-weight:600}
h1{font-family:var(--sans);font-size:1.5rem;line-height:1.2;letter-spacing:-.01em;
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
.item .d{font-size:.7rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);padding-top:8px}
.item .meta{margin-top:6px;font-size:.8125rem}.item .meta a{color:var(--mute);text-decoration:none}.item .meta a:hover{color:var(--link)}
.stories{display:flex;flex-direction:column}
.story{padding:20px 0 22px;border-bottom:1px solid var(--line)}
.story.lead{padding-top:6px}
.story h2{font-family:var(--sans);font-size:1.125rem;line-height:1.3;font-weight:700;letter-spacing:-.005em;margin:0 0 6px;text-wrap:balance}
.story h2 a{color:var(--ink);text-decoration:none}.story h2 a:hover{color:var(--link)}
.story p{margin:0;font-size:1rem;line-height:1.5;color:var(--ink);max-width:64ch}
.story .tail{color:var(--mute);white-space:nowrap}.story .tail a{color:var(--mute)}
.days{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 26px}
.days a{font-size:.8125rem;font-weight:600;padding:5px 12px;border-radius:999px;border:1px solid var(--line);color:var(--ink2);text-decoration:none}
.days a:hover{border-color:var(--ink);color:var(--ink)}.days a[aria-current]{background:var(--ink);color:#fff;border-color:var(--ink)}
.sec{font-size:.75rem;letter-spacing:.12em;text-transform:uppercase;color:var(--mute);margin:38px 0 4px;font-weight:600}
.record .r{display:grid;grid-template-columns:110px 1fr;gap:12px;padding:8px 0;border-bottom:1px solid var(--hair);font-size:.9375rem;line-height:1.45}
.record .k{color:var(--mute)}.record .v{color:var(--ink)}
.voice{padding:14px 0;border-bottom:1px solid var(--hair)}.voice .who{margin:0 0 4px;font-size:.875rem;color:var(--mute)}
.voice .who a{color:var(--ink);text-decoration:none;font-weight:600}.voice .who a:hover{color:var(--link)}
.voice p{margin:0;font-size:1rem;line-height:1.5;max-width:64ch}
.rec .r{display:grid;grid-template-columns:64px 1fr;gap:12px;padding:9px 0;border-bottom:1px solid var(--hair);font-size:.9375rem;line-height:1.45}
.rec .d{color:var(--mute);font-size:.8125rem;padding-top:2px;white-space:nowrap}.rec a{color:var(--ink);text-decoration:none}.rec a:hover{color:var(--link)}
.rec small{color:var(--mute);font-size:.8125rem}
.brief{padding-left:18px;margin:8px 0 0}.brief li{margin:0 0 8px}.brief a{color:var(--ink);text-decoration:none}.brief a:hover{color:var(--link)}.brief small{color:var(--mute)}
.item a.h{font-family:var(--sans);font-size:1.1875rem;font-weight:600;color:var(--ink);text-decoration:none;line-height:1.3}
.item a.h:hover{color:var(--link)}
.item p{margin:6px 0 0;color:var(--ink2);font-size:.9375rem;max-width:62ch}
.pill{display:inline-block;font-size:.7rem;font-weight:600;letter-spacing:.04em;padding:1px 8px;
border-radius:999px;background:var(--soft);color:var(--link);margin-top:8px}
@media (max-width:560px){.item{grid-template-columns:1fr;gap:4px}h1{font-size:1.625rem}.rec .r{grid-template-columns:1fr;gap:2px}}
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


FOOTER = """<footer class="foot"><nav class="footnav"><a href="index.html">Latest issue</a><a href="sources.html">The sources we check</a><a href="index.html#subscribe">Subscribe</a></nav><a href="https://caselens.tech" class="pub"><svg width="32" height="32" style="display:block;border-radius:7px" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 32 32"><g transform="translate(0.4 0.209)"><path d="M 24.514 0 L 6.686 0 C 2.993 0 0 2.993 0 6.686 L 0 24.514 C 0 28.207 2.993 31.2 6.686 31.2 L 24.514 31.2 C 28.207 31.2 31.2 28.207 31.2 24.514 L 31.2 6.686 C 31.2 2.993 28.207 0 24.514 0 Z" fill="rgb(77,104,249)"></path><path d="M 24.149 9.951 C 22.329 7.625 19.624 6.31 16.667 6.31 C 11.56 6.31 7.363 10.481 7.363 15.563 C 7.363 17.242 7.815 18.81 8.605 20.16 L 8.581 20.137 L 7.26 24.892 L 11.952 23.495 C 13.361 24.318 15.009 24.79 16.768 24.79 C 19.776 24.79 22.506 23.323 24.2 21.099 L 20.231 18.04 C 19.422 19.203 18.107 19.835 16.692 19.835 C 14.315 19.835 12.369 17.913 12.369 15.563 C 12.369 13.161 14.341 11.265 16.742 11.265 C 18.183 11.265 19.447 11.973 20.231 13.06 Z" fill="rgb(255,255,255)"></path></g></svg><span><small>Published by</small>CaseLens</span></a></footer>"""


def render_article(a: Article, it: Dict[str, Any], settings, date: str, day_href: str = None) -> str:
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
{date}</header>
<div class="eyebrow">{ev}</div>
<h1>{h}</h1>
{dek}
<div class="body">{paras}</div>
<div class="src">{src}</div>
{record}
{voices}
{foot}""".format(
        record=_record_block(it), voices=_voices_block(it),
        name=html.escape(settings.newsletter_name), foot=FOOTER,
        date=('<a class="date" href="{}">{}</a>'.format(html.escape(day_href), html.escape(_nice(date))) if day_href
              else '<span class="date">{}</span>'.format(html.escape(_nice(date)))),
        ev=html.escape(ev.get("label", "")), h=html.escape(__import__("arbradar.style", fromlist=["headline"]).headline(a.headline)),
        dek='<p class="dek">{}</p>'.format(html.escape(a.dek)) if (a.dek and a.dek not in " ".join(a.paragraphs)) else "",
        paras=paras, src=src_html)
    return _page(a.headline, body, a.dek, settings.newsletter_name)


def _record_block(it: Dict[str, Any]) -> str:
    """The facts the record carries, as they stand: parties, State, forum,
    treaty, reference, counsel, amount. Nothing inferred."""
    rows = []
    def add(label, value):
        if isinstance(value, str) and value.strip() in ("[]", "{}", "null"):
            value = ""
        if isinstance(value, list):
            value = [v for v in value if v]
        if value:
            rows.append('<div class="r"><span class="k">{}</span><span class="v">{}</span></div>'.format(
                html.escape(label), html.escape(value if isinstance(value, str) else ", ".join(str(v) for v in value if v))))
    add("Claimant", it.get("claimants"))
    add("Respondent", it.get("respondents"))
    add("State", it.get("states"))
    add("Forum", it.get("institution"))
    add("Instrument", it.get("treaty"))
    add("Reference", it.get("case_ref"))
    add("Counsel", it.get("counsel"))
    add("Tribunal", it.get("arbitrators"))
    add("Amount", "US${:,.0f} million".format(it["amount_usd"] / 1e6) if it.get("amount_usd") else "")
    if not rows:
        return ""
    return '<h2 class="sec">On the record</h2><div class="record">{}</div>'.format("".join(rows))


def _voices_block(it: Dict[str, Any]) -> str:
    """What each cited outlet says, in its own words, with the link. The
    explanation above is built from these; here they stand on their own."""
    from .style import sentences
    voices = []
    own = html.unescape(re.sub(r"<[^>]+>", " ", it.get("summary") or ""))
    own = re.sub(r"\s+", " ", own).strip()
    own_outlet = (it.get("source") or "").replace("Google News / ", "")
    if own and not own.lower().startswith((it.get("title") or "").lower()[:30]):
        voices.append((own_outlet, it.get("url"), str(it.get("published_at") or "")[:10], sentences(own, 90)))
    for c in it.get("corroboration") or []:
        if not isinstance(c, dict) or not c.get("url"):
            continue
        text = sentences(c.get("snippet") or "", 90)
        if len(text.split()) < 8:
            text = c.get("title") or ""
        voices.append((c.get("source") or "source", c["url"], (c.get("published_at") or "")[:10], text))
    if not voices:
        return ""
    items = "".join(
        '<article class="voice"><p class="who"><a href="{}" rel="noopener">{}</a>{}</p><p>{}</p></article>'.format(
            html.escape(u), html.escape(o), (" \u00b7 " + html.escape(d)) if d else "", html.escape(t))
        for o, u, d, t in voices)
    return '<h2 class="sec">What the sources say</h2><div class="voices">{}</div>'.format(items)


def _signup(settings) -> str:
    """The subscribe box. Posts to the list provider when one is configured; until
    then it opens a prepared email to the address in signup_email, so sign-ups
    are collected from day one."""
    action = (getattr(settings, "signup_url", "") or "").strip()
    field = (getattr(settings, "signup_field", "") or "email").strip()
    mailto = (getattr(settings, "signup_email", "") or "").strip()
    if not action and not mailto:
        return ""
    name = html.escape(settings.newsletter_name)
    css = """<style>
.signup{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:16px 18px;margin:0 0 30px;
background:var(--sunken);border:1px solid var(--hair);border-radius:12px}
.signup label{flex:1 1 100%;font-weight:600;font-size:.9375rem}
.signup input{flex:1 1 220px;font:inherit;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink)}
.signup input:focus{outline:2px solid var(--accent);outline-offset:1px}
.signup button{font:inherit;font-weight:600;padding:10px 16px;border:0;border-radius:8px;background:var(--accent);color:#fff;cursor:pointer}
.signup button:hover{filter:brightness(.94)}
.signup small{flex:1 1 100%;color:var(--mute);font-size:.8125rem}
</style>
"""
    if action:
        return css + """<form class="signup" id="subscribe" action="{action}" method="post"><label for="signup-email">Get {name} by email</label>
<input id="signup-email" type="email" name="{field}" placeholder="you@firm.com" autocomplete="email" required>
<button type="submit">Subscribe</button><small>Free. One email per issue. Unsubscribe in one click.</small></form>""".format(
            action=html.escape(action), field=html.escape(field), name=name)
    subject = "Subscribe to " + settings.newsletter_name
    return css + """<form class="signup" id="subscribe" onsubmit="var e=this.elements['email'].value;location.href='mailto:{to}?subject={subj}&body='+encodeURIComponent('Please add '+e+' to {name}.');return false;">
<label for="signup-email">Get {name} by email</label>
<input id="signup-email" type="email" name="email" placeholder="you@firm.com" autocomplete="email" required>
<button type="submit">Subscribe</button><small>Free. One email per issue. Or write to <a href="mailto:{to}?subject={subj}">{to}</a>.</small></form>""".format(
        to=html.escape(mailto), subj=html.escape(subject.replace(" ", "%20")), name=name)


def build(conn, settings, limit: int = 6, use_llm: bool = True) -> Dict[str, Any]:
    """Render the whole site from the saved days (see site.py)."""
    from . import site
    return site.build(settings, use_llm=use_llm)
