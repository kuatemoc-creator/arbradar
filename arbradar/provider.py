"""The list provider: where subscribers live and how the issue reaches them.

The pipeline writes the issue; a provider keeps the list, confirms sign-ups,
handles unsubscribes and bounces, and delivers. Buttondown is the one wired
here: the subscribe box posts to its form endpoint, and the daily run hands the
finished HTML to its API as a draft, so the editor approves from a phone before
anything goes to the list.

Set BUTTONDOWN_API_KEY (a repository secret in the cloud, an environment
variable on a laptop). Without it every call here is a no-op that says so.
"""
import json
import os
import urllib.request
from typing import Any, Dict, Optional

API = "https://api.buttondown.com/v1/emails"


def api_key() -> str:
    return (os.environ.get("BUTTONDOWN_API_KEY") or "").strip()


def draft(subject: str, html: str, publish: bool = False) -> Dict[str, Any]:
    """Create the issue at the provider. A draft by default; `publish` sends it
    to the list at once, which is for the day the approval step is automated."""
    key = api_key()
    if not key:
        return {"status": "skipped", "reason": "BUTTONDOWN_API_KEY not set"}
    body = json.dumps({"subject": subject, "body": html, "status": "about_to_send" if publish else "draft",
                       "email_type": "public"}).encode("utf-8")
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Authorization": "Token " + key, "Content-Type": "application/json", "User-Agent": "arbradar/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            out = json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        return {"status": "error", "code": exc.code, "reason": exc.read().decode("utf-8", "replace")[:300]}
    except Exception as exc:                          # noqa: BLE001 - boundary
        return {"status": "error", "reason": str(exc)[:300]}
    return {"status": "published" if publish else "drafted", "id": out.get("id"),
            "url": "https://buttondown.com/emails/{}".format(out.get("id")) if out.get("id") else None}
