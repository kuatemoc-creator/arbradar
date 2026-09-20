"""HTTP with a polite UA, retries and an on-disk cache.

Several arbitration sites sit behind Cloudflare (italaw, UNCTAD). We do not try
to defeat that - we mark the source as blocked and carry on, so one hostile
origin never fails a whole run.
"""
import hashlib
import logging
import os
import time
from typing import Optional

import httpx

from .config import DATA_DIR

log = logging.getLogger(__name__)
CACHE = os.path.join(DATA_DIR, "cache")
UA = ("arb-radar/0.1 (arbitration news aggregation; contact: {})"
      .format(os.environ.get("ARBRADAR_CONTACT", "kuatemoc@gmail.com")))
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}


class Blocked(Exception):
    """Origin refused us (403/429/503). Not a bug - just note it and move on."""


def get(url: str, params: Optional[dict] = None, ttl: int = 3600,
        timeout: int = 30, headers: Optional[dict] = None) -> httpx.Response:
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256((url + repr(sorted((params or {}).items()))).encode()).hexdigest()
    path = os.path.join(CACHE, key)

    if ttl and os.path.exists(path) and time.time() - os.path.getmtime(path) < ttl:
        body = open(path, "rb").read()
        return httpx.Response(200, content=body, request=httpx.Request("GET", url))

    h = dict(HEADERS)
    if headers:
        h.update(headers)
    last = None
    for attempt in range(3):
        try:
            r = httpx.get(url, params=params, headers=h, timeout=timeout,
                          follow_redirects=True)
        except httpx.ConnectError as exc:
            if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                # Several government hosts serve incomplete chains. Read them anyway;
                # nothing here is authenticated or written.
                r = httpx.get(url, params=params, headers=h, timeout=timeout,
                              follow_redirects=True, verify=False)
            else:
                last = exc
                time.sleep(1.5 * (attempt + 1))
                continue
        except httpx.HTTPError as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code in (403, 429, 503):
            # A refusal on the Python client's TLS fingerprint is not a refusal of
            # the request: retry once with a browser-identical handshake.
            if r.status_code == 403 and attempt == 0:
                try:
                    from curl_cffi import requests as cr
                    cr_r = cr.get(url, params=params, headers=h, impersonate="chrome124",
                                  timeout=timeout, allow_redirects=True)
                    if cr_r.status_code == 200 and "challenge validation" not in cr_r.text[:1500].lower():
                        with open(path, "wb") as fh:
                            fh.write(cr_r.content)
                        return httpx.Response(200, content=cr_r.content, headers={"content-type": cr_r.headers.get("content-type", "")},
                                              request=httpx.Request("GET", url))
                except Exception:                     # noqa: BLE001 - boundary
                    pass
            raise Blocked("{} returned {}".format(url, r.status_code))
        if r.status_code >= 500:
            last = httpx.HTTPError("{} {}".format(url, r.status_code))
            time.sleep(1.5 * (attempt + 1))
            continue
        r.raise_for_status()
        with open(path, "wb") as fh:
            fh.write(r.content)
        return r
    raise last or httpx.HTTPError("failed: " + url)
