"""House style applied by rule: headlines in sentence case without prefixes,
explanations that end on a sentence. See docs/house-style.md."""
import os
import re

# Words that are lower case in a sentence-case headline. Anything not listed
# and capitalised is treated as a name and left alone.
_COMMON = set("""a an the and or but nor of to in on at by for from with without over under into onto out
up down off after before during until against about across along among around between beyond despite
through toward towards within amid as than via per is are was were be been being has have had do does did
will would shall should may might can could must not no its their his her our your this that these those
it he she they we you who whom whose which what when where why how new old more most less least first second
third last next big small large major minor top key own same other another such each every all any some both
few many much several wins win won loses lose lost defeats defeat seeks seek sought threatens threaten launches
launch files file filed lodges lodge brings bring pursues pursue enforces enforce pays pay settles settle fails
fail faces face avoids avoid upholds uphold annuls annul sides side sends send orders order joins join leaves
leave names name instructs instruct takes take rejoins opens open probes probe rules rule declares declare
grants grant denies deny rejects reject dismisses dismiss revives revive overturns overturn confirms confirm
appeals appeal loses claims claim case cases award awards arbitration arbitrations tribunal tribunals court
courts judge judges investor investors investment investments company companies contractor contractors
dispute disputes damages billion million crore lakh over under against between dollar dollars euro euros
contract contracts concession concessions project projects plant plants mine mines mining oil gas power energy
renewable renewables solar wind bank banks insurer insurers shipbuilder airline airlines steelmaker steel
group state states government governments ministry minister court's state's treaty treaties claim's
seizure seizures seized seizes nationalisation nationalization expropriation licence license licences
licenses revoked revokes revoke cancels cancel cancelled terminated terminates termination sanctions sanction
tax taxes windfall asylum scheme deal deals talks fight row saga bid bids move moves head heads partner partners
lawyer lawyers firm firms boutique office offices practice practices team teams chair co-chair counsel
annulment enforcement immunity estoppel discovery attachment freeze freezing assets asset interim measures
emergency arbitrator arbitrators appointed appoints appointment appointments named naming resigns resigned
delays delay hearing hearings ruling rulings decision decisions judgment judgments finding findings
stake stakes plans plan planned set aside vacate vacates vacated confirm annul liable win loss victory
takes took gets got says said reports report announces announce reveals reveal told tells warns warn
completes complete ends end ended begins begin started starts start
prima facie de novo ex parte inter alia ultra vires bona fide res judicata lis pendens forum non conveniens
pro rata per se ad hoc mutatis mutandis sub judice rem personam ratione materiae temporis personae amicus curiae
aequo bono jure facto obiter locus standi maintainable clarifies clarify corrects correct refers refer larger
bench linked backed owned led based listed run held holds hold beats beat beaten""".split())

# The larger list is measured from the texts we have read (tools/wordlist.py):
# words seen in lower case mid-sentence far more often than capitalised.
_WORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "lowercase-words.txt")
try:
    with open(_WORDS_FILE, encoding="utf-8") as _fh:
        _COMMON |= {w.strip() for w in _fh if w.strip()}
except OSError:
    pass


def headline(text: str, keep=()) -> str:
    """Sentence case for a Title Case headline; prefixes and outlet suffixes off.

    `keep` is the names the item already knows - parties, counsel, institution -
    so that Reliance Infrastructure stays a company and not two common words."""
    kept = {w.lower() for name in (keep or []) if name for w in re.findall(r"[A-Za-z][A-Za-z'’-]+", str(name))}
    t = (text or "").strip()
    t = re.sub(r"^(?:BREAKING|UPDATE|UPDATED|EXCLUSIVE|WATCH|VIDEO|OPINION|ANALYSIS)\s*[:\u2013\u2014-]\s*", "", t, flags=re.I)
    t = re.sub(r"\s+[|\u2013\u2014-]\s+[A-Z][\w .&'-]{2,40}$", "", t)          # " - The Hindu"
    t = re.sub(r"\s*\((?:Reuters|Bloomberg|AP|AFP)\)\s*$", "", t)
    words = t.split()
    if len(words) < 4:
        return t
    caps = [w for w in words[1:] if w[:1].isupper() and not w.isupper()]
    if len(caps) < 0.6 * (len(words) - 1):
        return t                                           # already sentence case
    out = [words[0]]
    for i, w in enumerate(words[1:], 1):
        if w.isupper() or _in_name(words, i) or re.sub(r"[^A-Za-z'’-]", "", w).lower() in kept:
            out.append(w)
            continue
        # Each part of a hyphenated compound is judged on its own: Fridman-Linked.
        parts = w.split("-")
        for j, part in enumerate(parts):
            core = re.sub(r"[^A-Za-z']", "", part)
            if core and not part.isupper() and _is_common(core.lower()):
                parts[j] = part.replace(core, core.lower(), 1)
        out.append("-".join(parts))
    return " ".join(out)


def _is_common(w: str) -> bool:
    """In the list, or an inflection of a word in the list: corrects, referred, holding."""
    if w in _COMMON:
        return True
    for suffix in ("s", "es", "ed", "d", "ing", "ly", "er", "est"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            stem = w[: -len(suffix)]
            if stem in _COMMON or stem + "e" in _COMMON or (stem[-1:] == stem[-2:-1] and stem[:-1] in _COMMON):
                return True
    return False


# A common noun that follows a name is part of the name: Delhi High Court,
# Singapore Court of Appeal, Central Bank of Nigeria, Dangote Group.
_INSTITUTION = set("court courts tribunal bank ministry authority commission council chamber centre center "
                   "institute association corporation board agency university group high supreme federal".split())
_DEMONYM = re.compile(r"(ish|ese|ian|ean|an|ch|ic|i)$", re.I)
_CITIES_I = {"delhi", "mumbai", "dubai", "dhabi", "nairobi", "karachi", "hanoi", "helsinki", "tbilisi", "abu"}


def _in_name(words, i: int) -> bool:
    core = re.sub(r"[^A-Za-z'-]", "", words[i]).lower()
    # Court of Appeal, Bank of England: the noun after "of" belongs to the name too.
    if i >= 2 and words[i - 1].lower() == "of" and re.sub(r"[^A-Za-z'-]", "", words[i - 2]).lower() in _INSTITUTION \
            and words[i - 2][:1].isupper() and words[i][:1].isupper():
        return True
    if core not in _INSTITUTION:
        return False
    prev = re.sub(r"[^A-Za-z'-]", "", words[i - 1])
    if not prev or not prev[0].isupper() or prev.isupper() and len(prev) <= 2:
        return False
    if prev.lower() in _COMMON:
        return False
    if _DEMONYM.search(prev) and prev.lower() not in _CITIES_I and prev.lower() not in _INSTITUTION:
        return False                                   # "Turkish contractor", "Spanish group": an adjective, not a name
    return True


def sentences(text: str, max_words: int = 55) -> str:
    """Whole sentences up to about max_words; the first sentence is kept whole
    whatever its length. Never an ellipsis inside a sentence."""
    t = re.sub(r"\s+", " ", (text or "")).strip()
    if not t:
        return ""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\u201c\u2018(])", t)
    out, n = [], 0
    for p in parts:
        w = len(p.split())
        if out and n + w > max_words:
            break
        out.append(p)
        n += w
    s = " ".join(out).strip()
    if s and s[-1] not in ".!?\u201d\u2019\"":
        s = s.rstrip(",;:\u2026 ") + ("" if s.endswith("\u2026") else ".")
    return s
