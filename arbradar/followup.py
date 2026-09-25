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


_ACT = re.compile(r"\b(award|arbitration|arbitral|annul\w*|set aside|enforce\w*|confirm\w*|vacat\w*|tribunal|ICSID|claim|dispute|"
                  r"treaty|expropriat\w*|licen[cs]e|concession|notice|settle\w*|damages|immunity|attach\w*|seiz\w*)\b", re.I)


_FORUMS = [("nl", r"\b(Dutch|Netherlands|Amsterdam|Hague|rechtbank|gerechtshof)\b"),
           ("en", r"\b(English|England|EWHC|EWCA|Commercial Court|London court|High Court of Justice|UK Supreme Court)\b"),
           ("us", r"\b(US|U\.S\.|American|federal|district court|Circ\.?|Circuit|D\.C\.|S\.D\.N\.Y\.|DC Judge|magistrate)\b"),
           ("fr", r"\b(Paris|French|Cour de cassation|cour d'appel)\b"), ("ch", r"\b(Swiss|Switzerland|Federal Tribunal)\b"),
           ("sg", r"\b(Singapore|SICC|SGCA|SGHC)\b"), ("hk", r"\b(Hong Kong|HKCFI|HKCA)\b"), ("in", r"\b(Delhi High Court|Bombay High Court|Indian Supreme Court|Supreme Court of India)\b"),
           ("au", r"\b(Australia|Australian|HCA|Federal Court of Australia)\b"), ("ca", r"\b(Canada|Canadian|Ontario|Quebec|Québec)\b"),
           ("de", r"\b(German|Germany|Bundesgerichtshof|BGH|Oberlandesgericht)\b"), ("se", r"\b(Swedish|Sweden|Svea)\b")]
_FORUM_RX = [(k, re.compile(rx)) for k, rx in _FORUMS]


def _forum(text: str) -> str:
    """The court's jurisdiction a headline names, if any: 'Dutch appellate court' is nl, '9th Circ.' is us."""
    for k, rx in _FORUM_RX:
        if rx.search(text or ""):
            return k
    return ""


def _flat(title: str) -> str:
    """A headline with hyphens and possessives undone and every State under its
    plain name: 'Iraq-Türkiye pipeline' compares as 'Iraq Turkey pipeline'."""
    from .sources.editions import COUNTRIES, _HYPHENATED
    t = title or ""
    for f in _HYPHENATED:
        t = t.replace(f, f.replace("-", "\u2011"))
    t = re.sub(r"(?<=\w)[\u2019'](?:s\b)?", "", t.replace("-", " ").replace("/", " ")).replace("\u2011", "-")
    forms = sorted((f for f in COUNTRIES if len(f) >= 4), key=len, reverse=True)
    for f in forms:
        canon = COUNTRIES[f]
        if f != canon and f in t:
            t = re.sub(r"(?<![\w-])" + re.escape(f) + r"(?![\w-])", canon, t)
    return t


