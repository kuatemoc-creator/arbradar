"""House style applied by rule: headlines in sentence case without prefixes,
explanations that end on a sentence. See docs/house-style.md."""
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
completes complete ends end ended begins begin started starts start""".split())


def headline(text: str) -> str:
    """Sentence case for a Title Case headline; prefixes and outlet suffixes off."""
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
    for w in words[1:]:
        core = re.sub(r"[^A-Za-z'-]", "", w)
        if core and not w.isupper() and core.lower() in _COMMON:
            w = w.replace(core, core.lower(), 1)
        out.append(w)
    return " ".join(out)


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
