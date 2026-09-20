"""The source map: what ArbRadar reads, per country, and what it should read.

This file is the product. Edit the CANDIDATES table, then:

    python -m tools.sourcemap --probe     # checks every URL, writes SOURCES.md + docs/sources.html

Types:  register   State's own ISDS register (notices of intent, cases)
        gazette    official gazette / legal acts (decrees, licence revocations, expropriations)
        tenders    public procurement (States buying arbitration counsel)
        regulator  mining / energy / utilities regulator (licences, tariffs)
        courts     court decisions or docket (annulment, enforcement, anti-suit)
        exchange   stock exchange disclosures (listed companies announce disputes)
        press      national business / legal press
        agg        Google News edition in the local language (wired for every country below)
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import html
import json
import os
import re
import sys

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128 Safari/537.36", "Accept": "*/*", "Accept-Language": "en,ru;q=0.8,es;q=0.7"}

# (country, type, name, url, note)
CANDIDATES = [
    # ----------------------------------------------------------------- Armenia
    ("Armenia", "gazette", "Government decisions", "https://www.gov.am/en/decrees/", "cabinet decisions incl. concessions and licences"),
    ("Armenia", "gazette", "ARLIS legal information system", "https://www.arlis.am", "all legal acts; search only"),
    ("Armenia", "tenders", "ARMEPS procurement", "https://www.armeps.am", "state procurement portal"),
    ("Armenia", "tenders", "gnumner.am announcements", "https://gnumner.am", "procurement announcements"),
    ("Armenia", "courts", "DataLex court database", "https://www.datalex.am", "first-instance and appeal cases"),
    ("Armenia", "regulator", "Public Services Regulatory Commission", "https://psrc.am/en", "energy, water, telecoms tariffs and licences"),
    ("Armenia", "exchange", "Armenia Securities Exchange", "https://amx.am/en", "listed-company disclosures"),
    ("Armenia", "press", "Armenpress (EN RSS)", "https://armenpress.am/rss/eng", ""),
    ("Armenia", "press", "Hetq", "https://hetq.am/en/rss", "investigative"),
    ("Armenia", "press", "CivilNet", "https://www.civilnet.am/feed", ""),
    ("Armenia", "press", "News.am", "https://news.am/eng/rss/", ""),
    ("Armenia", "press", "Panorama.am", "https://www.panorama.am/en/rss", ""),
    # ----------------------------------------------------------------- Georgia
    ("Georgia", "gazette", "Legislative Herald (matsne)", "https://matsne.gov.ge", "all legal acts"),
    ("Georgia", "tenders", "State Procurement Agency", "https://tenders.procurement.gov.ge", ""),
    ("Georgia", "register", "Ministry of Justice", "https://www.justice.gov.ge", "MoJ represents Georgia in ISDS; check for a cases page"),
    ("Georgia", "courts", "Supreme Court", "https://www.supremecourt.ge", ""),
    ("Georgia", "regulator", "GNERC energy regulator", "https://gnerc.org", ""),
    ("Georgia", "regulator", "National Agency of Mines", "https://nam.gov.ge", "mining licences"),
    ("Georgia", "press", "Civil.ge", "https://civil.ge/feed", ""),
    ("Georgia", "press", "Agenda.ge", "https://agenda.ge/en/rss", ""),
    ("Georgia", "press", "Georgia Today", "https://georgiatoday.ge/feed", ""),
    ("Georgia", "press", "InterPressNews", "https://www.interpressnews.ge/en/rss", ""),
    ("Georgia", "press", "BM.ge (Business Media)", "https://bm.ge/rss", ""),
    # ----------------------------------------------------------------- Azerbaijan
    ("Azerbaijan", "gazette", "e-qanun legal acts", "https://e-qanun.az", ""),
    ("Azerbaijan", "gazette", "President's decrees", "https://president.az/en/rss", ""),
    ("Azerbaijan", "tenders", "etender.gov.az", "https://etender.gov.az", ""),
    ("Azerbaijan", "press", "Report.az", "https://report.az/en/rss/", ""),
    ("Azerbaijan", "press", "APA", "https://apa.az/en/rss", ""),
    ("Azerbaijan", "press", "Trend", "https://en.trend.az/rss", ""),
    ("Azerbaijan", "press", "Caliber", "https://caliber.az/en/rss", ""),
    # ----------------------------------------------------------------- Kazakhstan
    ("Kazakhstan", "gazette", "Adilet legal acts", "https://adilet.zan.kz", ""),
    ("Kazakhstan", "tenders", "Goszakup public procurement", "https://goszakup.gov.kz", "has an open API (ows.goszakup.gov.kz)"),
    ("Kazakhstan", "courts", "Judicial cabinet / court database", "https://sud.gov.kz", ""),
    ("Kazakhstan", "courts", "AIFC Court judgments", "https://court.aifc.kz/judgments/", "WIRED - judgments list with summaries"),
    ("Kazakhstan", "regulator", "Ministry of Industry and Construction (subsoil)", "https://www.gov.kz/memleket/entities/mic", "licence revocations"),
    ("Kazakhstan", "regulator", "Ministry of Energy", "https://www.gov.kz/memleket/entities/energo", ""),
    ("Kazakhstan", "exchange", "KASE", "https://kase.kz/en/news/", ""),
    ("Kazakhstan", "press", "Kursiv", "https://kz.kursiv.media/feed/", ""),
    ("Kazakhstan", "press", "Tengrinews", "https://tengrinews.kz/rss/", ""),
    ("Kazakhstan", "press", "Zakon.kz", "https://www.zakon.kz/rss", "legal news"),
    ("Kazakhstan", "press", "Vlast.kz", "https://vlast.kz/rss", ""),
    ("Kazakhstan", "press", "The Astana Times", "https://astanatimes.com/feed/", ""),
    ("Kazakhstan", "press", "Forbes Kazakhstan", "https://forbes.kz/rss", ""),
    # ----------------------------------------------------------------- Uzbekistan
    ("Uzbekistan", "gazette", "Lex.uz", "https://lex.uz", ""),
    ("Uzbekistan", "tenders", "UZEX e-procurement", "https://xarid.uzex.uz", ""),
    ("Uzbekistan", "regulator", "Ministry of Mining and Geology", "https://mmg.gov.uz", ""),
    ("Uzbekistan", "exchange", "Tashkent Stock Exchange", "https://uzse.uz", ""),
    ("Uzbekistan", "press", "Gazeta.uz", "https://www.gazeta.uz/ru/rss/", ""),
    ("Uzbekistan", "press", "Kun.uz", "https://kun.uz/en/rss", ""),
    ("Uzbekistan", "press", "Spot.uz", "https://www.spot.uz/rss", "business"),
    ("Uzbekistan", "press", "UzDaily", "https://uzdaily.uz/en/rss", ""),
    ("Uzbekistan", "press", "Daryo", "https://daryo.uz/en/feed", ""),
    # ----------------------------------------------------------------- Kyrgyzstan / Turkmenistan
    ("Kyrgyzstan", "gazette", "Ministry of Justice legal database", "https://cbd.minjust.gov.kg", ""),
    ("Kyrgyzstan", "tenders", "zakupki.gov.kg", "https://zakupki.gov.kg", ""),
    ("Kyrgyzstan", "press", "24.kg", "https://24.kg/rss/", ""),
    ("Kyrgyzstan", "press", "AKIpress", "https://akipress.com/rss/", ""),
    ("Turkmenistan", "press", "Turkmenportal", "https://turkmenportal.com/en/rss", ""),
    ("Turkmenistan", "press", "Chronicles of Turkmenistan", "https://en.hronikatm.com/feed/", "independent"),
    # ----------------------------------------------------------------- Ukraine
    ("Ukraine", "tenders", "Prozorro", "https://prozorro.gov.ua/api/search/tenders", "WIRED"),
    ("Ukraine", "gazette", "Verkhovna Rada legal acts", "https://zakon.rada.gov.ua", ""),
    ("Ukraine", "register", "Ministry of Justice - international disputes", "https://minjust.gov.ua", "MoJ defends Ukraine in ISDS; find the cases page"),
    ("Ukraine", "courts", "Unified State Register of Court Decisions", "https://reyestr.court.gov.ua", "every decision, searchable"),
    ("Ukraine", "regulator", "NEURC energy regulator", "https://www.nerc.gov.ua", ""),
    ("Ukraine", "press", "Ukrinform (EN)", "https://www.ukrinform.net/rss", ""),
    ("Ukraine", "press", "Ekonomichna Pravda", "https://www.epravda.com.ua/rss/", ""),
    ("Ukraine", "press", "LB.ua", "https://lb.ua/rss", ""),
    ("Ukraine", "press", "NV", "https://nv.ua/rss", ""),
    ("Ukraine", "press", "LIGA.net", "https://www.liga.net/rss", "legal and business"),
    ("Ukraine", "press", "Sudovo-yurydychna gazeta", "https://sud.ua/rss", "court news"),
    # ----------------------------------------------------------------- Russia
    ("Russia", "gazette", "Official publication of legal acts", "http://publication.pravo.gov.ru", ""),
    ("Russia", "courts", "Commercial courts case database (kad.arbitr)", "https://kad.arbitr.ru", "anti-suit injunctions, asset seizures; search needs session"),
    ("Russia", "press", "Pravo.ru", "https://pravo.ru/rss/", "legal news"),
    ("Russia", "press", "Kommersant", "https://www.kommersant.ru/RSS/news.xml", ""),
    ("Russia", "press", "Vedomosti", "https://www.vedomosti.ru/rss/news", ""),
    ("Russia", "press", "Interfax", "https://www.interfax.ru/rss.asp", ""),
    ("Russia", "press", "RBC", "https://rssexport.rbc.ru/rbcnews/news/30/full.rss", ""),
    # ----------------------------------------------------------------- Turkey
    ("Turkey", "gazette", "Resmî Gazete", "https://www.resmigazete.gov.tr", "daily official gazette"),
    ("Turkey", "exchange", "KAP public disclosure platform", "https://www.kap.org.tr/en", "listed companies disclose arbitrations"),
    ("Turkey", "regulator", "EPDK energy regulator", "https://www.epdk.gov.tr", ""),
    ("Turkey", "regulator", "MAPEG mining", "https://www.mapeg.gov.tr", ""),
    ("Turkey", "press", "Dünya", "https://www.dunya.com/rss", ""),
    ("Turkey", "press", "Bloomberg HT", "https://www.bloomberght.com/rss", ""),
    ("Turkey", "press", "Hürriyet Daily News", "https://www.hurriyetdailynews.com/rss", ""),
    ("Turkey", "press", "Daily Sabah", "https://www.dailysabah.com/rssFeed/10", ""),
    # ----------------------------------------------------------------- Mexico
    ("Mexico", "register", "Secretaría de Economía ISDS register", "https://www.gob.mx/se/acciones-y-programas/comercio-exterior-solucion-de-controversias-inversionista-estado", "publishes notices of intent; managed bot challenge - read by a person, not a script"),
    ("Mexico", "gazette", "Diario Oficial de la Federación", "https://www.dof.gob.mx/rss", ""),
    ("Mexico", "tenders", "CompraNet", "https://compranet.hacienda.gob.mx", ""),
    ("Mexico", "regulator", "CNH hydrocarbons", "https://www.gob.mx/cnh", ""),
    ("Mexico", "exchange", "BMV", "https://www.bmv.com.mx", ""),
    ("Mexico", "press", "El Economista", "https://www.eleconomista.com.mx/rss/", ""),
    ("Mexico", "press", "Expansión", "https://expansion.mx/rss", ""),
    ("Mexico", "press", "El Financiero", "https://www.elfinanciero.com.mx/rss", ""),
    ("Mexico", "press", "El Universal", "https://www.eluniversal.com.mx/rss", ""),
    # ----------------------------------------------------------------- Argentina
    ("Argentina", "register", "Procuración del Tesoro de la Nación", "https://www.argentina.gob.ar/procuraciondeltesoro", "defends Argentina; check for a cases page"),
    ("Argentina", "gazette", "Boletín Oficial", "https://www.boletinoficial.gob.ar", "RSS available"),
    ("Argentina", "tenders", "COMPR.AR", "https://comprar.gob.ar", ""),
    ("Argentina", "press", "La Nación", "https://www.lanacion.com.ar/arc/outboundfeeds/rss/", ""),
    ("Argentina", "press", "Clarín", "https://www.clarin.com/rss/", ""),
    ("Argentina", "press", "Ámbito", "https://www.ambito.com/rss", ""),
    ("Argentina", "press", "El Cronista", "https://www.cronista.com/rss", ""),
    ("Argentina", "press", "Infobae", "https://www.infobae.com/feeds/rss/", ""),
    # ----------------------------------------------------------------- Colombia
    ("Colombia", "register", "ANDJE - defensa internacional", "https://www.defensajuridica.gov.co", "publishes ISDS cases; managed bot challenge - read by a person, not a script"),
    ("Colombia", "tenders", "SECOP / Colombia Compra", "https://www.colombiacompra.gov.co", ""),
    ("Colombia", "regulator", "ANM mining", "https://www.anm.gov.co", ""),
    ("Colombia", "regulator", "ANH hydrocarbons", "https://www.anh.gov.co", ""),
    ("Colombia", "courts", "Consejo de Estado", "https://www.consejodeestado.gov.co", ""),
    ("Colombia", "press", "Portafolio", "https://www.portafolio.co/rss", ""),
    ("Colombia", "press", "La República", "https://www.larepublica.co/rss", ""),
    ("Colombia", "press", "Semana", "https://www.semana.com/rss", ""),
    ("Colombia", "press", "Valora Analitik", "https://www.valoraanalitik.com/feed/", ""),
    # ----------------------------------------------------------------- Peru
    ("Peru", "register", "MEF - SICRECI (State coordination for investment disputes)", "https://www.mef.gob.pe", "find the cases page"),
    ("Peru", "gazette", "El Peruano", "https://elperuano.pe", ""),
    ("Peru", "tenders", "SEACE", "https://www.gob.pe/seace", ""),
    ("Peru", "regulator", "Osinergmin", "https://www.osinergmin.gob.pe", ""),
    ("Peru", "press", "Gestión", "https://gestion.pe/rss", ""),
    ("Peru", "press", "El Comercio", "https://elcomercio.pe/rss", ""),
    ("Peru", "press", "RPP", "https://rpp.pe/rss", ""),
    # ----------------------------------------------------------------- Chile / Ecuador / Venezuela / Bolivia / Brazil
    ("Chile", "tenders", "Mercado Público", "https://www.mercadopublico.cl", ""),
    ("Chile", "press", "Diario Financiero", "https://www.df.cl/rss", ""),
    ("Chile", "press", "El Mercurio (Emol)", "https://www.emol.com/rss/", ""),
    ("Ecuador", "register", "Procuraduría General del Estado", "https://www.pge.gob.ec", "publishes arbitration cases against Ecuador"),
    ("Ecuador", "gazette", "Registro Oficial", "https://www.registroficial.gob.ec", ""),
    ("Ecuador", "press", "El Universo", "https://www.eluniverso.com/rss", ""),
    ("Ecuador", "press", "Primicias", "https://www.primicias.ec/feed/", ""),
    ("Venezuela", "press", "Efecto Cocuyo", "https://efectococuyo.com/feed/", ""),
    ("Venezuela", "press", "Banca y Negocios", "https://www.bancaynegocios.com/feed/", ""),
    ("Venezuela", "press", "El Nacional", "https://www.elnacional.com/feed/", ""),
    ("Bolivia", "press", "El Deber", "https://eldeber.com.bo/rss", ""),
    ("Brazil", "gazette", "Diário Oficial da União", "https://www.in.gov.br", ""),
    ("Brazil", "press", "Valor Econômico", "https://valor.globo.com/rss", ""),
    ("Brazil", "press", "JOTA", "https://www.jota.info/feed", "legal"),
    ("Brazil", "press", "Folha - Mercado", "https://feeds.folha.uol.com.br/mercado/rss091.xml", ""),
    # ----------------------------------------------------------------- Spain / Italy / Romania / Poland
    ("Spain", "gazette", "BOE", "https://www.boe.es/rss/canal.php?c=ultimos", "official gazette"),
    ("Spain", "exchange", "CNMV", "https://www.cnmv.es", "hechos relevantes"),
    ("Spain", "tenders", "PLACSP", "https://contrataciondelestado.es", ""),
    ("Spain", "press", "Expansión", "https://e00-expansion.uecdn.es/rss/portada.xml", ""),
    ("Spain", "press", "El Confidencial", "https://rss.elconfidencial.com/espana/", ""),
    ("Spain", "press", "Cinco Días", "https://cincodias.elpais.com/rss/", ""),
    ("Spain", "press", "El Economista", "https://www.eleconomista.es/rss/rss-empresas.php", ""),
    ("Italy", "gazette", "Gazzetta Ufficiale", "https://www.gazzettaufficiale.it", ""),
    ("Italy", "press", "Il Sole 24 Ore", "https://www.ilsole24ore.com/rss/italia.xml", ""),
    ("Romania", "press", "Ziarul Financiar", "https://www.zf.ro/rss", ""),
    ("Romania", "press", "Profit.ro", "https://www.profit.ro/rss", ""),
    ("Poland", "press", "Puls Biznesu", "https://www.pb.pl/rss", ""),
    ("Poland", "press", "Rzeczpospolita", "https://www.rp.pl/rss_main", ""),
    # ----------------------------------------------------------------- Nigeria / Ghana / Kenya / Tanzania / Zambia / DRC / South Africa
    ("Nigeria", "tenders", "Bureau of Public Procurement", "https://www.bpp.gov.ng", ""),
    ("Nigeria", "regulator", "NUPRC upstream regulator", "https://www.nuprc.gov.ng", ""),
    ("Nigeria", "regulator", "Mining Cadastre Office", "https://miningcadastre.gov.ng", ""),
    ("Nigeria", "exchange", "NGX", "https://ngxgroup.com", ""),
    ("Nigeria", "press", "BusinessDay", "https://businessday.ng/feed/", ""),
    ("Nigeria", "press", "Premium Times", "https://www.premiumtimesng.com/feed", ""),
    ("Nigeria", "press", "Punch", "https://punchng.com/feed/", ""),
    ("Nigeria", "press", "Nairametrics", "https://nairametrics.com/feed/", ""),
    ("Ghana", "regulator", "Minerals Commission", "https://www.mincom.gov.gh", ""),
    ("Ghana", "press", "Ghana Business News", "https://www.ghanabusinessnews.com/feed/", ""),
    ("Ghana", "press", "MyJoyOnline Business", "https://www.myjoyonline.com/business/feed/", ""),
    ("Kenya", "press", "Business Daily", "https://www.businessdailyafrica.com/rss", ""),
    ("Kenya", "press", "The Star", "https://www.the-star.co.ke/rss", ""),
    ("Tanzania", "regulator", "Mining Commission", "https://www.tumemadini.go.tz", ""),
    ("Tanzania", "press", "The Citizen", "https://www.thecitizen.co.tz/rss", ""),
    ("Zambia", "press", "Zambia Daily Mail", "https://www.daily-mail.co.zm/feed/", ""),
    ("Zambia", "press", "News Diggers", "https://diggers.news/feed/", ""),
    ("DRC", "regulator", "CAMI mining cadastre", "https://www.cami.cd", ""),
    ("DRC", "press", "Actualite.cd", "https://actualite.cd/feed", ""),
    ("South Africa", "exchange", "JSE SENS", "https://www.jse.co.za", ""),
    ("South Africa", "press", "Business Day", "https://www.businesslive.co.za/bd/rss", ""),
    ("South Africa", "press", "Moneyweb", "https://www.moneyweb.co.za/feed/", ""),
    ("Mozambique", "press", "Club of Mozambique", "https://clubofmozambique.com/feed/", ""),
    # ----------------------------------------------------------------- Egypt / Algeria / Morocco / Gulf / Iraq
    ("Egypt", "exchange", "Egyptian Exchange", "https://www.egx.com.eg", ""),
    ("Egypt", "press", "Enterprise", "https://enterprise.press/feed/", "the best daily on Egyptian business"),
    ("Egypt", "press", "Ahram Online", "https://english.ahram.org.eg/rss", ""),
    ("Egypt", "press", "Daily News Egypt", "https://www.dailynewsegypt.com/feed/", ""),
    ("Algeria", "press", "APS", "https://www.aps.dz/en/?format=feed", ""),
    ("Morocco", "press", "Médias24", "https://medias24.com/feed/", ""),
    ("UAE", "press", "The National", "https://www.thenationalnews.com/rss", ""),
    ("Saudi Arabia", "press", "Arab News", "https://www.arabnews.com/rss.xml", ""),
    ("Qatar", "press", "The Peninsula", "https://thepeninsulaqatar.com/rss", ""),
    ("Iraq", "press", "Iraq Business News", "https://www.iraq-businessnews.com/feed/", ""),
    # ----------------------------------------------------------------- India / Pakistan / Indonesia / Vietnam / Malaysia / Philippines / Korea
    ("India", "gazette", "eGazette", "https://egazette.gov.in", ""),
    ("India", "exchange", "BSE corporate announcements", "https://www.bseindia.com/corporates/ann.html", "arbitration disclosures; has an API"),
    ("India", "press", "Economic Times", "https://economictimes.indiatimes.com/rssfeedsdefault.cms", ""),
    ("India", "press", "Mint", "https://www.livemint.com/rss/companies", ""),
    ("India", "press", "Bar & Bench", "https://www.barandbench.com/feed", "legal"),
    ("India", "press", "LiveLaw", "https://www.livelaw.in/rss", "legal"),
    ("India", "press", "Business Standard", "https://www.business-standard.com/rss/companies-101.rss", ""),
    ("Pakistan", "press", "Dawn Business", "https://www.dawn.com/feeds/business", ""),
    ("Pakistan", "press", "Business Recorder", "https://www.brecorder.com/feeds/latest-news", ""),
    ("Indonesia", "gazette", "JDIH Setneg", "https://jdih.setneg.go.id", ""),
    ("Indonesia", "regulator", "ESDM ministry", "https://www.esdm.go.id", "IUP revocations"),
    ("Indonesia", "exchange", "IDX", "https://www.idx.co.id", ""),
    ("Indonesia", "press", "Kontan", "https://www.kontan.co.id/rss", ""),
    ("Indonesia", "press", "Bisnis.com", "https://www.bisnis.com/rss", ""),
    ("Indonesia", "press", "Hukumonline", "https://www.hukumonline.com/rss", "legal"),
    ("Indonesia", "press", "Jakarta Post", "https://www.thejakartapost.com/rss", ""),
    ("Vietnam", "press", "VnExpress International", "https://e.vnexpress.net/rss/business.rss", ""),
    ("Malaysia", "press", "The Edge", "https://theedgemalaysia.com/rss", ""),
    ("Philippines", "press", "BusinessWorld", "https://www.bworldonline.com/feed/", ""),
    ("Korea", "press", "Korea Economic Daily", "https://www.kedglobal.com/rss", ""),
    ("Korea", "press", "Korea JoongAng Daily", "https://koreajoongangdaily.joins.com/rss", ""),
    # ----------------------------------------------------------------- Global primary records and specialist press
    ("Global", "register", "ICSID docket API", "https://icsid.worldbank.org/api/cases/pending", "WIRED"),
    ("Global", "register", "UNCITRAL Transparency Registry", "https://www.uncitral.org/transparency-registry/registry/index.jspx", "notices under the Mauritius Convention; index answers, case list to parse"),
    ("Global", "register", "PCA cases", "https://pca-cpa.org/en/cases/", "client-rendered"),
    ("Global", "register", "italaw", "https://www.italaw.com", "awards and decisions; managed bot challenge - read by a person, not a script"),
    ("Global", "register", "UNCTAD ISDS Navigator", "https://investmentpolicy.unctad.org/investment-dispute-settlement", "managed bot challenge - read by a person, not a script"),
    ("Global", "courts", "CourtListener / RECAP", "https://www.courtlistener.com/api/rest/v4/search/", "WIRED"),
    ("Global", "exchange", "SEC EDGAR full-text", "https://efts.sec.gov/LATEST/search-index", "WIRED"),
    ("Global", "tenders", "TED", "https://api.ted.europa.eu/v3/notices/search", "WIRED"),
    ("Global", "exchange", "LSE RNS", "https://www.londonstockexchange.com/news", "no keyword feed"),
    ("Global", "exchange", "ASX announcements", "https://www.asx.com.au/markets/trade-our-cash-market/announcements", "per-company only"),
    ("Global", "exchange", "SEDAR+", "https://www.sedarplus.ca", "Canadian filings; client-rendered"),
    ("Global", "press", "GAR", "https://globalarbitrationreview.com/rss", "WIRED"),
    ("Global", "press", "IAReporter", "https://www.iareporter.com/feed/", "WIRED"),
    ("Global", "press", "Law360 International Arbitration", "https://www.law360.com/internationalarbitration/rss", "paywalled headlines"),
    ("Global", "press", "Lexology arbitration", "https://www.lexology.com/rss", ""),
    ("Global", "press", "Omni Bridgeway news", "https://omnibridgeway.com/news", "funder"),
    ("Global", "press", "Litigation Capital Management", "https://www.lcmfinance.com/news/", "funder"),
]
CANDIDATES += [
    # ===== arbitral institutions and treaty bodies =====
    ("Global", "press", "ICC news", "https://iccwbo.org/feed/", "institution"),
    ("Global", "press", "LCIA news", "https://www.lcia.org/News/news.aspx", "institution"),
    ("Global", "press", "VIAC news", "https://www.viac.eu/en/news", "institution"),
    ("Global", "press", "DIS news", "https://www.disarb.org/en/news", "institution"),
    ("Global", "press", "CRCICA news", "https://crcica.org/news/", "institution"),
    ("Global", "press", "CIETAC news", "http://www.cietac.org/index.php?m=Article&a=index&id=1&l=en", "institution"),
    ("Global", "press", "KCAB International", "http://www.kcabinternational.or.kr", "institution"),
    ("Global", "press", "JCAA news", "https://www.jcaa.or.jp/en/news/", "institution"),
    ("Global", "press", "DIAC news", "https://www.diac.com/news", "institution"),
    ("Global", "press", "ISTAC news", "https://istac.org.tr/en/news/", "institution"),
    ("Global", "press", "Russian Arbitration Center", "https://centerarbitr.ru/en/news/", "institution"),
    ("Global", "press", "CAM Santiago", "https://www.camsantiago.cl/noticias/", "institution"),
    ("Global", "press", "CAM-CCBC", "https://ccbc.org.br/cam-ccbc/noticias/", "institution"),
    ("Global", "press", "AAA-ICDR news", "https://www.adr.org/news", "institution"),
    ("Global", "press", "Energy Charter Secretariat", "https://www.energycharter.org/media/news/", "treaty body; case statistics"),
    ("Global", "press", "UNCITRAL news", "https://uncitral.un.org/en/news", ""),
    ("Global", "press", "EFILA blog", "https://efilablog.org/feed/", "investment law"),
    ("Global", "press", "Global Legal Chronicle", "https://www.globallegalchronicle.com/feed/", "deals and cases with counsel named"),
    ("Global", "press", "CDR News", "https://www.cdr-news.com/rss", "disputes press"),
    ("Global", "press", "Global Legal Post", "https://www.globallegalpost.com/rss", ""),
    ("Global", "press", "Legal Business", "https://www.legalbusiness.co.uk/feed/", ""),
    ("Global", "press", "The Lawyer", "https://www.thelawyer.com/feed/", ""),
    ("Global", "press", "Asian Legal Business", "https://www.legalbusinessonline.com/rss", ""),
    ("Global", "press", "Latin Lawyer", "https://latinlawyer.com/rss", "GAR's sister title"),
    ("Global", "press", "Africa Legal", "https://www.africa-legal.com/rss", ""),
    ("Global", "press", "JD Supra - arbitration", "https://www.jdsupra.com/rss/arbitration/", ""),
    ("Global", "press", "Mondaq - arbitration", "https://www.mondaq.com/rss/arbitration-dispute-resolution", ""),
    ("Global", "press", "Pinsent Masons Out-Law", "https://www.pinsentmasons.com/out-law/news/rss", ""),
    # ===== courts with open data or feeds =====
    ("Global", "courts", "England and Wales - Find Case Law search feed", "https://caselaw.nationalarchives.gov.uk/atom.xml?query=%22Arbitration+Act+1996%22&order=-date", "WIRED - s.67/68/69, anti-suit, s.9 stays, enforcement; search feed only, judgments not downloaded"),
    ("Global", "courts", "England - judiciary.uk judgments", "https://www.judiciary.uk/feed/", ""),
    ("Global", "courts", "Netherlands - rechtspraak open data", "https://data.rechtspraak.nl/uitspraken/zoeken?return=DOC&max=50&sort=DESC", "WIRED - civil decisions filtered on the court summary"),
    ("Global", "courts", "Switzerland - Federal Supreme Court", "https://www.bger.ch/ext/eurospider/live/de/php/aza/http/index.php?lang=de&type=simple_query&query_words=4A_", "every award challenge in Switzerland"),
    ("Global", "courts", "France - Cour de cassation news", "https://www.courdecassation.fr/en/actualites", ""),
    ("Global", "courts", "Singapore - Law Watch judgments feed", "https://www.singaporelawwatch.sg/Portals/0/RSS/Judgments.xml", "WIRED - SGHC, SICC, SGCA with catchwords"),
    ("Global", "courts", "Singapore - eLitigation judgments", "https://www.elitigation.sg/gd/Home/Index", ""),
    ("Global", "courts", "Hong Kong - judiciary legal reference", "https://legalref.judiciary.hk/lrs/common/ju/judgment.jsp", ""),
    ("Global", "courts", "India - Supreme Court (Indian Kanoon feed)", "https://indiankanoon.org/feeds/latest/supremecourt/", ""),
    ("Global", "courts", "India - Delhi High Court (Indian Kanoon feed)", "https://indiankanoon.org/feeds/latest/delhi/", "s.34/s.48 arbitration matters"),
    ("Global", "courts", "Australia - Federal Court (AustLII feed)", "https://www.austlii.edu.au/rss/au/cases/cth/FCA.xml", ""),
    ("Global", "courts", "Canada - CanLII court feeds", "https://www.canlii.org/en/on/onca/rss_new.xml", "WIRED - SCC, FCA, FC, ONCA, ONSC, BCCA, BCSC, ABCA, ABKB, QCCA, QCCS with catchwords"),
    ("Global", "courts", "Germany - Bundesgerichtshof decisions feed", "https://www.bundesgerichtshof.de/DE/Service/RSSFeed/Function/RSS_EN.xml", "WIRED - I ZB dockets confirmed against the decision text"),
    ("Global", "courts", "Ireland - judgments", "https://www.courts.ie/judgments", ""),
    ("Global", "courts", "Kenya Law - search API", "https://new.kenyalaw.org/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED - arbitration causes and miscellaneous applications"),
    ("Global", "courts", "Austria - RIS Judikatur API", "https://data.bka.gv.at/ris/api/v2.6/Judikatur?Applikation=Justiz&Suchworte=Schiedsspruch&DokumenteProSeite=Ten", "WIRED - OGH and lower-court decision texts"),
    ("Global", "courts", "DIFC Courts - arbitration list", "https://www.difccourts.ae/rules-decisions/judgments-orders/arbitration", "WIRED - ARB and ENF claims"),
    ("Global", "courts", "NigeriaLII - search API", "https://nigerialii.org/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED"),
    ("Global", "courts", "ULII (Uganda) - search API", "https://ulii.org/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED"),
    ("Global", "courts", "TanzLII - search API", "https://tanzlii.org/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED - documents themselves refuse scripts"),
    ("Global", "courts", "ZambiaLII - search API", "https://zambialii.org/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED"),
    ("Global", "courts", "MalawiLII - search API", "https://malawilii.org/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED"),
    ("Global", "courts", "LawLibrary.org.za (South Africa) - search API", "https://lawlibrary.org.za/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED"),
    ("Global", "courts", "NamibLII - search API", "https://namiblii.org/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED"),
    ("Global", "courts", "ZimLII - search API", "https://zimlii.org/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED"),
    ("Global", "courts", "SierraLII - search API", "https://sierralii.gov.sl/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED"),
    ("Global", "courts", "EswatiniLII - search API", "https://eswatinilii.org/search/api/documents/?search=%22arbitral+award%22&ordering=-date", "WIRED"),
    ("Global", "courts", "Qatar - QICDRC judgments", "https://www.qicdrc.gov.qa/judgments", "client-rendered list"),
    ("Global", "courts", "UAE - ADGM Courts judgments", "https://www.adgm.com/adgm-courts/judgments", "no arbitration marker in the list"),
    ("Global", "courts", "Cayman Islands - judgments", "https://www.judicial.ky/judgments", "subscription only"),
    ("Global", "courts", "New Zealand - judgments search", "https://www.courtsofnz.govt.nz/judgments/", "client-rendered"),
    ("Global", "courts", "Australia - NSW Caselaw", "https://www.caselaw.nsw.gov.au/search/advanced", "no feed; search is a form"),
    ("Global", "courts", "Brazil - STJ jurisprudence search", "https://scon.stj.jus.br/SCON/", "refuses scripts"),
    ("Global", "courts", "Pakistan - Supreme Court judgments", "https://www.supremecourt.gov.pk/judgement-search/", "refuses scripts"),
    # ===== funders =====
    ("Global", "press", "Omni Bridgeway - ASX announcements", "https://omnibridgeway.com/investors/asx-announcements", "funder; funded claims disclosed"),
    ("Global", "press", "LCM - RNS", "https://www.lcmfinance.com/investors/rns/", "funder"),
    ("Global", "press", "Therium news", "https://therium.com/news/", "funder"),
    ("Global", "press", "Harbour news", "https://www.harbourlitigationfunding.com/news/", "funder"),
    ("Global", "press", "Nivalion news", "https://nivalion.com/news/", "funder"),
    ("Global", "press", "Deminor news", "https://www.deminor.com/en/news/", "funder"),
    # ===== law firm newsrooms (instructions announced here first) =====
    ("Global", "press", "White & Case news", "https://www.whitecase.com/news", "firm"),
    ("Global", "press", "Freshfields", "https://www.freshfields.com/en/our-thinking/", "firm"),
    ("Global", "press", "Debevoise insights", "https://www.debevoise.com/insights", "firm"),
    ("Global", "press", "King & Spalding news", "https://www.kslaw.com/news-and-insights", "firm"),
    ("Global", "press", "Curtis news", "https://www.curtis.com/news", "firm"),
    ("Global", "press", "Foley Hoag news", "https://foleyhoag.com/news-and-insights/", "firm"),
    ("Global", "press", "Volterra Fietta news", "https://www.volterrafietta.com/news/", "firm"),
    ("Global", "press", "Withers insight", "https://www.withersworldwide.com/en-gb/insight", "firm"),
    ("Global", "press", "Hogan Lovells news", "https://www.hoganlovells.com/en/news", "firm"),
    ("Global", "press", "Latham news", "https://www.lw.com/en/news", "firm"),
    ("Global", "press", "Sidley news", "https://www.sidley.com/en/newslanding", "firm"),
    ("Global", "press", "Arnold & Porter news", "https://www.arnoldporter.com/en/news", "firm"),
    ("Global", "press", "Quinn Emanuel news", "https://www.quinnemanuel.com/the-firm/news-events/", "firm"),
    ("Global", "press", "Boies Schiller news", "https://www.bsfllp.com/news", "firm"),
    ("Global", "press", "HSF Kramer", "https://www.hsfkramer.com/notes", "firm"),
    ("Global", "press", "Clifford Chance news", "https://www.cliffordchance.com/news.html", "firm"),
    ("Global", "press", "A&O Shearman news", "https://www.aoshearman.com/en/news", "firm"),
    ("Global", "press", "Dechert", "https://www.dechert.com/knowledge.html", "firm"),
    ("Global", "press", "Jones Day news", "https://www.jonesday.com/en/news", "firm"),
    ("Global", "press", "Baker McKenzie newsroom", "https://www.bakermckenzie.com/en/newsroom", "firm"),
    ("Global", "press", "DLA Piper news", "https://www.dlapiper.com/en/news", "firm"),
    ("Global", "press", "Norton Rose Fulbright news", "https://www.nortonrosefulbright.com/en/news", "firm"),
    ("Global", "press", "Mayer Brown news", "https://www.mayerbrown.com/en/news", "firm"),
    ("Global", "press", "Steptoe news", "https://www.steptoe.com/en/news-publications", "firm"),
    ("Global", "press", "Gibson Dunn news", "https://www.gibsondunn.com/news/", "firm"),
    ("Global", "press", "Cleary news", "https://www.clearygottlieb.com/news-and-insights", "firm"),
    ("Global", "press", "WilmerHale insights", "https://www.wilmerhale.com/en/insights", "firm"),
    ("Global", "press", "Lalive news", "https://www.lalive.law/news/", "firm"),
    ("Global", "press", "Derains & Gharavi", "https://www.derainsgharavi.com/news/", "firm"),
    ("Global", "press", "Chaffetz Lindsey", "https://www.chaffetzlindsey.com/news/", "firm"),
    ("Global", "press", "Uría Menéndez news", "https://www.uria.com/en/actualidad", "firm"),
    ("Global", "press", "Garrigues news", "https://www.garrigues.com/en_GB/news", "firm"),
    ("Global", "press", "Sayenko Kharenko news", "https://sk.ua/news/", "firm, Ukraine"),
    ("Global", "press", "Asters news", "https://asters.com/news/", "firm, Ukraine"),
    ("Global", "press", "GRATA International news", "https://gratanet.com/news", "firm, Central Asia"),
    ("Global", "press", "AEQUO news", "https://aequo.ua/news", "firm, Ukraine"),
    # ===== wires and exchange feeds =====
    ("Global", "exchange", "GlobeNewswire - ICSID", "https://www.globenewswire.com/RssFeed/keyword/ICSID", "keyword feed"),
    ("Global", "exchange", "GlobeNewswire - investment treaty", "https://www.globenewswire.com/RssFeed/keyword/investment%20treaty", "keyword feed"),
    ("Global", "exchange", "GlobeNewswire - notice of arbitration", "https://www.globenewswire.com/RssFeed/keyword/notice%20of%20arbitration", "keyword feed"),
    ("Global", "exchange", "GlobeNewswire - arbitration award", "https://www.globenewswire.com/RssFeed/keyword/arbitration%20award", "keyword feed"),
    ("Global", "exchange", "GlobeNewswire - expropriation", "https://www.globenewswire.com/RssFeed/keyword/expropriation", "keyword feed"),
    ("Global", "exchange", "Newsfile (Canadian juniors)", "https://www.newsfilecorp.com/newsroom/rss", ""),
    ("Global", "exchange", "ACCESSWIRE", "https://www.accesswire.com/rss/newsroom", ""),
    ("Global", "exchange", "Business Wire - legal", "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeGVpRXg==", ""),
    ("Global", "exchange", "Investegate (LSE RNS)", "https://www.investegate.co.uk/rss.aspx", ""),
    ("Global", "exchange", "TSX - Market Activity", "https://www.tsx.com/news", ""),
    # ===== international institutions =====
    ("Global", "register", "EBRD news", "https://www.ebrd.com/news.html", "project disputes"),
    ("Global", "register", "IFC disclosures", "https://disclosures.ifc.org", ""),
    ("Global", "register", "MIGA news", "https://www.miga.org/news", "political risk claims"),
    ("Global", "register", "OECD investment news", "https://www.oecd.org/en/topics/investment.html", ""),
    # ===== priority countries: more source types =====
    ("Armenia", "gazette", "Prime Minister press releases", "https://www.primeminister.am/en/press-release/", ""),
    ("Armenia", "gazette", "President", "https://www.president.am/en/press-release/", ""),
    ("Armenia", "regulator", "Central Bank of Armenia", "https://www.cba.am/en/SitePages/newsevents.aspx", "FX and bank licences"),
    ("Armenia", "regulator", "Competition Protection Commission", "https://www.competition.am/en/news/", ""),
    ("Armenia", "regulator", "State Revenue Committee", "https://www.petekamutner.am/en/", "tax"),
    ("Armenia", "gazette", "Ministry of Justice", "https://www.moj.am/en", "represents Armenia in ISDS"),
    ("Armenia", "press", "Armenpress", "https://armenpress.am", "discover feed"),
    ("Armenia", "press", "Panorama.am", "https://www.panorama.am", "discover feed"),
    ("Armenia", "press", "Aravot", "https://www.aravot-en.am", "discover feed"),
    ("Armenia", "press", "Azatutyun (RFE/RL)", "https://www.azatutyun.am", "discover feed"),
    ("Armenia", "press", "Armenia Today", "https://armeniatoday.am", "carried the Vinitski story"),
    ("Georgia", "gazette", "Government of Georgia", "https://www.gov.ge/en/news", ""),
    ("Georgia", "regulator", "National Bank of Georgia", "https://nbg.gov.ge/en/media/news", ""),
    ("Georgia", "regulator", "Competition Agency", "https://gca.gov.ge/en/news", ""),
    ("Georgia", "gazette", "Ministry of Justice (justice.gov.ge)", "https://www.justice.gov.ge/en", "discover cases page"),
    ("Georgia", "press", "Agenda.ge", "https://agenda.ge", "discover feed"),
    ("Georgia", "press", "BM.ge", "https://bm.ge", "discover feed"),
    ("Georgia", "press", "Formula News", "https://formulanews.ge", "discover feed"),
    ("Georgia", "press", "Commersant.ge", "https://commersant.ge", "discover feed"),
    ("Azerbaijan", "gazette", "Cabinet of Ministers", "https://cabmin.gov.az/en/news", ""),
    ("Azerbaijan", "regulator", "Central Bank", "https://www.cbar.az/news", ""),
    ("Azerbaijan", "press", "Caliber", "https://caliber.az", "discover feed"),
    ("Azerbaijan", "press", "Turan", "https://turan.az", "discover feed"),
    ("Azerbaijan", "press", "ABC.az", "https://abc.az", "discover feed"),
    ("Kazakhstan", "gazette", "Akorda (President)", "https://www.akorda.kz/en/events", ""),
    ("Kazakhstan", "gazette", "Government (primeminister.kz)", "https://primeminister.kz/en/news", ""),
    ("Kazakhstan", "regulator", "National Bank", "https://www.nationalbank.kz/en/news", ""),
    ("Kazakhstan", "regulator", "Samruk-Kazyna", "https://sk.kz/en/press-center/news/", "sovereign holding"),
    ("Kazakhstan", "press", "Tengrinews", "https://tengrinews.kz", "discover feed"),
    ("Kazakhstan", "press", "Zakon.kz", "https://www.zakon.kz", "discover feed"),
    ("Kazakhstan", "press", "Vlast.kz", "https://vlast.kz", "discover feed"),
    ("Kazakhstan", "press", "Inbusiness.kz", "https://inbusiness.kz", "discover feed"),
    ("Kazakhstan", "press", "KazTAG", "https://kaztag.kz", "discover feed"),
    ("Uzbekistan", "gazette", "President", "https://president.uz/en", "discover feed"),
    ("Uzbekistan", "regulator", "Central Bank", "https://cbu.uz/en/press_center/news/", ""),
    ("Uzbekistan", "press", "Kun.uz", "https://kun.uz", "discover feed"),
    ("Uzbekistan", "press", "Podrobno.uz", "https://podrobno.uz", "discover feed"),
    ("Kyrgyzstan", "press", "Kaktus.media", "https://kaktus.media", "discover feed"),
    ("Kyrgyzstan", "press", "Economist.kg", "https://economist.kg", "discover feed"),
    ("Tajikistan", "press", "Asia-Plus", "https://asiaplustj.info", "discover feed"),
    ("Mongolia", "press", "Montsame", "https://montsame.mn/en", "discover feed"),
    ("Mongolia", "regulator", "Mineral Resources and Petroleum Authority", "https://mrpam.gov.mn", ""),
    ("Moldova", "press", "IPN", "https://www.ipn.md/en", "discover feed"),
    ("Belarus", "press", "BelTA", "https://eng.belta.by", "discover feed"),
    ("Ukraine", "gazette", "President", "https://www.president.gov.ua/en/news/all", ""),
    ("Ukraine", "gazette", "Cabinet of Ministers", "https://www.kmu.gov.ua/en/news", ""),
    ("Ukraine", "regulator", "National Bank", "https://bank.gov.ua/en/news", ""),
    ("Ukraine", "regulator", "State Property Fund", "https://www.spfu.gov.ua/en/news", "privatisation and seizures"),
    ("Ukraine", "regulator", "ARMA (asset recovery)", "https://arma.gov.ua/news", "seized assets"),
    ("Ukraine", "press", "Ukrinform", "https://www.ukrinform.net", "discover feed"),
    ("Ukraine", "press", "LIGA.net", "https://www.liga.net", "discover feed"),
    ("Ukraine", "press", "Interfax-Ukraine", "https://en.interfax.com.ua", "discover feed"),
    ("Ukraine", "press", "Ekonomichna Pravda", "https://www.epravda.com.ua", "discover feed"),
    ("Ukraine", "press", "Yurydychna Gazeta", "https://yur-gazeta.com", "discover feed"),
    ("Russia", "gazette", "Government", "http://government.ru/en/news/", ""),
    ("Russia", "regulator", "Central Bank", "https://www.cbr.ru/eng/press/", ""),
    ("Russia", "press", "Zakon.ru", "https://zakon.ru", "discover feed"),
    ("Turkey", "gazette", "Presidency", "https://www.tccb.gov.tr/en/", ""),
    ("Turkey", "regulator", "Central Bank", "https://www.tcmb.gov.tr/wps/wcm/connect/EN/TCMB+EN/Main+Menu/Announcements", ""),
    ("Turkey", "regulator", "Competition Authority", "https://www.rekabet.gov.tr/en", ""),
    ("Turkey", "press", "Ekonomim", "https://www.ekonomim.com", "discover feed"),
    ("Turkey", "press", "Hürriyet", "https://www.hurriyet.com.tr", "discover feed"),
    ("Mexico", "gazette", "DOF (main)", "https://www.dof.gob.mx", "discover feed"),
    ("Mexico", "regulator", "CRE energy regulator", "https://www.gob.mx/cre", ""),
    ("Mexico", "regulator", "Secretaría de Economía (main)", "https://www.gob.mx/se", "JS challenge"),
    ("Mexico", "press", "El Universal", "https://www.eluniversal.com.mx", "discover feed"),
    ("Mexico", "press", "Reforma", "https://www.reforma.com", "discover feed"),
    ("Mexico", "press", "Milenio", "https://www.milenio.com", "discover feed"),
    ("Mexico", "press", "Forbes México", "https://www.forbes.com.mx", "discover feed"),
    ("Argentina", "press", "Infobae", "https://www.infobae.com", "discover feed"),
    ("Argentina", "press", "iProfesional", "https://www.iprofesional.com", "discover feed"),
    ("Argentina", "press", "Página/12", "https://www.pagina12.com.ar", "discover feed"),
    ("Argentina", "regulator", "ENARGAS", "https://www.enargas.gob.ar", ""),
    ("Argentina", "exchange", "CNV", "https://www.argentina.gob.ar/cnv", ""),
    ("Colombia", "press", "Semana", "https://www.semana.com", "discover feed"),
    ("Colombia", "press", "El Tiempo", "https://www.eltiempo.com", "discover feed"),
    ("Colombia", "press", "El Espectador", "https://www.elespectador.com", "discover feed"),
    ("Colombia", "gazette", "Presidencia", "https://www.presidencia.gov.co", ""),
    ("Colombia", "regulator", "Superintendencia Financiera", "https://www.superfinanciera.gov.co", ""),
    ("Peru", "press", "Semana Económica", "https://semanaeconomica.com", "discover feed"),
    ("Peru", "press", "La República", "https://larepublica.pe", "discover feed"),
    ("Peru", "regulator", "INGEMMET", "https://www.gob.pe/ingemmet", "mining concessions"),
    ("Peru", "regulator", "Perupetro", "https://www.perupetro.com.pe", ""),
    ("Chile", "press", "Diario Financiero", "https://www.df.cl", "discover feed"),
    ("Chile", "press", "La Tercera", "https://www.latercera.com", "discover feed"),
    ("Chile", "press", "El Mostrador", "https://www.elmostrador.cl", "discover feed"),
    ("Chile", "regulator", "SERNAGEOMIN", "https://www.sernageomin.cl", "mining"),
    ("Ecuador", "press", "Expreso", "https://www.expreso.ec", "discover feed"),
    ("Ecuador", "regulator", "ARCERNNR", "https://www.controlrecursosyenergia.gob.ec", "mining and energy licences"),
    ("Venezuela", "press", "Petroguía", "https://www.petroguia.com", "discover feed"),
    ("Bolivia", "press", "Los Tiempos", "https://www.lostiempos.com", "discover feed"),
    ("Brazil", "press", "Valor Econômico", "https://valor.globo.com", "discover feed"),
    ("Brazil", "press", "Estadão", "https://www.estadao.com.br", "discover feed"),
    ("Brazil", "exchange", "CVM", "https://www.gov.br/cvm", ""),
    ("Brazil", "regulator", "ANP", "https://www.gov.br/anp", "oil and gas"),
    ("Brazil", "regulator", "ANM", "https://www.gov.br/anm", "mining"),
    ("Spain", "press", "Cinco Días", "https://cincodias.elpais.com", "discover feed"),
    ("Spain", "press", "Vozpópuli", "https://www.vozpopuli.com", "discover feed"),
    ("Spain", "register", "Abogacía General del Estado", "https://www.mjusticia.gob.es/es/ministerio/organismos-entidades/abogacia-general", "defends Spain in ISDS"),
    ("Italy", "press", "Milano Finanza", "https://www.milanofinanza.it", "discover feed"),
    ("Italy", "register", "Avvocatura dello Stato", "https://www.avvocaturastato.it", ""),
    ("Romania", "press", "Economica.net", "https://www.economica.net", "discover feed"),
    ("Romania", "register", "Ministry of Finance", "https://mfinante.gov.ro", "defends Romania in ISDS"),
    ("Poland", "register", "Prokuratoria Generalna", "https://www.gov.pl/web/prokuratoria", "defends Poland in ISDS"),
    ("Hungary", "press", "Portfolio.hu", "https://www.portfolio.hu", "discover feed"),
    ("Czechia", "press", "Hospodářské noviny", "https://hn.cz", "discover feed"),
    ("Czechia", "register", "Ministry of Finance - arbitration", "https://www.mfcr.cz/en/", "publishes ISDS cases"),
    ("Slovakia", "press", "Denník N", "https://dennikn.sk", "discover feed"),
    ("Croatia", "press", "Jutarnji list", "https://www.jutarnji.hr", "discover feed"),
    ("Slovenia", "press", "STA", "https://english.sta.si", "discover feed"),
    ("Serbia", "press", "N1", "https://n1info.rs", "discover feed"),
    ("Bosnia and Herzegovina", "press", "Klix", "https://www.klix.ba", "discover feed"),
    ("Montenegro", "press", "Vijesti", "https://www.vijesti.me", "discover feed"),
    ("North Macedonia", "press", "MIA", "https://mia.mk/en", "discover feed"),
    ("Albania", "press", "Albanian Daily News", "https://albaniandailynews.com", "discover feed"),
    ("Bulgaria", "press", "Novinite", "https://www.novinite.com", "discover feed"),
    ("Greece", "press", "Kathimerini", "https://www.ekathimerini.com", "discover feed"),
    ("Cyprus", "press", "Cyprus Mail", "https://cyprus-mail.com", "discover feed"),
    ("Latvia", "press", "LSM", "https://eng.lsm.lv", "discover feed"),
    ("Lithuania", "press", "LRT", "https://www.lrt.lt/en", "discover feed"),
    ("Estonia", "press", "ERR", "https://news.err.ee", "discover feed"),
    ("Germany", "press", "Handelsblatt", "https://www.handelsblatt.com", "discover feed"),
    ("Germany", "press", "JUVE", "https://www.juve.de", "legal press; discover feed"),
    ("France", "press", "Les Echos", "https://www.lesechos.fr", "discover feed"),
    ("France", "press", "Décideurs Juridiques", "https://www.decideurs-juridiques.com", "discover feed"),
    ("Netherlands", "press", "Het Financieele Dagblad", "https://fd.nl", "discover feed"),
    ("Switzerland", "press", "NZZ", "https://www.nzz.ch", "discover feed"),
    ("United Kingdom", "press", "Financial Times - law", "https://www.ft.com/law", "discover feed"),
    ("United Kingdom", "press", "Law Gazette", "https://www.lawgazette.co.uk", "discover feed"),
    ("Israel", "press", "Globes", "https://en.globes.co.il", "discover feed"),
    ("Jordan", "press", "Jordan Times", "https://jordantimes.com", "discover feed"),
    ("Lebanon", "press", "L'Orient Today", "https://today.lorientlejour.com", "discover feed"),
    ("Kuwait", "press", "Kuwait Times", "https://www.kuwaittimes.com", "discover feed"),
    ("Oman", "press", "Times of Oman", "https://timesofoman.com", "discover feed"),
    ("Bahrain", "press", "Gulf Daily News", "https://www.gdnonline.com", "discover feed"),
    ("UAE", "press", "The National", "https://www.thenationalnews.com", "discover feed"),
    ("UAE", "press", "Gulf News", "https://gulfnews.com", "discover feed"),
    ("Saudi Arabia", "press", "Argaam", "https://www.argaam.com/en", "discover feed"),
    ("Qatar", "press", "Gulf Times", "https://www.gulf-times.com", "discover feed"),
    ("Iraq", "press", "Rudaw", "https://www.rudaw.net/english", "discover feed"),
    ("Libya", "press", "Libya Observer", "https://libyaobserver.ly", "discover feed"),
    ("Tunisia", "press", "TAP", "https://www.tap.info.tn/en", "discover feed"),
    ("Egypt", "press", "Ahram Online", "https://english.ahram.org.eg", "discover feed"),
    ("Egypt", "press", "Mada Masr", "https://www.madamasr.com/en", "discover feed"),
    ("Egypt", "regulator", "GAFI", "https://www.gafi.gov.eg", "investment authority"),
    ("Morocco", "press", "Le360", "https://fr.le360.ma", "discover feed"),
    ("Morocco", "press", "L'Economiste", "https://www.leconomiste.com", "discover feed"),
    ("Algeria", "press", "TSA", "https://www.tsa-algerie.com", "discover feed"),
    ("Ethiopia", "press", "Addis Standard", "https://addisstandard.com", "discover feed"),
    ("Uganda", "press", "Daily Monitor", "https://www.monitor.co.ug", "discover feed"),
    ("Rwanda", "press", "The New Times", "https://www.newtimes.co.rw", "discover feed"),
    ("Kenya", "press", "Business Daily", "https://www.businessdailyafrica.com", "discover feed"),
    ("Kenya", "press", "The Star", "https://www.the-star.co.ke", "discover feed"),
    ("Kenya", "press", "Nation", "https://nation.africa/kenya", "discover feed"),
    ("Tanzania", "press", "The Citizen", "https://www.thecitizen.co.tz", "discover feed"),
    ("Zimbabwe", "press", "NewsDay", "https://www.newsday.co.zw", "discover feed"),
    ("Zimbabwe", "press", "The Herald", "https://www.herald.co.zw", "discover feed"),
    ("Namibia", "press", "The Namibian", "https://www.namibian.com.na", "discover feed"),
    ("Botswana", "press", "Mmegi", "https://www.mmegi.bw", "discover feed"),
    ("Madagascar", "press", "L'Express de Madagascar", "https://lexpress.mg", "discover feed"),
    ("Guinea", "press", "Guinéenews", "https://guineenews.org", "discover feed"),
    ("Mali", "press", "Maliweb", "https://www.maliweb.net", "discover feed"),
    ("Burkina Faso", "press", "Lefaso.net", "https://lefaso.net", "discover feed"),
    ("Niger", "press", "ActuNiger", "https://www.actuniger.com", "discover feed"),
    ("Côte d'Ivoire", "press", "Abidjan.net", "https://news.abidjan.net", "discover feed"),
    ("Cameroon", "press", "Journal du Cameroun", "https://www.journalducameroun.com", "discover feed"),
    ("Cameroon", "press", "Investir au Cameroun", "https://www.investiraucameroun.com", "discover feed"),
    ("Gabon", "press", "Gabonreview", "https://www.gabonreview.com", "discover feed"),
    ("Angola", "press", "Angop", "https://www.angop.ao/en", "discover feed"),
    ("Senegal", "press", "APS", "https://aps.sn", "discover feed"),
    ("South Africa", "press", "Business Day", "https://www.businesslive.co.za", "discover feed"),
    ("South Africa", "press", "Daily Maverick", "https://www.dailymaverick.co.za", "discover feed"),
    ("South Africa", "regulator", "DMRE", "https://www.dmre.gov.za", "mining rights"),
    ("Bangladesh", "press", "The Daily Star", "https://www.thedailystar.net", "discover feed"),
    ("Sri Lanka", "press", "Daily FT", "https://www.ft.lk", "discover feed"),
    ("Nepal", "press", "Kathmandu Post", "https://kathmandupost.com", "discover feed"),
    ("Thailand", "press", "Bangkok Post", "https://www.bangkokpost.com", "discover feed"),
    ("Cambodia", "press", "Khmer Times", "https://www.khmertimeskh.com", "discover feed"),
    ("Malaysia", "press", "The Edge Malaysia", "https://theedgemalaysia.com", "discover feed"),
    ("Malaysia", "press", "The Star", "https://www.thestar.com.my", "discover feed"),
    ("Indonesia", "press", "Bisnis.com", "https://www.bisnis.com", "discover feed"),
    ("Indonesia", "press", "Hukumonline", "https://www.hukumonline.com", "discover feed"),
    ("Indonesia", "press", "The Jakarta Post", "https://www.thejakartapost.com", "discover feed"),
    ("Indonesia", "press", "Katadata", "https://katadata.co.id", "discover feed"),
    ("Vietnam", "press", "VietnamNet", "https://vietnamnet.vn/en", "discover feed"),
    ("Philippines", "press", "Inquirer Business", "https://business.inquirer.net", "discover feed"),
    ("Korea", "press", "Korea JoongAng Daily", "https://koreajoongangdaily.joins.com", "discover feed"),
    ("Korea", "press", "The Korea Herald", "https://www.koreaherald.com", "discover feed"),
    ("Korea", "register", "Ministry of Justice ISDS", "https://www.moj.go.kr/moj_eng/1746/subview.do", "Korea publishes its ISDS cases"),
    ("Japan", "press", "Nikkei Asia", "https://asia.nikkei.com", "discover feed"),
    ("China", "press", "Caixin Global", "https://www.caixinglobal.com", "discover feed"),
    ("Taiwan", "press", "Focus Taiwan", "https://focustaiwan.tw", "discover feed"),
    ("Papua New Guinea", "press", "Post-Courier", "https://www.postcourier.com.pg", "discover feed"),
    ("Australia", "register", "DFAT - ISDS", "https://www.dfat.gov.au/trade/investment/investor-state-dispute-settlement", "cases against Australia"),
    ("Australia", "press", "AFR", "https://www.afr.com", "discover feed"),
    ("Australia", "press", "Lawyerly", "https://www.lawyerly.com.au", "discover feed"),
    ("Canada", "press", "The Globe and Mail", "https://www.theglobeandmail.com", "discover feed"),
    ("Canada", "press", "Northern Miner", "https://www.northernminer.com", "discover feed"),
    ("Canada", "press", "Mining.com", "https://www.mining.com", "discover feed"),
    ("United States", "press", "Reuters Legal", "https://www.reuters.com/legal/", "discover feed"),
    ("United States", "press", "Law360 - International Arbitration", "https://www.law360.com/internationalarbitration/rss", "WIRED"),
    ("Guatemala", "press", "Prensa Libre", "https://www.prensalibre.com", "discover feed"),
    ("Honduras", "press", "El Heraldo", "https://www.elheraldo.hn", "discover feed"),
    ("El Salvador", "press", "El Diario de Hoy", "https://www.elsalvador.com", "discover feed"),
    ("Nicaragua", "press", "Confidencial", "https://confidencial.digital", "discover feed"),
    ("Costa Rica", "press", "La Nación", "https://www.nacion.com", "discover feed"),
    ("Panama", "press", "La Prensa", "https://www.prensa.com", "discover feed"),
    ("Dominican Republic", "press", "Diario Libre", "https://www.diariolibre.com", "discover feed"),
    ("Jamaica", "press", "The Gleaner", "https://jamaica-gleaner.com", "discover feed"),
    ("Guyana", "press", "Stabroek News", "https://www.stabroeknews.com", "discover feed"),
    ("Paraguay", "press", "ABC Color", "https://www.abc.com.py", "discover feed"),
    ("Paraguay", "press", "Última Hora", "https://www.ultimahora.com", "discover feed"),
    ("Uruguay", "press", "El Observador", "https://www.elobservador.com.uy", "discover feed"),
]

CANDIDATES += [
    # ===== sector trade press: where commercial arbitrations surface first =====
    ("Sector: Construction", "press", "ENR", "https://www.enr.com/rss/all", ""),
    ("Sector: Construction", "press", "Global Construction Review", "https://www.globalconstructionreview.com/feed/", ""),
    ("Sector: Construction", "press", "Construction Week (Middle East)", "https://www.constructionweekonline.com/feed", ""),
    ("Sector: Construction", "press", "Building", "https://www.building.co.uk/rss", ""),
    ("Sector: Construction", "press", "New Civil Engineer", "https://www.newcivilengineer.com/feed/", ""),
    ("Sector: Construction", "press", "Construction Dive", "https://www.constructiondive.com/feeds/news/", ""),
    ("Sector: Construction", "press", "MEED", "https://www.meed.com", "discover feed"),
    ("Sector: Construction", "press", "Zawya", "https://www.zawya.com/en/rss", "Gulf projects"),
    ("Sector: Construction", "press", "Infrastructure Investor", "https://www.infrastructureinvestor.com/feed/", ""),
    ("Sector: Construction", "press", "IJGlobal", "https://www.ijglobal.com", "discover feed"),
    ("Sector: Construction", "press", "Construction Europe", "https://www.constructioneurope.com", "discover feed"),
    ("Sector: Construction", "press", "Railway Gazette", "https://www.railwaygazette.com/rss", ""),
    ("Sector: Energy", "press", "Upstream", "https://www.upstreamonline.com/rss", ""),
    ("Sector: Energy", "press", "Energy Voice", "https://www.energyvoice.com/feed/", ""),
    ("Sector: Energy", "press", "Rigzone", "https://www.rigzone.com/news/rss/rigzone_latest.aspx", ""),
    ("Sector: Energy", "press", "OilPrice", "https://oilprice.com/rss/main", ""),
    ("Sector: Energy", "press", "Offshore Energy", "https://www.offshore-energy.biz/feed/", ""),
    ("Sector: Energy", "press", "Natural Gas World", "https://www.naturalgasworld.com/rss", ""),
    ("Sector: Energy", "press", "LNG Industry", "https://www.lngindustry.com/rss", ""),
    ("Sector: Energy", "press", "World Oil", "https://www.worldoil.com/rss", ""),
    ("Sector: Energy", "press", "Hart Energy", "https://www.hartenergy.com/rss", ""),
    ("Sector: Energy", "press", "Power Technology", "https://www.power-technology.com/feed/", ""),
    ("Sector: Energy", "press", "PV Magazine", "https://www.pv-magazine.com/feed/", ""),
    ("Sector: Energy", "press", "Windpower Monthly", "https://www.windpowermonthly.com/rss", ""),
    ("Sector: Energy", "press", "reNews", "https://renews.biz/feed/", ""),
    ("Sector: Energy", "press", "Recharge", "https://www.rechargenews.com/rss", ""),
    ("Sector: Energy", "press", "Utility Dive", "https://www.utilitydive.com/feeds/news/", ""),
    ("Sector: Energy", "press", "Petroleum Economist", "https://www.petroleum-economist.com", "discover feed"),
    ("Sector: Energy", "press", "Energy Intelligence", "https://www.energyintel.com", "discover feed"),
    ("Sector: Energy", "press", "Africa Oil+Gas Report", "https://africaoilgasreport.com/feed/", ""),
    ("Sector: Energy", "press", "Interfax Global Energy", "https://interfaxenergy.com", "discover feed"),
    ("Sector: Energy", "press", "S&P Global Commodity Insights", "https://www.spglobal.com/commodityinsights/en/rss-feed", ""),
    ("Sector: Energy", "press", "Argus Media", "https://www.argusmedia.com/en/rss", ""),
    ("Sector: Mining", "press", "Mining.com", "https://www.mining.com/feed/", ""),
    ("Sector: Mining", "press", "The Northern Miner", "https://www.northernminer.com/feed/", ""),
    ("Sector: Mining", "press", "Mining Weekly", "https://www.miningweekly.com/rss", ""),
    ("Sector: Mining", "press", "Mining Journal", "https://www.mining-journal.com/rss", ""),
    ("Sector: Mining", "press", "MiningNews.net", "https://www.miningnews.net/rss", ""),
    ("Sector: Mining", "press", "Australian Mining", "https://www.australianmining.com.au/feed/", ""),
    ("Sector: Mining", "press", "Mining Technology", "https://www.mining-technology.com/feed/", ""),
    ("Sector: Mining", "press", "Kitco News", "https://www.kitco.com/rss", ""),
    ("Sector: Mining", "press", "Mining Review Africa", "https://www.miningreview.com/feed/", ""),
    ("Sector: Mining", "press", "Junior Mining Network", "https://www.juniorminingnetwork.com/rss", ""),
    ("Sector: Mining", "press", "Mining Magazine", "https://www.miningmagazine.com/rss", ""),
    ("Sector: Mining", "press", "Mining MX", "https://www.miningmx.com/feed/", "southern Africa"),
    ("Sector: Pharma", "press", "FiercePharma", "https://www.fiercepharma.com/rss/xml", ""),
    ("Sector: Pharma", "press", "FierceBiotech", "https://www.fiercebiotech.com/rss/xml", ""),
    ("Sector: Pharma", "press", "Endpoints News", "https://endpts.com/feed/", ""),
    ("Sector: Pharma", "press", "BioPharma Dive", "https://www.biopharmadive.com/feeds/news/", ""),
    ("Sector: Pharma", "press", "Pharmaphorum", "https://pharmaphorum.com/feed", ""),
    ("Sector: Pharma", "press", "STAT", "https://www.statnews.com/feed/", ""),
    ("Sector: Pharma", "press", "Pharmaceutical Technology", "https://www.pharmaceutical-technology.com/feed/", ""),
    ("Sector: Pharma", "press", "European Pharmaceutical Review", "https://www.europeanpharmaceuticalreview.com/feed/", ""),
    ("Sector: Pharma", "press", "Scrip", "https://scrip.citeline.com", "discover feed"),
    ("Sector: Shipping", "press", "TradeWinds", "https://www.tradewindsnews.com/rss", ""),
    ("Sector: Shipping", "press", "Splash247", "https://splash247.com/feed/", ""),
    ("Sector: Shipping", "press", "Hellenic Shipping News", "https://www.hellenicshippingnews.com/feed/", ""),
    ("Sector: Shipping", "press", "gCaptain", "https://gcaptain.com/feed/", ""),
    ("Sector: Shipping", "press", "Seatrade Maritime", "https://www.seatrade-maritime.com/rss.xml", ""),
    ("Sector: Shipping", "press", "Lloyd's List", "https://www.lloydslist.com", "discover feed"),
    ("Sector: Aviation", "press", "FlightGlobal", "https://www.flightglobal.com/rss", ""),
    ("Sector: Aviation", "press", "Aviation Week", "https://aviationweek.com/rss.xml", ""),
    ("Sector: Aviation", "press", "Simple Flying", "https://simpleflying.com/feed/", ""),
    ("Sector: Telecoms", "press", "Light Reading", "https://www.lightreading.com/rss.xml", ""),
    ("Sector: Telecoms", "press", "Telecompaper", "https://www.telecompaper.com/rss", ""),
    ("Sector: Telecoms", "press", "CommsUpdate (TeleGeography)", "https://www.commsupdate.com/rss", ""),
    ("Sector: Telecoms", "press", "Developing Telecoms", "https://developingtelecoms.com/feed", ""),
    ("Sector: Telecoms", "press", "Capacity Media", "https://www.capacitymedia.com", "discover feed"),
    ("Sector: Insurance", "press", "Reinsurance News", "https://www.reinsurancene.ws/feed/", ""),
    ("Sector: Insurance", "press", "Artemis", "https://www.artemis.bm/feed/", ""),
    ("Sector: Insurance", "press", "Insurance Journal", "https://www.insurancejournal.com/rss/", ""),
    ("Sector: Insurance", "press", "Insurance Day", "https://insuranceday.maritimeintelligence.informa.com", "discover feed"),
    ("Sector: Finance", "press", "Euromoney", "https://www.euromoney.com/rss", ""),
    ("Sector: Finance", "press", "Private Equity International", "https://www.privateequityinternational.com/feed/", ""),
    ("Sector: Finance", "press", "PE Hub", "https://www.pehub.com/feed/", ""),
    ("Sector: Agribusiness", "press", "FoodNavigator", "https://www.foodnavigator.com/rss", ""),
    ("Sector: Agribusiness", "press", "AgriCensus", "https://www.agricensus.com", "discover feed"),
    ("Sector: Defence", "press", "Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/", ""),
    ("Sector: Defence", "press", "Breaking Defense", "https://breakingdefense.com/feed/", ""),
    ("Sector: Tech", "press", "The Register", "https://www.theregister.com/headlines.atom", ""),
    ("Sector: Tech", "press", "Data Center Dynamics", "https://www.datacenterdynamics.com/en/rss/", ""),
]


WIRED = {"WIRED"}


FEED_PATHS = ["/rss", "/feed", "/rss.xml", "/feed.xml", "/feeds", "/rss/all", "/rss/news", "/en/rss", "/en/feed",
              "/arc/outboundfeeds/rss/", "/?feed=rss2", "/index.xml", "/atom.xml", "/rss/latest"]
_ALT = re.compile(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*>', re.I)
_HREF = re.compile(r'href="([^"]+)"', re.I)


def _get(url, timeout=15, insecure=False):
    """httpx first; a Chrome-identical TLS handshake when refused; verification off
    only for government hosts with broken chains, and flagged."""
    try:
        r = httpx.get(url, headers=UA, timeout=timeout, follow_redirects=True, verify=not insecure)
        if r.status_code in (403, 429, 503) or (r.status_code == 200 and "challenge" in r.text[:1500].lower()):
            raise PermissionError(r.status_code)
        return r.status_code, r.headers.get("content-type", ""), r.text, str(r.url), ""
    except PermissionError:
        pass
    except httpx.ConnectError as exc:
        if "CERTIFICATE_VERIFY_FAILED" in str(exc) and not insecure:
            code, ct, text, final, flag = _get(url, timeout, insecure=True)
            return code, ct, text, final, "insecure-tls"
        raise
    from curl_cffi import requests as cr
    r = cr.get(url, impersonate="chrome124", timeout=timeout, allow_redirects=True, verify=not insecure)
    head = r.text[:3000].lower()
    if r.status_code == 200 and ("challenge validation" in head or ("just a moment" in head and len(r.content) < 20000)):
        raise PermissionError("js-challenge")
    return r.status_code, r.headers.get("content-type", ""), r.text, str(r.url), "chrome-tls"


def _is_feed(ct, text):
    head = text[:4000].lower()
    return "xml" in ct or "<rss" in head or "<feed" in head


def _discover(url):
    """Find the site's own feed: <link rel=alternate> on the home page, then common paths."""
    from urllib.parse import urlsplit, urljoin
    parts = urlsplit(url)
    home = "{}://{}/".format(parts.scheme, parts.netloc)
    tried = []
    try:
        code, ct, text, final, flag = _get(home, 15)
        for tag in _ALT.findall(text)[:4]:
            m = _HREF.search(tag)
            if m:
                tried.append(urljoin(final, html.unescape(m.group(1))))
    except Exception:                                 # noqa: BLE001 - boundary
        pass
    tried += [home.rstrip("/") + p for p in FEED_PATHS]
    for cand in dict.fromkeys(tried):
        try:
            code, ct, text, final, flag = _get(cand, 12)
            if code == 200 and _is_feed(ct, text):
                return cand, flag
        except Exception:                             # noqa: BLE001 - boundary
            continue
    return None, ""


