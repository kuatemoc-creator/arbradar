#!/usr/bin/env python3
"""The words that are lower case in running text - the list behind style.headline().

Built from what we have already read: the English item texts in the database and
the newsletter corpus. A word that appears in lower case in the middle of a
sentence far more often than capitalised is a common word and gets lowered when a
Title Case headline is converted; anything else is treated as a name and left
alone. Regenerate after the corpus grows:  python tools/wordlist.py
"""
import collections
import html
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "arbradar", "data", "lowercase-words.txt")
DB = os.path.join(ROOT, "data", "arbradar.sqlite3")
CORPUS = os.path.join(ROOT, "data", "newsletters", "corpus.json")

low: collections.Counter = collections.Counter()
cap: collections.Counter = collections.Counter()


def feed(text: str) -> None:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    for sent in re.split(r"(?<=[.!?:])\s+|\s+[–—]\s+", text):
        toks = re.findall(r"[A-Za-z][A-Za-z'’-]*", sent)
        for i, w in enumerate(toks):
            if i == 0 or w.isupper() or len(w) < 3:
                continue                       # sentence starts and acronyms say nothing about case
            key = w.lower().replace("’", "'")
            if w[0].isupper():
                cap[key] += 1
            else:
                low[key] += 1


def main() -> int:
    n = 0
    if os.path.exists(DB):
        conn = sqlite3.connect(DB)
        # Google News summaries repeat Title Case headlines and say nothing about
        # case; the feeds, dockets and judgments are written in sentences.
        for title, summary, body, lang in conn.execute(
                "SELECT COALESCE(title_en, title), COALESCE(summary_en, summary), body, lang FROM items "
                "WHERE source NOT LIKE 'Google News%'"):
            if (lang or "en") != "en":
                continue
            for t in (summary, body):
                if t:
                    feed(t); n += 1
    if os.path.exists(CORPUS):
        with open(CORPUS, encoding="utf-8") as fh:
            for issue in json.load(fh):
                for it in issue.get("items") or []:
                    for t in (it.get("blurb"), it.get("headline")):
                        if t:
                            feed(t); n += 1
    words = sorted(w for w in low if low[w] >= 2 and low[w] >= 1.5 * cap.get(w, 0)
                   and re.fullmatch(r"[a-z][a-z'-]+", w))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(words) + "\n")
    print("{} texts read, {} lower-case words written to {}".format(n, len(words), os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
