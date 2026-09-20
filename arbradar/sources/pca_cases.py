"""PCA case list, via a headless browser.

The Permanent Court of Arbitration administers most UNCITRAL investor-State
cases outside ICSID, including the ones that matter most in the Caucasus and
Central Asia (Azerbaijan v. Armenia under the Energy Charter Treaty sits here).
Its case list is rendered by JavaScript and is not exposed over any API, so a
real browser reads it. Nothing is bypassed: the page is public and unwalled.

Case numbers carry the year of commencement ([2026-35]); we report cases whose
number belongs to the current or previous year and which we have not seen.
"""
import datetime as dt
import re
from typing import Dict, Iterator, List, Tuple

from ..fetch import get

LIST = "https://pca-cpa.org/en/cases/"
_NUM = re.compile(r"^\[(\d{4})-(\d+)\]\s*(.+)$")
_DATE_FIELDS = ("Date of Commencement", "Commencement", "Date of Notice of Arbitration", "Date of Request")
_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_DATE = re.compile(r"(\d{1,2} (?:%s) \d{4})" % _MONTHS)


def _list_cases() -> List[Tuple[int, int, str, str]]:
    """(year, number, title, url) for every case on the list page."""
    from playwright.sync_api import sync_playwright
    out = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/128 Safari/537.36", locale="en-US").new_page()
        page.goto(LIST, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(2000)
        for href, text in page.eval_on_selector_all(
                "a", "els=>els.map(e=>[e.href,e.innerText.trim().replace(/\\s+/g,' ')])"):
            m = _NUM.match(text or "")
            if m and "/cases/" in href:
                out.append((int(m.group(1)), int(m.group(2)), m.group(3).strip(), href))
        browser.close()
    return out


_LABELS = ["Name(s) of Claimant(s)", "Name(s) of Respondent(s)", "Names of Parties", "Case number",
           "Administering institution", "Case status", "Type of case", "Subject matter", "Rules of procedure",
           "Rules of Procedure", "Treaty or contract under which proceedings were commenced", "Language of Proceeding",
           "Seat of Arbitration (by Country)", "Arbitrator(s), Conciliator(s), Other Neutral(s)",
           "Representatives of the Claimant(s)", "Representatives of the Respondent(s)", "Representatives of the Parties"]


def _case_detail(url: str) -> Dict[str, str]:
    """The 'Case information' block: parties, status, type, instrument, seat, tribunal, counsel.
    PCA does not publish commencement dates; the case number carries the year."""
    try:
        html = get(url, ttl=7 * 24 * 3600, timeout=40).text
    except Exception:                                 # noqa: BLE001 - boundary
        return {}
    import html as _h
    text = _h.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)))
    i = text.find("Case information")
    if i < 0:
        return {}
    block = text[i:i + 6000]
    positions = sorted((block.find(lab), lab) for lab in _LABELS if block.find(lab) >= 0)
    out: Dict[str, str] = {}
    for k, (pos, lab) in enumerate(positions):
        nxt = positions[k + 1][0] if k + 1 < len(positions) else len(block)
        val = block[pos + len(lab):nxt].strip(" -:")
        out[lab] = " ".join(val.split())
    return out


def _clean_party(v: str) -> str:
    return re.sub(r"\s*\((State|[A-Za-z ,]+)\)$", "", v or "").strip()


def describe(d: Dict[str, str], year: int, num: int, title: str) -> str:
    cl = _clean_party(d.get("Name(s) of Claimant(s)", ""))
    rs = _clean_party(d.get("Name(s) of Respondent(s)", ""))
    kind = d.get("Type of case", "").lower()
    instrument = d.get("Treaty or contract under which proceedings were commenced", "")
    instrument = re.sub(r"^(Multilateral treaty|Bilateral treaty|Contract|Treaty)\s*", "", instrument)
    instrument = re.sub(r"\s*Country A:.*$", "", instrument).strip()
    status = d.get("Case status", "")
    seat = d.get("Seat of Arbitration (by Country)", "").strip(" -")
    if seat.upper() in ("N/A", "NA", ""):
        seat = ""
    arbs = d.get("Arbitrator(s), Conciliator(s), Other Neutral(s)", "")
    rep_c = d.get("Representatives of the Claimant(s)", "")
    rep_r = d.get("Representatives of the Respondent(s)", "")
    parts = []
    if cl and rs:
        article = "an" if kind[:1] in "aeiou" else "a"
        parts.append("{} against {}{}{}.".format(cl, rs, ", {} {}".format(article, kind) if kind else "",
                                                 " under the " + instrument if instrument else ""))
    else:
        parts.append("{}{}.".format(title, " under the " + instrument if instrument else ""))
    parts.append("PCA case {}-{}{}{}.".format(year, num, ", " + status.lower() if status else "", ", seated in " + seat if seat else ""))
    if arbs:
        parts.append("Tribunal: {}.".format(re.sub(r"\s*\((Presiding Arbitrator|President)\)", " (presiding)", arbs)[:260].rstrip(".")))
    if rep_c:
        parts.append("For the claimant: {}.".format(rep_c[:200].rstrip(".")))
    if rep_r:
        parts.append("For the respondent: {}.".format(rep_r[:200].rstrip(".")))
    return " ".join(parts)


def run(days: int = 7) -> Iterator[Dict]:
    today = dt.date.today()
    cutoff = today - dt.timedelta(days=days)
    try:
        cases = _list_cases()
    except Exception:                                 # noqa: BLE001 - boundary
        return
    recent = [c for c in cases if c[0] >= today.year - 1]
    recent.sort(key=lambda c: (c[0], c[1]), reverse=True)
    for year, num, title, url in recent[:40]:
        d = _case_detail(url)
        cl = _clean_party(d.get("Name(s) of Claimant(s)", ""))
        rs = _clean_party(d.get("Name(s) of Respondent(s)", ""))
        arbs = [a.strip() for a in re.split(r"(?<=[a-z\)])\s(?=(?:Mr|Ms|Mrs|Dr|Professor|Sir|Judge|H\.E\.)\b)",
                                             d.get("Arbitrator(s), Conciliator(s), Other Neutral(s)", "")) if a.strip()]
        counsel = [c.strip() for c in re.split(r"\s{2,}|;", d.get("Representatives of the Claimant(s)", "") + " ; " +
                                              d.get("Representatives of the Respondent(s)", "")) if c.strip()]
        yield {
            "url": url,
            "source": "PCA case list",
            "title": "{} v. {} \u2014 PCA case {}-{}".format(cl or title, rs or "", year, num) if cl and rs
                     else "{} \u2014 PCA case {}-{}".format(title, year, num),
            "summary": describe(d, year, num, title),
            "published_at": "{}-01-01".format(year),          # PCA publishes no dates; the number carries the year
            "event_type": "new_case_filed",
            "institution": "PCA",
            "treaty": re.sub(r"\s*Country A:.*$", "", re.sub(r"^(Multilateral treaty|Bilateral treaty|Contract|Treaty)\s*", "",
                             d.get("Treaty or contract under which proceedings were commenced", ""))).strip() or None,
            "case_ref": "PCA {}-{}".format(year, num),
            "claimants": [cl] if cl else [],
            "respondents": [rs] if rs else [],
            "arbitrators": arbs[:5],
            "counsel": counsel[:6],
            "flag_reason": "PCA case list: case number {}-{}{}".format(year, num, "; " + d["Type of case"].lower() if d.get("Type of case") else ""),
        }
