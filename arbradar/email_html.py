"""The issue as email HTML, built from structured data.

Everything here is chosen for a partner reading on a phone in a mail client:
a 600px column, a type scale that holds at arm's length, an "In this issue"
list to scan before reading, dated two-column records, and nothing a mail
client can break - tables, inline hex styles, Georgia and the system sans.

Scale: 11 labels, 13 meta, 15 body, 16 lead body, 19 headlines, 24 lead, 22 masthead.
"""
import base64
import datetime as dt
import html
import os
import re
from typing import Any, Dict, List, Optional

from .config import ROOT
from .taxonomy import EVENT_TYPES
from .pipeline import is_paywall
from .sources.editions import LANG_NAMES

INK, INK2, MUTE = "#131726", "#535865", "#6d717e"
LINE, HAIR, SUNKEN, LINK = "#dddfe7", "#eceef3", "#f5f7fa", "#3e55df"
SERIF = "Georgia,'Times New Roman',Times,serif"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

P = ('font-family:{sans};font-size:{size}px;line-height:{lh};color:{color};margin:0 0 {mb}px;'
     'mso-line-height-rule:exactly;')

# One or two words above the headline. That is the whole "why it is here".
SHORT = {"notice_of_intent": "Notice of dispute", "s1782_application": "§1782 application",
         "new_case_filed": "New case", "enforcement_action": "Enforcement", "annulment_setaside": "Annulment",
         "state_measure": "State measure", "distress_event": "State measure", "award_issued": "Award",
         "treaty_action": "Treaty", "funding": "Funding", "tribunal_constituted": "Tribunal",
         "lateral_move": "Move", "counsel_tender": "Tender for counsel", "commentary": "Note"}


def esc(s: Any) -> str:
    return html.escape(str(s or ""))


def date_label(iso: str) -> str:
    d = dt.date.fromisoformat(iso[:10])
    return "{} {} {}".format(d.day, d.strftime("%B"), d.year)


def title_of(it: Dict[str, Any]) -> str:
    return it.get("title_en") or it.get("title") or ""


def summary_of(it: Dict[str, Any]) -> str:
    raw = html.unescape(re.sub(r"<[^>]+>", " ", it.get("summary_en") or it.get("summary") or ""))
    text = re.sub(r"\s+", " ", raw).replace("\xa0", " ").strip()
    t = (it.get("title") or "").strip().lower()
    return "" if (is_paywall(text) or (t and text.lower().startswith(t[:40]))) else text


def firms(it: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for c in it.get("counsel") or []:
        f = c.split(",")[0].strip()
        if f and f not in out:
            out.append(f)
    return out


def p(text: str, size=15, lh=1.55, color=INK, mb=10) -> str:
    return '<p style="{}">{}</p>'.format(P.format(sans=SANS, size=size, lh=lh, color=color, mb=mb), text)


def a(href: str, text: str, color=LINK, weight="normal") -> str:
    return '<a href="{}" style="color:{};text-decoration:underline;font-weight:{};">{}</a>'.format(
        esc(href), color, weight, esc(text))


def label(text: str, mb=10, top=True) -> str:
    border = 'border-top:1px solid {};padding-top:22px;'.format(LINE) if top else ''
    return ('<h2 style="font-family:{sans};font-size:13px;letter-spacing:1.5px;text-transform:uppercase;'
            'font-weight:700;color:{ink};{border}margin:0 0 {mb}px;">{t}</h2>').format(
        sans=SANS, ink=INK, border=border, mb=mb, t=esc(text))


def meta_line(it: Dict[str, Any]) -> str:
    ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {})
    bits = ['<span style="color:{};font-weight:700;">{}</span>'.format(INK2, esc(ev.get("label", "")))]
    if (it.get("lang") or "en") != "en":
        bits.append(esc("{}-language press".format(LANG_NAMES.get(it["lang"], it["lang"]))))
    if it.get("institution"):
        bits.append(esc(it["institution"]))
    if it.get("treaty"):
        bits.append(esc(it["treaty"]))
    if it.get("amount_usd"):
        bits.append("US${:,.0f}m".format(it["amount_usd"] / 1e6))
    f = firms(it)
    if f:
        bits.append("counsel: " + esc(", ".join(f[:4])))
    elif (it.get("source_tier") or 2) == 1:
        bits.append('<em style="color:{};">no counsel on record</em>'.format(MUTE))
    src = (it.get("source") or "source").replace("Google News / ", "")
    bits.append(a(it.get("url") or "#", src))
    line = " &middot; ".join(bits)
    also = it.get("also") or []
    if also:
        line += "<br>also: " + ", ".join(
            a(x["url"], (x.get("source") or "source").replace("Google News / ", "")) for x in also[:5] if x.get("url"))
    return p(line, size=13, lh=1.5, color=MUTE, mb=0)


