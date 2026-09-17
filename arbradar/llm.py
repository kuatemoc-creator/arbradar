"""Claude layer.

Three tiers, cheapest first, because volume falls off sharply at each stage:
  triage   (Haiku 4.5)  - a few hundred raw items a day, one yes/no each
  extract  (Sonnet 5)   - only survivors, structured fields
  editorial(Fable 5.1)  - once per issue, writes the prose

Model-specific API rules that are easy to get wrong:
  * Fable 5.1 thinks always - omit `thinking` entirely; passing
    {"type": "disabled"} or budget_tokens returns 400.
  * Fable 5.1 rejects temperature/top_p/top_k, and rejects forced tool_choice.
  * Fable 5.1 can decline a request: HTTP 200 with stop_reason == "refusal".
    We opt into server-side fallbacks so an issue never dies on a false positive.
  * Haiku 4.5 does not accept output_config.effort at all.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .config import FALLBACK_BETA

log = logging.getLogger(__name__)
_client = None


def client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


# --------------------------------------------------------------------------
# schemas
# --------------------------------------------------------------------------
class TriageVerdict(BaseModel):
    ref: int
    relevant: bool = Field(description="True only if an arbitration practitioner "
                                       "hunting mandates would care.")
    event_type: str = Field(description="One key from the supplied taxonomy, or 'commentary'.")


class TriageBatch(BaseModel):
    verdicts: List[TriageVerdict]


class Extraction(BaseModel):
    event_type: str
    claimants: List[str] = []
    respondents: List[str] = []
    states: List[str] = []
    institution: Optional[str] = None
    treaty: Optional[str] = None
    case_ref: Optional[str] = None
    sectors: List[str] = []
    amount_usd: Optional[float] = Field(
        None, description="Amount in dispute or awarded, converted to USD. Null if unstated.")
    counsel: List[str] = Field([], description="Law firms already acting, if named.")
    arbitrators: List[str] = []
    why_it_matters: str = Field(
        description="One sentence, max 30 words, addressed to a partner deciding "
                    "whether to chase this. Say who may still need counsel.")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _refused(resp) -> bool:
    """Always branch on stop_reason; stop_details may be null even on refusal."""
    return getattr(resp, "stop_reason", None) == "refusal"


def _text(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")


# --------------------------------------------------------------------------
# stage 1 - triage (Haiku 4.5)
# --------------------------------------------------------------------------
TRIAGE_SYSTEM = """You screen news for a newsletter read by international arbitration \
practitioners who are looking for new mandates.

Mark an item relevant ONLY if it plausibly signals legal work that is available or \
about to become available: a dispute starting, escalating, being enforced, annulled, \
funded, or an event (expropriation, licence revocation, sanctions, insolvency) that \
typically produces an arbitration.

Mark irrelevant: general business news, conference write-ups, appointments to unrelated \
posts, opinion pieces with no underlying dispute, law firm marketing with no case, \
and anything about domestic litigation unconnected to arbitration.

Choose event_type from exactly these keys:
notice_of_intent, s1782_application, new_case_filed, enforcement_action,
annulment_setaside, distress_event, award_issued, treaty_action, funding,
tribunal_constituted, lateral_move, commentary"""


def triage(items: List[Dict[str, Any]], model: str, chunk: int = 20) -> Dict[int, TriageVerdict]:
    """Screen items in batches. Returns {item_id: verdict}."""
    out: Dict[int, TriageVerdict] = {}
    for i in range(0, len(items), chunk):
        batch = items[i:i + chunk]
        lines = []
        for it in batch:
            blurb = (it.get("summary") or it.get("body") or "")[:400]
            lines.append("[{}] source={} | {} | {}".format(
                it["id"], it.get("source", ""), it.get("title", ""), blurb))
        try:
            resp = client().beta.messages.parse(
                model=model,
                max_tokens=4000,
                system=TRIAGE_SYSTEM,
                messages=[{"role": "user",
                           "content": "Screen each item. Echo its [ref] number.\n\n"
                                      + "\n\n".join(lines)}],
                output_format=TriageBatch,
            )
        except Exception as exc:                      # noqa: BLE001 - boundary
            log.warning("triage batch failed (%s); passing items through", exc)
            continue
        if _refused(resp):
            log.warning("triage refused for batch starting %s", batch[0]["id"])
            continue
        for v in resp.parsed_output.verdicts:
            out[v.ref] = v
    return out


# --------------------------------------------------------------------------
# stage 2 - extraction (Sonnet 5)
# --------------------------------------------------------------------------
EXTRACT_SYSTEM = """Extract structured facts about an international arbitration matter \
from the text supplied. Use only what the text supports - never infer a party, amount or \
treaty that is not there. Leave fields empty rather than guessing. Amounts must be \
converted to USD; if the text gives another currency and no rate, estimate conservatively \
and still return USD."""


def extract(item: Dict[str, Any], model: str) -> Optional[Extraction]:
    text = "{}\n\n{}\n\n{}".format(
        item.get("title", ""), item.get("summary") or "", (item.get("body") or "")[:6000])
    try:
        resp = client().beta.messages.parse(
            model=model,
            max_tokens=2000,
            system=EXTRACT_SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": text}],
            output_format=Extraction,
        )
    except Exception as exc:                          # noqa: BLE001 - boundary
        log.warning("extract failed for item %s: %s", item.get("id"), exc)
        return None
    if _refused(resp):
        log.warning("extract refused for item %s", item.get("id"))
        return None
    return resp.parsed_output


# --------------------------------------------------------------------------
# stage 3 - editorial (Fable 5.1)
# --------------------------------------------------------------------------
EDITOR_SYSTEM = """You write {name}, a newsletter for international arbitration \
practitioners who are looking for cases to take on.

