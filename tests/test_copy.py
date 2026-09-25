"""The copy desk and the explanation cap: what a printed entry may look like."""
from arbradar import copydesk, style
from arbradar.explain import MAX_CHARS, _clause_cut, fit


def test_cut_sentence_closes_before_its_trailing_phrase():
    head = ("In a rare example of a successful set-aside in Hong Kong, a court has annulled an HKIAC award that "
            "ordered two shareholders in a listing vehicle to pay a co-investor US$480 million over a failed initial")
    assert _clause_cut(head, 10 ** 6).endswith("US$480 million.")
    assert _clause_cut("Central Africa’s regulator has revoked Axiome Capital’s licence and initiated its "
                       "liquidation after the Congolese", 10 ** 6).endswith("initiated its liquidation.")


def test_chained_short_phrases_go_together():
    t = ("EU finance ministers are considering ways to tax what Germany's finance minister described as "
         "'excessive profits' in the energy sector amid fears of a major energy price")
    assert _clause_cut(t, 10 ** 6).endswith("in the energy sector.")


def test_fit_keeps_whole_sentences_within_the_cap():
    text = "First sentence here. " * 6 + "A trailing one."
    out = fit(text)
    assert len(out) <= MAX_CHARS
    assert out.endswith(".")


def test_title_case_becomes_sentence_case_but_names_survive():
    h = style.headline("Contractual Bar On Interest For Delayed Payment Ousts Even Pre-Reference Interest: "
                       "Supreme Court In NEEPCO Arbitration Case")
    assert h.startswith("Contractual bar on interest for delayed payment ousts even pre-reference interest")
    assert "Supreme Court" in h and "NEEPCO" in h
    assert style.headline("Three Crowns Taps Freshfields Pro For New Dubai Office") == \
        "Three Crowns taps Freshfields pro for new Dubai office"


def test_copy_desk_strips_a_trailing_space_and_house_forms():
    it = {"title": "Hong Kong court sets aside $480 million award in IPO dispute ", "summary": ""}
    copydesk.fix_headline(it)
    assert it["title_en"] == "Hong Kong court sets aside US$480 million award in IPO dispute"


def test_banned_words_leave_the_explanation():
    it = {"title": "Firm hires partner", "story": "Three Crowns announced a significant partner hire for its office."}
    copydesk.fix_explanation(it)
    assert "significant" not in it["story"]
    assert it["story"].endswith(".")
