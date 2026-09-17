"""Render an issue to Markdown and to email-safe HTML.

Email HTML is deliberately old-fashioned: tables, inline styles, no flexbox or
grid. Outlook still renders with Word's engine and will mangle anything modern.
"""
import datetime as dt
import html
import os
from typing import Any, Dict, List

import markdown as md

from .config import OUT_DIR
from .taxonomy import EVENT_TYPES

CSS_BODY = "margin:0;padding:0;background:#f4f4f2;"
WRAP = ("max-width:640px;margin:0 auto;background:#ffffff;"
        "font-family:Georgia,'Times New Roman',serif;color:#1a1a1a;")


def fallback_markdown(items: List[Dict[str, Any]], name: str, date: str) -> str:
    """Used when no API key is set - deterministic, no model involved."""
    lines = ["# {} - {}".format(name, date), ""]
    if not items:
        lines.append("_No qualifying developments in this window._")
        return "\n".join(lines)

    lines.append("{} developments ranked by how likely they are to convert into "
                 "a mandate.".format(len(items)))
    lines.append("")
    lead, rest = items[0], items[1:]
    lines += ["## Lead", "", "### {}".format(lead["title"]), "",
              (lead.get("why_it_matters") or lead.get("summary") or "")[:600], "",
              _meta_line(lead), ""]
    if rest:
        lines += ["## Where the work is", ""]
        for it in rest[:8]:
            lines += ["### {}".format(it["title"]), "",
                      (it.get("why_it_matters") or it.get("summary") or "")[:400], "",
                      _meta_line(it), ""]
    if len(rest) > 8:
        lines += ["## Also moving", ""]
        for it in rest[8:]:
            lines.append("- [{}]({}) - {}".format(
                it["title"][:120], it["url"],
                EVENT_TYPES.get(it.get("event_type") or "commentary", {}).get("label", "")))
    return "\n".join(lines)


def _meta_line(it: Dict[str, Any]) -> str:
    bits = []
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
        bits.append("counsel: " + ", ".join(it["counsel"][:3]))
    elif (it.get("source_tier") or 2) == 1:
        bits.append("_no counsel on record_")   # meaningful only from a docket
    bits.append("[{}]({})".format(it.get("source") or "source", it["url"]))
    return " · ".join(bits)


def to_html(markdown_text: str, name: str, tagline: str, date: str,
            items: List[Dict[str, Any]]) -> str:
    body = md.markdown(markdown_text, extensions=["extra", "sane_lists"])
    # Style the generated tags inline so mail clients behave.
    body = (body
            .replace("<h1>", '<h1 style="font-size:26px;line-height:1.2;margin:0 0 6px;">')
            .replace("<h2>", '<h2 style="font-size:13px;letter-spacing:.14em;'
                             'text-transform:uppercase;color:#8a7a5c;border-top:1px solid #e3ded3;'
                             'padding-top:18px;margin:32px 0 12px;">')
            .replace("<h3>", '<h3 style="font-size:18px;line-height:1.3;margin:22px 0 6px;">')
            .replace("<p>", '<p style="font-size:16px;line-height:1.6;margin:0 0 12px;">')
            .replace("<li>", '<li style="font-size:15px;line-height:1.55;margin:0 0 8px;">')
            .replace("<a ", '<a style="color:#7a1f2b;text-decoration:underline;" '))

    sources = sorted({it.get("source") or "" for it in items} - {""})
    return """<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="{css}">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="{wrap}">
  <tr><td style="padding:28px 32px 0;border-top:3px solid #7a1f2b;">
    <div style="font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:#8a7a5c;">{name}</div>
    <div style="font-size:12px;color:#6b6b6b;margin-top:4px;">{tagline} &middot; {date}</div>
  </td></tr>
  <tr><td style="padding:12px 32px 28px;">{body}</td></tr>
  <tr><td style="padding:18px 32px 28px;border-top:1px solid #e3ded3;font-family:-apple-system,Segoe UI,sans-serif;font-size:11px;line-height:1.6;color:#8a8a8a;">
    Compiled from primary sources: {sources}.<br>
    Ranked by likelihood of an open mandate, not by news value. Always verify against the underlying record before acting.
  </td></tr>
</table></td></tr></table>""".format(
        css=CSS_BODY, wrap=WRAP, name=html.escape(name), tagline=html.escape(tagline),
        date=html.escape(date), body=body,
        sources=html.escape(", ".join(sources) or "n/a"))


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
