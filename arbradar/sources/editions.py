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


# Foreign investors with the balance sheet to instruct. A State measure against one
# of these is a lead even when nobody has said the word "arbitration" yet.
MAJORS = [
    # mining and metals
    "Glencore", "Rio Tinto", "BHP", "Anglo American", "Barrick", "Newmont", "First Quantum",
    "Freeport", "Vale", "Teck", "Antofagasta", "Southern Copper", "Ivanhoe", "AngloGold",
    "Gold Fields", "Kinross", "B2Gold", "Endeavour Mining", "Centamin", "Fortescue",
    "Lundin", "Eramet", "Albemarle", "SQM", "Ganfeng", "Tianqi", "Zijin", "CMOC",
    # oil and gas
    "TotalEnergies", "Shell", "BP", "Chevron", "ExxonMobil", "Eni", "Equinor", "Repsol",
    "Galp", "OMV", "Woodside", "Santos", "Tullow", "Kosmos", "Perenco", "Vitol", "Trafigura",
    "Gunvor", "Chariot", "Genel", "Gulf Keystone", "DNO", "Maurel", "Africa Oil",
    # power and utilities
    "Enel", "Iberdrola", "EDF", "Engie", "RWE", "Vattenfall", "Ørsted", "Orsted", "Scatec",
    "Globeleq", "ACWA", "Masdar", "AES", "Veolia", "Suez", "Acciona", "Naturgy", "EDP",
    # telecoms and tech
    "Vodafone", "Telefónica", "Telefonica", "MTN", "Orange", "Airtel", "Millicom", "Veon",
    "Ooredoo", "Zain", "Etisalat", "Meta", "Google", "Amazon", "Microsoft", "Apple", "Uber",
    "Oracle", "Starlink", "SpaceX",
    # consumer, pharma, finance, infrastructure
    "Nestlé", "Nestle", "Unilever", "AB InBev", "Philip Morris", "British American Tobacco",
    "Coca-Cola", "PepsiCo", "Diageo", "Heineken", "Carlsberg", "Pfizer", "Novartis", "Roche",
    "Sanofi", "AstraZeneca", "Bayer", "Siemens", "Alstom", "Bombardier", "Airbus", "Boeing",
    "Vinci", "Bouygues", "Eiffage", "Ferrovial", "ACS", "Sacyr", "Strabag", "Salini", "Webuild",
    "DP World", "APM Terminals", "Maersk", "MSC", "CMA CGM", "Hutchison", "PSA International",
    "HSBC", "Citi", "Standard Chartered", "Société Générale", "BNP Paribas", "Santander",
    "BBVA", "Scotiabank", "Blackstone", "KKR", "Brookfield", "Macquarie", "Actis", "Carlyle",
]

