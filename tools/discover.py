"""Find and verify the feed of every outlet in tools/outlets.py, and wire the ones that answer.

    python -m tools.discover              # probe everything, write sources.yaml + docs/press.json
    python -m tools.discover --country Armenia --country Georgia
    python -m tools.discover --dry-run    # probe and report, touch nothing

For each outlet: if the URL is already a feed, it is parsed; otherwise the site's
own <link rel="alternate"> and the usual feed paths are tried. A feed counts only
if it parses, has entries, and the newest entry is recent (or the feed carries no
dates at all but has several entries). Sites that answer with a bot challenge are
recorded as blocked and left alone.

Feeds that pass are merged into sources.yaml `national_press`. Existing entries are
kept (an outage today is not a reason to drop a feed) and marked with the last
date they answered.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import sys
import time
from urllib.parse import urlsplit, urljoin

import feedparser
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.outlets import OUTLETS                       # noqa: E402
from tools.sourcemap import _get, _is_feed, _ALT, _HREF, ROOT   # noqa: E402

FRESH_DAYS = 45
PATHS = ["/feed/", "/feed", "/rss", "/rss.xml", "/feed.xml", "/rss/", "/index.xml", "/atom.xml",
         "/?feed=rss2", "/en/feed/", "/en/rss", "/en/rss.xml", "/arc/outboundfeeds/rss/", "/rss/news", "/feeds/posts/default"]


def _newest(parsed):
    latest = None
    for e in parsed.entries[:40]:
        tm = e.get("published_parsed") or e.get("updated_parsed")
        if tm:
            d = dt.date(*tm[:3])
            if latest is None or d > latest:
                latest = d
    return latest


def _check(url, timeout=12):
    """(ok, detail) for a URL that should be a feed."""
    code, ct, text, final, flag = _get(url, timeout)
    if code != 200 or not _is_feed(ct, text):
        return False, "not a feed", final
    parsed = feedparser.parse(text)
    if not parsed.entries:
        return False, "empty", final
    newest = _newest(parsed)
    if newest is None:
        return (len(parsed.entries) >= 3), "undated, {} entries".format(len(parsed.entries)), final
    age = (dt.date.today() - newest).days
    if age > FRESH_DAYS:
        return False, "stale: newest {}".format(newest.isoformat()), final
    return True, "newest {}{}".format(newest.isoformat(), " " + flag if flag else ""), final


def _find(url):
    """The site's own feed, from its home page or the usual paths."""
    parts = urlsplit(url)
    home = "{}://{}/".format(parts.scheme, parts.netloc)
    cands = []
    for base in (url if url.rstrip("/") != home.rstrip("/") else home, home):
        try:
            code, ct, text, final, flag = _get(base, 12)
        except PermissionError:
            raise
        except Exception:                             # noqa: BLE001 - boundary
            continue
        if code == 200 and _is_feed(ct, text):
            return base
        for tag in _ALT.findall(text)[:6]:
            m = _HREF.search(tag)
            if m:
                href = urljoin(final, m.group(1).replace("&amp;", "&"))
                if "comments" not in href.lower():
                    cands.append(href)
        if base == home:
            break
    section = url.rstrip("/")
    if section != home.rstrip("/"):
        cands += [section + p for p in PATHS[:4]]
    cands += [home.rstrip("/") + p for p in PATHS]
    for cand in dict.fromkeys(cands):
        try:
            ok, detail, final = _check(cand, 8)
        except PermissionError:
            raise
        except Exception:                             # noqa: BLE001 - boundary
            continue
        if ok:
            return cand
    return None