def who(it: Dict[str, Any]) -> str:
    """Parties from the record where we have one; otherwise the names the text
    contains, labelled as such - a press headline does not say who is suing whom."""
    cl = [c for c in (it.get("claimants") or []) if c]
    rs = [r for r in (it.get("respondents") or []) if r]
    named = [s for s in (it.get("states") or []) if s]
    if cl and rs:
        return "{} v. {}".format(", ".join(cl[:2]), ", ".join(rs[:2]))
    if rs:
        return "State: " + ", ".join(rs[:2])
    if cl and named:
        return "{}; State named: {}".format(", ".join(cl[:2]), ", ".join(named[:2]))
    if cl:
        return ", ".join(cl[:3])
    if named:
        return "Named: " + ", ".join(named[:3])
    return ""


def _clip(text: str, n: int) -> str:
    text = text.strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "\u2026"


def what(it: Dict[str, Any]) -> str:
    ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {}).get("label", "")
    text = summary_of(it)
    if it.get("source") == "ICSID docket":
        m = re.search(r"Latest step, [^:]+: (.+?)\.?$", text)
        if m:
            return _clip(m.group(1), 140)
        t = re.search(r"under the ([^.]+)\.", text)
        return "Case registered at ICSID" + (" under the " + t.group(1) if t else "")
    if text:
        first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
        return "{}: {}".format(ev, _clip(first.rstrip("."), 120))
    return ev


def facts(it: Dict[str, Any]) -> str:
    """The four questions, answered in the same place every time."""
    rows = []
    when = str(it.get("published_at") or "")[:10]
    try:
        when_label = date_label(when)
    except ValueError:
        when_label = ""
    why = it.get("flag_reason") or ""
    if why.startswith("matched"):
        why = "{}: {}".format((it.get("source") or "press").replace("Google News / ", ""), why)
    for k, v in (("Who", who(it)), ("When", when_label), ("What", what(it)), ("Why flagged", why)):
        if not v:
            continue
        rows.append(
            '<tr><td valign="top" style="font-family:{sans};font-size:10px;letter-spacing:1.5px;text-transform:uppercase;'
            'font-weight:700;color:{mute};padding:3px 12px 3px 0;white-space:nowrap;width:74px;">{k}</td>'
            '<td valign="top" style="font-family:{sans};font-size:13px;line-height:1.45;color:{ink};padding:3px 0;">{v}</td></tr>'.format(
                sans=SANS, mute=MUTE, ink=INK, k=esc(k), v=esc(v)))
    if not rows:
        return ""
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{bg}" '
            'style="background-color:{bg};margin:8px 0 12px;"><tr><td style="padding:8px 12px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>'
            '</td></tr></table>').format(bg=SUNKEN, rows="".join(rows))


def _when(it: Dict[str, Any]) -> str:
    try:
        d = dt.date.fromisoformat(str(it.get("published_at") or "")[:10])
        return "{} {}".format(d.day, d.strftime("%B"))
    except ValueError:
        return ""


