"""SEC EDGAR full-text search.

Why this matters: a US-listed company must disclose a material dispute long
before the arbitration press notices it. Searching the filing text for arbitration
language surfaces disputes weeks to months ahead of the trade press, and it is
free and unauthenticated.
"""
import datetime as dt
from typing import Dict, Iterator, List

import html as _html
import re

from ..fetch import get

_SIGNAL = re.compile(r"(received|served|filed|commenced|initiated|submitted|notified|delivered|claim|"
                     r"seeking|damages|\$|US\$|million|billion|tribunal|ICSID|UNCITRAL|ICC|LCIA|treaty)", re.I)
_CLAUSE = re.compile(r"(shall be (finally )?(settled|resolved)|agree(s)? to (submit|arbitrate)|"
                     r"governed by|in accordance with the (rules|arbitration rules)|any dispute)", re.I)


def _nice_date(iso: str) -> str:
    try:
        d = dt.date.fromisoformat((iso or "")[:10])
        return "{} {} {}".format(d.day, d.strftime("%B"), d.year)
    except ValueError:
        return iso or ""


def passage(url: str, phrase: str) -> str:
    """The sentences around the first substantive occurrence of the phrase in the
    filing. A dispute-resolution clause ('any dispute shall be settled by...') is
    skipped; a disclosure ('On 8 September the Company received a notice...') is kept."""
    try:
        doc = get(url, ttl=7 * 24 * 3600, timeout=60).text
    except Exception:                                 # noqa: BLE001 - boundary
        return ""
    text = _html.unescape(re.sub(r"<[^>]+>", " ", doc))
    text = re.sub(r"\s+", " ", text)
    needle = phrase.strip('"').lower()
    low = text.lower()
    start = 0
    for _ in range(6):
        i = low.find(needle, start)
        if i < 0:
            break
        a = max(0, text.rfind(". ", 0, max(0, i - 260)) + 2)
        b = text.find(". ", i + len(needle) + 220)
        snippet = text[a:(b + 1 if b > 0 else i + 400)].strip()
        if _SIGNAL.search(snippet) and not _CLAUSE.search(snippet[:200]) and len(snippet) > 80:
            return snippet[:700]
        start = i + len(needle)
    return ""

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
    # The phrases a legal-proceedings note actually uses. "expropriation" alone
    # is risk-factor boilerplate, so it needs a dispute word beside it.
    '"arbitral tribunal"',
    '"final award" arbitration',
    '"emergency arbitrator"',
    '"expropriation" (arbitration OR tribunal OR "notice of")',
    '"arbitration" ("statement of claim" OR "request for arbitration" OR "notice of arbitration" OR "commenced arbitration")',
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
            url = DOC_URL.format(cik=cik, acc_nodash=acc.replace("-", ""), doc=doc)
            quoted = passage(url, q.split('" "')[0])
            if not quoted:
                continue                              # a clause, not a disclosure
            yield {
                "url": url,
                "source": "SEC EDGAR",
                "title": "{} discloses {} in {} filing".format(
                    filer, q.strip('"').replace('" "', " and "), src.get("form", "SEC")),
                "summary": "In a {} filed on {}, {} disclosed: \u201c{}\u201d".format(
                    src.get("form"), _nice_date(src.get("file_date")), filer, quoted),
                "published_at": src.get("file_date"),
                "case_ref": acc,
                "flag_reason": "SEC {} filing text contains \u2018{}\u2019".format(src.get("form"), q.strip('"').split('" "')[0]),
            }
