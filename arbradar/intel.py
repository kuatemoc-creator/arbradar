"""Appointment and mandate intelligence, derived from the ICSID corpus.

This is the part the trade press does not systematically publish. GAR and
IAReporter report appointments one case at a time, as news. The value for a
practitioner is in the aggregate: who appoints whom, how often, which pairings
repeat, who is saturated, and who has been challenged off a tribunal.

Everything here is computed from the public ICSID case record - the same data
any party can read, just never assembled.
"""
import datetime as dt
import re
import time
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from selectolax.parser import HTMLParser

from .fetch import get

API = "https://icsid.worldbank.org/api/cases/{status}"
RESULT_KEY = "GetBulkCasesByStatusIdResult"

# "Name (Nationality) - Appointed by the Claimant(s)"
APPT = re.compile(r"^(?P<name>.+?)\s*\((?P<nat>[^)]*)\)\s*-\s*Appointed by (?P<by>.+)$")
# "July 24, 2023: X (German) appointed following the resignation of Y (Argentine)"
RECON = re.compile(
    r"(?P<date>[A-Z][a-z]+ \d{1,2}, \d{4}):\s*"
    r"(?P<incoming>[^(]+)\((?P<in_nat>[^)]*)\)\s*"
    r"appointed following the (?P<reason>resignation|disqualification|death|removal|withdrawal)"
    r"\s+of\s+(?P<outgoing>[^(]+)\((?P<out_nat>[^)]*)\)", re.I)

SIDE = {"claimant": "claimant", "respondent": "respondent",
        "parties": "parties", "chairman": "chairman",
        "administrative council": "chairman", "tribunal": "tribunal"}


def _clean(html: Optional[str]) -> str:
    return " ".join(HTMLParser(html).text().split()) if html else ""


def _split(html: Optional[str]) -> List[str]:
    if not html:
        return []
    return [x for x in (_clean(p) for p in re.split(r"<br\s*/?>", html, flags=re.I)) if x]


# ICSID's own text carries artefacts: honorifics, a stray "arbitrator of", and
# "Name of Firm" run-ons. Normalise so one person is one node in the graph.
_NAME_JUNK = re.compile(r"^(the\s+)?(arbitrator\s+of\s+|mr\.?\s+|ms\.?\s+|mrs\.?\s+"
                        r"|dr\.?\s+|prof\.?\s+|sir\s+|judge\s+)+", re.I)


def normalise_name(raw: str) -> str:
    name = _NAME_JUNK.sub("", (raw or "").strip())
    name = re.split(r"\s+of\s+", name)[0]        # "Sofia Martins of Sofia Martins & Co"
    return " ".join(name.split()).strip(" ,;")


def _side(label: str) -> str:
    low = label.lower()
    for key, val in SIDE.items():
        if key in low:
            return val
    return "other"


def _firm(raw: str) -> str:
    """Counsel lines are 'Firm, City, Country'. Keep the firm, drop geography.
    Individual barristers appear as 'Name, City' - kept as-is, they matter too."""
    return raw.split(",")[0].strip()


def load_cases(ttl: int = 86400) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for status in ("pending", "concluded"):
        try:
            r = get(API.format(status=status), params={"dt": int(time.time() * 1000)},
                    ttl=ttl, timeout=120)
            for c in r.json()["data"][RESULT_KEY]:
                c["_status"] = status
                out.append(c)
        except Exception:                             # noqa: BLE001 - boundary
            continue
    return out


