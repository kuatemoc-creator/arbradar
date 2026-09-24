"""Go deeper on a hint.

One outlet's line about a seized plant or a cancelled concession is a hint, not
a story. Given an item, this module looks for the same event in other outlets
(the Google News search feed and Bing's news feed, the two open news indexes),
keeps the copies that are plainly about the same parties and the same act, and
builds the story from what they add: an amount, a treaty, a deadline, who acts
for whom. The item keeps its own link; the other copies are cited beside it.

Nothing is decoded or scraped through a challenge: Google News entries are
cited by the outlet name the feed gives and the feed's own link.
"""
import datetime as dt
import html
import json
import re
import urllib.parse as up
from typing import Any, Dict, List, Optional

import feedparser

from .fetch import get
from .outlets import rank as outlet_rank
from .enrich import BING, UA, _sig, _stem, _NEWSY, _PROMO, _publisher_url, page_summary
from .sources.editions import states_in
from .style import sentences

GNEWS = "https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en"
_FACT = re.compile(r"(US\$|€|£|\$|\b\d[\d,.]*\s*(?:million|billion|bn|m\b)|\b(?:19|20)\d\d\b|treaty|\bBIT\b|ICSID|"
                   r"arbitra|tribunal|notice|cooling|compensat|licen[cs]e|concession|expropriat|nationali[sz]|"
                   r"seiz|court|counsel|law firm|instruct|acts? for|represent)", re.I)


_ALIAS = {"gar": "globalarbitrationreview", "iareporter": "iareporter", "investmentarbitrationreporter": "iareporter",
          "law360internationalarbitration": "law360", "cdrnews": "cdrnews", "ft": "ft", "financialtimes": "ft"}


def _domain(url: str) -> str:
    """The registrable name: premiumtimesng.com and en.antaranews.com -> premiumtimesng, antaranews."""
    host = up.urlsplit(url or "").netloc.lower()
    host = re.sub(r"^(www|amp|m|en|news)\.", "", host)
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "ac", "gov") and len(parts[-1]) == 2:
        return parts[-3]
    return parts[-2] if len(parts) >= 2 else host


def _ident(name: str) -> str:
    """An outlet's name as letters only: 'Premium Times' -> premiumtimes."""
    n = re.sub(r"[^a-z0-9]+", "", (name or "").lower())
    n = re.sub(r"(news|online|com|global)$", "", n) if len(n) > 8 else n
    return _ALIAS.get(n, n)


from .pipeline import _entities  # noqa: E402


def _same(a: str, b: str) -> bool:
    a, b = _ALIAS.get(a, a), _ALIAS.get(b, b)
    if not a or not b:
        return False
    return a == b or (len(a) >= 5 and a in b) or (len(b) >= 5 and b in a)


def _clean(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).replace("\xa0", " ").strip()
    return re.sub(r"\s*The post .{0,200}? appeared first on .{0,80}?(?:\.|$)", "", text).strip()


def _stems(text: str) -> set:
    return {_stem(w.lower()) for w in _sig(text)}


def _names(text: str) -> set:
    """The names in a headline: capitalised content words that are not common
    words. In a Title Case headline every word is capitalised, so the common
    ones ("Launches", "Group") are set aside by the house word list."""
    from .style import _is_common
    words = _sig(text)
    out = set()
    for w in words:
        if w[:1].isupper() and not _is_common(w.lower()) and not states_in(w):
            out.add(_stem(w.lower()))                 # a demonym ("Turkish") is a State, not a name
    return out


def _queries(it: Dict[str, Any]) -> List[str]:
    """A few phrasings: the names in the headline, the parties on record, the
    State plus the act. Short queries find the other copies; long ones find none."""
    title = it.get("title_en") or it.get("title") or ""
    words = _sig(title)
    proper = [w for w in words if w[0].isupper()][:4]
    names = [n for n in (it.get("claimants") or []) + (it.get("respondents") or []) if n][:2]
    states = list(it.get("states") or [])[:1]
    out = []
    if names:
        out.append(" ".join(names + states)[:80])
    if proper:
        out.append(" ".join(proper))
    if len(words) >= 3:
        out.append(" ".join(words[:5]))
    return list(dict.fromkeys(q for q in out if len(q.split()) >= 2))


