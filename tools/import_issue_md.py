"""Import an issue written before day data existed (out/issue-YYYY-MM-DD.md) into
out/site/data/YYYY-MM-DD.json, so the web site can show that day.

    python -m tools.import_issue_md out/issue-2026-09-18.md
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arbradar import site, config, pipeline                        # noqa: E402
from arbradar.email_html import SHORT                                 # noqa: E402
from arbradar.taxonomy import EVENT_TYPES                             # noqa: E402
from arbradar.render import story_slug                                # noqa: E402
from arbradar.sources.gnews import _majors                            # noqa: E402

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
LABELS = {v["label"]: k for k, v in EVENT_TYPES.items()}
SECTION_KEYS = {"From the ICSID docket": "docket", "Company disclosures": "disclosures",
                "In the US courts": "courts", "In the courts": "courts", "People and appointments": "people"}


def _story(block: str, tier: str):
    lines = [l.rstrip() for l in block.strip().split("\n")]
    title = lines[0].lstrip("# ").strip()
    summary, label, source, url, also = "", "", "", "", []
    for l in lines[1:]:
        s = l.strip()
        if not s:
            continue
        if s.startswith("**"):
            m = re.match(r"\*\*(.+?)\*\*", s)
            label = m.group(1) if m else ""
            links = LINK.findall(s)
            if links:
                source, url = links[-1]
        elif s.startswith("also:"):
            also = [{"source": t.replace("Google News / ", ""), "url": u} for t, u in LINK.findall(s)]
        elif not summary:
            summary = s
    event_type = LABELS.get(label, "commentary")
    it = {"title": title, "summary": summary, "url": url, "source": source, "event_type": event_type,
          "also": also, "lang": "en"}
    it.update({k: v for k, v in pipeline.rule_classify(dict(it, event_type=event_type)).items() if k == "states"})
    it["claimants"] = _majors(title + " " + summary)[:3]
    it["tier"] = tier
    it["event"] = SHORT.get(event_type, "Note")
    return it


def _brief(line: str):
    m = LINK.search(line)
    if not m:
        return None
    title, url = m.groups()
    label = line.split(")", 1)[1].strip(" -–") if ")" in line else ""
    event_type = LABELS.get(label, "commentary")
    it = {"title": title, "summary": "", "url": url, "source": "", "event_type": event_type, "also": [],
          "lang": "en", "tier": "brief", "event": SHORT.get(event_type, "Note")}
    it["states"] = pipeline.rule_classify(dict(it)).get("states") or []
    it["claimants"] = _majors(title)[:3]
    return it


def _record(kind: str, line: str):
    m = LINK.search(line)
    if not m:
        return None
    title, url = m.groups()
    if kind in ("docket", "people") and " — " in title:
        main, _, step = title.partition(" — ")
        return {"date": "", "title": title, "main": main, "step": step[:1].upper() + step[1:], "tail": "", "url": url}
    if kind == "courts":
        main, _, court = title.partition(" (")
        return {"date": "", "title": title, "main": main, "step": "", "tail": court.rstrip(")"), "url": url}
    if kind == "disclosures":
        filer, _, rest = title.partition(" discloses ")
        return {"date": "", "title": title, "main": filer, "step": ("discloses " + rest) if rest else "", "tail": "", "url": url}
    return {"date": "", "title": title, "main": title, "step": "", "tail": "", "url": url}


def main(path: str) -> str:
    md = open(path, encoding="utf-8").read()
    date = re.search(r"(\d{4}-\d{2}-\d{2})", md.split("\n", 1)[0]).group(1)
    sections = re.split(r"^## ", md, flags=re.M)[1:]
    stories, records = [], {k: [] for k in ("docket", "disclosures", "courts", "people")}
    for sec in sections:
        name, _, body = sec.partition("\n")
        name = name.strip()
        if name in ("Lead", "Developments"):
            for block in re.split(r"^### ", body, flags=re.M)[1:]:
                stories.append(_story(block, "lead" if name == "Lead" and not stories else "development"))
        elif name == "In brief":
            for line in body.split("\n"):
                if line.startswith("- "):
                    it = _brief(line)
                    if it:
                        stories.append(it)
        elif name in SECTION_KEYS:
            key = SECTION_KEYS[name]
            for line in body.split("\n"):
                if line.startswith("- "):
                    r = _record(key, line)
                    if r:
                        records[key].append(r)
    for s in stories:
        s["slug"] = story_slug(s, date)
        s["published_at"] = date
    os.makedirs(site.DATA, exist_ok=True)
    out = site.day_file(date)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"date": date, "subject": "", "stories": stories, "records": records}, fh, ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    print(main(sys.argv[1]))
