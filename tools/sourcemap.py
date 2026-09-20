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
    ("Kazakhstan", "courts", "AIFC Court", "https://court.aifc.kz", "judgments published"),
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
    ("Mexico", "register", "Secretaría de Economía ISDS register", "https://www.gob.mx/se/acciones-y-programas/comercio-exterior-solucion-de-controversias-inversionista-estado", "publishes notices of intent; bot challenge"),
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
    ("Colombia", "register", "ANDJE - defensa internacional", "https://www.defensajuridica.gov.co", "publishes ISDS cases; WAF 403 to scripts"),
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
    ("Global", "register", "UNCITRAL Transparency Registry", "https://www.uncitral.org/transparency-registry/registry/index.jspx", "notices under the Mauritius Convention"),
    ("Global", "register", "PCA cases", "https://pca-cpa.org/en/cases/", "client-rendered"),
    ("Global", "register", "italaw", "https://www.italaw.com", "awards and decisions; Cloudflare"),
    ("Global", "register", "UNCTAD ISDS Navigator", "https://investmentpolicy.unctad.org/investment-dispute-settlement", "Cloudflare"),
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

WIRED = {"WIRED"}


def probe(entry):
    country, kind, name, url, note = entry
    if note.startswith("WIRED"):
        return entry + ("wired", "")
    try:
        r = httpx.get(url, headers=UA, timeout=20, follow_redirects=True)
        ct = r.headers.get("content-type", "")
        head = r.text[:4000].lower()
        if r.status_code in (403, 429, 503) or "challenge" in head[:1500] and r.status_code == 200 and len(r.content) < 5000:
            return entry + ("blocked", "HTTP {}".format(r.status_code))
        if r.status_code >= 400:
            return entry + ("dead", "HTTP {}".format(r.status_code))
        if "xml" in ct or "<rss" in head or "<feed" in head:
            return entry + ("rss", "feed")
        return entry + ("html", "{} KB".format(len(r.content) // 1024))
    except Exception as exc:                          # noqa: BLE001 - boundary
        return entry + ("error", type(exc).__name__)


def run_probe():
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
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
