"""GDELT DOC 2.0 - global news, machine-tagged by country.

Slower and noisier than Google News, but it reads non-English press and tags the
country each article is *about*, which catches the "minister announces review of
foreign concessions" story that never mentions arbitration at all.

Hard rate limit: one request every five seconds. Keep the query bank short.
"""
import datetime as dt
import time
from typing import Dict, Iterator

from ..fetch import get, Blocked

ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

QUERIES = [
    '(expropriation OR expropriated OR nationalisation OR nationalization) (investor OR company OR compensation)',
    '("investment treaty" OR ICSID OR "bilateral investment treaty") (claim OR arbitration OR notice)',
    '("licence revoked" OR "license revoked" OR "concession terminated" OR "permit cancelled") (foreign OR investor OR company)',
    '("international arbitration" OR "arbitration proceedings") (government OR ministry OR republic) (threat OR file OR launch)',
    '("temporary management" OR "state control" OR "taken over by the state" OR "under administration") (plant OR company OR assets OR subsidiary)',
    '("tax assessment" OR "back taxes" OR "windfall tax" OR "royalty") (foreign OR investor OR miner OR operator) (dispute OR arbitration OR treaty)',
]


def run(days: int = 7) -> Iterator[Dict]:
    params = {"mode": "artlist", "maxrecords": 75, "format": "json",
              "timespan": "{}d".format(days), "sort": "datedesc"}
    for q in QUERIES:
        arts = None
        for wait in (6, 20):
            time.sleep(wait)
            try:
                r = get(ENDPOINT, params=dict(params, query=q), ttl=3600, timeout=60)
                arts = r.json().get("articles", [])
                break
            except Blocked:
                continue                              # 429 - back off and retry once
            except Exception:                         # noqa: BLE001 - boundary
                break
        if not arts:
            continue
        for a in arts:
            seen = a.get("seendate") or ""
            try:
                published = dt.datetime.strptime(seen[:8], "%Y%m%d").date().isoformat()
            except ValueError:
                published = None
            yield {
                "url": a.get("url") or "",
                "source": "GDELT / " + (a.get("domain") or ""),
                "title": (a.get("title") or "").strip()[:300],
                "summary": "Tagged country: {}. Language: {}.".format(
                    a.get("sourcecountry") or "unknown", a.get("language") or "unknown"),
                "published_at": published,
                "states": [a["sourcecountry"]] if a.get("sourcecountry") else [],
            }
