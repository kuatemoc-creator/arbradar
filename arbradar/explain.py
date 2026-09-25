"""One explanation per entry, three lines at most, for every entry.

Every headline in the issue gets an explanation of the same shape: whole
sentences, at most about 40 words, opening with the actor. The text comes from
the story built from other outlets, else the source's own summary, else a line
composed from the record (the parties, the State, the forum, the instrument),
else the headline restated with its attribution. Bylines, datelines and
standfirsts glued to a feed summary are stripped first.
"""
import html
import re
from typing import Any, Dict, Optional

from .style import sentences

MAX_WORDS = 36
MAX_CHARS = 230          # three lines at 15px in a 560px column

# "By Joseph Erunke, Abuja ABUJA — The Independent..." / "MUMBAI: The Bombay..."
_BYLINE = re.compile(r"^(?P<lede>.{0,160}?)\s*\bBy [A-Z][\w.'’-]+(?: [A-Z][\w.'’-]+){0,3}(?:,\s*[A-Z][a-z]+)?\s*", re.S)
_DATELINE = re.compile(r"^(?:[A-Z][A-Z .'’-]{2,30}|[A-Z][a-z]+(?: [A-Z][a-z]+)?)\s*[—–:-]\s+(?=[A-Z])")
_TAG = re.compile(r"<[^>]+>")
_TRAILERS = re.compile(r"\s*(?:The post .{0,200}? appeared first on .{0,80}?(?:\.|$)|Read more.{0,40}$|Continue reading.{0,40}$|"
                       r"The article .{0,120} first appeared on .{0,60}\.?$)", re.S)
_LABELS = {
    "new_case_filed": "a new case", "notice_of_intent": "a notice of dispute", "award_issued": "an award",
    "enforcement_action": "enforcement of an award", "annulment_setaside": "a challenge to an award",
    "interim_relief": "interim relief", "s1782_application": "a discovery application",
    "state_measure": "a State measure against an investor", "distress_event": "a measure against an asset",
    "counsel_instructed": "an instruction of counsel", "counsel_change": "a change of counsel",
    "settlement": "a settlement", "commercial_dispute": "a commercial dispute", "funding": "third-party funding",
    "counsel_tender": "a tender for counsel", "lateral_move": "a move", "appointment": "an appointment",
}


def clean(text: str) -> str:
    t = html.unescape(_TAG.sub(" ", text or ""))
    t = re.sub(r"\s+", " ", t).replace("\xa0", " ").strip()
    t = _TRAILERS.sub("", t).strip()
    m = _BYLINE.match(t)
    if m:
        lede = m.group("lede").strip()
        rest = t[m.end():].strip()
        rest = _DATELINE.sub("", rest)
        # keep the standfirst only when it is a sentence of its own
        t = (lede + " " + rest).strip() if lede.endswith((".", "!", "?")) else (rest or lede)
    t = _DATELINE.sub("", t)
    return t.strip()


def _clause_cut(sentence: str, max_words: int) -> str:
    """A sentence over the cap, or one the feed cut short, closed where a
    clause ends: at the last clause boundary within the cap, else at the last
    word that is not a function word. Never mid-phrase."""
    sentence = sentence.rstrip(" .\u2026")
    words = sentence.split()
    if not words:
        return ""
    if len(words) <= max_words and sentence[-1] in "!?\u201d\u2019\")":
        return sentence
    head = words[:max_words]
    text = " ".join(head)
    cut = max(text.rfind(", "), text.rfind("; "), text.rfind(" \u2014 "), text.rfind(" \u2013 "), text.rfind(": "))
    if cut >= len(text) * 0.5:
        return text[:cut].rstrip(" ,;:\u2014\u2013") + "."
    while head and head[-1].lower().strip(",;:") in _FUNCTION:
        head.pop()
    # "...to pay US$480 million over a failed initial": the trailing phrase
    # began at a preposition a few words back; the sentence closes before it.
    idx = [i for i in range(8, len(head)) if head[i].lower().strip(",;:") in _PHRASE_OPENERS]
    if idx and idx[-1] >= len(head) - 7:
        cut = idx[-1]
        while len(idx) >= 2 and cut - idx[-2] <= 3:      # "amid fears of": one chained phrase, cut before it
            idx.pop()
            cut = idx[-1]
        head = head[:cut]
    if len(head) < 8:
        return ""
    return " ".join(head).rstrip(" ,;:") + "."