def story(it: Dict[str, Any], n: int, lead: bool, site_url: str, date: str) -> str:
    """Headline, one paragraph, source. The shape of every good legal newsletter."""
    href = it.get("site_link") or it.get("url") or "#"
    head = ('<h3 id="s{n}" style="font-family:{sans};font-size:21px;line-height:1.25;font-weight:700;'
            'margin:0 0 8px;"><a href="{href}" style="color:{link};text-decoration:none;">{t}</a></h3>'
            ).format(n=n, sans=SANS, href=esc(href), link=LINK, t=esc(title_of(it)))
    body = summary_of(it)
    src = (it.get("source") or "").replace("Google News / ", "")
    tail = ' <span style="color:{};">&mdash; {}</span>'.format(MUTE, esc(src)) if src else ""
    para = p(esc(_clip(body, 600)) + tail, size=16, lh=1.5, mb=0) if body else \
        p('<span style="color:{};">{}{}</span>'.format(MUTE, esc(src), (", " + _when(it)) if _when(it) else ""), size=14, lh=1.5, mb=0)
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
            '<tr><td style="padding:20px 0 22px;border-bottom:1px solid {line};">{head}{para}</td></tr></table>'
            ).format(line=LINE, head=head, para=para)


def brief(items: List[Dict[str, Any]]) -> str:
    rows = []
    for it in items:
        ev = SHORT.get(it.get("event_type") or "commentary", "Note")
        rows.append('<li style="{}">{} <span style="color:{};">&middot; {}</span></li>'.format(
            P.format(sans=SANS, size=15, lh=1.5, color=INK, mb=8), a(it.get("url") or "#", title_of(it)[:120], color=INK),
            MUTE, esc(ev)))
    return '<ul style="padding-left:18px;margin:0;">{}</ul>'.format("".join(rows))


# ---- records: date | text rows ------------------------------------------------
_DOCKET = re.compile(r"^(?:New ICSID case registered: )?(?P<case>.+?) \(ICSID Case No\. (?P<ref>[^)]+)\)(?::\s*(?P<step>.*))?$")


def _docket_parts(it: Dict[str, Any]):
    t = title_of(it)
    if " \u2014 " in t:                       # "Party v. State — step"
        case, _, step = t.partition(" \u2014 ")
        return case, it.get("case_ref") or "", step[:1].upper() + step[1:]
    m = _DOCKET.match(t)
    if not m:
        return t, "", ""
    step = (m.group("step") or "").strip().rstrip(".")
    if not step and title_of(it).startswith("New ICSID case registered"):
        step = "Registered"
    return m.group("case"), m.group("ref"), step


def record_rows(kind: str, items: List[Dict[str, Any]]) -> str:
    rows = []
    for it in items:
        when = str(it.get("published_at") or "")[:10]
        try:
            dlabel = dt.date.fromisoformat(when).strftime("%-d %b")
        except ValueError:
            dlabel = ""
        if kind == "docket":
            case, ref, step = _docket_parts(it)
            main = '<b style="font-weight:700;">{}</b>'.format(esc(case))
            if step:
                main += " &mdash; " + esc(step)
            tail = esc(ref)
        elif kind == "disclosures":
            t = title_of(it)
            filer, _, rest = t.partition(" discloses ")
            main = '<b style="font-weight:700;">{}</b> {}'.format(esc(filer), esc(("discloses " + rest) if rest else ""))
            tail = ""
        else:
            t = title_of(it)
            case, _, court = t.partition(" (")
            main = '<b style="font-weight:700;">{}</b>'.format(esc(case))
            tail = esc(court.rstrip(")"))
        rows.append(
            '<tr><td valign="top" style="font-family:{mono};font-size:11px;line-height:1.5;color:{mute};'
            'padding:7px 10px 7px 0;white-space:nowrap;width:52px;">{d}</td>'
            '<td valign="top" style="font-family:{sans};font-size:14px;line-height:1.5;color:{ink};'
            'padding:7px 0;border-bottom:1px solid {hair};">{main}{tail}</td></tr>'.format(
                mono=MONO, mute=MUTE, sans=SANS, ink=INK, hair=HAIR, d=esc(dlabel),
                main='<a href="{}" style="color:{};text-decoration:none;">{}</a>'.format(esc(it.get("url") or "#"), INK, main),
                tail=(' <span style="font-family:{};font-size:11px;color:{};">{}</span>'.format(MONO, MUTE, tail) if tail else "")))
    return '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{}</table>'.format("".join(rows))