# Measures a State takes that map onto treaty standards: expropriation, fair and
# equitable treatment, umbrella clause, transfers. Queried in the editions' languages.
MEASURES: Dict[str, List[str]] = {
    "en": ['(revokes OR revoked OR cancels OR cancelled OR terminates OR terminated) (licence OR license OR concession OR permit OR contract) (foreign OR international OR "-owned" OR investor OR company)',
           '("tax assessment" OR "back taxes" OR "windfall tax" OR "retroactive tax" OR "tax demand") (mining OR oil OR gas OR telecom OR "foreign company" OR multinational) (billion OR million)',
           '(nationalise OR nationalize OR nationalisation OR nationalization OR expropriate OR expropriation OR "takes control" OR seizes OR seized) (mine OR plant OR refinery OR company OR assets OR subsidiary) government',
           '(government OR ministry OR regulator OR president OR decree) (suspends OR halts OR freezes OR blocks OR bans) (exports OR operations OR project OR licence OR dividends OR transfers) (foreign OR investor OR company)',
           '("renegotiate" OR "review" OR "reopen") (contract OR concession OR "production sharing" OR "power purchase" OR PPA OR tariff) government (foreign OR investor OR company)'],
    "es": ['(revoca OR revocó OR cancela OR canceló OR rescinde OR rescindió OR caduca) (licencia OR concesión OR permiso OR contrato) (extranjera OR extranjero OR inversionista OR empresa OR minera OR petrolera)',
           '(expropia OR expropiación OR nacionaliza OR nacionalización OR "toma el control" OR incauta OR embarga) (mina OR planta OR empresa OR activos OR filial) gobierno',
           '(gobierno OR ministerio OR decreto OR regulador) (suspende OR bloquea OR prohíbe OR congela) (exportaciones OR operaciones OR proyecto OR tarifa OR dividendos) (extranjera OR inversionista OR empresa)',
           '("renegociar" OR "revisar" OR "reabrir") (contrato OR concesión OR tarifa OR "contrato de exploración") gobierno (extranjera OR inversionista OR empresa)'],
    "fr": ['(retire OR retrait OR annule OR annulation OR résilie OR résiliation) (licence OR permis OR concession OR contrat) (étrangère OR étranger OR investisseur OR société OR minière OR pétrolière)',
           '(nationalise OR nationalisation OR exproprie OR expropriation OR saisit OR saisie OR "prend le contrôle") (mine OR usine OR société OR actifs OR filiale) gouvernement',
           '(gouvernement OR ministère OR décret OR régulateur) (suspend OR bloque OR interdit OR gèle) (exportations OR activités OR projet OR tarif OR dividendes) (étrangère OR investisseur OR société)'],
    "ru": ['(отзыв OR отозвал OR аннулировал OR расторг OR лишил) (лицензии OR лицензию OR концессии OR контракта OR разрешения) (иностранн OR инвестор OR компани)',
           '(национализац OR экспроприац OR изъятие OR арест OR "передан в собственность государства") (завод OR рудник OR месторождение OR компани OR активы OR доля) (иностранн OR инвестор)',
           '(правительство OR министерство OR указ OR суд) (приостановил OR запретил OR заморозил OR заблокировал) (экспорт OR деятельность OR проект OR дивиденды OR вывод) (иностранн OR инвестор OR компани)',
           '(доначислил OR доначисление OR "налоговые претензии" OR "налоговая проверка") (иностранн OR компани) (млрд OR миллиард OR млн)'],
    "tr": ['(iptal OR iptal etti OR feshetti OR askıya aldı) (lisans OR ruhsat OR imtiyaz OR sözleşme) (yabancı OR yatırımcı OR şirket)',
           '(kamulaştırma OR millileştirme OR "el koydu" OR "el konuldu" OR TMSF) (şirket OR maden OR santral OR varlık) (yabancı OR yatırımcı)'],
    "pt": ['(revoga OR revogou OR cancela OR cancelou OR rescinde OR rescindiu) (licença OR concessão OR contrato OR alvará) (estrangeira OR estrangeiro OR investidor OR empresa OR mineradora OR petrolífera)',
           '(nacionaliza OR nacionalização OR expropria OR expropriação OR "assume o controle") (mina OR fábrica OR empresa OR ativos OR subsidiária) governo'],
    "ar": ['(إلغاء OR سحب OR فسخ OR تعليق) (رخصة OR ترخيص OR امتياز OR عقد) (أجنبية OR أجنبي OR مستثمر OR شركة)',
           '(تأميم OR مصادرة OR "الاستيلاء على") (شركة OR منجم OR مصنع OR أصول) (أجنبية OR مستثمر)'],
    "id": ['(mencabut OR pencabutan OR membatalkan OR menghentikan) (izin OR IUP OR konsesi OR kontrak) (asing OR investor OR perusahaan)',
           '(nasionalisasi OR pengambilalihan OR menyita OR "mengambil alih") (tambang OR pabrik OR perusahaan OR aset OR saham) pemerintah (asing OR investor)'],
    "uk": ['(анулював OR анулювання OR скасував OR розірвав OR позбавив) (ліцензії OR ліцензію OR концесії OR контракту OR дозволу) (іноземн OR інвестор OR компані)',
           '(націоналізац OR експропріац OR арешт OR вилучення OR "передано державі") (завод OR родовище OR компані OR активи OR частка) (іноземн OR інвестор)'],
    "hy": ['(լիցենզիա OR թույլտվություն OR պայմանագիր) (զրկել OR դադարեցնել OR չեղարկել) (օտարերկրյա OR ներդրող OR ընկերություն)',
           '(ազգայնացում OR բռնագրավում OR արգելանք) (ընկերություն OR հանք OR գործարան OR ակտիվներ) (օտարերկրյա OR ներդրող)'],
    "ka": ['(გაუქმება OR შეჩერება OR ჩამორთმევა) (ლიცენზია OR ნებართვა OR კონცესია OR კონტრაქტი) (უცხოური OR ინვესტორი OR კომპანია)',
           '(ნაციონალიზაცია OR ექსპროპრიაცია OR დაყადაღება OR "ჩამორთმევა") (კომპანია OR საწარმო OR აქტივები) (უცხოური OR ინვესტორი)'],
    "az": ['(ləğv OR dayandırıl OR geri alın) (lisenziya OR icazə OR konsessiya OR müqavilə) (xarici OR investor OR şirkət)',
           '(milliləşdirmə OR müsadirə OR "həbs qoyul") (şirkət OR mədən OR zavod OR aktiv) (xarici OR investor)'],
    "vi": ['("thu hồi" OR "hủy bỏ" OR "đình chỉ" OR "chấm dứt") ("giấy phép" OR "hợp đồng" OR "dự án") ("nhà đầu tư nước ngoài" OR "doanh nghiệp FDI" OR "công ty nước ngoài")'],
    "uz": ['(bekor OR toʻxtatildi OR "qaytarib olindi") (litsenziya OR ruxsatnoma OR shartnoma OR kontsessiya) (xorijiy OR investor OR kompaniya)'],
}


