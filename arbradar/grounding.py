"""The last check before anything prints: every sentence must come from a source we cite.

A practitioner who reads one made-up clause never opens the next issue. So
each sentence of an explanation is tested against the evidence on hand - the
item's own text, the corroborating outlets' text, the page text read for it -
and a sentence that is not found there, near-verbatim, is dropped. What is
left is printed; if nothing is left, the entry prints as a headline and a
source line, which is honest, rather than as prose, which would not be.

This also gates the model tier: a summary written by the model is vetted the
same way, so it may compress the sources but not add to them.
"""
import json
import os
import re
from typing import Any, Dict, List, Tuple

from .enrich import _sig, _stem

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z“‘(])")
_FRAGMENT = re.compile(r"(?:…|\.\.\.)\s*$|^[a-z]")


def _stems(text: str) -> List[str]:
    return [_stem(w.lower()) for w in _sig(text or "")]


def _evidence(it: Dict[str, Any]) -> List[str]:
    texts = [it.get("summary") or "", it.get("body") or "", it.get("page_text") or ""]
    for s in it.get("corroboration") or []:
        if isinstance(s, dict):
            texts.append(s.get("snippet") or "")
            texts.append(s.get("title") or "")
    return [t for t in texts if t]


def grounded(sentence: str, evidence: List[str], min_share: float = 0.7) -> bool:
    """True when at least `min_share` of the sentence's content words appear in
    one piece of evidence. Near-verbatim copying passes; paraphrase mostly
    passes; an added fact (a number, a name, a claim) that no source carries
    pulls the share down and fails."""
    words = _stems(sentence)
    if len(words) < 3:
        return True                                   # too short to carry a claim of its own
    need = set(words)
    for text in evidence:
        have = set(_stems(text))
        if len(need & have) >= min_share * len(need):
            # Numbers and currency amounts are the facts most often invented:
            # every one in the sentence must be in this same piece of evidence.
            nums = re.findall(r"\d[\d,.]*", sentence)
            if all(n in text for n in nums):
                return True
    return False


def vet(it: Dict[str, Any]) -> Tuple[str, List[str]]:
    """The explanation with every ungrounded sentence removed, and what was removed."""
    text = (it.get("story") or it.get("summary_en") or "").strip()
    if not text:
        return "", []
    evidence = _evidence(it)
    kept, dropped = [], []
    for sent in _SENT.split(text):
        sent = sent.strip()
        if not sent:
            continue
        if _FRAGMENT.search(sent) or sent[-1] not in ".!?”’\")":
            dropped.append(sent)                      # a cut-off piece is not a sentence
            continue
        if grounded(sent, evidence):
            kept.append(sent)
        else:
            dropped.append(sent)
    return " ".join(kept), dropped


def apply(items: List[Dict[str, Any]], date: str, out_dir: str) -> Dict[str, Any]:
    """Vet every entry in place and write the report for the day."""
    report = {"date": date, "entries": []}
    for it in items:
        before = it.get("story") or it.get("summary_en") or ""
        text, dropped = vet(it)
        if before:
            if it.get("story"):
                it["story"] = text
            else:
                it["summary_en"] = text
        report["entries"].append({
            "title": it.get("title_en") or it.get("title"), "url": it.get("url"),
            "source": (it.get("source") or "").replace("Google News / ", ""),
            "cited": [s.get("source") for s in (it.get("corroboration") or []) if isinstance(s, dict)],
            "sentences_kept": len(_SENT.split(text)) if text else 0,
            "sentences_dropped": dropped,
            "explanation": "built" if it.get("story") else "source text" if it.get("summary") else "none",
        })
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "grounding-{}.json".format(date)), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    report["dropped"] = sum(len(e["sentences_dropped"]) for e in report["entries"])
    return report