def build(items: List[Dict[str, Any]], extras: Dict[str, List[Dict[str, Any]]], settings, date: str) -> Dict[str, str]:
    """Returns {"html": ..., "subject": ..., "preheader": ...}."""
    name = settings.newsletter_name
    site_url = (getattr(settings, "site_url", "") or "").rstrip("/")
    dl = date_label(date)
    starters = ("notice_of_intent", "new_case_filed", "counsel_tender", "s1782_application", "state_measure")
    lead = next((it for it in items[:5] if it.get("event_type") in starters), items[0])
    rest = [it for it in items if it is not lead]
    devs, briefs = rest[:6], rest[6:9]

    subject = "{} · {} — {}".format(name, dl, title_of(lead)[:70].rstrip(" :,-"))
    preheader = " · ".join([title_of(lead)] + [title_of(it) for it in devs[:2]])[:180]

    mark_src = "{}/caselens-mark.png".format(site_url) if site_url else None
    if not mark_src:
        with open(os.path.join(ROOT, "assets", "caselens-mark-64.png"), "rb") as fh:
            mark_src = "data:image/png;base64," + base64.b64encode(fh.read()).decode()

    sources = sorted({(it.get("source") or "").replace("Google News / ", "") for it in items} - {""})
    unsubscribe = getattr(settings, "unsubscribe_url", "") or "mailto:{}?subject=unsubscribe".format(
        (settings.smtp or {}).get("from") or "newsletter@caselens.tech")

    sections = []
    stories = [lead] + devs + briefs
    sections.append("".join(story(it, i, i == 1, site_url, date) for i, it in enumerate(stories, start=1)))
    for key, heading in (("docket", "From the ICSID docket"), ("disclosures", "Company disclosures"),
                         ("courts", "In the US courts")):
        rows = (extras or {}).get(key) or []
        if rows:
            sections.append(label(heading, mb=4) + record_rows(key, rows))

    body = "".join('<tr><td style="padding:0 0 26px;">{}</td></tr>'.format(sec) for sec in sections)

    html_doc = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">
<title>{title}</title>
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
<style>
:root{{color-scheme:light;supported-color-schemes:light}}
body{{margin:0;padding:0;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%}}
table{{border-collapse:collapse}} img{{border:0;outline:none;text-decoration:none}}
a{{color:{link}}}
@media only screen and (max-width:620px){{
  .wrap{{padding:22px 18px !important}}
  .h-lead{{font-size:22px !important}}
}}
</style>
</head>
<body bgcolor="#ffffff" style="margin:0;padding:0;background-color:#ffffff;">
<div style="display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;color:#ffffff;opacity:0;">{preheader}&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" style="background-color:#ffffff;">
<tr><td align="center" class="wrap" style="padding:32px 20px;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;margin:0 auto;">
  <tr><td style="padding:0 0 14px;border-bottom:1px solid {ink};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="font-family:{sans};font-size:24px;line-height:1;font-weight:700;letter-spacing:-0.3px;color:{ink};">{name}</td>
      <td align="right" style="font-family:{sans};font-size:15px;color:{mute};white-space:nowrap;">{dl}</td>
    </tr></table>
  </td></tr>
  {body}
  <tr><td style="padding:22px 0 0;border-top:1px solid {line};">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="padding-right:10px;vertical-align:middle;"><a href="https://caselens.tech"><img src="{mark}" width="32" height="32" alt="CaseLens" style="border:0;display:block;"></a></td>
      <td style="vertical-align:middle;font-family:{sans};font-size:13px;line-height:1.35;color:{ink};">
        <span style="font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:600;color:{mute};">Published by</span><br>
        <a href="https://caselens.tech" style="font-size:15px;font-weight:700;color:{ink};text-decoration:none;">CaseLens</a></td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:16px 0 0;font-family:{sans};font-size:12px;line-height:1.6;color:{mute};">
    Compiled from {sources}. Verify against the underlying record before relying on any item.<br>
    You are receiving {name} because you asked for it. <a href="{unsub}" style="color:{mute};">Unsubscribe</a>.
  </td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table>
</body></html>""".format(
        title=esc(subject), preheader=esc(preheader), link=LINK, ink=INK, ink2=INK2, mute=MUTE, line=LINE,
        serif=SERIF, sans=SANS, name=esc(name), dl=esc(dl), tagline=esc(settings.tagline), body=body,
        mark=mark_src, sources=esc(", ".join(sources) or "primary sources"), unsub=esc(unsubscribe))
    return {"html": html_doc, "subject": subject, "preheader": preheader}
