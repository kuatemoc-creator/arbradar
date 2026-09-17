"""Google News editions and native-language query banks.

The global English edition misses most of what happens in a country's own press.
Querying each edition in its own language finds the ministry statement in Yerevan,
the mining-licence story in Astana, the concession row in Lima - before any of it
is translated, if it ever is. Titles come back in the source language; the
extraction stage produces the English headline.

Each edition: (label, hl, gl, ceid, language key). Each language: three
compact OR-queries - forum terms, distress terms, treaty terms.
"""
from typing import Dict, List, Tuple

EDITIONS: List[Tuple[str, str, str, str, str]] = [
    # Caucasus and Central Asia - the hard-to-track set
    ("Armenia", "hy", "AM", "AM:hy", "hy"),
    ("Armenia (ru)", "ru", "AM", "AM:ru", "ru"),
    ("Georgia", "ka", "GE", "GE:ka", "ka"),
    ("Azerbaijan", "az", "AZ", "AZ:az", "az"),
    ("Kazakhstan", "ru", "KZ", "KZ:ru", "ru"),
    ("Uzbekistan", "ru", "UZ", "UZ:ru", "ru"),
    ("Uzbekistan (uz)", "uz", "UZ", "UZ:uz", "uz"),
    ("Ukraine", "uk", "UA", "UA:uk", "uk"),
    ("Russia", "ru", "RU", "RU:ru", "ru"),
    ("Turkey", "tr", "TR", "TR:tr", "tr"),
    # Latin America - the largest ISDS docket by respondent
    ("Mexico", "es-419", "MX", "MX:es-419", "es"),
    ("Argentina", "es-419", "AR", "AR:es-419", "es"),
    ("Colombia", "es-419", "CO", "CO:es-419", "es"),
    ("Peru", "es-419", "PE", "PE:es-419", "es"),
    ("Chile", "es-419", "CL", "CL:es-419", "es"),
    ("Spain", "es", "ES", "ES:es", "es"),
    ("Brazil", "pt-BR", "BR", "BR:pt-419", "pt"),
    ("Portugal", "pt-PT", "PT", "PT:pt-150", "pt"),
    # Francophone Africa and the Maghreb
    ("France", "fr", "FR", "FR:fr", "fr"),
    ("Senegal", "fr", "SN", "SN:fr", "fr"),
    ("Morocco", "fr", "MA", "MA:fr", "fr"),
    # Arabic
    ("Egypt", "ar", "EG", "EG:ar", "ar"),
    ("Saudi Arabia", "ar", "SA", "SA:ar", "ar"),
    ("UAE", "ar", "AE", "AE:ar", "ar"),
    # South-East Asia
    ("Indonesia", "id", "ID", "ID:id", "id"),
    ("Vietnam", "vi", "VN", "VN:vi", "vi"),
    # English editions scoped to a country - local press the global edition buries
    ("Nigeria", "en-NG", "NG", "NG:en", "en"),
    ("Kenya", "en", "KE", "KE:en", "en"),
    ("South Africa", "en-ZA", "ZA", "ZA:en", "en"),
    ("India", "en-IN", "IN", "IN:en", "en"),
    ("Pakistan", "en", "PK", "PK:en", "en"),
    ("Australia", "en-AU", "AU", "AU:en", "en"),
    ("Canada", "en-CA", "CA", "CA:en", "en"),
    ("Singapore", "en-SG", "SG", "SG:en", "en"),
    ("United Kingdom", "en-GB", "GB", "GB:en", "en"),
    ("United States", "en-US", "US", "US:en", "en"),
]

