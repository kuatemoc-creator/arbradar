"""Configuration: models, watchlists, scoring weights, source toggles."""
import os
from dataclasses import dataclass, field
from typing import Dict, List
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "out")
DB_PATH = os.path.join(DATA_DIR, "arbradar.sqlite3")
CONFIG_PATH = os.path.join(ROOT, "config.yaml")

# Model tiers. Cheap models do the bulk reading; the expensive one writes once
# per issue. Costs are $/1M tokens (input/output) as of 2026-06.
TRIAGE_MODEL = "claude-haiku-4-5"    # $1 / $5   - is this item even relevant?
EXTRACT_MODEL = "claude-sonnet-5"    # $2 / $10  - pull structured fields
EDITOR_MODEL = "claude-fable-5-1"    # $10 / $50 - writes the issue, once

# Fable 5.1 declines some requests outright; route those to a fallback rather
# than dropping the issue. Beta header pairs with the scalar "default" form.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass
class Settings:
    newsletter_name: str = "Arbitration Radar"
    tagline: str = "Mandate intelligence for arbitration counsel"
    editor: str = ""
    timezone: str = "Asia/Yerevan"
    lookback_days: int = 7
    max_items_per_issue: int = 25
    min_score: float = 20.0

    triage_model: str = TRIAGE_MODEL
    extract_model: str = EXTRACT_MODEL
    editor_model: str = EDITOR_MODEL
    use_llm: bool = True

    # watchlists: term -> weight multiplier contribution
    states: Dict[str, float] = field(default_factory=dict)
    sectors: Dict[str, float] = field(default_factory=dict)
    companies: Dict[str, float] = field(default_factory=dict)
    firms: Dict[str, float] = field(default_factory=dict)
    mute: List[str] = field(default_factory=list)

    sources: Dict[str, bool] = field(default_factory=dict)
    smtp: Dict[str, str] = field(default_factory=dict)
    recipients: List[str] = field(default_factory=list)


def load(path: str = CONFIG_PATH) -> Settings:
    s = Settings()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        for k, v in raw.items():
            if hasattr(s, k) and v is not None:
                setattr(s, k, v)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        s.use_llm = False
    return s
