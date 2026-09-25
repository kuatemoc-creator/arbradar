"""SMTP delivery.

Sending is always an explicit, separate command. The pipeline never mails anyone
as a side effect of building an issue - you review the file first.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage
import html as _html
import re
from typing import List, Optional


def plain_text(html_doc: str) -> str:
    """The text alternative, from the one rendering: block ends become line
    breaks, tags go, entities are decoded."""
    t = re.sub(r"<(?:style|script)[^>]*>.*?</(?:style|script)>", " ", html_doc, flags=re.S | re.I)
    t = re.sub(r"<div[^>]*display:none[^>]*>.*?</div>", " ", t, flags=re.S | re.I)   # the preheader
    t = re.sub(r"</(?:p|h[1-6]|tr|div|li)>|<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = _html.unescape(t)
    lines = [re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in t.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(ln for ln in lines if ln)).strip() + "\n"


def build_message(html_path: str, md_path: Optional[str], subject: str, settings,
                  recipients: List[str]) -> EmailMessage:
    cfg = settings.smtp or {}
    sender = cfg.get("from") or cfg.get("user") or os.environ.get("SMTP_USER", "") or "newsletter@caselens.tech"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "{} <{}>".format(settings.newsletter_name, sender)
    msg["To"] = ", ".join(recipients) if recipients else sender
    html_doc = open(html_path, encoding="utf-8").read()
    if md_path and os.path.exists(md_path):
        msg.set_content(open(md_path, encoding="utf-8").read())      # an issue from before the one rendering
    else:
        msg.set_content(plain_text(html_doc))
    msg.add_alternative(html_doc, subtype="html")
    return msg


def write_eml(html_path: str, md_path: Optional[str], subject: str, settings,
              recipients: List[str] = None) -> str:
    """The message as an .eml file - opens in Mail.app or Outlook exactly as sent."""
    path = html_path[:-5] + ".eml"
    msg = build_message(html_path, md_path, subject, settings, recipients or [])
    with open(path, "wb") as fh:
        fh.write(bytes(msg))
    return path


def send(html_path: str, md_path: Optional[str], subject: str, settings,
         recipients: List[str] = None, dry_run: bool = True) -> str:
    recipients = recipients or settings.recipients or []
    if not recipients:
        return "no recipients configured"

    cfg = settings.smtp or {}
    host = cfg.get("host", "smtp.gmail.com")
    port = int(cfg.get("port", 587))
    user = cfg.get("user") or os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = cfg.get("from") or user

    msg = build_message(html_path, md_path, subject, settings, recipients)

    if dry_run:
        return ("DRY RUN - would send '{}' to {} recipient(s): {}"
                .format(subject, len(recipients), ", ".join(recipients)))
    if not password:
        return "SMTP_PASSWORD not set - aborting"

    with smtplib.SMTP(host, port) as server:
        server.starttls(context=ssl.create_default_context())
        server.login(user, password)
        server.send_message(msg)
    return "sent to {} recipient(s)".format(len(recipients))
