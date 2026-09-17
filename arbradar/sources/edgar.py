"""SEC EDGAR full-text search.

Why this matters: a US-listed company must disclose a material dispute long
before the arbitration press notices it. Searching the filing text for arbitration
language surfaces disputes weeks to months ahead of the trade press, and it is
free and unauthenticated.
"""
import datetime as dt
from typing import Dict, Iterator, List

from ..fetch import get

ENDPOINT = "https://efts.sec.gov/LATEST/search-index"
DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"

QUERIES: List[str] = [
    '"notice of arbitration"',
    '"request for arbitration"',
    '"notice of intent to submit"',
    '"ICSID"',
    '"investor-state"',
    '"bilateral investment treaty"',
    '"UNCITRAL arbitration"',
    '"arbitral tribunal" "expropriation"',
    '"notice of dispute"',
]


def run(days: int = 7, forms: str = "8-K,6-K,20-F,10-Q,10-K") -> Iterator[Dict]:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    for q in QUERIES:
        try:
            r = get(ENDPOINT, params={
                "q": q, "forms": forms,
                "dateRange": "custom",
                "startdt": start.isoformat(), "enddt": end.isoformat(),
            }, ttl=1800)
        except Exception:                             # noqa: BLE001 - boundary
            continue
        for hit in r.json().get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            # Exhibit 10 (material contracts), 2 (merger agreements) and 4 (instruments)
            # carry dispute-resolution clauses by the thousand. A dispute is disclosed in
            # the filing body or a press release (EX-99), not in a template clause.
            ftype = (src.get("file_type") or "").upper()
            if ftype.startswith(("EX-10", "EX-2", "EX-4", "EX-3")):
                continue
            ident = hit.get("_id", "")
            acc, _, doc = ident.partition(":")
            cik = (src.get("ciks") or ["0"])[0].lstrip("0")
            names = src.get("display_names") or ["Unknown filer"]
            # EDGAR shouts filer names in caps; a headline should not.
            filer = names[0].split("  (")[0]
            if filer.isupper():
                filer = filer.title().replace(" Ltd.", " Ltd.").replace(" Llc", " LLC").replace(" Inc", " Inc")
            yield {
                "url": DOC_URL.format(cik=cik, acc_nodash=acc.replace("-", ""), doc=doc),
                "source": "SEC EDGAR",
                "title": "{} discloses {} in {} filing".format(
                    filer, q.strip('"').replace('" "', " and "), src.get("form", "SEC")),
                "summary": "{} filed {} ({}). Full-text hit on {}.".format(
                    names[0], src.get("form"), src.get("file_date"), q),
                "published_at": src.get("file_date"),
                "case_ref": acc,
            }