def appointments(cases: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One row per arbitrator seat, with the side that put them there."""
    rows: List[Dict[str, Any]] = []
    for case in cases:
        treaty = " / ".join(x for x in (case.get("instrumentinvk1"),
                                        case.get("instrumentinvk2")) if x)
        for proc in case.get("caseproceedings") or []:
            claimant_firms = [_firm(x) for x in _split(proc.get("claimant"))]
            respondent_firms = [_firm(x) for x in _split(proc.get("respondent"))]
            seats = ([(x, "member") for x in _split(proc.get("arbitrators"))]
                     + [(x, "president") for x in _split(proc.get("president"))])
            for raw, role in seats:
                m = APPT.match(raw)
                if not m:
                    continue
                side = _side(m.group("by"))
                rows.append({
                    "case": case.get("caseno"),
                    "title": _clean(case.get("casetitle")),
                    "status": case.get("_status"),
                    "arbitrator": normalise_name(m.group("name")),
                    "nationality": m.group("nat").strip(),
                    "role": role,
                    "appointed_by": side,
                    "registered": proc.get("dateregistered"),
                    "constituted": proc.get("dateconstituted"),
                    "sector": case.get("econsector"),
                    "treaty": treaty,
                    "respondent_state": _clean(proc.get("resp_nationality")),
                    "claimant_party": _clean(proc.get("clmnt_nationality")),
                    "claimant_firms": claimant_firms,
                    "respondent_firms": respondent_firms,
                })
    return rows


def reconstitutions(cases: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Resignations, disqualifications and removals, with dates.

    A disqualification is the single most gossip-dense fact in the record: it
    means a challenge succeeded. The trade press covers only a fraction of these.
    """
    out: List[Dict[str, Any]] = []
    for case in cases:
        for proc in case.get("caseproceedings") or []:
            text = _clean(proc.get("reconstituted"))
            if not text:
                continue
            for m in RECON.finditer(text):
                try:
                    when = dt.datetime.strptime(m.group("date"), "%B %d, %Y").date()
                except ValueError:
                    when = None
                out.append({
                    "case": case.get("caseno"),
                    "title": _clean(case.get("casetitle")),
                    "date": when.isoformat() if when else m.group("date"),
                    "reason": m.group("reason").lower(),
                    "outgoing": normalise_name(m.group("outgoing")),
                    "outgoing_nat": m.group("out_nat").strip(),
                    "incoming": normalise_name(m.group("incoming")),
                    "incoming_nat": m.group("in_nat").strip(),
                    "respondent_state": _clean(proc.get("resp_nationality")),
                })
    out.sort(key=lambda r: str(r["date"]), reverse=True)
    return out


def arbitrator_table(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    agg: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "claimant": 0, "respondent": 0, "president": 0,
                 "chairman": 0, "pending": 0, "sectors": Counter(),
                 "states": Counter(), "nationality": ""})
    for r in rows:
        a = agg[r["arbitrator"]]
        a["total"] += 1
        a["nationality"] = a["nationality"] or r["nationality"]
        if r["role"] == "president":
            a["president"] += 1
        if r["appointed_by"] in ("claimant", "respondent", "chairman"):
            a[r["appointed_by"]] += 1
        if r["status"] == "pending":
            a["pending"] += 1
        if r.get("sector"):
            a["sectors"][r["sector"]] += 1
        if r.get("respondent_state"):
            a["states"][r["respondent_state"]] += 1

    table = []
    for name, a in agg.items():
        party = a["claimant"] + a["respondent"]
        lean = (a["claimant"] / party) if party else 0.5
        table.append({
            "arbitrator": name, "nationality": a["nationality"],
            "total": a["total"], "pending": a["pending"],
            "claimant_side": a["claimant"], "respondent_side": a["respondent"],
            "president": a["president"],
            # 1.0 = only ever appointed by claimants, 0.0 = only by respondents
            "claimant_lean": round(lean, 2),
            "top_sector": a["sectors"].most_common(1)[0][0] if a["sectors"] else "",
            "top_state": a["states"].most_common(1)[0][0] if a["states"] else "",
        })
    table.sort(key=lambda r: -r["total"])
    return table


def firm_affinity(rows: List[Dict[str, Any]], min_count: int = 2
                  ) -> List[Dict[str, Any]]:
    """Which counsel repeatedly appoint which arbitrators.

    This is the practical output: facing firm X, you can see the pool they
    appoint from, and how concentrated it is.
    """
    pair: Counter = Counter()
    firm_total: Counter = Counter()
    for r in rows:
        if r["appointed_by"] == "claimant":
            firms = r["claimant_firms"]
        elif r["appointed_by"] == "respondent":
            firms = r["respondent_firms"]
        else:
            continue
        for f in set(firms):
            pair[(f, r["arbitrator"])] += 1
            firm_total[f] += 1

    out = []
    for (firm, arb), n in pair.items():
        if n < min_count:
            continue
        out.append({"firm": firm, "arbitrator": arb, "appointments": n,
                    "firm_total": firm_total[firm],
                    "share": round(n / firm_total[firm], 2)})
    out.sort(key=lambda r: (-r["appointments"], -r["share"]))
    return out


def counsel_table(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Firm league table, split by which side they act for."""
    agg: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"claimant": set(), "respondent": set(), "states": Counter(),
                 "sectors": Counter()})
    for r in rows:
        for f in set(r["claimant_firms"]):
            agg[f]["claimant"].add(r["case"])
            if r.get("sector"):
                agg[f]["sectors"][r["sector"]] += 1
        for f in set(r["respondent_firms"]):
            agg[f]["respondent"].add(r["case"])
            if r.get("respondent_state"):
                agg[f]["states"][r["respondent_state"]] += 1
    out = []
    for firm, a in agg.items():
        out.append({
            "firm": firm,
            "claimant_cases": len(a["claimant"]),
            "respondent_cases": len(a["respondent"]),
            "total": len(a["claimant"] | a["respondent"]),
            "top_state_defended": a["states"].most_common(1)[0][0] if a["states"] else "",
            "top_sector": a["sectors"].most_common(1)[0][0] if a["sectors"] else "",
        })
    out.sort(key=lambda r: -r["total"])
    return out


def recent_appointments(rows: List[Dict[str, Any]], days: int = 120
                        ) -> List[Dict[str, Any]]:
    """Tribunals constituted inside the window - who just got the nod."""
    cutoff = dt.date.today() - dt.timedelta(days=days)
    out = []
    for r in rows:
        try:
            when = dt.datetime.strptime(r["constituted"], "%B %d, %Y").date()
        except (ValueError, TypeError):
            continue
        if when >= cutoff:
            out.append(dict(r, constituted_date=when.isoformat()))
    out.sort(key=lambda r: r["constituted_date"], reverse=True)
    return out


def concentration(table: List[Dict[str, Any]], top: int = 20) -> Dict[str, Any]:
    """How closed is the club? Share of all seats held by the busiest N."""
    total = sum(r["total"] for r in table)
    head = sum(r["total"] for r in table[:top])
    return {"arbitrators": len(table), "seats": total,
            "top_n": top, "top_n_share": round(head / total, 3) if total else 0}
