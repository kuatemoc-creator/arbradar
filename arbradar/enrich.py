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
    best, best_score = None, None
    for e in feedparser.parse(raw).entries[:8]:
        title = e.get("title") or ""
        theirs = {_stem(w) for w in _sig(title)}
        shared = len(ours & theirs)
        if shared < max(2, min(3, len(ours) // 2)):
            continue                                  # a different story
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
    if not url or "news.google.com" in url:
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


def enrich(conn, items: List[Dict[str, Any]], limit: int = 10) -> int:
    """Fill in text for featured items that have none. Writes back to the DB."""
    from . import db
    from .pipeline import is_paywall
    done = 0
    for it in items[:limit]:
        text = (it.get("summary_en") or it.get("summary") or "").strip()
        title = (it.get("title") or "").strip()
        if text and not is_paywall(text) and not text.lower().startswith(title.lower()[:40]):
            continue
        found = lookup(it.get("title_en") or title)
        if not found:
            page = page_summary(it.get("url") or "")
            if page and not page.lower().startswith(title.lower()[:40]):
                db.update_item(conn, it["id"], summary=page)
                it["summary"] = page
                done += 1
            continue
        updates = {"summary": found["summary"]}
        if "news.google.com" in (it.get("url") or "") and found["url"].startswith("http"):
            # The link must follow the text we found, and the label must follow the link.
            from .outlets import label
            updates["url"] = found["url"]
            if (it.get("source") or "").startswith("Google News"):
                updates["source"] = "Google News / " + (found["outlet"] or label(found["url"], "source"))
        db.update_item(conn, it["id"], **updates)
        it.update(updates)
        done += 1
    conn.commit()
    return done