def probe(entry):
    country, kind, name, url, note = entry
    if note.startswith("WIRED"):
        return entry + ("wired", "")
    try:
        code, ct, text, final, flag = _get(url, 15)
        if code >= 400:
            raise FileNotFoundError(code)
        if _is_feed(ct, text):
            return entry + ("rss", ("feed " + flag).strip())
        if kind == "press":
            found, fflag = _discover(url)
            if found:
                return (country, kind, name, found, note) + ("rss", "discovered " + (fflag or "").strip())
        return entry + ("html", "{} KB {}".format(len(text) // 1024, flag).strip())
    except PermissionError as exc:
        if kind == "press":
            found, fflag = _discover(url)
            if found:
                return (country, kind, name, found, note) + ("rss", "discovered " + (fflag or "").strip())
        return entry + ("blocked", str(exc))
    except FileNotFoundError as exc:
        if kind == "press":
            found, fflag = _discover(url)
            if found:
                return (country, kind, name, found, note) + ("rss", "discovered " + (fflag or "").strip())
        return entry + ("dead", "HTTP {}".format(exc))
    except Exception as exc:                          # noqa: BLE001 - boundary
        if kind == "press":
            try:
                found, fflag = _discover(url)
                if found:
                    return (country, kind, name, found, note) + ("rss", "discovered " + (fflag or "").strip())
            except Exception:                         # noqa: BLE001 - boundary
                pass
        return entry + ("error", type(exc).__name__[:14])


def run_probe():
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        return list(ex.map(probe, CANDIDATES))


def write_docs(results):
    today = dt.date.today().isoformat()
    countries = []
    for r in results:
        if r[0] not in countries:
            countries.append(r[0])
    lines = ["# ArbRadar source map", "", "Verified {}. Edit `tools/sourcemap.py`, then run "
             "`python -m tools.sourcemap --probe` to re-verify and regenerate this file.".format(today), "",
             "Status: **wired** = read on every run · **rss** = feed answers, ready to wire · **html** = page answers, "
             "needs a parser · **blocked** = refuses scripts · **dead** = not found · **error** = no answer", ""]
    counts = {}
    for r in results:
        counts[r[5]] = counts.get(r[5], 0) + 1
    lines.append("Totals: " + ", ".join("{} {}".format(v, k) for k, v in sorted(counts.items())))
    lines.append("")
    for c in countries:
        rows = [r for r in results if r[0] == c]
        lines += ["## {}".format(c), "", "| Type | Source | Status | Detail | Note |", "|---|---|---|---|---|"]
        for _, kind, name, url, note, status, detail in rows:
            lines.append("| {} | [{}]({}) | {} | {} | {} |".format(kind, name, url, status, detail, note.replace("WIRED", "").strip(" ;")))
        lines.append("")
    md = "\n".join(lines)
    open(os.path.join(ROOT, "SOURCES.md"), "w", encoding="utf-8").write(md)
    json.dump([list(r) for r in results], open(os.path.join(ROOT, "docs", "sources.json"), "w"), ensure_ascii=False, indent=1)
    return md


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()
    if a.probe:
        res = run_probe()
        md = write_docs(res)
        print(md.split("\n")[6])
        for r in res:
            print("  {:<14} {:<10} {:<8} {:<8} {}".format(r[0][:14], r[1], r[5], r[6][:8], r[2][:48]))
    else:
        print(len(CANDIDATES), "candidates")
