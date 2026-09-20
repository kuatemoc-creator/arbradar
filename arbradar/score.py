"""Lead scoring.

The score answers one question: how likely is it that a partner reading this
line can win work from it? That is deliberately not the same as newsworthiness,
which is what GAR optimises for. A routine procedural filing in a famous case is
great journalism and a terrible lead; a notice of intent from an unknown junior
miner is dull copy and an excellent lead.
"""
import datetime as dt
import math
from typing import Any, Dict, Tuple

from .taxonomy import EVENT_TYPES

TIER_FACTOR = {1: 1.15, 2: 1.0, 3: 0.85}
HALF_LIFE_DAYS = 6.0


def _age_days(item: Dict[str, Any]) -> float:
    stamp = item.get("published_at") or item.get("fetched_at")
    if not stamp:
        return 3.0
    try:
        when = dt.date.fromisoformat(str(stamp)[:10])
    except ValueError:
        return 3.0
    return max(0.0, (dt.date.today() - when).days)


def _watchlist_boost(item: Dict[str, Any], settings) -> Tuple[float, list]:
    """Weighted term matches across the item's text and extracted entities."""
    haystack = " ".join(filter(None, [
        item.get("title") or "", item.get("summary") or "",
        " ".join(item.get("states") or []), " ".join(item.get("claimants") or []),
        " ".join(item.get("respondents") or []), " ".join(item.get("sectors") or []),
        item.get("treaty") or "", " ".join(item.get("counsel") or []),
    ])).lower()

    boost, hits = 0.0, []
    for group in (settings.states, settings.sectors, settings.companies, settings.firms):
        for term, weight in (group or {}).items():
            if term.lower() in haystack:
                boost += float(weight)
                hits.append(term)
    return boost, hits


def score_item(item: Dict[str, Any], settings) -> Tuple[float, Dict[str, Any]]:
    event = item.get("event_type") or "commentary"
    base = EVENT_TYPES.get(event, EVENT_TYPES["commentary"])["weight"]

    age = _age_days(item)
    recency = math.pow(0.5, age / HALF_LIFE_DAYS)

    boost, hits = _watchlist_boost(item, settings)
    # An investor of means named in the story (set by the sweep) counts like a
    # watchlist hit: they can instruct, and they will.
    if item.get("claimants") and item.get("event_type") in ("state_measure", "distress_event"):
        boost += 0.5
        hits = hits + ["investor: " + item["claimants"][0]]
    tier = TIER_FACTOR.get(item.get("source_tier") or 2, 1.0)

    # Size of the dispute, damped - a $2bn claim is not 100x a $20m claim in
    # terms of how winnable the mandate is.
    amount = item.get("amount_usd") or 0
    amount_bonus = min(20.0, 4.0 * math.log10(amount / 1e6)) if amount > 1e6 else 0.0

    # Nobody on record yet is the strongest single BD signal we can observe -
    # but only from a primary record. A press item omitting counsel is silence,
    # not evidence, and treating it as a lead sends you after taken mandates.
    unrepresented = 12.0 if (
        not (item.get("counsel") or [])
        and (item.get("source_tier") or 2) == 1
        and not (item.get("source") or "").startswith("Court:")   # a judgment lists no counsel; that is not vacancy
        and event in ("notice_of_intent", "new_case_filed", "s1782_application",
                      "enforcement_action", "distress_event")) else 0.0

    total = (base * recency * tier) * (1.0 + boost) + amount_bonus + unrepresented

    # A non-English item classified by keyword alone is a guess: keyword "nationalisation"
    # in Russian is as often a domestic policy story as a treaty lead. Damp it until
    # the triage model has actually read it.
    unverified = (item.get("lang") or "en") != "en" and (item.get("llm_stage") or "none") in ("none", "skipped")
    if unverified:
        total *= 0.55

    muted = [m for m in (settings.mute or [])
             if m.lower() in ((item.get("title") or "") + (item.get("summary") or "")).lower()]
    if muted:
        total *= 0.25

    detail = {
        "base": base, "event": event, "age_days": age,
        "recency": round(recency, 3), "tier": tier,
        "watchlist_boost": round(boost, 2), "watchlist_hits": hits,
        "amount_bonus": round(amount_bonus, 1),
        "unrepresented_bonus": unrepresented,
        "unverified_foreign": unverified,
        "muted": muted,
    }
    return round(total, 2), detail