_PHRASE_OPENERS = {"of", "in", "on", "at", "to", "for", "by", "with", "from", "as", "that", "which", "who", "over",
                   "under", "after", "before", "during", "about", "against", "between", "through", "while", "amid",
                   "into", "than", "and", "or", "but", "because", "since", "until", "unless", "whether", "when",
                   "where", "if", "following", "despite", "including", "without", "within", "via", "per"}
_FUNCTION = {"a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or", "but", "by", "with", "from", "as", "that",
             "which", "who", "whom", "is", "are", "was", "were", "has", "have", "had", "been", "be", "its", "their", "his",
             "her", "than", "into", "over", "under", "after", "before", "during", "about", "against", "between", "through",
             "while", "amid", "per", "via", "not", "no", "nor", "so", "if", "when", "where", "will", "would", "can", "could",
             "may", "might", "shall", "should", "this", "these", "those", "such", "also", "both", "either", "another",
             "other", "any", "some", "each", "every", "all", "most", "several", "many", "using", "including", "without",
             "within", "because", "since", "until", "unless", "whether", "what", "how", "why", "then", "yet", "just"}


def from_record(it: Dict[str, Any]) -> str:
    """One sentence from what the record says: parties, State, forum, instrument, amount."""
    claimants = [c for c in (it.get("claimants") or []) if c]
    respondents = [r for r in (it.get("respondents") or []) if r]
    states = [s for s in (it.get("states") or []) if s]
    forum = (it.get("forum") or "").strip()
    treaty = (it.get("treaty") or it.get("instrument") or "").strip()
    amount = it.get("amount_usd")
    kind = _LABELS.get(it.get("event_type") or "", "")
    parts = []
    if claimants and (respondents or states):
        parts.append("{} against {}".format(", ".join(claimants[:2]), ", ".join((respondents or states)[:2])))
    if not (claimants or forum or treaty or amount):
        return ""                                     # a State name alone explains nothing the headline does not
    if forum:
        parts.append("at {}".format(forum))
    if treaty:
        parts.append("under the {}".format(treaty))
    if amount:
        try:
            parts.append("US${:,.0f} million at stake".format(float(amount) / 1e6))
        except (TypeError, ValueError):
            pass
    if not parts:
        return ""
    s = ("{}: ".format(kind[:1].upper() + kind[1:]) if kind else "") + "; ".join(parts) + "."
    return s[:1].upper() + s[1:]


def restated(it: Dict[str, Any]) -> str:
    """Nothing but a headline on record: the brief says print the headline and
    the source line and stop. No note, no restatement. The copy desk flags the
    entry for a person, and the editor pass writes the line from the record
    when it runs."""
    return ""


