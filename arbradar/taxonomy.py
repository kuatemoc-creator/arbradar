"""Event taxonomy and gazetteers.

The ordering of EVENT_TYPES is the whole editorial thesis: GAR and IAReporter
report events, which is useful but late. A practitioner hunting mandates cares
about the point at which counsel has *not yet* been chosen. So the weights below
rank leading indicators above reported outcomes.
"""
from typing import Dict, List

# weight = raw BD value of the event, before recency / watchlist multipliers
EVENT_TYPES: Dict[str, Dict] = {
    "counsel_tender": {
        "weight": 90,
        "label": "State tendering for counsel",
        "why": "A State or state enterprise is procuring arbitration counsel: the dispute exists and the instruction is open.",
    },
    "commercial_dispute": {
        "weight": 68,
        "label": "Commercial arbitration",
        "why": "A contract dispute has gone, or is going, to arbitration: EPC, JV, supply, licence, charter, offtake.",
    },
    "notice_of_intent": {
        "weight": 100,
        "label": "Notice of intent / dispute",
        "why": "The cooling-off period is running and counsel is being chosen now.",
    },
    "s1782_application": {
        "weight": 85,
        "label": "s.1782 discovery application",
        "why": "Someone is gathering evidence for an arbitration that has not yet been reported.",
    },
    "new_case_filed": {
        "weight": 80,
        "label": "New case registered",
        "why": "Registration comes first; the respondent side and co-counsel are often still to be settled.",
    },
    "enforcement_action": {
        "weight": 78,
        "label": "Enforcement / recognition",
        "why": "Enforcement needs counsel in every jurisdiction where the assets sit.",
    },
    "annulment_setaside": {
        "weight": 72,
        "label": "Annulment / set-aside",
        "why": "A second mandate, and usually a different team from the merits.",
    },
    "state_measure": {
        "weight": 70,
        "label": "State measure against a foreign investor",
        "why": "A licence, contract, tax or regulatory action against a foreign investor of means: the fact pattern of a treaty claim, before any notice.",
    },
    "distress_event": {
        "weight": 52,
        "label": "Expropriation / licence / sanctions event",
        "why": "Events of this kind tend to produce a treaty claim within a year or two.",
    },
    "award_issued": {
        "weight": 55,
        "label": "Award issued",
        "why": "The award starts the clock on annulment and enforcement.",
    },
    "treaty_action": {
        "weight": 45,
        "label": "Treaty signature / denunciation",
        "why": "Treaty changes move the deadlines for everyone with an investment covered by it.",
    },
    "funding": {
        "weight": 42,
        "label": "Third-party funding",
        "why": "A funded claimant has the money to instruct.",
    },
    "tribunal_constituted": {
        "weight": 35,
        "label": "Tribunal constituted / challenge",
        "why": "Who sits, and who put them there, is worth knowing before the next appointment.",
    },
    "appointment": {
        "weight": 32,
        "label": "Appointment",
        "why": "Who now sits on the tribunal, runs the institution or leads the practice.",
    },
    "lateral_move": {
        "weight": 30,
        "label": "Lateral move / team change",
        "why": "A move opens conflicts and makes clients reachable.",
    },
    "commentary": {
        "weight": 10,
        "label": "Commentary / analysis",
        "why": "Context rather than a lead.",
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
    ("commercial_dispute", [
        "request for arbitration", "commenced arbitration", "initiated arbitration", "arbitration proceedings",
        "referred to arbitration", "refer the dispute to arbitration", "icc arbitration", "lcia arbitration",
        "siac arbitration", "hkiac arbitration", "scc arbitration", "dis arbitration", "arbitral tribunal",
        "dispute adjudication board", "dispute board", "fidic", "take-or-pay", "take or pay", "price review",
        "price reopener", "notice of default", "terminated the contract", "contract terminated", "termination notice",
        "terminates contract", "terminated the agreement", "termination of the contract", "termination of the concession",
        "epc contract", "epc contractor", "liquidated damages",
        "delay claim", "variation claim", "final account", "force majeure", "offtake agreement", "charterparty",
        "licence agreement", "license agreement", "royalty dispute", "milestone payment", "joint venture dispute",
        "shareholder dispute", "call on the bond", "performance bond", "demand guarantee",
    ]),
    ("new_case_filed", [
        "request for arbitration", "notice of arbitration", "registered the request",
        "case registered", "new case", "files claim", "filed a claim",
        "commenced arbitration", "initiated arbitration", "statement of claim",
        "request for the institution",
        # native-language triggers - the LLM tier does this properly; these catch the obvious
        "подал в icsid", "подал иск", "иск против", "иск в icsid", "иск в мцуис",
        "demanda ante el ciadi", "presentó una demanda", "demanda de arbitraje",
        "a déposé une demande", "recours au cirdi", "tahkim davası", "tahkime başvurdu",
        "ação de arbitragem", "icsid-ի", "հայց",
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
    ("appointment", [
        "appointed as arbitrator", "appointed arbitrator", "appointed president", "elected president",
        "appointed secretary", "new secretary-general", "new secretary general", "as secretary-general",
        "as secretary general", "appointed to the icc court", "appointed to the court of arbitration",
        "joins the lcia court", "appointed as head of", "named head of", "named as head of", "appointed head of",
        "as arbitration head", "arbitration head", "head of international arbitration", "head of arbitration",
        "co-head of", "chair of the arbitration", "arbitration chair", "vice-president of the icc",
        "appointed as chair", "appointed chair", "elected chair", "appointed director general",
        "appointed registrar", "new registrar", "appointed as counsel to the",
    ]),
    ("lateral_move", [
        "joins as partner", "joined as partner", "lateral hire", "lateral move",
        "launches arbitration practice", "hires arbitration", "team joins",
        "boutique", "lawyers launch", "opens an office", "opens office", "opens in",
        " hires ", " hired ", " hiring ", "joins from", "joins firm", "joins the firm", "head joins",
        "partner joins", "partners join", "relocates", "moves to", "leaves for", "departs", " exits ",
        "rejoins", "returns to", "new partner", "promoted to partner", "partner promotion", "makes up",
        "spin-off", "spins off", "launches practice", "launches disputes", "launch of", "sets up",
        "poaches", "snaps up", "recruits", "adds partner", "adds arbitration", "bolsters", "strengthens",
        "expands arbitration", "grows arbitration",
    ]),
    ("distress_event", [
        "expropriat", "nationalisation", "nationalization", "nationalised", "nationalized",
        "nationalise ", "nationalize ", "nationalises", "nationalizes", "licence revoked", "license revoked",
        "permit cancelled", "permit canceled", "concession terminated", "seizure of",
        "asset freeze", "windfall tax", "sanctions-related claim",
        "forced divestment", "mining permit", "resource rent",
        "экспроприац", "национализац", "отзыв лицензии", "expropiación", "nacionalización",
        "revocación de licencia", "expropriação", "nacionalização", "kamulaştırma",
        "millileştirme", "lisans iptali", "nationalisation des", "retrait de licence",
        "ազգայնաց", "բռնագրավ", "ექსპროპრიაცია", "ნაციონალიზაცია", "مصادرة", "تأميم",
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