def probe(job):
    country, name, url, lang = job
    t0 = time.time()
    try:
        try:
            ok, detail, final = _check(url)
        except PermissionError as exc:
            return dict(country=country, name=name, url=url, lang=lang, status="blocked", detail=str(exc), secs=round(time.time() - t0))
        except Exception as exc:                      # noqa: BLE001 - boundary
            ok, detail = False, type(exc).__name__
        if ok:
            return dict(country=country, name=name, url=url, lang=lang, status="ok", detail=detail, secs=round(time.time() - t0))
        found = _find(url)
        if found:
            ok, detail, final = _check(found)
            if ok:
                return dict(country=country, name=name, url=found, lang=lang, status="ok", detail="discovered; " + detail, secs=round(time.time() - t0))
        return dict(country=country, name=name, url=url, lang=lang, status="none", detail=detail, secs=round(time.time() - t0))
    except PermissionError as exc:
        return dict(country=country, name=name, url=url, lang=lang, status="blocked", detail=str(exc), secs=round(time.time() - t0))
    except Exception as exc:                          # noqa: BLE001 - boundary
        return dict(country=country, name=name, url=url, lang=lang, status="error", detail=type(exc).__name__, secs=round(time.time() - t0))


def _key(url):
    p = urlsplit(url)
    return re.sub(r"^(www|amp|m)\.", "", p.netloc.lower()) + p.path.rstrip("/").lower()


def merge(results, path):
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    press = cfg.get("national_press") or []
    today = dt.date.today().isoformat()
    have = {_key(x["url"]): x for x in press}
    added = 0
    for r in results:
        if r["status"] != "ok":
            continue
        k = _key(r["url"])
        if k in have:
            have[k]["verified"] = today
            continue
        entry = {"country": r["country"], "name": r["name"], "url": r["url"], "lang": r["lang"], "enabled": True, "verified": today}
        press.append(entry)
        have[k] = entry
        added += 1
    # keep the file grouped by country, sectors and Global last
    def order(x):
        c = x["country"]
        return (c.startswith("Sector"), c == "Global", c, x["name"])
    cfg["national_press"] = sorted(press, key=order)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, allow_unicode=True, sort_keys=False, width=200)
    return added, len(press)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", action="append")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--under", type=int, help="only countries with fewer than this many verified feeds in the last run")
    a = ap.parse_args()
    wanted = set(a.country or [])
    if a.under:
        last = os.path.join(ROOT, "docs", "press.json")
        ok = {}
        if os.path.exists(last):
            for r in json.load(open(last, encoding="utf-8"))["results"]:
                ok.setdefault(r["country"], 0)
                ok[r["country"]] += r["status"] == "ok"
        wanted |= {c for c in OUTLETS if ok.get(c, 0) < a.under}
    jobs = [(c, n, u, l) for c, lst in OUTLETS.items() if not wanted or c in wanted for n, u, l in lst]
    print(len(jobs), "outlets in", len({j[0] for j in jobs}), "countries", flush=True)
    results = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, r in enumerate(ex.map(probe, jobs), 1):
            results.append(r)
            print("{:4} {:<22} {:<8} {:<34} {}".format(i, r["country"][:22], r["status"], r["name"][:34], r["detail"][:60]), flush=True)
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    probed = {j[0] for j in jobs}
    last = os.path.join(ROOT, "docs", "press.json")
    if wanted and os.path.exists(last):
        results = [r for r in json.load(open(last, encoding="utf-8"))["results"] if r["country"] not in probed] + results
    with open(os.path.join(ROOT, "docs", "press.json"), "w", encoding="utf-8") as fh:
        json.dump({"date": dt.date.today().isoformat(), "results": results}, fh, ensure_ascii=False, indent=1)
    counts = {}
    for r in results:
        counts.setdefault(r["country"], [0, 0])
        counts[r["country"]][1] += 1
        if r["status"] == "ok":
            counts[r["country"]][0] += 1
    print()
    for c, (ok, tot) in sorted(counts.items(), key=lambda kv: kv[1][0]):
        print("{:3}/{:<3} {}".format(ok, tot, c))
    if not a.dry_run:
        added, total = merge(results, os.path.join(ROOT, "sources.yaml"))
        print("\nsources.yaml: {} feeds added, {} national press feeds now".format(added, total))


if __name__ == "__main__":
    main()