def fit(text: str, max_chars: int = MAX_CHARS) -> str:
    """Whole sentences within the character cap; the last one closed at a clause if it must be."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z\u201c\u2018(])", text) if p.strip()]
    out = ""
    for p in parts:
        if len((out + " " + p).strip()) <= max_chars:
            out = (out + " " + p).strip()
        else:
            break
    if out:
        return out
    head = parts[0][:max_chars]
    head = head[:head.rfind(" ")] if " " in head else head
    return _clause_cut(head, 10 ** 6)


def explain(it: Dict[str, Any], max_words: int = MAX_WORDS) -> str:
    """The explanation printed under a headline: never empty, never over three lines."""
    from .email_html import summary_of
    c = from_court(it)                                # a judgment row is composed from the judgment, never from the search hit
    if c:
        return fit(c) or c
    for text in (it.get("story") or "", summary_of(it) or ""):
        t = clean(text)
        if not t:
            continue
        s = sentences(t, max_words)
        if s and len(s.split()) <= max_words + 5:
            f = fit(s)
            if f:
                return f
        first = re.split(r"(?<=[.!?])\s+(?=[A-Z“‘(])", t)[0]
        first = first.strip()
        if first.endswith(("\u2026", "...")):
            first = first.rstrip(" .\u2026")            # cut by the feed: close it at a clause below
        elif first and first[-1] in ".!?\u201d\u2019\")" and len(first.split()) <= max_words + 10:
            f = fit(first)
            if f:
                return f                              # one whole sentence a little over the cap beats a cut one
        c = _clause_cut(first, max_words)
        if c:
            return c
    rec = it.get("record") if isinstance(it.get("record"), dict) else None
    if rec and rec.get("snippet"):
        t = re.sub(r"\s*Parties:.*$", "", clean(rec["snippet"])).strip()
        letters = [ch for ch in t if ch.isalpha()]
        shouting = bool(letters) and sum(1 for ch in letters if ch.isupper()) / len(letters) > 0.3
        if t and len(t.split()) >= 6 and not shouting:                  # a caption block is not an explanation
            s = sentences(t, max_words) or _clause_cut(t, max_words)
            if s:
                return fit("{} ({}).".format(s.rstrip("."), _record_name(rec))) or s
    r = from_record(it)
    if r:
        return fit(r) or r
    return fit(restated(it)) or restated(it)


def _record_name(rec: Dict[str, Any]) -> str:
    src = rec.get("source") or "record"
    if src == "US federal docket":
        m = re.search(r"\(([^)]*\d[^)]*)\)\s*$", rec.get("title") or "")
        return "US docket " + m.group(1) if m else "US federal docket"
    if src == "ICSID docket":
        return "ICSID case page"
    return src


_CATCH = re.compile(r"Catchwords?:\s*(.+?)(?:\.|$)")
_COURT_HEAD = re.compile(r"^(?P<court>[^,.]+?)(?:,| decided on)\s+(?P<date>\d{1,2} \w+ \d{4})(?:,\s*(?P<cite>\[[^\]]+\][^.]*|\d{4} \w+ \d+))?")


def from_court(it: Dict[str, Any]) -> str:
    """A judgment row: the court, the date, the citation and the catchwords the
    court itself gave; never the search phrase that matched."""
    if not (it.get("source") or "").startswith("Court:"):
        return ""
    text = clean(it.get("summary") or "")
    m = _COURT_HEAD.match(text)
    court = m.group("court").strip() if m else (it.get("source") or "")[6:].strip()
    date = m.group("date") if m else ""
    cite = (m.group("cite") or "").strip() if m else ""
    catch = _CATCH.search(text)
    what = catch.group(1).strip() if catch else (it.get("flag_reason") or "").strip()
    what = re.sub(r"^[^:]{0,40}:\s*", "", what).strip()             # "High Court: enforcement of an award" -> the matter
    what = re.sub(r"^matched the phrase.*$", "", what, flags=re.I).strip()
    if not what:
        low = text.lower()
        what = ("enforcement of an arbitral award" if "enforc" in low else "an arbitral award" if "award" in low
                else "an arbitration agreement" if "agreement" in low else "arbitration")
    parts = ["{} judgment{}{}".format(court, " of " + date if date else "", ", " + cite if cite else "")]
    what = what[:1].lower() + what[1:]
    if "judgment" in what or "related" in what:
        parts.append("in an arbitration-related matter")
    else:
        parts.append(what if what.startswith(("on ", "in ", "under ")) else "on " + what)
    out = " ".join(parts).strip()
    return out[:1].upper() + out[1:].rstrip(".") + "."
