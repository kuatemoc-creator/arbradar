"""Render an issue to Markdown and to email-safe HTML.

Email HTML is deliberately old-fashioned: tables, inline styles, no flexbox or
grid. Outlook still renders with Word's engine and will mangle anything modern.
"""
import datetime as dt
import html
import re
import os
from typing import Any, Dict, List

import markdown as md

import base64

from .config import OUT_DIR, ROOT
from .taxonomy import EVENT_TYPES
from .pipeline import is_paywall
from .sources.editions import LANG_NAMES

# CaseLens light palette as plain hex. Mail clients do not understand CSS
# variables, oklch, web fonts, flexbox or dark-mode media queries, so the
# email is one light theme, tables and inline styles only.
INK, INK2, MUTE = "#131726", "#535865", "#6d717e"
LINE, HAIR, SUNKEN, LINK, ACCENT = "#dddfe7", "#eceef3", "#f5f7fa", "#3e55df", "#4D68F9"
SERIF = "Georgia,'Times New Roman',Times,serif"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def _docket_line(it: Dict[str, Any]) -> str:
    t = _title(it)
    line = "- [{}]({})".format(t[:160], it["url"])
    if (it.get("source") or "").startswith("Court:"):
        court, _, what = (it.get("flag_reason") or "").partition(": ")
        bits = [b for b in (what, court, it.get("case_ref") or "") if b]
        if bits:
            line += " \u2014 " + ", ".join(bits)
    elif it.get("event_type") in ("lateral_move", "appointment"):
        src = (it.get("source") or "").replace("Google News / ", "")
        line += " \u2014 " + re.sub(r"\s*\((?:Global|Sector: [^)]*)\)\s*$", "", src)
    return line


def record_sections(extras: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """Compact lists straight from the primary records: the ICSID docket, company
    disclosures, and court filings. These are the items the trade press reports
    a fraction of, days later. Nothing here is written by a model."""
    lines: List[str] = []
    order = [("docket", "From the ICSID docket"), ("disclosures", "Company disclosures"),
             ("courts", "In the courts"), ("people", "People and appointments")]
    for key, heading in order:
        rows = extras.get(key) or []
        if not rows:
            continue
        lines += ["## {}".format(heading), ""]
        for it in rows:
            lines.append(_docket_line(it))
        lines.append("")
    return lines


def fallback_markdown(items: List[Dict[str, Any]], name: str, date: str, settings=None,
                      extras: Dict[str, List[Dict[str, Any]]] = None) -> str:
    """Used when no API key is set - deterministic, no model involved."""
    lines = ["# {} - {}".format(name, date), ""]
    if not items:
        lines.append("_Nothing in this window met the threshold._")
        return "\n".join(lines)

    lines.append("{} developments this week.".format(len(items)))
    lines.append("")
    # The lead is the strongest story that starts a dispute, if one is near the top;
    # enforcement and award stories are later-stage and go below.
    starters = ("notice_of_intent", "new_case_filed", "counsel_tender", "s1782_application", "state_measure")
    lead = next((it for it in items[:5] if it.get("event_type") in starters), items[0])
    rest = [it for it in items if it is not lead]
    lines += ["## Lead", "", _headline(lead, settings, date), ""]
    if _summary(lead):
        lines += [_summary(lead)[:600], ""]
    lines += [_meta_line(lead), ""]
    if rest:
        lines += ["## Developments", ""]
        for it in rest:
            lines += [_headline(it, settings, date), ""]
            if _summary(it):
                lines += [_summary(it)[:400], ""]
            lines += [_meta_line(it), ""]
    for it in (extras or {}).get("leads") or []:
        if "## Leads" not in lines:
            lines += ["## Leads", ""]
        lines += [_headline(it, settings, date), ""]
        if _summary(it):
            lines += [_summary(it), ""]
        lines += [_meta_line(it), ""]
    for it in (extras or {}).get("enforcement") or []:
        if "## Enforcement" not in lines:
            lines += ["## Enforcement", ""]
        lines += [_headline(it, settings, date), ""]
        if _summary(it):
            lines += [_summary(it), ""]
        lines += [_meta_line(it), ""]
    if extras:
        lines += record_sections(extras)
    return "\n".join(lines)


def _title(it: Dict[str, Any]) -> str:
    return it.get("title_en") or it.get("title") or ""


def story_slug(it: Dict[str, Any], date: str) -> str:
    """Shared with the article site so the email can deep-link each story."""
    s = re.sub(r"[^a-z0-9]+", "-", _title(it).lower()).strip("-")[:70]
    return "{}-{}.html".format(date, s)


def _headline(it: Dict[str, Any], settings, date: str) -> str:
    from .config import live_site_url
    base = live_site_url(settings)
    if base:
        return "### [{}]({}/{})".format(_title(it), base, story_slug(it, date))
    return "### {}".format(_title(it))


def _summary(it: Dict[str, Any]) -> str:
    from .explain import explain
    return explain(it)


def _meta_line(it: Dict[str, Any]) -> str:
    bits = []
    if (it.get("lang") or "en") != "en":
        bits.append("{}-language press".format(LANG_NAMES.get(it["lang"], it["lang"])))
    ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {})
    if ev:
        bits.append("**{}**".format(ev.get("label")))
    if it.get("institution"):
        bits.append(it["institution"])
    if it.get("treaty"):
        bits.append(it["treaty"])
    if it.get("amount_usd"):
        bits.append("US${:,.0f}m".format(it["amount_usd"] / 1e6))
    if it.get("counsel"):
        # ICSID lists "Firm, City, Country"; the reader wants the firm.
        firms = []
        for c in it["counsel"]:
            f = c.split(",")[0].strip()
            if f and f not in firms:
                firms.append(f)
        bits.append("counsel: " + ", ".join(firms[:4]))
    elif (it.get("source_tier") or 2) == 1:
        bits.append("_no counsel on record_")   # meaningful only from a docket
    bits.append("[{}]({})".format(it.get("source") or "source", it["url"]))
    line = " · ".join(bits)
    also = it.get("also") or []
    if also:
        line += "  \nalso: " + ", ".join(
            "[{}]({})".format((a.get("source") or "source").replace("Google News / ", ""), a["url"])
            for a in also[:5])
    return line


