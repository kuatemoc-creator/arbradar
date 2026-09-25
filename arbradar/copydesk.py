"""The copy desk: the editor's brief applied by rule to every entry, every build.

The partner's edit (llm.edit_entries) runs when the editorial tier is on. This
runs always, after it, and enforces what a rule can enforce: house forms for
amounts and spelling, banned words out, a label before a colon off the
headline, an over-long headline closed at a clause, whole sentences within
the cap. It writes out/editor-<date>.json listing every entry, what was
changed, and which entries still need a person: a restated headline where no
source carried text, a headline the rule could not shorten.
"""
import json
import os
import re
from typing import Any, Dict, List

from .explain import explain, MAX_WORDS
from .style import headline as sentence_case

HEADLINE_MAX = 14

_BANNED = re.compile(r"\b(notably|crucially|importantly|landscape|navigate|delve|robust|leverage|game-?changer|unpack|"
                     r"underscores?|highlights? the importance|a testament to|moving forward|at the end of the day|"
                     r"it is worth noting|in today'?s|this development|significant(?:ly)?|landmark|pivotal|"
                     r"stakeholders?|synerg\w+|paradigm)\b", re.I)
_BRITISH = [(re.compile(r"\b(a|the|its|their|his|her|operating|mining|banking|electronic-money|e-money|payments?) license(s?)\b", re.I), r"\1 licence\2"),
            (re.compile(r"\blicense (revoked|suspended|cancelled|canceled|withdrawn)\b", re.I), r"licence \1"),
            (re.compile(r"\bdefense\b", re.I), "defence"), (re.compile(r"\bfavor(s|ed|able|ite)?\b"), r"favour\1"),
            (re.compile(r"\bcenter(s)?\b"), r"centre\1"), (re.compile(r"\borganization(s)?\b"), r"organisation\1"),
            (re.compile(r"\brecogni(z)(e|es|ed|ing|ition)\b"), r"recognis\2"), (re.compile(r"\banaly(z)(e|es|ed|ing)\b"), r"analys\2"),
            (re.compile(r"\blabor\b"), "labour"), (re.compile(r"\bhonor(s|ed)?\b"), r"honour\1"),
            (re.compile(r"\bcanceled\b"), "cancelled"), (re.compile(r"\barbitral award(s)?\b"), r"arbitral award\1")]
_AMOUNT = [(re.compile(r"(?<![A-Za-z$])\$\s?(\d[\d,.]*)\s?(billion|bn|B)\b"), r"US$\1 billion"),
           (re.compile(r"(?<![A-Za-z$])\$\s?(\d[\d,.]*)\s?(million|mn|M)\b"), r"US$\1 million"),
           (re.compile(r"(?<![A-Za-z$])\$\s?(\d[\d,.]*)(?![\d,.])"), r"US$\1"),
           (re.compile(r"\bUSD\s?(\d[\d,.]*)\s?(billion|million|bn|mn)?\b", re.I), lambda m: "US$" + m.group(1) + ({"bn": " billion", "mn": " million", "billion": " billion", "million": " million"}.get((m.group(2) or "").lower(), ""))),
           (re.compile(r"\bEUR\s?(\d[\d,.]*)"), r"€\1"), (re.compile(r"\bGBP\s?(\d[\d,.]*)"), r"£\1"),
           (re.compile(r"(US\$|€|£)(\d[\d,.]*)\s?M\b"), r"\1\2 million"), (re.compile(r"(US\$|€|£)(\d[\d,.]*)\s?bn\b"), r"\1\2 billion")]
_LABEL = re.compile(r"^([A-Z][\w&.'’ -]{1,28}):\s+(?=[A-Z])")
_CLAUSE = re.compile(r"\s(?:over|amid|after|as|following|despite|while|in dispute|in a dispute|in row|in bid|for)\s|,\s")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z“‘(])")


def _forms(text: str) -> str:
    for rx, rep in _AMOUNT:
        text = rx.sub(rep, text)
    for rx, rep in _BRITISH:
        text = rx.sub(rep, text)
    return text


def fix_headline(it: Dict[str, Any]) -> List[str]:
    """Sentence case, label off, house forms, closed at a clause when over-long."""
    notes = []
    h = (it.get("title_en") or it.get("title") or "").strip()
    keep = list(it.get("claimants") or []) + list(it.get("respondents") or []) + list(it.get("counsel") or [])
    new = sentence_case(h, keep)
    m = _LABEL.match(new)
    if m and len(new[m.end():].split()) >= 5:
        new = new[m.end():]
        notes.append("label before colon removed")
    new = _forms(new)
    record = (it.get("source") or "").startswith(("ICSID docket", "Court:", "US federal docket", "PCA", "SEC EDGAR"))
    if len(new.split()) > HEADLINE_MAX and not record:   # a docket line has its own shape
        head = " ".join(new.split()[:HEADLINE_MAX])
        cuts = [c.start() for c in _CLAUSE.finditer(head)]
        cuts = [c for c in cuts if c >= len(head) * 0.45]
        if cuts:
            new = head[:cuts[-1]].rstrip(" ,")
            notes.append("headline closed at a clause")
        else:
            notes.append("headline over {} words; needs a person".format(HEADLINE_MAX))
    if new != h:
        it["title_en"] = new
    return notes


def fix_explanation(it: Dict[str, Any]) -> List[str]:
    """House forms, banned words out (the sentence goes if another remains), whole sentences within the cap."""
    notes = []
    text = explain(it)
    if it.get("_restated"):
        notes.append("no source text: headline restated; needs a person")
    fixed = _forms(text)
    if fixed != text:
        notes.append("amounts or spelling to house form")
    sents = [s for s in _SENT.split(fixed) if s.strip()]
    kept = [s for s in sents if not _BANNED.search(s)]
    if len(kept) < len(sents):
        if kept:
            notes.append("sentence with a banned word dropped")
            fixed = " ".join(kept)
        else:
            fixed = _BANNED.sub("", fixed)
            fixed = re.sub(r"\s{2,}", " ", fixed).replace(" ,", ",").replace(" .", ".").strip()
            notes.append("banned word removed")
    words = fixed.split()
    if len(words) > MAX_WORDS + 10:
        first = _SENT.split(fixed)[0]
        fixed = first if len(first.split()) <= MAX_WORDS + 10 else fixed
        notes.append("explanation cut to its first sentence")
    if fixed and fixed[-1] not in ".!?”’\")":
        fixed = fixed.rstrip(" ,;:") + "."
    it["story"] = fixed
    return notes


def apply(items: List[Dict[str, Any]], date: str, out_dir: str, llm_pass: bool) -> Dict[str, Any]:
    report = {"date": date, "llm_pass": llm_pass, "entries": [], "needs_person": 0}
    for it in items:
        before = (it.get("title_en") or it.get("title") or "", explain(it))
        it["_restated"] = not (it.get("story") or it.get("summary_en") or it.get("summary"))
        notes = fix_headline(it) + fix_explanation(it)
        it.pop("_restated", None)
        needs = any("needs a person" in n for n in notes)
        report["needs_person"] += int(needs)
        report["entries"].append({"headline": it.get("title_en") or it.get("title"), "explanation": it.get("story"),
                                  "before": {"headline": before[0], "explanation": before[1]},
                                  "words": len((it.get("story") or "").split()), "changes": notes,
                                  "margin": it.get("margin"), "needs_person": needs})
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "editor-{}.json".format(date)), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    return report
