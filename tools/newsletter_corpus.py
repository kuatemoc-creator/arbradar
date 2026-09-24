#!/usr/bin/env python3
"""Build the style corpus from the newsletters archived under data/newsletters/raw.

The raw emails are the publishers' subscription content, so they stay on the
machine (data/ is gitignored) and in the inbox they came from. What the repo
keeps is derived: an index of every issue, every headline, and the measured
shape of the copy - enough to rebuild the house style, and enough to re-fetch
the raw text from Gmail by thread id if it is ever needed again.

    data/newsletters/raw/gar/<thread>.txt        plain text of the email
    data/newsletters/raw/gar/<thread>.json       date, subject, sender
    data/newsletters/raw/iareporter/...          same

Writes
    docs/style-corpus/index.json     one row per issue (id, date, subject, counts)
    docs/style-corpus/headlines.json every headline with its section and date
    docs/style-corpus/stats.json     the measurements the house style rests on
    docs/style-corpus/README.md      the same, readable
    data/newsletters/corpus.json     everything, standfirsts included (local only)
"""
import collections
import glob
import json
import os
import re
import statistics
import sys
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "newsletters", "raw")
OUT_DOCS = os.path.join(ROOT, "docs", "style-corpus")
OUT_LOCAL = os.path.join(ROOT, "data", "newsletters", "corpus.json")

SEP = "------------------------------"
GAR_FOOTER = ("Subscribe", "Follow on LinkedIn", "Law Business Research", "Manage your email",
              "To receive our emails", "Registered in England", "View in browser", "GAR logo")
_SECTION = re.compile(r"^[A-Z][A-Z0-9'’&/\-\s]{3,}?(?:\s+(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4}))?$")
_IAR_ITEM = re.compile(r"^(.*?)\s+\((https?://[^\s)]+)\)\s*$")
_IAR_LABEL = re.compile(r"^(\[[^\]]+\]|[A-Z][A-Za-z\- ]{2,24}:)\s*")
_MONTHS = {m: i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July",
                                       "August", "September", "October", "November", "December"), 1)}


