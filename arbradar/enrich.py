"""Text for stories that arrive as a bare headline.

Google News feeds carry no article text and their links cannot be followed by a
script. Bing News publishes an RSS search feed with a real publisher link and a
snippet. For every featured story that has no paragraph, we search Bing News with
the significant words of the headline, accept the first result whose title shares
enough of those words with ours, and take its snippet and publisher link.
"""
import html
import re
import urllib.parse as up
from typing import Any, Dict, List, Optional, Tuple

import feedparser

from .fetch import get

BING = "https://www.bing.com/news/search?q={}&format=RSS"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128 Safari/537.36"}
_NEWSY = ("notice", "dispute", "arbitrat", "claim", "tribunal", "decree", "revok", "award", "seiz", " tax",
          "licence", "license", "expropriat", "nationalis", "nationaliz", "court", "filed", "million", "billion",
          "treaty", "icsid", "government", "ministry")
STOP = set("the a an of to in on for and or with by from at as is are was were be has have had its their "
           "this that over under against into after amid says said new will could may how why who what when "
           "orders order tests test fight ".split())


def _sig(text: str) -> List[str]:
    return [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", text or "") if len(w) >= 4 and w.lower() not in STOP]


def _stem(w: str) -> str:
    return re.sub(r"(ies|es|s|ed|ing)$", "", w.lower())


def _tidy(text: str) -> str:
    """A wire snippet is cut at a fixed length; end it on a sentence, or failing
    that on a clause, never on 'the' or a possessive."""
    text = text.strip().rstrip("\u2026. ")
    if re.search(r"[.!?]$", text):
        return text
    cut = max(text.rfind(". "), text.rfind("? "), text.rfind("! "))
    if cut >= 60:
        return text[:cut + 1]
    cut = max(text.rfind(", "), text.rfind("; "))
    if cut >= 60:
        return text[:cut] + "\u2026"
    return text.rsplit(" ", 1)[0] + "\u2026"


def _publisher_url(link: str) -> str:
    """Bing wraps links: .../apiclick.aspx?...&url=<encoded publisher url>."""
    try:
        qs = up.parse_qs(up.urlsplit(link).query)
        return qs.get("url", [link])[0]
    except Exception:                                 # noqa: BLE001 - boundary
        return link


def lookup(headline: str) -> Optional[Dict[str, str]]:
    """Best snippet across a few query phrasings; a weak (boilerplate) hit from
    the first query does not stop the search for a better one."""
    words = _sig(headline)
    if len(words) < 2:
        return None
    proper = [w for w in words if w[0].isupper()]
    best = None
    for query in dict.fromkeys([" ".join(words[:6]), " ".join(proper[:4]), " ".join(words[:3])]):
        if len(query.split()) < 2:
            continue
        found = _search(query, words)
        if found and (best is None or found["score"] > best["score"]):
            best = found
        if best and best["score"] >= 2:
            break
    return best


def _search(query: str, words: List[str]) -> Optional[Dict[str, str]]:
    try:
        raw = get(BING.format(up.quote(query)), ttl=6 * 3600, headers=UA, timeout=25).content
    except Exception:                                 # noqa: BLE001 - boundary
        return None
    ours = {_stem(w) for w in words}
    from .pipeline import _entities
    my_ents = _entities(" ".join(words))
    best, best_score = None, None
    for e in feedparser.parse(raw).entries[:8]:
        title = e.get("title") or ""
        theirs = {_stem(w) for w in _sig(title)}
        shared = len(ours & theirs)
        if shared < max(2, min(3, len(ours) // 2)):
            continue                                  # a different story
        # The same words about another company are another story: "Turkey
        # revokes operating licence" fits Papel and Bank Mellat alike, and
        # only the name tells them apart. A page that names a company the
        # headline does not, or none where the headline names one, is skipped.
        their_ents = _entities(title)
        if my_ents and not (my_ents & their_ents):
            continue
        if their_ents and not my_ents:
            continue
        # A headline that names a State is about that State: a page that names
        # none of its States is another story ("Laos' bid to enforce" is not a
        # Utah police case, however alike the court words).
        from .sources.editions import states_in
        mine_states = set(states_in(" ".join(words)))
        snippet_text = html.unescape(re.sub(r"<[^>]+>", " ", e.get("summary") or e.get("description") or ""))
        if mine_states and not (mine_states & set(states_in(title + " " + snippet_text))):
            continue
        if not (my_ents & their_ents) and shared < 4:
            continue                                  # common words alone do not make it the same story
        text = html.unescape(re.sub(r"<[^>]+>", " ", e.get("summary") or e.get("description") or ""))
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 60:
            continue
        # Title overlap only gates the match. The snippet's own content decides:
        # a sentence that states the development beats a company's boilerplate
        # opening ("X, the leading developer of...").
        newsy = sum(1 for k in _NEWSY if k in text.lower())
        boilerplate = bool(re.match(r"^[A-Z][\w .&'-]{0,40}, (the|a) ", text))
        score = newsy * 2 - (5 if boilerplate else 0) + min(shared, 3) * 0.5
        if best_score is None or score > best_score:
            outlet = ((e.get("source") or {}).get("title")) or ""
            best, best_score = {"summary": _tidy(text),
                                "url": _publisher_url(e.get("link") or ""),
                                "outlet": outlet, "title": title, "score": score}, score
    return best


def page_summary(url: str) -> str:
    """The article's own description, for a story whose feed carried only a headline:
    og:description, then the meta description, then the first real paragraph."""
    if not url or "news.google.com" in url or "iareporter.com" in url:
        return ""
    try:
        from .fetch import get
        html_text = get(url, ttl=86400, timeout=20).text
    except Exception:                                 # noqa: BLE001 - boundary
        return ""
    try:
        from selectolax.parser import HTMLParser
        tree = HTMLParser(html_text)
        for sel in ('meta[property="og:description"]', 'meta[name="description"]', 'meta[name="twitter:description"]'):
            node = tree.css_first(sel)
            if node and (node.attributes.get("content") or "").strip():
                text = node.attributes.get("content").strip()
                if len(text.split()) >= 12:
                    return _tidy(re.sub(r"\s+", " ", text))
        for p in tree.css("article p, main p, .article-body p, .story p, p"):
            text = re.sub(r"\s+", " ", p.text(separator=" ")).strip()
            if len(text) >= 80 and not re.search(r"cookie|subscribe|sign in|log in|advertis|©", text, re.I):
                return _tidy(" ".join(text.split()[:90]))
    except Exception:                                 # noqa: BLE001 - parser edge cases
        return ""
    return ""


_PROMO = re.compile(r"subscribe|sign up|newsletter|cookie|click here|read more|topic tool|3000\+ topics|"
                    r"log in|register to|free trial|all rights reserved|terms of use|privacy policy", re.I)
_STOP = {"about", "after", "against", "amid", "before", "between", "court", "from", "over", "says", "said",
         "that", "their", "there", "these", "this", "under", "what", "when", "which", "while", "with", "would",
         "your", "into", "than", "them", "then", "they", "were", "will", "have", "been", "being", "more", "most"}


def _stems(text: str) -> set:
    return {w[:5] for w in re.findall(r"[a-z0-9]{4,}", (text or "").lower()) if w not in _STOP}


def relevant_summary(title: str, text: str) -> bool:
    """An explanation must be prose about the headline's subject: not a paywall
    notice, not the site's promotion, not the headline repeated, and it must
    share content words with the headline - two of them, or one that is a name."""
    from .pipeline import is_paywall
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).replace("\xa0", " ").strip()
    if not text or len(text.split()) < 8:
        return False
    if is_paywall(text) or _PROMO.search(text):
        return False
    if text.lower().startswith((title or "").lower()[:40]):
        return False
    tt, st = _stems(title), _stems(text)
    if not tt:
        return True
    shared = tt & st
    names = {w.lower()[:5] for w in re.findall(r"\b[A-Z][a-zA-Z]{3,}", title or "")}
    return len(shared) >= 2 or bool(shared & names)


def match_docket(conn, it: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The one ICSID docket entry a press story is about: same State, same kind of
    step, within a fortnight. None unless the match is unambiguous."""
    import datetime as dt
    from . import db
    text = ((it.get("title") or "") + " " + (it.get("summary") or "")).lower()
    if "icsid" not in text and "investment treaty" not in text:
        return None
    kinds = []
    if re.search(r"award|concludes|rules|damages|dismiss", text):
        kinds.append("award_issued")
    if re.search(r"annul|set aside|committee", text):
        kinds.append("annulment_setaside")
    if re.search(r"registered|files|filed|lodge|brings|takes .* to icsid|new case", text):
        kinds.append("new_case_filed")
    if not kinds:
        return None
    states = [s.lower() for s in (it.get("states") or [])]
    if not states:
        return None
    when = str(it.get("published_at") or dt.date.today().isoformat())[:10]
    try:
        base = dt.date.fromisoformat(when)
    except ValueError:
        base = dt.date.today()
    lo, hi = (base - dt.timedelta(days=14)).isoformat(), (base + dt.timedelta(days=3)).isoformat()
    rows = [db.row_to_dict(r) for r in conn.execute(
        "SELECT * FROM items WHERE source='ICSID docket' AND published_at BETWEEN ? AND ? AND event_type IN ({})".format(
            ",".join("?" * len(kinds))), [lo, hi] + kinds)]
    hits = [r for r in rows if any(s.lower() in states for s in (r.get("states") or []))]
    return hits[0] if len(hits) == 1 else None


def enrich(conn, items: List[Dict[str, Any]], limit: int = 10) -> int:
    """Give every featured story an explanation that is about the story. Writes
    back to the DB. Candidates in order: the ICSID docket's own prose, a search
    snippet, the article page. Each is checked against the headline."""
    from . import db
    from .outlets import label
    done = 0
    for it in items[:limit]:
        title = (it.get("title_en") or it.get("title") or "").strip()
        if relevant_summary(title, it.get("summary_en") or it.get("summary") or ""):
            continue
        docket = match_docket(conn, it)
        if docket and relevant_summary(title, docket.get("summary") or ""):
            updates = {"summary": docket["summary"], "case_ref": it.get("case_ref") or docket.get("case_ref")}
            db.update_item(conn, it["id"], **updates)
            it.update(updates)
            it["also"] = list(it.get("also") or []) + [{"source": "ICSID docket", "url": docket["url"], "title": docket["title"]}]
            done += 1
            continue
        found = lookup(title)
        if found and relevant_summary(title, found["summary"]):
            updates = {"summary": found["summary"]}
            if "news.google.com" in (it.get("url") or "") and found["url"].startswith("http"):
                updates["url"] = found["url"]           # the link follows the text, the label follows the link
                if (it.get("source") or "").startswith("Google News"):
                    updates["source"] = "Google News / " + (found["outlet"] or label(found["url"], "source"))
            db.update_item(conn, it["id"], **updates)
            it.update(updates)
            done += 1
            continue
        page = page_summary(it.get("url") or "")
        if page and relevant_summary(title, page):
            db.update_item(conn, it["id"], summary=page)
            it["summary"] = page
            done += 1
    conn.commit()
    return done
