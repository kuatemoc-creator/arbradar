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
    """A sentence longer than the cap, closed at its last clause boundary within it."""
    words = sentence.split()
    if len(words) <= max_words:
        return sentence
    head = " ".join(words[:max_words])
    cut = max(head.rfind(", "), head.rfind("; "), head.rfind(" — "), head.rfind(" – "), head.rfind(": "))
    if cut < len(head) // 2:
        return ""                                     # no clause to close on: leave it to the fallback
    return head[:cut].rstrip(" ,;:—–") + "."


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
    """The headline as a sentence with its attribution, when nothing else is on record."""
    from .email_html import _outlet, title_of
    title = title_of(it).strip().rstrip(".")
    if not title:
        return ""
    from .sources.editions import states_in
    outlet = _outlet(it.get("source") or "") or "The source"
    w = title.split()[0]
    proper = w.isupper() or (len(w) > 1 and w[1:2].isupper()) or bool(states_in(w)) or w in ("I",)
    body = title if proper else title[:1].lower() + title[1:]
    return "{} reports that {}.".format(outlet, body)


def explain(it: Dict[str, Any], max_words: int = MAX_WORDS) -> str:
    """The explanation printed under a headline: never empty, never over the cap."""
    from .email_html import summary_of
    for text in (it.get("story") or "", summary_of(it) or ""):
        t = clean(text)
        if not t:
            continue
        s = sentences(t, max_words)
        if s and len(s.split()) <= max_words + 5:
            return s
        first = re.split(r"(?<=[.!?])\s+(?=[A-Z“‘(])", t)[0]
        first = first.strip()
        if first and first[-1] in ".!?\u201d\u2019\")" and len(first.split()) <= max_words + 10:
            return first                              # one whole sentence a little over the cap beats a cut one
        c = _clause_cut(first, max_words)
        if c:
            return c
    r = from_record(it)
    if r:
        return r
    return restated(it)
