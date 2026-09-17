"""SMTP delivery.

Sending is always an explicit, separate command. The pipeline never mails anyone
as a side effect of building an issue - you review the file first.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import List


def send(html_path: str, md_path: str, subject: str, settings,
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

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "{} <{}>".format(settings.newsletter_name, sender)
    msg["To"] = ", ".join(recipients)
    msg.set_content(open(md_path, encoding="utf-8").read())
    msg.add_alternative(open(html_path, encoding="utf-8").read(), subtype="html")

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