def _queries(it: Dict[str, Any]) -> List[str]:
    """A few phrasings that find other copies of the same story: the States
    named (under their plain names), the companies named, the act. Hyphens and
    possessives are undone first: 'Iraq-Türkiye' is Iraq and Turkey, 'Laos''
    is Laos."""
    from .sources.editions import COUNTRIES
    title = it.get("title_en") or it.get("title") or ""
    flat = re.sub(r"[\u2019']s?\b", "", title.replace("-", " ").replace("/", " "))
    states = []
    for s in states_in(flat):
        plain = {"United States": "US", "United Kingdom": "UK", "United Arab Emirates": "UAE", "Congo (DRC)": "Congo",
                 "Congo (Brazzaville)": "Congo", "Korea": "Korea"}.get(s, s)
        if plain not in states:
            states.append(plain)
    states = [s for s in states if s not in ("US", "UK")][:3] or states[:2]
    ents = []
    for w in re.findall(r"\b[A-Z][A-Za-z&.]{2,}(?:\s+[A-Z][A-Za-z&.]{2,}){0,2}", flat):
        if _stem(w.split()[0].lower()) in _entities(flat) and w not in ents and not states_in(w):
            ents.append(w)
    acts = [m.group(1).lower() for m in _ACT.finditer(flat)]
    order = ("award", "arbitration", "arbitral", "tribunal", "icsid", "treaty", "expropriation", "enforcement", "annulment")
    acts = sorted(dict.fromkeys(a for a in acts if a not in ("dispute", "claim")),
                  key=lambda a: next((i for i, o in enumerate(order) if a.startswith(o[:5])), 99))[:2] or ["arbitration"]
    names = [n for n in (it.get("claimants") or []) + (it.get("respondents") or []) if n][:2]
    out = []
    if names:
        out.append(" ".join('"{}"'.format(n) for n in names) + " " + " ".join(acts[:1]))
    if ents:
        out.append(" ".join('"{}"'.format(e) for e in ents[:2]) + " " + " ".join(acts[:1]))
    if len(states) >= 2:
        out.append(" ".join('"{}"'.format(s) for s in states[:2]) + " " + " ".join(acts[:1]))
    elif states:
        out.append('"{}" {}'.format(states[0], " ".join(acts[:2])))
    if re.search(r"\b(court|judge|magistrate|circuit|tribunal)\b", flat, re.I):
        anchor = " ".join('"{}"'.format(x) for x in (ents[:1] or states[:2]))
        if anchor:
            out.append(anchor + " court " + " ".join(acts[:1]))
    words = [w for w in _sig(flat) if w.isascii()]
    if len(words) >= 3:
        out.append(" ".join(words[:6]))
    return list(dict.fromkeys(q for q in out if len(q.split()) >= 2))[:5]


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
    title = _flat(it.get("title_en") or it.get("title") or "")
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
    # Copies already in our own database come first: the outlets' own feeds,
    # with their own text, linking straight to the publisher.
    for e in _local_copies(it, title, ours, my_states, seen_outlets, seen_titles):
        seen_titles.add(re.sub(r"[^a-z0-9]+", " ", e["title"].lower()).strip())
        seen_outlets.add(_ident(e["source"]))
        seen_outlets.add(_domain(e["url"]))
        picks.append(e)
    for q in _queries(it)[:3]:
        for e in _entries(q):
            theirs = _stems(_flat(e["title"]))
            shared = len(ours & theirs)
            _dbg = __import__("os").environ.get("ARB_DEBUG")
            if shared < 2:
                if _dbg: print("   reject stems<2:", e["title"][:60])
                continue                              # the anchoring below does the real work; two stems is the floor
            # Common words alone ("launches", "arbitration", "group") join two
            # different stories; a shared name or the same State must anchor it.
            same_state = bool(my_states & {s.lower() for s in states_in(e["title"] + " " + e["snippet"])})
            # A company named on one side and not the other is another matter:
            # Turkey revoking Papel's licence is not Turkey revoking Bank
            # Mellat's, and the Bombay court's anti-suit order is not its
            # defamation ruling. Only when neither headline names a company can
            # the State and the wording carry the match.
            my_ents = _entities(title)
            their_ents = _entities(e["title"]) | _entities(e.get("snippet") or "")
            if my_ents and not (my_ents & their_ents):
                if _dbg: print("   reject ents:", e["title"][:60], my_ents, their_ents)
                continue                              # the party in our headline is nowhere in theirs: another matter
            if not my_ents and not same_state:
                if _dbg: print("   reject no state:", e["title"][:60])
                continue                              # a headline that names only States is matched on those States
            from .pipeline import shared_propers
            if not shared_propers(title, e["title"] + " " + (e.get("snippet") or "")):
                if _dbg: print("   reject propers:", e["title"][:60])
                continue                              # no name in common beyond the words of the trade
            # The same parties before different courts are different stories:
            # the Dutch appeal in Devas is not the Ninth Circuit's rehearing.
            mine_forum, theirs_forum = _forum(title), _forum(e["title"] + " " + (e.get("snippet") or ""))
            if mine_forum and theirs_forum and mine_forum != theirs_forum:
                if _dbg: print("   reject forum:", e["title"][:60], mine_forum, theirs_forum)
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
    # Copies already in our own database - the outlets' own feeds, with their
    # own text - come before anything the web search found: they link straight
    # to the publisher and carry a paragraph, not a headline.
    picks.sort(key=lambda e: (0 if e.get("local") else 1, outlet_rank(e["source"], e["url"]), -e["shared"]))
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


def _local_copies(it, title, ours, my_states, seen_outlets, seen_titles) -> List[Dict[str, str]]:
    """Other outlets' copies of the story already fetched into the database:
    matched on the same names and States as the web copies, same guards."""
    from . import db
    from .pipeline import shared_propers
    out: List[Dict[str, str]] = []
    when = str(it.get("published_at") or "")[:10] or dt.date.today().isoformat()
    try:
        lo = (dt.date.fromisoformat(when) - dt.timedelta(days=14)).isoformat()
        hi = (dt.date.fromisoformat(when) + dt.timedelta(days=3)).isoformat()
    except ValueError:
        return out
    try:
        conn = db.connect()
        rows = conn.execute("SELECT id, title, title_en, url, source, summary, published_at FROM items WHERE id != ? "
                            "AND COALESCE(published_at, substr(fetched_at,1,10)) BETWEEN ? AND ? AND url NOT LIKE '%news.google.com%' "
                            "AND length(COALESCE(summary,'')) > 60 AND source NOT LIKE 'Court:%' AND source NOT IN ('ICSID docket','SEC EDGAR')",
                            (it.get("id") or -1, lo, hi)).fetchall()
    except Exception:                                 # noqa: BLE001 - boundary
        return out
    my_ents = _entities(title)
    mine_forum = _forum(title)
    for r in rows:
        t2 = _flat(r["title_en"] or r["title"] or "")
        shared = len(ours & _stems(t2))
        if shared < 1:
            continue                                  # the name and forum checks below carry a local copy
        outlet = _ident((r["source"] or "").replace("Google News / ", ""))
        if outlet in seen_outlets or any(_same(outlet, o) for o in seen_outlets):
            continue
        key = re.sub(r"[^a-z0-9]+", " ", t2.lower()).strip()
        if key in seen_titles:
            continue
        text2 = t2 + " " + (r["summary"] or "")
        their_ents = _entities(text2)
        if my_ents and not (my_ents & their_ents):
            continue
        same_state = bool(my_states & {x.lower() for x in states_in(text2)})
        if not my_ents and not same_state:
            continue
        if not shared_propers(title, text2):
            continue
        f2 = _forum(text2)
        if mine_forum and f2 and mine_forum != f2:
            continue
        out.append({"title": r["title"], "source": (r["source"] or "").replace("Google News / ", ""), "url": r["url"],
                    "published_at": r["published_at"] or "", "snippet": _clean(r["summary"] or ""), "shared": shared, "local": True})
        if len(out) >= 3:
            break
    return out


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
