"""Source registry. Each adapter yields raw dicts; the pipeline normalises them."""
from . import rss, edgar, courtlistener, icsid, pca, gnews, gdelt, tenders, registers, pca_cases, courts, wires

REGISTRY = {
    "rss": rss.run,
    "edgar": edgar.run,
    "courtlistener": courtlistener.run,
    "icsid": icsid.run,
    "pca": pca.run,
    "gnews": gnews.run,
    "gdelt": gdelt.run,
    "tenders": tenders.run,
    "registers": registers.run,
    "pca_cases": pca_cases.run,
    "courts": courts.run,
    "wires": wires.run,
}

# tier 1 = primary record (registry, docket, filing); tier 2 = reported;
# tier 3 = commentary. Feeds the source-reliability term in scoring.
TIERS = {"edgar": 1, "courtlistener": 1, "icsid": 1, "pca": 1, "rss": 2,
         "gnews": 2, "gdelt": 3, "tenders": 1, "registers": 1, "pca_cases": 1, "courts": 1,
         "wires": 1}                                  # a company's own disclosure is a primary record