def to_html(markdown_text: str, name: str, tagline: str, date: str,
            items: List[Dict[str, Any]], site_url: str = "") -> str:
    body = md.markdown(markdown_text, extensions=["extra", "sane_lists"])
    # The issue title is already in the masthead; drop the generated h1.
    body = re.sub(r"<h1>.*?</h1>\s*", "", body, count=1, flags=re.S)
    body = (body
            .replace("<h2>", '<h2 style="font-family:{sans};font-size:11px;letter-spacing:2px;'
                             'text-transform:uppercase;font-weight:700;color:{mute};'
                             'border-top:1px solid {line};padding-top:22px;margin:34px 0 14px;">')
            .replace("<h3>", '<h3 style="font-family:{serif};font-size:19px;line-height:1.3;'
                             'font-weight:bold;color:{ink};margin:24px 0 6px;">')
            .replace("<p>", '<p style="font-family:{sans};font-size:15px;line-height:1.6;'
                            'color:{ink};margin:0 0 12px;">')
            .replace("<ul>", '<ul style="padding-left:18px;margin:0 0 12px;">')
            .replace("<li>", '<li style="font-family:{sans};font-size:15px;line-height:1.55;'
                             'color:{ink};margin:0 0 8px;">')
            .replace("<em>", '<em style="color:{ink2};">')
            .replace("<a ", '<a style="color:{link};text-decoration:underline;" ')
            ).format(sans=SANS, serif=SERIF, ink=INK, ink2=INK2, mute=MUTE, line=LINE, link=LINK)

    sources = sorted({(it.get("source") or "").replace("Google News / ", "") for it in items} - {""})
    preheader = html.escape("{} - {}".format(tagline, date))
    # CaseLens brand, linked. The C mark comes from the site's host once there is
    # one; until then it is embedded, which Gmail's composer turns into an inline
    # attachment on paste. Mail clients never render SVG, so it is a PNG.
    base = (site_url or "").rstrip("/")
    if base:
        src = "{}/caselens-mark.png".format(base)
    else:
        with open(os.path.join(ROOT, "assets", "caselens-mark-64.png"), "rb") as fh:
            src = "data:image/png;base64," + base64.b64encode(fh.read()).decode()
    mark_lg = ('<a href="https://caselens.tech"><img src="{}" width="32" height="32" alt="CaseLens" '
               'style="border:0;display:block;"></a>'.format(src))
    brand = ('<a href="https://caselens.tech" style="font-family:{sans};font-size:15px;font-weight:700;'
             'color:{ink};text-decoration:none;letter-spacing:-0.1px;">CaseLens</a>'
             ).format(sans=SANS, ink=INK)
    return """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{title}</title>
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
<style>:root{{color-scheme:light;supported-color-schemes:light}} body{{margin:0;padding:0}} table{{border-collapse:collapse}} a{{color:{link}}}</style>
</head>
<body bgcolor="#ffffff" style="margin:0;padding:0;background-color:#ffffff;">
<div style="display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;color:#ffffff;">{preheader}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" style="background-color:#ffffff;">
<tr><td align="center" style="padding:32px 16px;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;margin:0 auto;">
  <tr><td style="padding:0 0 14px;border-bottom:2px solid {ink};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="font-family:{serif};font-size:22px;font-weight:bold;letter-spacing:-0.2px;color:{ink};">{name}</td>
      <td align="right" style="font-family:{sans};font-size:12px;color:{mute};white-space:nowrap;">{date}</td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:26px 0 4px;">
    <div style="font-family:{serif};font-size:26px;line-height:1.2;font-weight:bold;color:{ink};">{tagline}</div>
  </td></tr>
  <tr><td style="padding:0 0 8px;">{body}</td></tr>
  <tr><td style="padding:26px 0 0;border-top:1px solid {line};">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="padding-right:10px;vertical-align:middle;">{mark_lg}</td>
      <td style="vertical-align:middle;font-family:{sans};font-size:13px;line-height:1.4;color:{ink};">
        <span style="font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:600;color:{mute};">Published by</span><br>
        {brand}</td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:16px 0 0;font-family:{sans};font-size:12px;line-height:1.6;color:{mute};">
    Compiled from {sources}. Verify against the underlying record before relying on any item.
  </td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table>
</body></html>""".format(
        title=html.escape("{} - {}".format(name, date)), preheader=preheader,
        name=html.escape(name), tagline=html.escape(tagline), date=html.escape(date),
        body=body, sources=html.escape(", ".join(sources) or "primary sources"),
        brand=brand, mark_lg=mark_lg,
        sans=SANS, serif=SERIF, ink=INK, mute=MUTE, line=LINE, link=LINK)


def write_issue(markdown_text: str, items: List[Dict[str, Any]], settings,
                date: str = None, html_doc: str = None) -> Dict[str, str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    date = date or dt.date.today().isoformat()
    slug = "issue-{}".format(date)
    md_path = os.path.join(OUT_DIR, slug + ".md")
    html_path = os.path.join(OUT_DIR, slug + ".html")

    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(markdown_text)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html_doc or to_html(markdown_text, settings.newsletter_name,
                                     settings.tagline, date, items, getattr(settings, "site_url", "")))
    return {"md": md_path, "html": html_path}