TERMS: Dict[str, List[str]] = {
    "en": ['arbitration (ICSID OR "investment treaty" OR "international arbitration") government -referee -football',
           '(expropriation OR nationalisation OR nationalization OR "licence revoked" OR "license revoked") investor',
           '("notice of dispute" OR "notice of intent" OR "notice of arbitration") (treaty OR government)'],
    "hy": ['(արբիտրաժ OR ICSID) (ներդրող OR միջազգային OR պետություն)',
           'ազգայնացում OR բռնագրավում OR "օտարերկրյա ներդրող"',
           '"ներդրումային վեճ" OR "ներդրումային համաձայնագիր"'],
    "ka": ['(არბიტრაჟი OR ICSID) (ინვესტორი OR საერთაშორისო OR სახელმწიფო) -ფეხბურთი',
           'ექსპროპრიაცია OR ნაციონალიზაცია OR "უცხოელი ინვესტორი"',
           '"საინვესტიციო დავა" OR "საინვესტიციო ხელშეკრულება"'],
    "az": ['(arbitraj OR ICSID) (investor OR beynəlxalq OR dövlət) -futbol',
           'ekspropriasiya OR milliləşdirmə OR "xarici investor"',
           '"investisiya mübahisəsi" OR "investisiya sazişi"'],
    "ru": ['(арбитраж OR ICSID OR МЦУИС) (инвестор OR международный OR государство OR иск) -футбол -судья',
           '(экспроприация OR национализация OR "отзыв лицензии") (инвестор OR компания OR иностранн)',
           '"инвестиционный спор" OR "инвестиционное соглашение" OR "уведомление о споре"'],
    "uk": ['(арбітраж OR ICSID) (інвестор OR міжнародний OR держава OR позов) -футбол',
           '(експропріація OR націоналізація) (інвестор OR компанія)',
           '"інвестиційний спір" OR "інвестиційна угода"'],
    "uz": ['(arbitraj OR ICSID) (investor OR xalqaro OR davlat) -futbol',
           'ekspropriatsiya OR milliylashtirish OR "xorijiy investor"',
           '"investitsiya nizosi"'],
    "tr": ['(tahkim OR ICSID) (yatırımcı OR uluslararası OR devlet OR dava) -maç -hakem',
           '(kamulaştırma OR millileştirme OR "lisans iptali") (yabancı OR yatırımcı OR şirket) -"acele kamulaştırma"',
           '"yatırım anlaşmazlığı" OR "yatırım uyuşmazlığı" OR "ikili yatırım anlaşması"'],
    "es": ['(arbitraje OR CIADI) (inversión OR inversionista OR inversor OR internacional OR Estado) -fútbol -árbitro -liga',
           '(expropiación OR nacionalización OR "revocación de licencia") (inversionista OR inversor OR empresa OR extranjer)',
           '"tratado bilateral de inversión" OR "controversia de inversión" OR "notificación de controversia"'],
    "pt": ['(arbitragem OR CIRDI OR ICSID) (investimento OR investidor OR internacional OR Estado) -futebol -árbitro',
           '(expropriação OR desapropriação OR nacionalização) (investidor OR empresa OR estrangeir)',
           '"tratado de investimento" OR "disputa de investimento"'],
    "fr": ['(arbitrage OR CIRDI) (investissement OR investisseur OR international OR État) -football -match -arbitre',
           '(expropriation OR nationalisation OR "retrait de licence") (investisseur OR entreprise OR étranger)',
           '"traité bilatéral d\'investissement" OR "différend relatif aux investissements"'],
    "ar": ['("التحكيم الدولي" OR "المركز الدولي لتسوية منازعات الاستثمار") -مباراة -كرة',
           '(مصادرة OR تأميم) (مستثمر OR شركة OR أجنبي)',
           '"نزاع استثماري" OR "اتفاقية استثمار"'],
    "id": ['(arbitrase OR ICSID) (investor OR internasional OR pemerintah) -sepak',
           '(nasionalisasi OR pengambilalihan OR "pencabutan izin") (investor OR asing OR perusahaan)',
           '"sengketa investasi" OR "perjanjian investasi"'],
    "vi": ['"trọng tài quốc tế" OR ICSID -bóng',
           '("quốc hữu hóa" OR "thu hồi giấy phép") ("nhà đầu tư" OR "doanh nghiệp")',
           '"tranh chấp đầu tư"'],
}

LANG_NAMES = {"hy": "Armenian", "ka": "Georgian", "az": "Azerbaijani", "ru": "Russian",
              "uk": "Ukrainian", "uz": "Uzbek", "tr": "Turkish", "es": "Spanish",
              "pt": "Portuguese", "fr": "French", "ar": "Arabic", "id": "Indonesian",
              "vi": "Vietnamese", "en": "English"}
