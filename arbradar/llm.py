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
import os
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
    headline_en: str = Field(description="English headline, at most 14 words, sentence case. "
                                         "A faithful rendering if the source is not in English.")
    summary_en: str = Field(description="Two sentences in English stating what happened.")
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
        description="One neutral sentence on the procedural posture: what stage the "
                    "matter is at and what happens next. No advice.")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _refused(resp) -> bool:
    """Always branch on stop_reason; stop_details may be null even on refusal."""
    return getattr(resp, "stop_reason", None) == "refusal"


def _text(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")



HOUSE_STYLE = """House style - this matters more than anything else in this brief:
- Write as a senior practitioner writes to a peer. British spelling (arbitral, licence, favour, \
centre). Vocabulary of the trade: a party is "instructed" or "retained"; a firm "acts for" or \
"appears for"; a seat is "taken" or "open"; the respondent is "the State"; an award is \
"rendered"; a challenge "succeeds" or "fails".
- Short declarative sentences. One idea per sentence. No rhetorical questions, no exclamation \
marks, no colons used for drama.
- Never use: notably, crucially, importantly, landscape, navigate, delve, robust, leverage, \
game-changer, unpack, "it is worth noting", "in today's", "this development", "underscores", \
"highlights the importance", "a testament to", "moving forward", "at the end of the day".
- No lists of three for rhythm. No em dashes as a substitute for a full stop. No sentence that \
begins with "This" referring vaguely to the previous sentence.
- Amounts as "US$350 million", not "$350M". Dates as "4 September 2026". Case names in italics \
are the only italics. Firms as they style themselves (Three Crowns, not "Three Crowns LLP").
- Say what is known. Where a fact is absent, leave it out; never write around it."""

# The measured house style (docs/house-style.md) travels with the brief, so the
# model writes to the shape of the trade press rather than to a description of it.
try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "house-style.md"),
              encoding="utf-8") as _fh:
        HOUSE_STYLE += "\n\n" + _fh.read()
except OSError:
    pass

# The editor's brief is the arb-editor skill: the same rules a person applies
# when editing by hand are the rules the model edits by.
EDITOR_BRIEF = ""
try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".claude", "skills", "arb-editor", "SKILL.md"),
              encoding="utf-8") as _fh:
        _raw = _fh.read()
        EDITOR_BRIEF = _raw.split("---", 2)[2].strip() if _raw.startswith("---") else _raw
except OSError:
    pass


class EntryEdit(BaseModel):
    ref: int
    headline: str = Field(description="Six to twelve words, sentence case, present tense, no colon.")
    explanation: str = Field(description="Whole sentences, 36 words or fewer, only facts in the supplied source text.")
    margin: str = Field(description="One line: what was changed and why.")


class EntryEdits(BaseModel):
    edits: List[EntryEdit]


EDIT_SYSTEM = """You are the editor described below. Edit each entry's headline and explanation. \
Use only facts present in that entry's own source text and corroborating snippets; if the source \
carries no text, write the explanation from the record fields supplied, and if those are empty, \
say the outlet reports the development and stop. Return every entry, by ref.

{brief}"""


def edit_entries(items: List[Dict[str, Any]], model: str, chunk: int = 8) -> int:
    """The partner's edit of every entry: headline and explanation rewritten to the
    brief, from the entry's own sources. Sets title_en and story; the grounding
    check that follows drops anything the sources do not carry."""
    if not EDITOR_BRIEF or not items:
        return 0
    done = 0
    for start in range(0, len(items), chunk):
        batch = items[start:start + chunk]
        payload = []
        for i, it in enumerate(batch):
            payload.append({
                "ref": i,
                "headline": it.get("title_en") or it.get("title"),
                "source": it.get("source"), "url": it.get("url"), "published": it.get("published_at"),
                "event_type": it.get("event_type"),
                "source_text": (it.get("story") or it.get("summary_en") or it.get("summary") or "")[:1500],
                "corroborating_snippets": [{"source": c.get("source"), "snippet": (c.get("snippet") or "")[:500]}
                                           for c in (it.get("corroboration") or [])[:3] if isinstance(c, dict)],
                "record": {k: it.get(k) for k in ("claimants", "respondents", "states", "institution", "treaty",
                                                  "amount_usd", "counsel", "arbitrators", "case_ref") if it.get(k)},
            })
        try:
            resp = client().messages.parse(
                model=model, max_tokens=4000,
                system=EDIT_SYSTEM.format(brief=EDITOR_BRIEF),
                messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=1)}],
                output_format=EntryEdits,
            )
            edits = resp.parsed_output.edits if resp.parsed_output else []
        except Exception as exc:                      # noqa: BLE001 - boundary
            log.warning("editor pass failed on a batch: %s", exc)
            continue
        for e in edits:
            if 0 <= e.ref < len(batch):
                it = batch[e.ref]
                if e.headline.strip():
                    it["title_en"] = e.headline.strip()
                if e.explanation.strip():
                    it["story"] = e.explanation.strip()
                it["margin"] = e.margin
                done += 1
    return done


# --------------------------------------------------------------------------
# stage 1 - triage (Haiku 4.5)
# --------------------------------------------------------------------------
TRIAGE_SYSTEM = """You screen news for a daily briefing read by international arbitration \
practitioners: the kind of story Global Arbitration Review or IAReporter would carry.

Items arrive in any language - Armenian, Georgian, Russian, Spanish, Arabic and others. \
Judge each in its own language; do not mark an item irrelevant for being non-English.

Mark an item relevant ONLY if it is news of an arbitration or of a dispute on its way \
to one: a claim threatened, lodged or registered; a decision, award, enforcement or \
annulment step; a state measure of the kind that produces treaty claims (expropriation, \
licence revocation, sanctions, nationalisation); a counsel or arbitrator appointment; a \
move in the profession.

Mark irrelevant: general business news, conference write-ups, appointments to unrelated \
posts, opinion pieces with no underlying dispute, law firm marketing with no case, \
and anything about domestic litigation unconnected to arbitration.

Choose event_type from exactly these keys:
counsel_tender, counsel_change, notice_of_intent, s1782_application, new_case_filed,
enforcement_action, interim_relief, annulment_setaside, state_measure, commercial_dispute,
award_issued, distress_event, counsel_instructed, treaty_action, funding, settlement,
law_reform, tribunal_constituted, appointment, lateral_move, commentary"""


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

Your reader is a partner or senior counsel. They already know what ICSID is and what a \
notice of dispute means. Report the development: what happened, between whom, in which \
forum, at what stage, with which counsel and arbitrators on record. Do not explain the \
significance to their practice and do not suggest what they should do about it. They will \
draw their own conclusions; being told is an insult.

House style:
- Lead with the commercial fact, not the procedural one.
- Never pad. If an item only deserves one sentence, give it one sentence.
- No hedging adverbs, no "notably", no "it is worth noting".
- Name parties, amounts and forums plainly.
- Where counsel is already on record, say so - that tells the reader the seat is taken.
- Never invent a fact that is not in the supplied items. If something is unknown, omit it \
rather than writing around it.

{style}

Where an item carries a site_link, make its ### headline a Markdown link to it.

Return GitHub-flavoured Markdown only. Structure:
# {name} - {date}
Two or three sentences naming the single most valuable development and why.
## Lead
The top item, three or four sentences.
## Developments
Three to six items, each as `### <headline>` plus two or three sentences, ordered by the \
score supplied. Where counsel or arbitrators are on record, name them.
## In brief
Bulleted one-liners for the remainder.
"""