Your reader is a partner or senior counsel. They already know what ICSID is. They do not \
need the law explained. They need to know, for each item: what happened, and where the \
work is. Be concrete about which side may still be unrepresented, which jurisdictions will \
need local counsel, and what the timing pressure is.

House style:
- Lead with the commercial fact, not the procedural one.
- Never pad. If an item only deserves one sentence, give it one sentence.
- No hedging adverbs, no "notably", no "it is worth noting".
- Name parties, amounts and forums plainly.
- Where counsel is already on record, say so - that tells the reader the seat is taken.
- Never invent a fact that is not in the supplied items. If something is unknown, omit it \
rather than writing around it.

Return GitHub-flavoured Markdown only. Structure:
# {name} - {date}
A two-to-three sentence opener naming the single most valuable development.
## Lead
The top item, three or four sentences.
## Where the work is
Three to six items, each as `### <headline>` plus two or three sentences, ordered by the \
score supplied. End each with a bolded **Angle:** line naming the specific pitch.
## Also moving
Bulleted one-liners for the remainder.
"""


def write_issue(items: List[Dict[str, Any]], model: str, name: str, date: str,
                effort: str = "high") -> str:
    """Fable 5.1 writes the issue. Streams because output can be long."""
    payload = []
    for it in items:
        payload.append({
            "headline": it.get("title"),
            "url": it.get("url"),
            "source": it.get("source"),
            "published": it.get("published_at"),
            "event_type": it.get("event_type"),
            "score": round(it.get("score") or 0, 1),
            "claimants": it.get("claimants"),
            "respondents": it.get("respondents"),
            "states": it.get("states"),
            "institution": it.get("institution"),
            "treaty": it.get("treaty"),
            "sectors": it.get("sectors"),
            "amount_usd": it.get("amount_usd"),
            "counsel_on_record": it.get("counsel"),
            "arbitrators": it.get("arbitrators"),
            "why_it_matters": it.get("why_it_matters"),
            "excerpt": (it.get("summary") or "")[:600],
            "also_reported_by": [a.get("source") for a in (it.get("also") or [])],
        })

    kwargs = dict(
        model=model,
        max_tokens=16000,
        system=EDITOR_SYSTEM.format(name=name, date=date),
        output_config={"effort": effort},
        messages=[{"role": "user",
                   "content": "Today is {}. Write the issue from these items, "
                              "highest score first.\n\n{}".format(
                                  date, json.dumps(payload, ensure_ascii=False, indent=1))}],
    )
    # Server-side fallback: Fable 5.1's classifiers occasionally decline benign
    # work (sanctions, cyber-adjacent disputes). Route rather than lose the issue.
    if model.startswith("claude-fable") or model.startswith("claude-opus-5"):
        kwargs["betas"] = [FALLBACK_BETA]
        kwargs["fallbacks"] = "default"

    with client().beta.messages.stream(**kwargs) as stream:
        resp = stream.get_final_message()

    if _refused(resp):
        raise RuntimeError(
            "Editorial model declined the issue (category: {}). "
            "Re-run with --editor-model claude-opus-5.".format(
                getattr(getattr(resp, "stop_details", None), "category", None)))
    return _text(resp)