# State names and demonyms -> canonical State. Used to answer "who" for a press
# item that no model has read yet.
COUNTRIES = {}
for _canon, _forms in {
    "Argentina": ["Argentina", "Argentine", "Argentinian"], "Armenia": ["Armenia", "Armenian"],
    "Australia": ["Australia", "Australian"], "Azerbaijan": ["Azerbaijan", "Azerbaijani", "Azeri"],
    "Belgium": ["Belgium", "Belgian"], "Bolivia": ["Bolivia", "Bolivian"], "Brazil": ["Brazil", "Brazilian"],
    "Bulgaria": ["Bulgaria", "Bulgarian"], "Burkina Faso": ["Burkina Faso", "Burkinabe"],
    "Cameroon": ["Cameroon", "Cameroonian"], "Canada": ["Canada", "Canadian"], "Chile": ["Chile", "Chilean"],
    "China": ["China", "Chinese"], "Colombia": ["Colombia", "Colombian"], "Congo (DRC)": ["DRC", "Congo", "Congolese"],
    "Croatia": ["Croatia", "Croatian"], "Cyprus": ["Cyprus", "Cypriot"], "Czechia": ["Czech Republic", "Czechia", "Czech"],
    "Ecuador": ["Ecuador", "Ecuadorian", "Ecuadorean"], "Egypt": ["Egypt", "Egyptian"],
    "Georgia": ["Georgia", "Georgian"], "Germany": ["Germany", "German"], "Ghana": ["Ghana", "Ghanaian"],
    "Greece": ["Greece", "Greek"], "Guatemala": ["Guatemala", "Guatemalan"], "Guinea": ["Guinea", "Guinean"],
    "Honduras": ["Honduras", "Honduran"], "Hungary": ["Hungary", "Hungarian"], "India": ["India", "Indian"],
    "Indonesia": ["Indonesia", "Indonesian"], "Iraq": ["Iraq", "Iraqi"], "Ireland": ["Ireland", "Irish"],
    "Italy": ["Italy", "Italian"], "Kazakhstan": ["Kazakhstan", "Kazakh"], "Kenya": ["Kenya", "Kenyan"],
    "Korea": ["South Korea", "Korea", "Korean"], "Kyrgyzstan": ["Kyrgyzstan", "Kyrgyz"], "Lebanon": ["Lebanon", "Lebanese"],
    "Libya": ["Libya", "Libyan"], "Malaysia": ["Malaysia", "Malaysian"], "Mali": ["Mali", "Malian"],
    "Malta": ["Malta", "Maltese"], "Mexico": ["Mexico", "Mexican"], "Moldova": ["Moldova", "Moldovan"],
    "Mongolia": ["Mongolia", "Mongolian"], "Montenegro": ["Montenegro", "Montenegrin"], "Morocco": ["Morocco", "Moroccan"],
    "Mozambique": ["Mozambique", "Mozambican"], "Netherlands": ["Netherlands", "Dutch"], "Niger": ["Niger", "Nigerien"],
    "Nigeria": ["Nigeria", "Nigerian"], "Norway": ["Norway", "Norwegian"], "Pakistan": ["Pakistan", "Pakistani"],
    "Panama": ["Panama", "Panamanian"], "Paraguay": ["Paraguay", "Paraguayan"], "Peru": ["Peru", "Peruvian"],
    "Philippines": ["Philippines", "Philippine", "Filipino"], "Poland": ["Poland", "Polish"], "Portugal": ["Portugal", "Portuguese"],
    "Qatar": ["Qatar", "Qatari"], "Romania": ["Romania", "Romanian"], "Russia": ["Russia", "Russian", "Kremlin", "Putin"],
    "Saudi Arabia": ["Saudi Arabia", "Saudi"], "Senegal": ["Senegal", "Senegalese"], "Serbia": ["Serbia", "Serbian"],
    "Slovakia": ["Slovakia", "Slovak"], "Slovenia": ["Slovenia", "Slovenian"], "South Africa": ["South Africa", "South African"],
    "Spain": ["Spain", "Spanish"], "Sri Lanka": ["Sri Lanka", "Sri Lankan"], "Tanzania": ["Tanzania", "Tanzanian"],
    "Tajikistan": ["Tajikistan", "Tajik"], "Turkey": ["Turkey", "Türkiye", "Turkish"], "Turkmenistan": ["Turkmenistan", "Turkmen"],
    "Uganda": ["Uganda", "Ugandan"], "Ukraine": ["Ukraine", "Ukrainian"], "United Arab Emirates": ["UAE", "United Arab Emirates", "Emirati"],
    "United Kingdom": ["United Kingdom", "Britain", "British", "UK"], "United States": ["United States", "U.S.", "US government"],
    "Uruguay": ["Uruguay", "Uruguayan"], "Uzbekistan": ["Uzbekistan", "Uzbek"], "Venezuela": ["Venezuela", "Venezuelan"],
    "Vietnam": ["Vietnam", "Vietnamese"], "Zambia": ["Zambia", "Zambian"], "Zimbabwe": ["Zimbabwe", "Zimbabwean"],
    "Algeria": ["Algeria", "Algerian"], "Angola": ["Angola", "Angolan"], "Bangladesh": ["Bangladesh", "Bangladeshi"],
    "Bosnia and Herzegovina": ["Bosnia", "Bosnian"], "Costa Rica": ["Costa Rica", "Costa Rican"], "Dominican Republic": ["Dominican Republic", "Dominican"],
    "El Salvador": ["El Salvador", "Salvadoran"], "Ethiopia": ["Ethiopia", "Ethiopian"], "Jordan": ["Jordan", "Jordanian"],
    "Kuwait": ["Kuwait", "Kuwaiti"], "Laos": ["Laos", "Lao"], "Latvia": ["Latvia", "Latvian"], "Lithuania": ["Lithuania", "Lithuanian"],
    "Madagascar": ["Madagascar", "Malagasy"], "Myanmar": ["Myanmar", "Burmese"], "Nicaragua": ["Nicaragua", "Nicaraguan"],
    "Oman": ["Oman", "Omani"], "Papua New Guinea": ["Papua New Guinea", "PNG"], "Sierra Leone": ["Sierra Leone"],
    "Sudan": ["Sudan", "Sudanese"], "Tunisia": ["Tunisia", "Tunisian"], "Yemen": ["Yemen", "Yemeni"],
}.items():
    for _f in _forms:
        COUNTRIES[_f] = _canon

_COUNTRY_RE = None


def states_in(text: str):
    """Canonical States named in a text, longest form first, whole words only."""
    global _COUNTRY_RE
    if _COUNTRY_RE is None:
        forms = sorted(COUNTRIES, key=len, reverse=True)
        _COUNTRY_RE = __import__("re").compile(r"(?<![\w-])(" + "|".join(__import__("re").escape(f) for f in forms) + r")(?![\w-])")
    out = []
    for m in _COUNTRY_RE.finditer(text or ""):
        c = COUNTRIES[m.group(1)]
        if c not in out:
            out.append(c)
    return out
