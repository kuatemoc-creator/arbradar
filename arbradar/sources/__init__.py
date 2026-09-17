"""Source registry. Each adapter yields raw dicts; the pipeline normalises them."""
from . import rss, edgar, courtlistener, icsid, pca

REGISTRY = {
    "rss": rss.run,
    "edgar": edgar.run,
    "courtlistener": courtlistener.run,
    "icsid": icsid.run,
    "pca": pca.run,
}

# tier 1 = primary record (registry, docket, filing); tier 2 = reported;
# tier 3 = commentary. Feeds the source-reliability term in scoring.
TIERS = {"edgar": 1, "courtlistener": 1, "icsid": 1, "pca": 1, "rss": 2}