def _sidecar(path: str) -> Dict[str, Any]:
    try:
        with open(path[:-4] + ".json", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _iso(day: str, month: str, year: str) -> str:
    return "{}-{:02d}-{:02d}".format(year, _MONTHS.get(month, 1), int(day))


# ----------------------------------------------------------------------------
# GAR daily briefing
# ----------------------------------------------------------------------------

def parse_gar(text: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    subject = (meta.get("subject") or "").strip()
    issue_date = (meta.get("date") or "")[:10]
    section: Optional[str] = None
    sections: List[str] = []
    items: List[Dict[str, Any]] = []
    for block in text.split(SEP):
        lines = [l.rstrip() for l in block.split("\n")]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            continue
        # A section header may open the block; anything above it is the mail's
        # own title line, not a story.
        hdr_at = None
        for i, l in enumerate(lines[:4]):
            s = re.sub(r"\s+\d{1,2}\s+[A-Z][a-z]+\s+\d{4}$", "", l.strip())
            if s and not s.startswith("[") and s == s.upper() and re.search(r"[A-Z]{3}", s) and len(s.split()) <= 6:
                hdr_at = i
        if hdr_at is not None:
            s = lines[hdr_at].strip()
            m = re.search(r"(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})$", s)
            if m:
                issue_date = _iso(*m.groups())
                s = s[: m.start()].strip()
            section = s.title().replace("'S", "'s").replace("’S", "’s")
            if section not in sections:
                sections.append(section)
            lines = lines[hdr_at + 1:]
            while lines and not lines[0].strip():
                lines.pop(0)
        if not lines:
            continue
        head = lines[0].strip()
        if head.startswith("[") or any(head.startswith(f) for f in GAR_FOOTER):
            if head.startswith("Subscribe"):
                break
            continue
        url = ""
        rest: List[str] = []
        for l in lines[1:]:
            s = l.strip()
            if s.startswith("[http") and s.endswith("]"):
                if not url:
                    url = s[1:-1]
                continue
            if s and not s.startswith("["):
                rest.append(s)
        blurb = re.sub(r"\s+", " ", " ".join(rest)).strip()
        if not url and not blurb:
            continue
        items.append({"section": section or "Today's Headlines", "headline": head, "url": url, "blurb": blurb})
    return {"source": "gar", "id": meta.get("id"), "date": issue_date, "subject": subject,
            "sections": sections, "items": items}


# ----------------------------------------------------------------------------
# IAReporter latest headlines
# ----------------------------------------------------------------------------

def parse_iar(text: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    section = "Latest Headlines"
    sections: List[str] = []
    items: List[Dict[str, Any]] = []
    topics: List[str] = []
    for raw in text.split("\n"):
        s = raw.strip()
        if not s:
            continue
        low = s.lower()
        if low in ("latest headlines", "previous headlines", "documents for download") or low.startswith("notable legal topics"):
            section = "Notable legal topics" if low.startswith("notable") else s.title()
            if section not in sections:
                sections.append(section)
            continue
        if section == "Notable legal topics" and " > " in s:
            chain = re.sub(r"\s*\(As discussed here.*$", "", s)
            chain = re.sub(r"\s*\(https?://[^)]*\)", "", chain)
            chain = re.sub(r"\s*>\s*", " > ", re.sub(r"\s+", " ", chain)).strip(" )")
            topics.append(chain)
            continue
        m = _IAR_ITEM.match(s)
        if not m:
            continue
        title, url = m.group(1).strip(), m.group(2)
        if "/articles/" in url:
            label = ""
            lm = _IAR_LABEL.match(title)
            if lm and len(lm.group(1)) < 26:
                label = lm.group(1).strip("[]: ")
                title = title[lm.end():].strip()
            items.append({"section": section if section in ("Latest Headlines", "Previous Headlines") else "Latest Headlines",
                          "headline": title, "label": label, "url": url, "blurb": ""})
        elif "download.php" in url:
            items.append({"section": "Documents", "headline": title, "label": "", "url": url, "blurb": ""})
    return {"source": "iareporter", "id": meta.get("id"), "date": (meta.get("date") or "")[:10],
            "subject": (meta.get("subject") or "").strip(), "sections": sections, "items": items, "topics": topics}


# ----------------------------------------------------------------------------
# measurements
# ----------------------------------------------------------------------------

_AMOUNT = re.compile(r"(US\$|€|£|\$|\b\d[\d,.]*\s*(?:million|billion|bn|m)\b)", re.I)
_INST = re.compile(r"\b(ICC|ICSID|LCIA|SIAC|HKIAC|UNCITRAL|PCA|SCC|DIAC|NAFTA|ECT|Energy Charter Treaty|CJEU|ITLOS|AAA|ICDR|CAS|VIAC|JAMS|CIETAC|LMAA|DIS|SCAI)\b")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z“\"])")
_VERBS = ("wins", "loses", "faces", "defeats", "beats", "enforces", "seeks", "pursues", "launches", "files", "brings",
          "threatens", "fails", "upholds", "annuls", "sets aside", "rules", "orders", "rejects", "dismisses", "declines",
          "grants", "refuses", "revives", "settles", "pays", "joins", "leaves", "names", "appoints", "hires", "adds",
          "avoids", "secures", "claims", "says", "hits", "sued", "sues", "escapes", "loses bid", "overturns", "affirms",
          "confirms", "quashes", "stays", "halts", "blocks", "probes", "investigates", "opens", "closes", "withdraws",
          "takes", "heads to", "targets", "turns to", "must pay", "liable", "ordered to pay", "cleared", "found liable",
          "censured", "sanctioned", "instructs", "retains", "elects", "promotes", "moves", "launches claim", "resigns",
          "steps down", "dies", "held", "may face", "could face", "to hear", "to consider", "surfaces", "revealed",
          "reveals", "emerges", "concludes", "lodges", "registers", "announces", "warns", "denies", "accepts", "endorses")


def _words(s: str) -> int:
    return len([w for w in re.split(r"\s+", s.strip()) if w])


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def _dist(xs: List[int]) -> Dict[str, float]:
    if not xs:
        return {}
    xs = sorted(xs)
    return {"n": len(xs), "mean": round(statistics.mean(xs), 1), "median": statistics.median(xs),
            "p10": xs[int(0.1 * (len(xs) - 1))], "p90": xs[int(0.9 * (len(xs) - 1))], "min": xs[0], "max": xs[-1]}


def measure(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for src in ("gar", "iareporter"):
        rows = [i for i in issues if i["source"] == src]
        items = [it for i in rows for it in i["items"] if it.get("section") != "Documents"]
        if not rows:
            continue
        heads = [it["headline"] for it in items]
        blurbs = [it["blurb"] for it in items if it.get("blurb")]
        first = collections.Counter(h.split()[0] for h in heads if h.split())
        bfirst = collections.Counter(" ".join(b.split()[:2]) for b in blurbs if b.split())
        verbs = collections.Counter()
        for h in heads:
            hl = " " + h.lower() + " "
            for v in _VERBS:
                if " " + v + " " in hl or hl.endswith(" " + v + " "):
                    verbs[v] += 1
        openings = collections.Counter()
        for b in blurbs:
            m = re.match(r"^(An?|The)\s+([A-Z][\w-]+(?:-[A-Z][\w-]+)?)\s+(\w+)", b)
            if m:
                openings[m.group(1) + " <Adjective> " + m.group(3).lower() if m.group(3).lower() in ("company", "investor", "contractor", "group", "court", "tribunal", "judge", "businessman", "developer", "producer", "miner", "bank", "insurer", "consortium", "arbitrator", "panel") else m.group(1)] += 1
            elif re.match(r"^[A-Z]", b):
                openings["<Name> …"] += 1
        patterns = collections.Counter()
        for b in blurbs:
            for p in ("says it has", "has ruled", "has ordered", "has upheld", "has rejected", "has dismissed", "has filed",
                      "has threatened", "has won", "has lost", "has been ordered", "has agreed", "has applied", "has found",
                      "has declined", "has refused", "has issued", "has left", "has joined", "has named", "has hired",
                      "has failed", "has secured", "reportedly", "is to", "is facing", "are pursuing", "has brought",
                      "has launched", "has asked", "has granted", "has set aside", "has annulled", "has enforced",
                      "has confirmed", "has affirmed", "has criticised", "has opened", "has paid", "has defeated"):
                if p in b:
                    patterns[p] += 1
        sections = collections.Counter(it.get("section") or "" for it in items)
        labels = collections.Counter(it.get("label") for it in items if it.get("label"))
        per_issue = [len([it for it in i["items"] if it.get("section") != "Documents"]) for i in rows]
        docs_per_issue = [len([it for it in i["items"] if it.get("section") == "Documents"]) for i in rows]
        out[src] = {
            "issues": len(rows),
            "date_range": [min(i["date"] for i in rows if i["date"]), max(i["date"] for i in rows if i["date"])],
            "items": len(items),
            "items_per_issue": _dist(per_issue),
            "documents_per_issue": _dist(docs_per_issue) if any(docs_per_issue) else {},
            "sections": dict(sections.most_common()),
            "headline_words": _dist([_words(h) for h in heads]),
            "headline_chars": _dist([len(h) for h in heads]),
            "headline_starts_with_top": first.most_common(25),
            "headline_verbs_top": verbs.most_common(40),
            "headline_pct_with_amount": _pct(sum(1 for h in heads if _AMOUNT.search(h)), len(heads)),
            "headline_pct_with_institution": _pct(sum(1 for h in heads if _INST.search(h)), len(heads)),
            "headline_pct_with_colon": _pct(sum(1 for h in heads if ":" in h), len(heads)),
            "headline_pct_with_quote": _pct(sum(1 for h in heads if re.search(r"[\"“”']", h)), len(heads)),
            "headline_pct_sentence_case": _pct(sum(1 for h in heads if h.split() and sum(1 for w in h.split()[1:] if w[:1].isupper()) <= max(1, len(h.split()) // 4)), len(heads)),
            "headline_labels": labels.most_common(20),
            "blurbs": len(blurbs),
            "blurb_words": _dist([_words(b) for b in blurbs]),
            "blurb_sentences": _dist([len(_SENT.split(b)) for b in blurbs]),
            "blurb_pct_one_sentence": _pct(sum(1 for b in blurbs if len(_SENT.split(b)) == 1), len(blurbs)),
            "blurb_pct_with_amount": _pct(sum(1 for b in blurbs if _AMOUNT.search(b)), len(blurbs)),
            "blurb_pct_with_institution": _pct(sum(1 for b in blurbs if _INST.search(b)), len(blurbs)),
            "blurb_opening_shape": openings.most_common(12),
            "blurb_first_two_words_top": bfirst.most_common(25),
            "blurb_phrases": patterns.most_common(40),
        }
    return out


def readme(stats: Dict[str, Any], issues: List[Dict[str, Any]]) -> str:
    lines = ["# Style corpus", "",
             "Measured from the GAR daily briefings and IAReporter headline emails archived from the",
             "inbox (thread ids in `index.json`; raw text stays local under `data/newsletters/`).",
             "Regenerate with `python tools/newsletter_corpus.py`.", ""]
    for src, name in (("gar", "GAR daily briefing"), ("iareporter", "IAReporter latest headlines")):
        s = stats.get(src)
        if not s:
            continue
        lines += ["## {}".format(name), "",
                  "| measure | value |", "|---|---|",
                  "| issues | {} ({} to {}) |".format(s["issues"], *s["date_range"]),
                  "| stories | {} |".format(s["items"]),
                  "| stories per issue | median {}, p10 {}, p90 {} |".format(s["items_per_issue"].get("median"), s["items_per_issue"].get("p10"), s["items_per_issue"].get("p90")),
                  "| headline length | median {} words ({} chars), p90 {} words |".format(s["headline_words"].get("median"), s["headline_chars"].get("median"), s["headline_words"].get("p90")),
                  "| headlines naming an amount | {}% |".format(s["headline_pct_with_amount"]),
                  "| headlines naming an institution or treaty | {}% |".format(s["headline_pct_with_institution"]),
                  "| headlines with a colon | {}% |".format(s["headline_pct_with_colon"]),
                  "| headlines in sentence case | {}% |".format(s["headline_pct_sentence_case"])]
        if s["blurbs"]:
            lines += ["| standfirst length | median {} words, p90 {} |".format(s["blurb_words"].get("median"), s["blurb_words"].get("p90")),
                      "| standfirsts of one sentence | {}% |".format(s["blurb_pct_one_sentence"]),
                      "| standfirsts naming an amount | {}% |".format(s["blurb_pct_with_amount"]),
                      "| standfirsts naming an institution or treaty | {}% |".format(s["blurb_pct_with_institution"])]
        lines += ["", "Sections: " + ", ".join("{} ({})".format(k, v) for k, v in s["sections"].items()), ""]
        lines += ["Headline verbs, most used: " + ", ".join("{} ({})".format(k, v) for k, v in s["headline_verbs_top"][:25]), ""]
        lines += ["Headline first words: " + ", ".join("{} ({})".format(k, v) for k, v in s["headline_starts_with_top"][:15]), ""]
        if s.get("headline_labels"):
            lines += ["Headline labels: " + ", ".join("{} ({})".format(k, v) for k, v in s["headline_labels"]), ""]
        if s["blurbs"]:
            lines += ["Standfirst openings: " + ", ".join("{} ({})".format(k, v) for k, v in s["blurb_opening_shape"]), ""]
            lines += ["Standfirst phrases: " + ", ".join("{} ({})".format(k, v) for k, v in s["blurb_phrases"][:30]), ""]
    return "\n".join(lines) + "\n"


def main() -> int:
    issues: List[Dict[str, Any]] = []
    for src, parser in (("gar", parse_gar), ("iareporter", parse_iar)):
        for path in sorted(glob.glob(os.path.join(RAW, src, "*.txt"))):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            meta = _sidecar(path)
            meta.setdefault("id", os.path.basename(path)[:-4])
            issue = parser(text, meta)
            if not issue["items"]:
                print("no items:", path, file=sys.stderr)
                continue
            issues.append(issue)
    issues.sort(key=lambda i: (i["source"], i["date"]), reverse=True)
    os.makedirs(OUT_DOCS, exist_ok=True)
    index = [{"id": i["id"], "source": i["source"], "date": i["date"], "subject": i["subject"],
              "sections": i["sections"], "stories": len([x for x in i["items"] if x.get("section") != "Documents"]),
              "documents": len([x for x in i["items"] if x.get("section") == "Documents"])} for i in issues]
    headlines = [{"source": i["source"], "date": i["date"], "section": it["section"], "headline": it["headline"],
                  **({"label": it["label"]} if it.get("label") else {})}
                 for i in issues for it in i["items"] if it.get("section") != "Documents"]
    stats = measure(issues)
    with open(os.path.join(OUT_DOCS, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DOCS, "headlines.json"), "w", encoding="utf-8") as fh:
        json.dump(headlines, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DOCS, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DOCS, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme(stats, issues))
    with open(OUT_LOCAL, "w", encoding="utf-8") as fh:
        json.dump(issues, fh, ensure_ascii=False, indent=1)
    for src in ("gar", "iareporter"):
        s = stats.get(src)
        if s:
            print("{}: {} issues, {} stories, {} standfirsts".format(src, s["issues"], s["items"], s["blurbs"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