def _entries(query: str) -> List[Dict[str, str]]:
    found: List[Dict[str, str]] = []
    for url in (GNEWS.format(up.quote(query)), BING.format(up.quote(query))):
        try:
            raw = get(url, ttl=6 * 3600, headers=UA, timeout=25).content
        except Exception:                             # noqa: BLE001 - boundary
            continue
        for e in feedparser.parse(raw).entries[:12]:
            title = _clean(e.get("title") or "")
            outlet = ((e.get("source") or {}).get("title") if isinstance(e.get("source"), dict) else "") or ""
            if not outlet and " - " in title:
                title, outlet = title.rsplit(" - ", 1)
            link = e.get("link") or ""
            if not title or not link:
                continue
            if "bing.com" in link:
                link = _publisher_url(link) or link      # Bing links through itself; the publisher is in the query
            if not outlet:
                outlet = re.sub(r"^(www|amp|m)\.", "", up.urlsplit(link).netloc.lower())
            when = ""
            for k in ("published_parsed", "updated_parsed"):
                if e.get(k):
                    import datetime as _dt
                    when = _dt.date(*e[k][:3]).isoformat()
                    break
            found.append({"title": title.strip(), "source": outlet.strip(),
                          "url": link, "published_at": when,
                          "snippet": _clean(e.get("summary") or e.get("description") or "")})
    return found


