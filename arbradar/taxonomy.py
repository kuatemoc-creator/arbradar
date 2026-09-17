"""Event taxonomy and gazetteers.

The ordering of EVENT_TYPES is the whole editorial thesis: GAR and IAReporter
report events, which is useful but late. A practitioner hunting mandates cares
about the point at which counsel has *not yet* been chosen. So the weights below
rank leading indicators above reported outcomes.
"""
from typing import Dict, List

# weight = raw BD value of the event, before recency / watchlist multipliers
EVENT_TYPES: Dict[str, Dict] = {
    "notice_of_intent": {
        "weight": 100,
        "label": "Notice of intent / dispute",
        "why": "Cooling-off period running. Counsel is being selected right now.",
    },
    "s1782_application": {
        "weight": 85,
        "label": "s.1782 discovery application",
        "why": "Evidence-gathering ahead of, or early in, an arbitration.",
    },
    "new_case_filed": {
        "weight": 80,
        "label": "New case registered",
        "why": "Respondent-side and co-counsel roles often still open.",
    },
    "enforcement_action": {
        "weight": 78,
        "label": "Enforcement / recognition",
        "why": "Needs local counsel in every enforcement jurisdiction.",
    },
    "annulment_setaside": {
        "weight": 72,
        "label": "Annulment / set-aside",
        "why": "Fresh mandate, distinct team from the merits phase.",
    },
    "distress_event": {
        "weight": 60,
        "label": "Expropriation / licence / sanctions event",
        "why": "Treaty claim frequently follows within 6-24 months.",
    },
    "award_issued": {
        "weight": 55,
        "label": "Award issued",
        "why": "Starts the annulment and enforcement clock.",
    },
    "treaty_action": {
        "weight": 45,
        "label": "Treaty signature / denunciation",
        "why": "Sunset-clause races and standing changes.",
    },
    "funding": {
        "weight": 42,
        "label": "Third-party funding",
        "why": "Funded claimant is a buyer of legal services.",
    },
    "tribunal_constituted": {
        "weight": 35,
        "label": "Tribunal constituted / challenge",
        "why": "Appointment intelligence and conflicts mapping.",
    },
    "lateral_move": {
        "weight": 30,
        "label": "Lateral move / team change",
        "why": "Conflicts open up; clients become reachable.",
    },
    "commentary": {
        "weight": 10,
        "label": "Commentary / analysis",
        "why": "Context, not a lead.",
    },
}

# Phrase -> event type. Ordered most-specific first; first match wins.
EVENT_PATTERNS: List = [
    ("notice_of_intent", [
        "notice of intent", "notice of dispute", "trigger letter",
        "notice of intention to submit", "cooling-off period", "cooling off period",
        "intention to commence arbitration", "amicable settlement period",
    ]),
    ("s1782_application", [
        "1782", "section 1782", "28 u.s.c. 1782", "discovery in aid of",
    ]),
    ("new_case_filed", [
        "request for arbitration", "notice of arbitration", "registered the request",
        "case registered", "new case", "files claim", "filed a claim",
        "commenced arbitration", "initiated arbitration", "statement of claim",
        "request for the institution",
    ]),
    ("enforcement_action", [
        "enforcement of the award", "recognition and enforcement", "new york convention",
        "petition to confirm", "confirm the award", "exequatur", "attachment of assets",
        "seize assets", "garnishment", "turnover order",
    ]),
    ("annulment_setaside", [
        "annulment", "set aside", "setting aside", "vacatur", "vacate the award",
        "ad hoc committee", "challenge to the award", "revision of the award",
    ]),
    ("award_issued", [
        "award", "tribunal ruled", "tribunal found", "ordered to pay",
        "dismissed the claim", "declined jurisdiction", "final award",
        "partial award", "damages of",
    ]),
    ("lateral_move", [
        "joins as partner", "joined as partner", "lateral hire",
        "launches arbitration practice", "hires arbitration", "team joins",
        "boutique launch", "launch london boutique", "launch a boutique",
        "launches a boutique", "lawyers launch", "opens an office",
    ]),
    ("distress_event", [
        "expropriat", "nationalis", "nationaliz", "licence revoked", "license revoked",
        "permit cancelled", "permit canceled", "concession terminated", "seizure of",
        "sanction", "asset freeze", "state of emergency", "windfall tax",
        "forced divestment", "mining permit", "resource rent",
    ]),
    ("treaty_action", [
        "bilateral investment treaty", " bit ", "energy charter treaty", "denounc",
        "withdraw from the", "terminate the treaty", "sunset clause",
        "investment protection agreement", "free trade agreement", "icsid convention",
    ]),
    ("funding", [
        "third-party funding", "third party funding", "litigation funder",
        "funding agreement", "burford", "omni bridgeway", "therium", "nivalion",
        "fortress investment", "claim monetis", "claim monetiz",
    ]),
    ("tribunal_constituted", [
        "tribunal constituted", "appointed as arbitrator", "presiding arbitrator",
        "chair of the tribunal", "challenge to the arbitrator", "disqualification",
        "resigned from the tribunal", "co-arbitrator",
    ]),
]

INSTITUTIONS = {
    "ICSID": ["icsid", "international centre for settlement"],
    "PCA": ["permanent court of arbitration", "pca "],
    "UNCITRAL": ["uncitral"],
    "ICC": ["international chamber of commerce", "icc arbitration", " icc "],
    "LCIA": ["lcia", "london court of international arbitration"],
    "SCC": ["stockholm chamber of commerce", " scc "],
    "SIAC": ["siac", "singapore international arbitration"],
    "HKIAC": ["hkiac", "hong kong international arbitration"],
    "VIAC": ["viac", "vienna international arbitral"],
    "DIS": ["deutsche institution fur schiedsgerichtsbarkeit", "german arbitration institute"],
    "CRCICA": ["crcica", "cairo regional centre"],
    "ICDR/AAA": ["icdr", "american arbitration association"],
    "DIAC": ["diac", "dubai international arbitration"],
    "CIETAC": ["cietac"],
    "ad hoc": ["ad hoc arbitration"],
}

SECTORS = {
    "Mining & metals": ["mining", "mine ", "gold", "copper", "lithium", "nickel",
                        "cobalt", "bauxite", "iron ore", "concession", "tailings"],
    "Oil & gas": ["oil", "gas", "lng", "petroleum", "upstream", "refinery",
                  "pipeline", "psc ", "production sharing"],
    "Power & renewables": ["solar", "wind", "hydro", "power plant", "tariff",
                           "feed-in", "renewable", "electricity", "grid"],
    "Construction": ["construction", "epc", "fidic", "contractor", "infrastructure",
                     "highway", "metro", "airport", "delay claim"],
    "Telecoms": ["telecom", "spectrum", "mobile operator", "licence fee"],
    "Finance & banking": ["bank", "bond", "sovereign debt", "financial institution",
                          "insurance", "reinsurance"],
    "Pharma & health": ["pharmaceutic", "patent", "clinical", "health"],
    "Agribusiness": ["agricultur", "farmland", "sugar", "palm oil", "timber"],
    "Transport & logistics": ["port ", "terminal", "shipping", "railway", "logistics"],
    "Tech & data": ["data centre", "data center", "software", "platform", "crypto"],
}
