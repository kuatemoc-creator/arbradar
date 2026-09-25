"""Same story or not: the cases that went wrong once and must not again."""
from arbradar import pipeline


def _it(title, source="Google News / x", url=None, score=50.0, **kw):
    d = {"title": title, "source": source, "url": url or "https://example.com/" + str(abs(hash(title))),
         "score": score, "lang": "en", "summary": ""}
    d.update(kw)
    return d


def test_mellat_copies_merge_into_one_story():
    reps = pipeline.cluster([
        _it("Turkey revokes Iran’s Bank Mellat license after 44 years"),
        _it("Türkiye revokes Bank Mellat’s operating license"),
        _it("Turkey revokes operating license of Iran's Mellat Bank amid US economic pressure campaign"),
    ])
    assert len(reps) == 1
    assert len(reps[0]["also"]) == 2


def test_papel_is_not_mellat():
    reps = pipeline.cluster([
        _it("Turkey revokes Iran’s Bank Mellat license after 44 years"),
        _it("Turkey’s central bank revokes license of Papel payments company amid money laundering case"),
    ])
    assert len(reps) == 2


def test_windfall_tax_in_the_eu_is_one_lead_whatever_the_headline():
    a = pipeline._topics_of([_it("EU Considers Windfall Tax on Energy Companies Amid Oil Price Surge")])
    b = pipeline._topics_of([_it("'Oil companies are exploiting the situation': Europe eyes windfall tax on energy giants")])
    c = pipeline._topics_of([_it("Germany Pushes EU To Tax Oil Windfall Profits Tied To Hormuz")])
    assert a & b and a & c


def test_a_czech_windfall_tax_is_another_lead():
    eu = pipeline._topics_of([_it("EU Considers Windfall Tax on Energy Companies")])
    cz = pipeline._topics_of([_it("Czech government reinstates fuel margin caps, plans windfall tax on refineries")])
    assert not (eu & cz)


def test_a_story_with_no_measure_has_no_topic():
    assert pipeline._topics_of([_it("Egypt defeats Saudi real estate investors’ mega-claim")]) == set()


def test_entities_ignore_dictionary_words_and_states():
    ents = pipeline._entities("Turkey revokes Iran’s Bank Mellat license after 44 years")
    assert "mellat" in ents
    assert "turkey" not in ents and "license" not in ents


def test_a_capital_names_its_state():
    prague = pipeline._topics_of([_it("Prague caps fuel prices and taxes refiners' windfall profits")])
    czech = pipeline._topics_of([_it("Czech government reinstates fuel margin caps, plans windfall tax on refineries")])
    assert prague & czech
