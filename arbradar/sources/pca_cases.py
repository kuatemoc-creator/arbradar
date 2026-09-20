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


def _case_detail(url: str) -> Dict[str, str]:
    """Parties and dates from the case page (server-rendered, plain fetch)."""
    try:
        html = get(url, ttl=7 * 24 * 3600, timeout=40).text
    except Exception:                                 # noqa: BLE001 - boundary
        return {}
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    out: Dict[str, str] = {}
    for label in _DATE_FIELDS:
        m = re.search(re.escape(label) + r"[^0-9]{0,40}" + _DATE.pattern, text)
        if m:
            out["commenced"] = m.group(1)
            break
    m = re.search(r"Case Type[:\s]+([A-Za-z\- /]+?)(?:\s{2,}|Subject|Applicable|Arbitrator)", text)
    if m:
        out["type"] = m.group(1).strip()
    m = re.search(r"Rules[:\s]+([^.]{5,80}?)(?:\s{2,}|Language|Seat|Administer)", text)
    if m:
        out["rules"] = m.group(1).strip()
    return out


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
        detail = _case_detail(url)
        when = None
        if detail.get("commenced"):
            try:
                when = dt.datetime.strptime(detail["commenced"], "%d %B %Y").date()
            except ValueError:
                when = None
        # a case whose page carries no date is reported once, dated by its number's year
        if when and when < cutoff:
            continue
        parties = re.search(r"\(([^()]+ v\.? [^()]+)\)\s*$", title)
        claimant = respondent = ""
        if parties:
            claimant, _, respondent = parties.group(1).partition(" v. ")
        yield {
            "url": url,
            "source": "PCA case list",
            "title": "PCA {}-{}: {}".format(year, num, title),
            "summary": "Case {}-{} on the PCA list{}{}{}.".format(
                year, num,
                ", commenced " + detail["commenced"] if detail.get("commenced") else "",
                "; type: " + detail["type"] if detail.get("type") else "",
                "; rules: " + detail["rules"] if detail.get("rules") else ""),
            "published_at": when.isoformat() if when else "{}-01-01".format(year),
            "event_type": "new_case_filed",
            "institution": "PCA",
            "case_ref": "PCA {}-{}".format(year, num),
            "claimants": [claimant.strip()] if claimant else [],
            "respondents": [respondent.strip()] if respondent else [],
            "flag_reason": "PCA case list: case number {}-{}".format(year, num),
        }
