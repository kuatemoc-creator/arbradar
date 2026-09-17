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

from .config import OUT_DIR
from .taxonomy import EVENT_TYPES
from .sources.editions import LANG_NAMES

# CaseLens light palette as plain hex. Mail clients do not understand CSS
# variables, oklch, web fonts, flexbox or dark-mode media queries, so the
# email is one light theme, tables and inline styles only.
INK, INK2, MUTE = "#131726", "#535865", "#6d717e"
LINE, HAIR, SUNKEN, LINK, ACCENT = "#dddfe7", "#eceef3", "#f5f7fa", "#3e55df", "#4D68F9"
SERIF = "Georgia,'Times New Roman',Times,serif"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def fallback_markdown(items: List[Dict[str, Any]], name: str, date: str, settings=None) -> str:
    """Used when no API key is set - deterministic, no model involved."""
    lines = ["# {} - {}".format(name, date), ""]
    if not items:
        lines.append("_Nothing in this window met the threshold._")
        return "\n".join(lines)

    lines.append("{} developments this week, in order of how likely each is to lead to "
                 "new instructions.".format(len(items)))
    lines.append("")
    lead, rest = items[0], items[1:]
    lines += ["## Lead", "", _headline(lead, settings, date), "",
              _summary(lead)[:600], "", _meta_line(lead), ""]
    if rest:
        lines += ["## Where the work is", ""]
        for it in rest[:8]:
            lines += [_headline(it, settings, date), "",
                      _summary(it)[:400], "", _meta_line(it), ""]
    if len(rest) > 8:
        lines += ["## Also moving", ""]
        for it in rest[8:]:
            lines.append("- [{}]({}) - {}".format(
                _title(it)[:120], it["url"],
                EVENT_TYPES.get(it.get("event_type") or "commentary", {}).get("label", "")))
    return "\n".join(lines)


def _title(it: Dict[str, Any]) -> str:
    return it.get("title_en") or it.get("title") or ""


def story_slug(it: Dict[str, Any], date: str) -> str:
    """Shared with the article site so the email can deep-link each story."""
    s = re.sub(r"[^a-z0-9]+", "-", _title(it).lower()).strip("-")[:70]
    return "{}-{}.html".format(date, s)


def _headline(it: Dict[str, Any], settings, date: str) -> str:
    base = (getattr(settings, "site_url", "") or "").rstrip("/")
    if base:
        return "### [{}]({}/{})".format(_title(it), base, story_slug(it, date))
    return "### {}".format(_title(it))


def _summary(it: Dict[str, Any]) -> str:
    text = it.get("summary_en") or it.get("why_it_matters") or it.get("summary") or ""
    text = re.sub(r"\s+", " ", text).strip()
    title = (it.get("title") or "").strip().lower()
    if title and text.lower().startswith(title[:40]):
        ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {})
        return it.get("why_it_matters") or ev.get("why", "")
    return text


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
            items: List[Dict[str, Any]]) -> str:
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
      <td style="font-family:{sans};font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:700;color:{ink};">{name}
        <span style="color:{mute};font-weight:500;">&nbsp;&middot;&nbsp;by CaseLens</span></td>
      <td align="right" style="font-family:{sans};font-size:12px;color:{mute};white-space:nowrap;">{date}</td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:26px 0 4px;">
    <div style="font-family:{serif};font-size:26px;line-height:1.2;font-weight:bold;color:{ink};">{tagline}</div>
  </td></tr>
  <tr><td style="padding:0 0 8px;">{body}</td></tr>
  <tr><td style="padding:22px 0 0;border-top:1px solid {line};font-family:{sans};font-size:12px;line-height:1.6;color:{mute};">
    Compiled from {sources}.<br>
    Ranked by likelihood of an open mandate, not by news value. Verify against the underlying record before acting.
  </td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table>
</body></html>""".format(
        title=html.escape("{} - {}".format(name, date)), preheader=preheader,
        name=html.escape(name), tagline=html.escape(tagline), date=html.escape(date),
        body=body, sources=html.escape(", ".join(sources) or "primary sources"),
        sans=SANS, serif=SERIF, ink=INK, mute=MUTE, line=LINE, link=LINK)


def write_issue(markdown_text: str, items: List[Dict[str, Any]], settings,
                date: str = None) -> Dict[str, str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    date = date or dt.date.today().isoformat()
    slug = "issue-{}".format(date)
    md_path = os.path.join(OUT_DIR, slug + ".md")
    html_path = os.path.join(OUT_DIR, slug + ".html")

    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(markdown_text)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(to_html(markdown_text, settings.newsletter_name,
                         settings.tagline, date, items))
    return {"md": md_path, "html": html_path}
