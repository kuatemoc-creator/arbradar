"""Items fetched where a source can be reached, imported where it cannot.

Cloudflare refuses GitHub's runner addresses at pca-cpa.org and a few court
sites, while the same pages open from an ordinary connection. We do not argue
with that: a machine that can read the source runs the adapter, writes what it
found to a JSON-lines file on the `relay` branch, and the cloud run imports it
through the same path a live fetch would take. Nothing is spoofed and nothing is
fetched twice - the fingerprint dedupes.

    tools/relay.sh                      on the machine that can reach the source
    arbradar.cli import --file …        in the cloud run, before the build
"""
import datetime as dt
import json
from typing import Any, Dict, Iterable, List

from . import db, pipeline
from .sources import REGISTRY

# The adapters GitHub's runners are refused by. Everything else fetches in the cloud.
BLOCKED_IN_CLOUD = ("pca", "pca_cases", "courts")


def export(names: Iterable[str], days: int, path: str) -> Dict[str, int]:
    """Run the named adapters here and write their raw items to `path`."""
    counts: Dict[str, int] = {}
    with open(path, "w", encoding="utf-8") as fh:
        for name in names:
            fn = REGISTRY.get(name)
            if not fn:
                continue
            n = 0
            try:
                for raw in fn(days=days):
                    if not (raw.get("title") and raw.get("url")):
                        continue
                    fh.write(json.dumps({"adapter": name, "raw": raw}, ensure_ascii=False, default=str) + "\n")
                    n += 1
            except Exception as exc:                  # noqa: BLE001 - boundary
                print("relay: {} failed: {}".format(name, str(exc)[:200]))
            counts[name] = n
    return counts


def import_file(conn, settings, path: str) -> Dict[str, int]:
    """Store relayed items exactly as a live fetch would, and log the run."""
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    found: Dict[str, int] = {}
    new: Dict[str, int] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            name, raw = rec.get("adapter") or "relay", rec.get("raw") or {}
            if settings.sources and settings.sources.get(name) is False:
                continue
            found[name] = found.get(name, 0) + 1
            item = pipeline.item_from_raw(name, raw, now)
            if item and db.upsert_item(conn, item):
                new[name] = new.get(name, 0) + 1
    for name, n in found.items():
        conn.execute("INSERT INTO fetch_log (source, ran_at, found, new_items, error) VALUES (?,?,?,?,?)",
                     (name, now, n, new.get(name, 0), "relayed"))
    conn.commit()
    return new
