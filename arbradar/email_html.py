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
from .sources.editions import LANG_NAMES

INK, INK2, MUTE = "#131726", "#535865", "#6d717e"
LINE, HAIR, SUNKEN, LINK = "#dddfe7", "#eceef3", "#f5f7fa", "#3e55df"
SERIF = "Georgia,'Times New Roman',Times,serif"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

P = ('font-family:{sans};font-size:{size}px;line-height:{lh};color:{color};margin:0 0 {mb}px;'
     'mso-line-height-rule:exactly;')


def esc(s: Any) -> str:
    return html.escape(str(s or ""))


def date_label(iso: str) -> str:
    d = dt.date.fromisoformat(iso[:10])
    return "{} {} {}".format(d.day, d.strftime("%B"), d.year)


def title_of(it: Dict[str, Any]) -> str:
    return it.get("title_en") or it.get("title") or ""


def summary_of(it: Dict[str, Any]) -> str:
    text = re.sub(r"\s+", " ", it.get("summary_en") or it.get("summary") or "").strip()
    t = (it.get("title") or "").strip().lower()
    return "" if (t and text.lower().startswith(t[:40])) else text


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
    return ('<h2 style="font-family:{sans};font-size:11px;letter-spacing:2px;text-transform:uppercase;'
            'font-weight:700;color:{mute};{border}margin:0 0 {mb}px;">{t}</h2>').format(
        sans=SANS, mute=MUTE, border=border, mb=mb, t=esc(text))


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


def story(it: Dict[str, Any], n: int, lead: bool, site_url: str, date: str) -> str:
    href = it.get("site_link") or it.get("url") or "#"
    size, lh, mb = (24, 1.2, 8) if lead else (19, 1.3, 6)
    head = ('<h3 id="s{n}" style="font-family:{serif};font-size:{size}px;line-height:{lh};font-weight:bold;'
            'color:{ink};margin:0 0 {mb}px;"><a href="{href}" style="color:{ink};text-decoration:none;">{t}</a></h3>'
            ).format(n=n, serif=SERIF, size=size, lh=lh, ink=INK, mb=mb, href=esc(href), t=esc(title_of(it)))
    body = summary_of(it)
    body_html = p(esc(body[:700 if lead else 420]), size=16 if lead else 15, lh=1.55, mb=8) if body else ""
    sep = "" if lead else 'border-bottom:1px solid {};'.format(HAIR)
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
            '<tr><td style="padding:{pt}px 0 18px;{sep}">{head}{body}{meta}</td></tr></table>').format(
        pt=4 if lead else 18, sep=sep, head=head, body=body_html, meta=meta_line(it))


def brief(items: List[Dict[str, Any]]) -> str:
    rows = []
    for it in items:
        ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {}).get("label", "")
        rows.append('<li style="{}">{} <span style="color:{};">&middot; {}</span></li>'.format(
            P.format(sans=SANS, size=15, lh=1.5, color=INK, mb=8), a(it.get("url") or "#", title_of(it)[:120], color=INK),
            MUTE, esc(ev)))
    return '<ul style="padding-left:18px;margin:0;">{}</ul>'.format("".join(rows))


# ---- records: date | text rows ------------------------------------------------
_DOCKET = re.compile(r"^(?:New ICSID case registered: )?(?P<case>.+?) \(ICSID Case No\. (?P<ref>[^)]+)\)(?::\s*(?P<step>.*))?$")


def _docket_parts(it: Dict[str, Any]):
    m = _DOCKET.match(title_of(it))
    if not m:
        return title_of(it), "", ""
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

    # In this issue: scan list linking to anchors
    toc = "".join('<li style="{}"><a href="#s{}" style="color:{};text-decoration:none;">{}</a></li>'.format(
        P.format(sans=SANS, size=15, lh=1.45, color=INK, mb=6), i, INK, esc(title_of(it)[:110]))
        for i, it in enumerate([lead] + devs, start=1))

    mark_src = "{}/caselens-mark.png".format(site_url) if site_url else None
    if not mark_src:
        with open(os.path.join(ROOT, "assets", "caselens-mark-64.png"), "rb") as fh:
            mark_src = "data:image/png;base64," + base64.b64encode(fh.read()).decode()

    sources = sorted({(it.get("source") or "").replace("Google News / ", "") for it in items} - {""})
    unsubscribe = getattr(settings, "unsubscribe_url", "") or "mailto:{}?subject=unsubscribe".format(
        (settings.smtp or {}).get("from") or "newsletter@caselens.tech")

    sections = []
    sections.append(label("In this issue", top=False) + '<ol style="padding-left:20px;margin:0 0 26px;">{}</ol>'.format(toc))
    sections.append(label("Lead") + story(lead, 1, True, site_url, date))
    if devs:
        sections.append(label("Developments", mb=0) + "".join(story(it, i, False, site_url, date) for i, it in enumerate(devs, start=2)))
    if briefs:
        sections.append(label("In brief") + brief(briefs))
    for key, heading in (("docket", "From the ICSID docket"), ("disclosures", "Company disclosures"),
                         ("courts", "In the US courts")):
        rows = (extras or {}).get(key) or []
        if rows:
            sections.append(label(heading, mb=4) + record_rows(key, rows))

    body = "".join('<tr><td style="padding:0 0 30px;">{}</td></tr>'.format(sec) for sec in sections)

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
  <tr><td style="padding:0 0 12px;border-bottom:2px solid {ink};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="font-family:{serif};font-size:22px;line-height:1;font-weight:bold;letter-spacing:-0.2px;color:{ink};">{name}</td>
      <td align="right" style="font-family:{sans};font-size:13px;color:{mute};white-space:nowrap;">{dl}</td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:22px 0 26px;">
    <div style="font-family:{sans};font-size:15px;line-height:1.5;color:{ink2};">{tagline}</div>
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