def corroborate(it: Dict[str, Any], max_sources: int = 5) -> Dict[str, Any]:
    """Other outlets' copies of the same event, and the story built from them."""
    title = it.get("title_en") or it.get("title") or ""
    ours = _stems(title)
    if len(ours) < 2:
        return {"sources": [], "story": ""}
    own_host = _domain(it.get("url") or "")
    if "google" in own_host or "bing" in own_host:
        own_host = ""                                 # an index link: the outlet name is the identity
    own_outlet = _ident((it.get("source") or "").replace("Google News / ", ""))
    my_states = {s.lower() for s in states_in(title + " " + (it.get("summary") or ""))}
    my_names = _names(title) | {_stem(w.lower()) for n in (it.get("claimants") or []) + (it.get("respondents") or []) for w in _sig(n)}
    seen_outlets = {own_outlet, _ALIAS.get(own_outlet, own_outlet)} | ({own_host} if own_host else set())
    seen_titles = {re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()}
    picks: List[Dict[str, str]] = []
    for q in _queries(it)[:3]:
        for e in _entries(q):
            theirs = _stems(e["title"])
            shared = len(ours & theirs)
            if shared < max(2, min(3, len(ours) // 2)):
                continue
            # Common words alone ("launches", "arbitration", "group") join two
            # different stories; a shared name or the same State must anchor it.
            same_state = bool(my_states & {s.lower() for s in states_in(e["title"] + " " + e["snippet"])})
            # A company named on one side and not the other is another matter:
            # Turkey revoking Papel's licence is not Turkey revoking Bank
            # Mellat's, and the Bombay court's anti-suit order is not its
            # defamation ruling. Only when neither headline names a company can
            # the State and the wording carry the match.
            my_ents = _entities(title)
            their_ents = _entities(e["title"])
            if my_ents and their_ents and not (my_ents & their_ents):
                continue
            if not (my_ents & their_ents) and not (same_state and shared >= 4):
                continue
            # An article from years before the item is background, not a copy of
            # the story: a 2021 sale of a company is not this week's petition.
            mine = str(it.get("published_at") or "")[:10]
            theirs_date = str(e.get("published_at") or "")[:10]
            if mine and theirs_date and theirs_date < (dt.date.fromisoformat(mine) - dt.timedelta(days=21)).isoformat():
                continue
            their_states = {s.lower() for s in states_in(e["title"] + " " + e["snippet"])}
            if my_states and their_states and not (my_states & their_states):
                continue                              # same words, another country: a different story
            key = re.sub(r"[^a-z0-9]+", " ", e["title"].lower()).strip()
            host = _domain(e["url"])
            outlet = _ident(e["source"])
            if key in seen_titles or outlet in seen_outlets or host in seen_outlets or (own_host and host == own_host):
                continue
            if any(_same(outlet, o) for o in seen_outlets):
                continue                              # "Premium Times" and premiumtimesng.com are one outlet
            seen_titles.add(key)
            seen_outlets.add(outlet)
            seen_outlets.add(host)
            e["shared"] = shared
            picks.append(e)
        if len(picks) >= max_sources * 2:
            break
    picks.sort(key=lambda e: (outlet_rank(e["source"], e["url"]), -e["shared"]))
    picks = picks[:max_sources]
    # A cut-off snippet is not a sentence. For the two best copies that link
    # straight to the publisher, read the page for its opening paragraph.
    fetched = 0
    for e in picks:
        if fetched >= 2:
            break
        if "google." in up.urlsplit(e["url"]).netloc:
            continue
        if re.search(r"[.!?\u201d\u2019\"]\s*$", e["snippet"]) and len(e["snippet"].split()) >= 12:
            continue
        try:
            text = page_summary(e["url"])
        except Exception:                             # noqa: BLE001 - boundary
            text = ""
        fetched += 1
        if text and len(text.split()) >= 12:
            e["snippet"] = _clean(text)
    for e in picks:
        # Google News' snippet is the headline followed by the outlet's name.
        src = (e.get("source") or "").strip()
        snip = (e.get("snippet") or "").strip()
        if src and snip.lower().endswith(src.lower()):
            snip = snip[: -len(src)].rstrip(" -|·,")
        if snip and snip[-1] not in ".!?\u201d\u2019\")" and len(snip.split()) <= 25 and snip.lower().startswith(e.get("title", "").lower()[:30]):
            snip = ""                                 # a headline is not an explanation
        e["snippet"] = snip
    return {"sources": [{k: e[k] for k in ("source", "url", "title", "published_at", "snippet")} for e in picks],
            "story": compose(it, picks)}


def compose(it: Dict[str, Any], sources: List[Dict[str, str]], max_words: int = 70) -> str:
    """The item's own explanation first; then the sentences from other copies
    that add a fact it lacks. Whole sentences, no repetition, no boilerplate."""
    base = _clean(it.get("summary_en") or it.get("summary") or "")
    title = (it.get("title") or "").strip().lower()
    if base.lower().startswith(title[:40]) or _PROMO.search(base[:200]):
        base = ""
    parts: List[str] = []
    have: set = set()
    if base:
        first = sentences(base, 45)
        parts.append(first)
        have |= _stems(first)
    ours = _stems(it.get("title_en") or it.get("title") or "")
    for s in sources:
        for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z“‘(])", s.get("snippet") or ""):
            sent = sent.strip()
            if len(sent.split()) < 8 or len(sent.split()) > 45 or _PROMO.search(sent):
                continue
            if sent[-1] not in ".!?”’\"":
                continue                              # a cut-off snippet, not a sentence
            st = _stems(sent)
            if len(st & ours) < 2 or not _FACT.search(sent):
                continue
            if have and len(st & have) >= 0.6 * max(1, len(st)):
                continue                              # says what we already have
            parts.append(sent)
            have |= st
            break                                     # one sentence per outlet
        if sum(len(p.split()) for p in parts) >= max_words:
            break
    return sentences(" ".join(parts), max_words)


def cite(sources: List[Dict[str, str]], limit: int = 3) -> List[Dict[str, str]]:
    """The outlets worth naming beside the story, best first."""
    return [{"source": s["source"], "url": s["url"]} for s in (sources or [])[:limit] if s.get("url")]


def load(raw) -> List[Dict[str, str]]:
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw) if raw else []
    except (ValueError, TypeError):
        return []
