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
        except httpx.HTTPError as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code in (403, 429, 503):
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
