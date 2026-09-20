# ArbRadar source map

Verified 2026-09-20. Edit `tools/sourcemap.py`, then run `python -m tools.sourcemap --probe` to re-verify and regenerate this file.

Status: **wired** = read on every run · **rss** = feed answers, ready to wire · **html** = page answers, needs a parser · **blocked** = refuses scripts · **dead** = not found · **error** = no answer

Totals: 19 blocked, 30 dead, 21 error, 77 html, 62 rss, 7 wired

## Armenia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Government decisions](https://www.gov.am/en/decrees/) | html | 73 KB | cabinet decisions incl. concessions and licences |
| gazette | [ARLIS legal information system](https://www.arlis.am) | html | 1406 KB | all legal acts; search only |
| tenders | [ARMEPS procurement](https://www.armeps.am) | html | 33 KB | state procurement portal |
| tenders | [gnumner.am announcements](https://gnumner.am) | error | ConnectError | procurement announcements |
| courts | [DataLex court database](https://www.datalex.am) | error | ConnectError | first-instance and appeal cases |
| regulator | [Public Services Regulatory Commission](https://psrc.am/en) | dead | HTTP 404 | energy, water, telecoms tariffs and licences |
| exchange | [Armenia Securities Exchange](https://amx.am/en) | html | 3 KB | listed-company disclosures |
| press | [Armenpress (EN RSS)](https://armenpress.am/rss/eng) | dead | HTTP 404 |  |
| press | [Hetq](https://hetq.am/en/rss) | rss | feed | investigative |
| press | [CivilNet](https://www.civilnet.am/feed) | html | 80 KB |  |
| press | [News.am](https://news.am/eng/rss/) | rss | feed |  |
| press | [Panorama.am](https://www.panorama.am/en/rss) | dead | HTTP 404 |  |

## Georgia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Legislative Herald (matsne)](https://matsne.gov.ge) | html | 1266 KB | all legal acts |
| tenders | [State Procurement Agency](https://tenders.procurement.gov.ge) | html | 11 KB |  |
| register | [Ministry of Justice](https://www.justice.gov.ge) | dead | HTTP 404 | MoJ represents Georgia in ISDS; check for a cases page |
| courts | [Supreme Court](https://www.supremecourt.ge) | html | 45 KB |  |
| regulator | [GNERC energy regulator](https://gnerc.org) | error | ConnectError |  |
| regulator | [National Agency of Mines](https://nam.gov.ge) | error | ConnectTimeout | mining licences |
| press | [Civil.ge](https://civil.ge/feed) | rss | feed |  |
| press | [Agenda.ge](https://agenda.ge/en/rss) | error | ConnectError |  |
| press | [Georgia Today](https://georgiatoday.ge/feed) | html | 323 KB |  |
| press | [InterPressNews](https://www.interpressnews.ge/en/rss) | html | 6 KB |  |
| press | [BM.ge (Business Media)](https://bm.ge/rss) | blocked | HTTP 403 |  |

## Azerbaijan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [e-qanun legal acts](https://e-qanun.az) | error | ConnectTimeout |  |
| gazette | [President's decrees](https://president.az/en/rss) | rss | feed |  |
| tenders | [etender.gov.az](https://etender.gov.az) | error | ConnectTimeout |  |
| press | [Report.az](https://report.az/en/rss/) | rss | feed |  |
| press | [APA](https://apa.az/en/rss) | html | 292 KB |  |
| press | [Trend](https://en.trend.az/rss) | rss | feed |  |
| press | [Caliber](https://caliber.az/en/rss) | dead | HTTP 404 |  |

## Kazakhstan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Adilet legal acts](https://adilet.zan.kz) | html | 2 KB |  |
| tenders | [Goszakup public procurement](https://goszakup.gov.kz) | html | 6 KB | has an open API (ows.goszakup.gov.kz) |
| courts | [Judicial cabinet / court database](https://sud.gov.kz) | html | 83 KB |  |
| courts | [AIFC Court](https://court.aifc.kz) | html | 73 KB | judgments published |
| regulator | [Ministry of Industry and Construction (subsoil)](https://www.gov.kz/memleket/entities/mic) | html | 0 KB | licence revocations |
| regulator | [Ministry of Energy](https://www.gov.kz/memleket/entities/energo) | html | 0 KB |  |
| exchange | [KASE](https://kase.kz/en/news/) | html | 322 KB |  |
| press | [Kursiv](https://kz.kursiv.media/feed/) | rss | feed |  |
| press | [Tengrinews](https://tengrinews.kz/rss/) | dead | HTTP 500 |  |
| press | [Zakon.kz](https://www.zakon.kz/rss) | dead | HTTP 404 | legal news |
| press | [Vlast.kz](https://vlast.kz/rss) | dead | HTTP 404 |  |
| press | [The Astana Times](https://astanatimes.com/feed/) | rss | feed |  |
| press | [Forbes Kazakhstan](https://forbes.kz/rss) | html | 0 KB |  |

## Uzbekistan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Lex.uz](https://lex.uz) | html | 224 KB |  |
| tenders | [UZEX e-procurement](https://xarid.uzex.uz) | html | 1 KB |  |
| regulator | [Ministry of Mining and Geology](https://mmg.gov.uz) | error | ConnectError |  |
| exchange | [Tashkent Stock Exchange](https://uzse.uz) | html | 307 KB |  |
| press | [Gazeta.uz](https://www.gazeta.uz/ru/rss/) | rss | feed |  |
| press | [Kun.uz](https://kun.uz/en/rss) | dead | HTTP 404 |  |
| press | [Spot.uz](https://www.spot.uz/rss) | rss | feed | business |
| press | [UzDaily](https://uzdaily.uz/en/rss) | rss | feed |  |
| press | [Daryo](https://daryo.uz/en/feed) | error | ConnectError |  |

## Kyrgyzstan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Ministry of Justice legal database](https://cbd.minjust.gov.kg) | html | 2 KB |  |
| tenders | [zakupki.gov.kg](https://zakupki.gov.kg) | html | 1 KB |  |
| press | [24.kg](https://24.kg/rss/) | rss | feed |  |
| press | [AKIpress](https://akipress.com/rss/) | rss | feed |  |

## Turkmenistan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Turkmenportal](https://turkmenportal.com/en/rss) | dead | HTTP 404 |  |
| press | [Chronicles of Turkmenistan](https://en.hronikatm.com/feed/) | error | ConnectError | independent |

## Ukraine

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| tenders | [Prozorro](https://prozorro.gov.ua/api/search/tenders) | wired |  |  |
| gazette | [Verkhovna Rada legal acts](https://zakon.rada.gov.ua) | error | ConnectTimeout |  |
| register | [Ministry of Justice - international disputes](https://minjust.gov.ua) | blocked | HTTP 403 | MoJ defends Ukraine in ISDS; find the cases page |
| courts | [Unified State Register of Court Decisions](https://reyestr.court.gov.ua) | html | 47 KB | every decision, searchable |
| regulator | [NEURC energy regulator](https://www.nerc.gov.ua) | html | 886 KB |  |
| press | [Ukrinform (EN)](https://www.ukrinform.net/rss) | dead | HTTP 404 |  |
| press | [Ekonomichna Pravda](https://www.epravda.com.ua/rss/) | blocked | HTTP 403 |  |
| press | [LB.ua](https://lb.ua/rss) | html | 24 KB |  |
| press | [NV](https://nv.ua/rss) | html | 74 KB |  |
| press | [LIGA.net](https://www.liga.net/rss) | dead | HTTP 404 | legal and business |
| press | [Sudovo-yurydychna gazeta](https://sud.ua/rss) | rss | feed | court news |

## Russia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Official publication of legal acts](http://publication.pravo.gov.ru) | html | 27 KB |  |
| courts | [Commercial courts case database (kad.arbitr)](https://kad.arbitr.ru) | html | 90 KB | anti-suit injunctions, asset seizures; search needs session |
| press | [Pravo.ru](https://pravo.ru/rss/) | rss | feed | legal news |
| press | [Kommersant](https://www.kommersant.ru/RSS/news.xml) | rss | feed |  |
| press | [Vedomosti](https://www.vedomosti.ru/rss/news) | rss | feed |  |
| press | [Interfax](https://www.interfax.ru/rss.asp) | rss | feed |  |
| press | [RBC](https://rssexport.rbc.ru/rbcnews/news/30/full.rss) | rss | feed |  |

## Turkey

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Resmî Gazete](https://www.resmigazete.gov.tr) | error | ConnectError | daily official gazette |
| exchange | [KAP public disclosure platform](https://www.kap.org.tr/en) | html | 149 KB | listed companies disclose arbitrations |
| regulator | [EPDK energy regulator](https://www.epdk.gov.tr) | html | 187 KB |  |
| regulator | [MAPEG mining](https://www.mapeg.gov.tr) | error | ConnectError |  |
| press | [Dünya](https://www.dunya.com/rss) | rss | feed |  |
| press | [Bloomberg HT](https://www.bloomberght.com/rss) | rss | feed |  |
| press | [Hürriyet Daily News](https://www.hurriyetdailynews.com/rss) | rss | feed |  |
| press | [Daily Sabah](https://www.dailysabah.com/rssFeed/10) | rss | feed |  |

## Mexico

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [Secretaría de Economía ISDS register](https://www.gob.mx/se/acciones-y-programas/comercio-exterior-solucion-de-controversias-inversionista-estado) | blocked | HTTP 200 | publishes notices of intent; bot challenge |
| gazette | [Diario Oficial de la Federación](https://www.dof.gob.mx/rss) | error | ConnectError |  |
| tenders | [CompraNet](https://compranet.hacienda.gob.mx) | error | ConnectError |  |
| regulator | [CNH hydrocarbons](https://www.gob.mx/cnh) | blocked | HTTP 200 |  |
| exchange | [BMV](https://www.bmv.com.mx) | error | ConnectTimeout |  |
| press | [El Economista](https://www.eleconomista.com.mx/rss/) | blocked | HTTP 403 |  |
| press | [Expansión](https://expansion.mx/rss) | rss | feed |  |
| press | [El Financiero](https://www.elfinanciero.com.mx/rss) | rss | feed |  |
| press | [El Universal](https://www.eluniversal.com.mx/rss) | dead | HTTP 404 |  |

## Argentina

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [Procuración del Tesoro de la Nación](https://www.argentina.gob.ar/procuraciondeltesoro) | html | 42 KB | defends Argentina; check for a cases page |
| gazette | [Boletín Oficial](https://www.boletinoficial.gob.ar) | html | 239 KB | RSS available |
| tenders | [COMPR.AR](https://comprar.gob.ar) | html | 78 KB |  |
| press | [La Nación](https://www.lanacion.com.ar/arc/outboundfeeds/rss/) | rss | feed |  |
| press | [Clarín](https://www.clarin.com/rss/) | rss | feed |  |
| press | [Ámbito](https://www.ambito.com/rss) | blocked | HTTP 403 |  |
| press | [El Cronista](https://www.cronista.com/rss) | html | 1632 KB |  |
| press | [Infobae](https://www.infobae.com/feeds/rss/) | dead | HTTP 404 |  |

## Colombia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [ANDJE - defensa internacional](https://www.defensajuridica.gov.co) | blocked | HTTP 403 | publishes ISDS cases; WAF 403 to scripts |
| tenders | [SECOP / Colombia Compra](https://www.colombiacompra.gov.co) | html | 588 KB |  |
| regulator | [ANM mining](https://www.anm.gov.co) | html | 319 KB |  |
| regulator | [ANH hydrocarbons](https://www.anh.gov.co) | html | 71 KB |  |
| courts | [Consejo de Estado](https://www.consejodeestado.gov.co) | html | 270 KB |  |
| press | [Portafolio](https://www.portafolio.co/rss) | html | 92 KB |  |
| press | [La República](https://www.larepublica.co/rss) | rss | feed |  |
| press | [Semana](https://www.semana.com/rss) | dead | HTTP 404 |  |
| press | [Valora Analitik](https://www.valoraanalitik.com/feed/) | blocked | HTTP 403 |  |

## Peru

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [MEF - SICRECI (State coordination for investment disputes)](https://www.mef.gob.pe) | html | 0 KB | find the cases page |
| gazette | [El Peruano](https://elperuano.pe) | html | 82 KB |  |
| tenders | [SEACE](https://www.gob.pe/seace) | dead | HTTP 404 |  |
| regulator | [Osinergmin](https://www.osinergmin.gob.pe) | html | 0 KB |  |
| press | [Gestión](https://gestion.pe/rss) | html | 765 KB |  |
| press | [El Comercio](https://elcomercio.pe/rss) | html | 884 KB |  |
| press | [RPP](https://rpp.pe/rss) | rss | feed |  |

## Chile

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| tenders | [Mercado Público](https://www.mercadopublico.cl) | html | 0 KB |  |
| press | [Diario Financiero](https://www.df.cl/rss) | dead | HTTP 404 |  |
| press | [El Mercurio (Emol)](https://www.emol.com/rss/) | error | ReadError |  |

## Ecuador

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [Procuraduría General del Estado](https://www.pge.gob.ec) | html | 80 KB | publishes arbitration cases against Ecuador |
| gazette | [Registro Oficial](https://www.registroficial.gob.ec) | html | 182 KB |  |
| press | [El Universo](https://www.eluniverso.com/rss) | html | 145 KB |  |
| press | [Primicias](https://www.primicias.ec/feed/) | html | 263 KB |  |

## Venezuela

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Efecto Cocuyo](https://efectococuyo.com/feed/) | rss | feed |  |
| press | [Banca y Negocios](https://www.bancaynegocios.com/feed/) | error | RemoteProtocolError |  |
| press | [El Nacional](https://www.elnacional.com/feed/) | rss | feed |  |

## Bolivia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [El Deber](https://eldeber.com.bo/rss) | html | 158 KB |  |

## Brazil

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Diário Oficial da União](https://www.in.gov.br) | error | RemoteProtocolError |  |
| press | [Valor Econômico](https://valor.globo.com/rss) | dead | HTTP 404 |  |
| press | [JOTA](https://www.jota.info/feed) | rss | feed | legal |
| press | [Folha - Mercado](https://feeds.folha.uol.com.br/mercado/rss091.xml) | rss | feed |  |

## Spain

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [BOE](https://www.boe.es/rss/canal.php?c=ultimos) | html | 0 KB | official gazette |
| exchange | [CNMV](https://www.cnmv.es) | html | 289 KB | hechos relevantes |
| tenders | [PLACSP](https://contrataciondelestado.es) | html | 0 KB |  |
| press | [Expansión](https://e00-expansion.uecdn.es/rss/portada.xml) | rss | feed |  |
| press | [El Confidencial](https://rss.elconfidencial.com/espana/) | rss | feed |  |
| press | [Cinco Días](https://cincodias.elpais.com/rss/) | dead | HTTP 404 |  |
| press | [El Economista](https://www.eleconomista.es/rss/rss-empresas.php) | blocked | HTTP 403 |  |

## Italy

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Gazzetta Ufficiale](https://www.gazzettaufficiale.it) | html | 41 KB |  |
| press | [Il Sole 24 Ore](https://www.ilsole24ore.com/rss/italia.xml) | rss | feed |  |

## Romania

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Ziarul Financiar](https://www.zf.ro/rss) | rss | feed |  |
| press | [Profit.ro](https://www.profit.ro/rss) | rss | feed |  |

## Poland

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Puls Biznesu](https://www.pb.pl/rss) | html | 70 KB |  |
| press | [Rzeczpospolita](https://www.rp.pl/rss_main) | rss | feed |  |

## Nigeria

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| tenders | [Bureau of Public Procurement](https://www.bpp.gov.ng) | html | 179 KB |  |
| regulator | [NUPRC upstream regulator](https://www.nuprc.gov.ng) | html | 73 KB |  |
| regulator | [Mining Cadastre Office](https://miningcadastre.gov.ng) | html | 135 KB |  |
| exchange | [NGX](https://ngxgroup.com) | html | 66 KB |  |
| press | [BusinessDay](https://businessday.ng/feed/) | rss | feed |  |
| press | [Premium Times](https://www.premiumtimesng.com/feed) | rss | feed |  |
| press | [Punch](https://punchng.com/feed/) | rss | feed |  |
| press | [Nairametrics](https://nairametrics.com/feed/) | rss | feed |  |

## Ghana

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| regulator | [Minerals Commission](https://www.mincom.gov.gh) | html | 285 KB |  |
| press | [Ghana Business News](https://www.ghanabusinessnews.com/feed/) | rss | feed |  |
| press | [MyJoyOnline Business](https://www.myjoyonline.com/business/feed/) | rss | feed |  |

## Kenya

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Business Daily](https://www.businessdailyafrica.com/rss) | dead | HTTP 404 |  |
| press | [The Star](https://www.the-star.co.ke/rss) | dead | HTTP 404 |  |

## Tanzania

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| regulator | [Mining Commission](https://www.tumemadini.go.tz) | error | ConnectError |  |
| press | [The Citizen](https://www.thecitizen.co.tz/rss) | dead | HTTP 404 |  |

## Zambia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Zambia Daily Mail](https://www.daily-mail.co.zm/feed/) | rss | feed |  |
| press | [News Diggers](https://diggers.news/feed/) | rss | feed |  |

## DRC

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| regulator | [CAMI mining cadastre](https://www.cami.cd) | html | 145 KB |  |
| press | [Actualite.cd](https://actualite.cd/feed) | rss | feed |  |

## South Africa

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| exchange | [JSE SENS](https://www.jse.co.za) | blocked | HTTP 403 |  |
| press | [Business Day](https://www.businesslive.co.za/bd/rss) | dead | HTTP 404 |  |
| press | [Moneyweb](https://www.moneyweb.co.za/feed/) | rss | feed |  |

## Mozambique

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Club of Mozambique](https://clubofmozambique.com/feed/) | rss | feed |  |

## Egypt

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| exchange | [Egyptian Exchange](https://www.egx.com.eg) | html | 6 KB |  |
| press | [Enterprise](https://enterprise.press/feed/) | html | 453 KB | the best daily on Egyptian business |
| press | [Ahram Online](https://english.ahram.org.eg/rss) | blocked | HTTP 403 |  |
| press | [Daily News Egypt](https://www.dailynewsegypt.com/feed/) | rss | feed |  |

## Algeria

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [APS](https://www.aps.dz/en/?format=feed) | html | 230 KB |  |

## Morocco

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Médias24](https://medias24.com/feed/) | blocked | HTTP 403 |  |

## UAE

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The National](https://www.thenationalnews.com/rss) | dead | HTTP 404 |  |

## Saudi Arabia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Arab News](https://www.arabnews.com/rss.xml) | blocked | HTTP 403 |  |

## Qatar

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The Peninsula](https://thepeninsulaqatar.com/rss) | html | 91 KB |  |

## Iraq

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Iraq Business News](https://www.iraq-businessnews.com/feed/) | rss | feed |  |

## India

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [eGazette](https://egazette.gov.in) | error | ConnectError |  |
| exchange | [BSE corporate announcements](https://www.bseindia.com/corporates/ann.html) | html | 13 KB | arbitration disclosures; has an API |
| press | [Economic Times](https://economictimes.indiatimes.com/rssfeedsdefault.cms) | rss | feed |  |
| press | [Mint](https://www.livemint.com/rss/companies) | rss | feed |  |
| press | [Bar & Bench](https://www.barandbench.com/feed) | rss | feed | legal |
| press | [LiveLaw](https://www.livelaw.in/rss) | dead | HTTP 404 | legal |
| press | [Business Standard](https://www.business-standard.com/rss/companies-101.rss) | rss | feed |  |

## Pakistan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Dawn Business](https://www.dawn.com/feeds/business) | rss | feed |  |
| press | [Business Recorder](https://www.brecorder.com/feeds/latest-news) | rss | feed |  |

## Indonesia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [JDIH Setneg](https://jdih.setneg.go.id) | html | 2466 KB |  |
| regulator | [ESDM ministry](https://www.esdm.go.id) | html | 136 KB | IUP revocations |
| exchange | [IDX](https://www.idx.co.id) | blocked | HTTP 403 |  |
| press | [Kontan](https://www.kontan.co.id/rss) | html | 39 KB |  |
| press | [Bisnis.com](https://www.bisnis.com/rss) | blocked | HTTP 403 |  |
| press | [Hukumonline](https://www.hukumonline.com/rss) | dead | HTTP 404 | legal |
| press | [Jakarta Post](https://www.thejakartapost.com/rss) | dead | HTTP 404 |  |

## Vietnam

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [VnExpress International](https://e.vnexpress.net/rss/business.rss) | rss | feed |  |

## Malaysia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The Edge](https://theedgemalaysia.com/rss) | dead | HTTP 404 |  |

## Philippines

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [BusinessWorld](https://www.bworldonline.com/feed/) | rss | feed |  |

## Korea

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Korea Economic Daily](https://www.kedglobal.com/rss) | rss | feed |  |
| press | [Korea JoongAng Daily](https://koreajoongangdaily.joins.com/rss) | dead | HTTP 404 |  |

## Global

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [ICSID docket API](https://icsid.worldbank.org/api/cases/pending) | wired |  |  |
| register | [UNCITRAL Transparency Registry](https://www.uncitral.org/transparency-registry/registry/index.jspx) | html | 73 KB | notices under the Mauritius Convention |
| register | [PCA cases](https://pca-cpa.org/en/cases/) | html | 129 KB | client-rendered |
| register | [italaw](https://www.italaw.com) | blocked | HTTP 403 | awards and decisions; Cloudflare |
| register | [UNCTAD ISDS Navigator](https://investmentpolicy.unctad.org/investment-dispute-settlement) | blocked | HTTP 403 | Cloudflare |
| courts | [CourtListener / RECAP](https://www.courtlistener.com/api/rest/v4/search/) | wired |  |  |
| exchange | [SEC EDGAR full-text](https://efts.sec.gov/LATEST/search-index) | wired |  |  |
| tenders | [TED](https://api.ted.europa.eu/v3/notices/search) | wired |  |  |
| exchange | [LSE RNS](https://www.londonstockexchange.com/news) | html | 53 KB | no keyword feed |
| exchange | [ASX announcements](https://www.asx.com.au/markets/trade-our-cash-market/announcements) | html | 133 KB | per-company only |
| exchange | [SEDAR+](https://www.sedarplus.ca) | blocked | HTTP 403 | Canadian filings; client-rendered |
| press | [GAR](https://globalarbitrationreview.com/rss) | wired |  |  |
| press | [IAReporter](https://www.iareporter.com/feed/) | wired |  |  |
| press | [Law360 International Arbitration](https://www.law360.com/internationalarbitration/rss) | rss | feed | paywalled headlines |
| press | [Lexology arbitration](https://www.lexology.com/rss) | dead | HTTP 404 |  |
| press | [Omni Bridgeway news](https://omnibridgeway.com/news) | html | 23 KB | funder |
| press | [Litigation Capital Management](https://www.lcmfinance.com/news/) | html | 74 KB | funder |
