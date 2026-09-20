# ArbRadar source map

Verified 2026-09-20. Edit `tools/sourcemap.py`, then run `python -m tools.sourcemap --probe` to re-verify and regenerate this file.

Status: **wired** = read on every run · **rss** = feed answers, ready to wire · **html** = page answers, needs a parser · **blocked** = refuses scripts · **dead** = not found · **error** = no answer

Totals: 75 dead, 28 error, 216 html, 201 rss, 8 wired

## Armenia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Government decisions](https://www.gov.am/en/decrees/) | html | 73 KB | cabinet decisions incl. concessions and licences |
| gazette | [ARLIS legal information system](https://www.arlis.am) | html | 1400 KB | all legal acts; search only |
| tenders | [ARMEPS procurement](https://www.armeps.am) | html | 30 KB | state procurement portal |
| tenders | [gnumner.am announcements](https://gnumner.am) | html | 120 KB insecure-tls | procurement announcements |
| courts | [DataLex court database](https://www.datalex.am) | html | 17 KB insecure-tls | first-instance and appeal cases |
| regulator | [Public Services Regulatory Commission](https://psrc.am/en) | dead | HTTP 404 | energy, water, telecoms tariffs and licences |
| exchange | [Armenia Securities Exchange](https://amx.am/en) | html | 3 KB | listed-company disclosures |
| press | [Armenpress (EN RSS)](https://armenpress.am/rss/eng) | dead | HTTP 404 |  |
| press | [Hetq](https://hetq.am/en/rss) | rss | feed | investigative |
| press | [CivilNet](https://www.civilnet.am/feed) | html | 66 KB |  |
| press | [News.am](https://news.am/eng/rss/) | rss | feed |  |
| press | [Panorama.am](https://www.panorama.am/en/rss) | dead | HTTP 404 |  |
| gazette | [Prime Minister press releases](https://www.primeminister.am/en/press-release/) | html | 30 KB |  |
| gazette | [President](https://www.president.am/en/press-release/) | html | 26 KB |  |
| regulator | [Central Bank of Armenia](https://www.cba.am/en/SitePages/newsevents.aspx) | dead | HTTP 404 | FX and bank licences |
| regulator | [Competition Protection Commission](https://www.competition.am/en/news/) | html | 113 KB insecure-tls |  |
| regulator | [State Revenue Committee](https://www.petekamutner.am/en/) | error | ConnectTimeout | tax |
| gazette | [Ministry of Justice](https://www.moj.am/en) | dead | HTTP 403 | represents Armenia in ISDS |
| press | [Armenpress](https://armenpress.am) | html | 132 KB | discover feed |
| press | [Panorama.am](https://www.panorama.am) | html | 263 KB | discover feed |
| press | [Aravot](https://www.aravot-en.am) | error | ConnectError | discover feed |
| press | [Azatutyun (RFE/RL)](https://www.azatutyun.am/api/) | rss | discovered  | discover feed |
| press | [Armenia Today](https://armeniatoday.am/feed/) | rss | discovered  | carried the Vinitski story |

## Georgia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Legislative Herald (matsne)](https://matsne.gov.ge) | html | 1211 KB | all legal acts |
| tenders | [State Procurement Agency](https://tenders.procurement.gov.ge) | html | 8 KB |  |
| register | [Ministry of Justice](https://www.justice.gov.ge) | dead | HTTP 404 | MoJ represents Georgia in ISDS; check for a cases page |
| courts | [Supreme Court](https://www.supremecourt.ge) | html | 44 KB |  |
| regulator | [GNERC energy regulator](https://gnerc.org) | html | 296 KB insecure-tls |  |
| regulator | [National Agency of Mines](https://nam.gov.ge) | error | ConnectTimeout | mining licences |
| press | [Civil.ge](https://civil.ge/feed) | rss | feed |  |
| press | [Agenda.ge](https://agenda.ge/en/rss) | error | ConnectError |  |
| press | [Georgia Today](https://georgiatoday.ge/feed) | html | 323 KB |  |
| press | [InterPressNews](https://www.interpressnews.ge/en/rss) | html | 6 KB |  |
| press | [BM.ge (Business Media)](https://bm.ge/rss) | dead | HTTP 403 |  |
| gazette | [Government of Georgia](https://www.gov.ge/en/news) | error | ConnectTimeout |  |
| regulator | [National Bank of Georgia](https://nbg.gov.ge/en/media/news) | html | 337 KB |  |
| regulator | [Competition Agency](https://gca.gov.ge/en/news) | error | ConnectError |  |
| gazette | [Ministry of Justice (justice.gov.ge)](https://www.justice.gov.ge/en) | dead | HTTP 404 | discover cases page |
| press | [Agenda.ge](https://agenda.ge) | error | ConnectError | discover feed |
| press | [BM.ge](https://bm.ge) | dead | HTTP 403 | discover feed |
| press | [Formula News](https://formulanews.ge) | html | 102 KB | discover feed |
| press | [Commersant.ge](https://commersant.ge) | html | 779 KB | discover feed |

## Azerbaijan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [e-qanun legal acts](https://e-qanun.az) | error | ConnectTimeout |  |
| gazette | [President's decrees](https://president.az/en/rss) | rss | feed |  |
| tenders | [etender.gov.az](https://etender.gov.az) | error | ConnectTimeout |  |
| press | [Report.az](https://report.az/en/rss/) | rss | feed |  |
| press | [APA](https://apa.az/rss) | rss | discovered  |  |
| press | [Trend](https://en.trend.az/rss) | rss | feed |  |
| press | [Caliber](https://caliber.az/rss.xml) | rss | discovered  |  |
| gazette | [Cabinet of Ministers](https://cabmin.gov.az/en/news) | dead | HTTP 403 |  |
| regulator | [Central Bank](https://www.cbar.az/news) | error | ConnectTimeout |  |
| press | [Caliber](https://caliber.az/rss.xml) | rss | discovered  | discover feed |
| press | [Turan](https://turan.az) | html | 185 KB | discover feed |
| press | [ABC.az](https://abc.az) | html | 144 KB | discover feed |

## Kazakhstan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Adilet legal acts](https://adilet.zan.kz) | html | 2 KB |  |
| tenders | [Goszakup public procurement](https://goszakup.gov.kz) | html | 6 KB | has an open API (ows.goszakup.gov.kz) |
| courts | [Judicial cabinet / court database](https://sud.gov.kz) | html | 77 KB |  |
| courts | [AIFC Court](https://court.aifc.kz) | html | 73 KB | judgments published |
| regulator | [Ministry of Industry and Construction (subsoil)](https://www.gov.kz/memleket/entities/mic) | html | 0 KB | licence revocations |
| regulator | [Ministry of Energy](https://www.gov.kz/memleket/entities/energo) | html | 0 KB |  |
| exchange | [KASE](https://kase.kz/en/news/) | html | 321 KB |  |
| press | [Kursiv](https://kz.kursiv.media/feed/) | rss | feed |  |
| press | [Tengrinews](https://tengrinews.kz/rss/) | dead | HTTP 404 |  |
| press | [Zakon.kz](https://www.zakon.kz/rss) | dead | HTTP 404 | legal news |
| press | [Vlast.kz](https://vlast.kz/feed/) | rss | discovered  |  |
| press | [The Astana Times](https://astanatimes.com/feed/) | rss | feed |  |
| press | [Forbes Kazakhstan](https://forbes.kz/rss) | html | 0 KB |  |
| gazette | [Akorda (President)](https://www.akorda.kz/en/events) | html | 45 KB insecure-tls |  |
| gazette | [Government (primeminister.kz)](https://primeminister.kz/en/news) | html | 64 KB |  |
| regulator | [National Bank](https://www.nationalbank.kz/en/news) | dead | HTTP 404 |  |
| regulator | [Samruk-Kazyna](https://sk.kz/en/press-center/news/) | dead | HTTP 404 | sovereign holding |
| press | [Tengrinews](https://tengrinews.kz) | html | 413 KB | discover feed |
| press | [Zakon.kz](https://www.zakon.kz) | html | 290 KB | discover feed |
| press | [Vlast.kz](https://vlast.kz/feed/) | rss | discovered  | discover feed |
| press | [Inbusiness.kz](https://inbusiness.kz/ru/rss) | rss | discovered  | discover feed |
| press | [KazTAG](https://kaztag.kz) | html | 104 KB | discover feed |

## Uzbekistan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Lex.uz](https://lex.uz) | html | 223 KB |  |
| tenders | [UZEX e-procurement](https://xarid.uzex.uz) | html | 1 KB |  |
| regulator | [Ministry of Mining and Geology](https://mmg.gov.uz) | error | ConnectError |  |
| exchange | [Tashkent Stock Exchange](https://uzse.uz) | html | 293 KB |  |
| press | [Gazeta.uz](https://www.gazeta.uz/ru/rss/) | rss | feed |  |
| press | [Kun.uz](https://kun.uz/news/rss?lang=uz) | rss | discovered  |  |
| press | [Spot.uz](https://www.spot.uz/rss) | rss | feed | business |
| press | [UzDaily](https://uzdaily.uz/en/rss) | rss | feed |  |
| press | [Daryo](https://daryo.uz/en/feed) | error | ConnectError |  |
| gazette | [President](https://president.uz/en) | html | 185 KB | discover feed |
| regulator | [Central Bank](https://cbu.uz/en/press_center/news/) | html | 209 KB |  |
| press | [Kun.uz](https://kun.uz/news/rss?lang=uz) | rss | discovered  | discover feed |
| press | [Podrobno.uz](https://podrobno.uz/rss) | rss | discovered  | discover feed |

## Kyrgyzstan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Ministry of Justice legal database](https://cbd.minjust.gov.kg) | html | 1 KB |  |
| tenders | [zakupki.gov.kg](https://zakupki.gov.kg) | html | 1 KB |  |
| press | [24.kg](https://24.kg/rss/) | rss | feed |  |
| press | [AKIpress](https://akipress.com/rss/) | rss | feed |  |
| press | [Kaktus.media](https://kaktus.media) | html | 350 KB | discover feed |
| press | [Economist.kg](https://economist.kg/rss/) | rss | discovered  | discover feed |

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
| register | [Ministry of Justice - international disputes](https://minjust.gov.ua) | html | 55 KB chrome-tls | MoJ defends Ukraine in ISDS; find the cases page |
| courts | [Unified State Register of Court Decisions](https://reyestr.court.gov.ua) | html | 44 KB | every decision, searchable |
| regulator | [NEURC energy regulator](https://www.nerc.gov.ua) | html | 808 KB |  |
| press | [Ukrinform (EN)](https://www.ukrinform.net/rss) | dead | HTTP 404 |  |
| press | [Ekonomichna Pravda](https://www.epravda.com.ua/rss/) | dead | HTTP 403 |  |
| press | [LB.ua](https://lb.ua/rss) | html | 21 KB |  |
| press | [NV](https://nv.ua/ukr/rss/all.xml) | rss | discovered  |  |
| press | [LIGA.net](https://news.liga.net/ua/all/rss.xml) | rss | discovered  | legal and business |
| press | [Sudovo-yurydychna gazeta](https://sud.ua/rss) | rss | feed | court news |
| gazette | [President](https://www.president.gov.ua/en/news/all) | dead | HTTP 403 |  |
| gazette | [Cabinet of Ministers](https://www.kmu.gov.ua/en/news) | html | 14 KB |  |
| regulator | [National Bank](https://bank.gov.ua/en/news) | html | 192 KB |  |
| regulator | [State Property Fund](https://www.spfu.gov.ua/en/news) | dead | HTTP 404 | privatisation and seizures |
| regulator | [ARMA (asset recovery)](https://arma.gov.ua/news) | html | 48 KB | seized assets |
| press | [Ukrinform](https://www.ukrinform.net) | html | 87 KB | discover feed |
| press | [LIGA.net](https://news.liga.net/ua/all/rss.xml) | rss | discovered  | discover feed |
| press | [Interfax-Ukraine](https://en.interfax.com.ua) | html | 163 KB | discover feed |
| press | [Ekonomichna Pravda](https://www.epravda.com.ua) | dead | HTTP 403 | discover feed |
| press | [Yurydychna Gazeta](https://yur-gazeta.com) | html | 48 KB insecure-tls | discover feed |

## Russia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Official publication of legal acts](http://publication.pravo.gov.ru) | html | 26 KB |  |
| courts | [Commercial courts case database (kad.arbitr)](https://kad.arbitr.ru) | html | 83 KB | anti-suit injunctions, asset seizures; search needs session |
| press | [Pravo.ru](https://pravo.ru/rss/) | rss | feed | legal news |
| press | [Kommersant](https://www.kommersant.ru/RSS/news.xml) | rss | feed |  |
| press | [Vedomosti](https://www.vedomosti.ru/rss/news) | rss | feed |  |
| press | [Interfax](https://www.interfax.ru/rss.asp) | rss | feed |  |
| press | [RBC](https://rssexport.rbc.ru/rbcnews/news/30/full.rss) | rss | feed |  |
| gazette | [Government](http://government.ru/en/news/) | html | 64 KB |  |
| regulator | [Central Bank](https://www.cbr.ru/eng/press/) | dead | HTTP 404 |  |
| press | [Zakon.ru](https://zakon.ru) | html | 0 KB | discover feed |

## Turkey

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Resmî Gazete](https://www.resmigazete.gov.tr) | html | 195 KB insecure-tls | daily official gazette |
| exchange | [KAP public disclosure platform](https://www.kap.org.tr/en) | html | 149 KB | listed companies disclose arbitrations |
| regulator | [EPDK energy regulator](https://www.epdk.gov.tr) | html | 186 KB |  |
| regulator | [MAPEG mining](https://www.mapeg.gov.tr) | html | 714 KB insecure-tls |  |
| press | [Dünya](https://www.dunya.com/rss) | rss | feed |  |
| press | [Bloomberg HT](https://www.bloomberght.com/rss) | rss | feed |  |
| press | [Hürriyet Daily News](https://www.hurriyetdailynews.com/rss) | rss | feed |  |
| press | [Daily Sabah](https://www.dailysabah.com/rssFeed/10) | rss | feed |  |
| gazette | [Presidency](https://www.tccb.gov.tr/en/) | html | 54 KB |  |
| regulator | [Central Bank](https://www.tcmb.gov.tr/wps/wcm/connect/EN/TCMB+EN/Main+Menu/Announcements) | html | 31 KB |  |
| regulator | [Competition Authority](https://www.rekabet.gov.tr/en) | html | 66 KB |  |
| press | [Ekonomim](https://www.ekonomim.com/export/rss) | rss | discovered  | discover feed |
| press | [Hürriyet](https://www.hurriyet.com.tr) | html | 244 KB | discover feed |

## Mexico

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [Secretaría de Economía ISDS register](https://www.gob.mx/se/acciones-y-programas/comercio-exterior-solucion-de-controversias-inversionista-estado) | dead | HTTP 404 | publishes notices of intent; bot challenge |
| gazette | [Diario Oficial de la Federación](https://www.dof.gob.mx/rss) | dead | HTTP 404 |  |
| tenders | [CompraNet](https://compranet.hacienda.gob.mx) | error | ConnectError |  |
| regulator | [CNH hydrocarbons](https://www.gob.mx/cnh) | html | 46 KB chrome-tls |  |
| exchange | [BMV](https://www.bmv.com.mx) | error | ConnectTimeout |  |
| press | [El Economista](https://www.eleconomista.com.mx/rss/) | dead | HTTP 403 |  |
| press | [Expansión](https://expansion.mx/rss) | rss | feed |  |
| press | [El Financiero](https://www.elfinanciero.com.mx/rss) | rss | feed |  |
| press | [El Universal](https://www.eluniversal.com.mx/arc/outboundfeeds/rss/) | rss | discovered  |  |
| gazette | [DOF (main)](https://www.dof.gob.mx) | html | 66 KB insecure-tls | discover feed |
| regulator | [CRE energy regulator](https://www.gob.mx/cre) | html | 49 KB chrome-tls |  |
| regulator | [Secretaría de Economía (main)](https://www.gob.mx/se) | html | 48 KB chrome-tls | JS challenge |
| press | [El Universal](https://www.eluniversal.com.mx/arc/outboundfeeds/rss/) | rss | discovered  | discover feed |
| press | [Reforma](https://www.reforma.com/rss/portada.xml) | rss | discovered  | discover feed |
| press | [Milenio](https://www.milenio.com) | dead | HTTP 403 | discover feed |
| press | [Forbes México](https://www.forbes.com.mx) | html | 248 KB | discover feed |

## Argentina

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [Procuración del Tesoro de la Nación](https://www.argentina.gob.ar/procuraciondeltesoro) | html | 42 KB | defends Argentina; check for a cases page |
| gazette | [Boletín Oficial](https://www.boletinoficial.gob.ar) | html | 239 KB | RSS available |
| tenders | [COMPR.AR](https://comprar.gob.ar) | html | 78 KB |  |
| press | [La Nación](https://www.lanacion.com.ar/arc/outboundfeeds/rss/) | rss | feed |  |
| press | [Clarín](https://www.clarin.com/rss/) | rss | feed |  |
| press | [Ámbito](https://www.ambito.com/rss) | dead | HTTP 403 |  |
| press | [El Cronista](https://www.cronista.com/arc/outboundfeeds/rss/) | rss | discovered  |  |
| press | [Infobae](https://www.infobae.com/arc/outboundfeeds/rss/category/america/mundo/) | rss | discovered  |  |
| press | [Infobae](https://www.infobae.com/arc/outboundfeeds/rss/category/america/mundo/) | rss | discovered  | discover feed |
| press | [iProfesional](https://www.iprofesional.com/rss/home) | rss | discovered  | discover feed |
| press | [Página/12](https://www.pagina12.com.ar/arc/outboundfeeds/rss/) | rss | discovered  | discover feed |
| regulator | [ENARGAS](https://www.enargas.gob.ar) | html | 35 KB |  |
| exchange | [CNV](https://www.argentina.gob.ar/cnv) | html | 49 KB |  |

## Colombia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [ANDJE - defensa internacional](https://www.defensajuridica.gov.co) | dead | HTTP 403 | publishes ISDS cases; WAF 403 to scripts |
| tenders | [SECOP / Colombia Compra](https://www.colombiacompra.gov.co) | html | 589 KB |  |
| regulator | [ANM mining](https://www.anm.gov.co) | html | 319 KB |  |
| regulator | [ANH hydrocarbons](https://www.anh.gov.co) | html | 71 KB |  |
| courts | [Consejo de Estado](https://www.consejodeestado.gov.co) | html | 270 KB |  |
| press | [Portafolio](https://www.portafolio.co/rss) | html | 91 KB |  |
| press | [La República](https://www.larepublica.co/rss) | rss | feed |  |
| press | [Semana](https://www.semana.com/arc/outboundfeeds/rss/) | rss | discovered  |  |
| press | [Valora Analitik](https://www.valoraanalitik.com/feed/) | dead | HTTP 403 |  |
| press | [Semana](https://www.semana.com/arc/outboundfeeds/rss/) | rss | discovered  | discover feed |
| press | [El Tiempo](https://www.eltiempo.com) | html | 853 KB | discover feed |
| press | [El Espectador](https://www.elespectador.com/feed/) | rss | discovered  | discover feed |
| gazette | [Presidencia](https://www.presidencia.gov.co) | html | 5 KB |  |
| regulator | [Superintendencia Financiera](https://www.superfinanciera.gov.co) | html | 239 KB |  |

## Peru

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [MEF - SICRECI (State coordination for investment disputes)](https://www.mef.gob.pe) | html | 0 KB | find the cases page |
| gazette | [El Peruano](https://elperuano.pe) | html | 82 KB |  |
| tenders | [SEACE](https://www.gob.pe/seace) | dead | HTTP 404 |  |
| regulator | [Osinergmin](https://www.osinergmin.gob.pe) | html | 0 KB |  |
| press | [Gestión](https://gestion.pe/arcio/rss/) | rss | discovered  |  |
| press | [El Comercio](https://elcomercio.pe/arcio/rss/) | rss | discovered  |  |
| press | [RPP](https://rpp.pe/rss) | rss | feed |  |
| press | [Semana Económica](https://semanaeconomica.com/feed) | rss | discovered  | discover feed |
| press | [La República](https://larepublica.pe/rss.xml) | rss | discovered  | discover feed |
| regulator | [INGEMMET](https://www.gob.pe/ingemmet) | html | 248 KB | mining concessions |
| regulator | [Perupetro](https://www.perupetro.com.pe) | html | 0 KB insecure-tls |  |

## Chile

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| tenders | [Mercado Público](https://www.mercadopublico.cl) | html | 0 KB |  |
| press | [Diario Financiero](https://www.df.cl/rss) | dead | HTTP 404 |  |
| press | [El Mercurio (Emol)](https://www.emol.com/rss/) | error | ReadError |  |
| press | [Diario Financiero](https://www.df.cl) | html | 542 KB | discover feed |
| press | [La Tercera](https://www.latercera.com/rss) | rss | discovered  | discover feed |
| press | [El Mostrador](https://www.elmostrador.cl) | html | 216 KB | discover feed |
| regulator | [SERNAGEOMIN](https://www.sernageomin.cl) | html | 150 KB insecure-tls | mining |

## Ecuador

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [Procuraduría General del Estado](https://www.pge.gob.ec) | html | 80 KB | publishes arbitration cases against Ecuador |
| gazette | [Registro Oficial](https://www.registroficial.gob.ec) | html | 182 KB |  |
| press | [El Universo](https://www.eluniverso.com/arc/outboundfeeds/rss/?outputType=xml) | rss | discovered  |  |
| press | [Primicias](https://www.primicias.ec/rss/latest) | rss | discovered  |  |
| press | [Expreso](https://www.expreso.ec/rss/home.xml) | rss | discovered  | discover feed |
| regulator | [ARCERNNR](https://www.controlrecursosyenergia.gob.ec) | html | 4 KB insecure-tls | mining and energy licences |

## Venezuela

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Efecto Cocuyo](https://efectococuyo.com/feed/) | rss | feed |  |
| press | [Banca y Negocios](https://www.bancaynegocios.com/feed/) | error | RemoteProtocol |  |
| press | [El Nacional](https://www.elnacional.com/feed/) | rss | feed |  |
| press | [Petroguía](https://www.petroguia.com) | error | ConnectTimeout | discover feed |

## Bolivia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [El Deber](https://eldeber.com.bo/feed) | rss | discovered  |  |
| press | [Los Tiempos](https://www.lostiempos.com) | html | 226 KB | discover feed |

## Brazil

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Diário Oficial da União](https://www.in.gov.br) | error | RemoteProtocol |  |
| press | [Valor Econômico](https://valor.globo.com/rss/valor) | rss | discovered  |  |
| press | [JOTA](https://www.jota.info/feed) | rss | feed | legal |
| press | [Folha - Mercado](https://feeds.folha.uol.com.br/mercado/rss091.xml) | rss | feed |  |
| press | [Valor Econômico](https://valor.globo.com/rss/valor) | rss | discovered  | discover feed |
| press | [Estadão](https://www.estadao.com.br/arc/outboundfeeds/feeds/rss/sections/geral/?body=%7B%22layout%22:%22google-news%22%7D) | rss | discovered  | discover feed |
| exchange | [CVM](https://www.gov.br/cvm) | html | 224 KB |  |
| regulator | [ANP](https://www.gov.br/anp) | html | 328 KB | oil and gas |
| regulator | [ANM](https://www.gov.br/anm) | html | 321 KB | mining |

## Spain

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [BOE](https://www.boe.es/rss/canal.php?c=ultimos) | html | 0 KB | official gazette |
| exchange | [CNMV](https://www.cnmv.es) | html | 289 KB | hechos relevantes |
| tenders | [PLACSP](https://contrataciondelestado.es) | html | 0 KB |  |
| press | [Expansión](https://e00-expansion.uecdn.es/rss/portada.xml) | rss | feed |  |
| press | [El Confidencial](https://rss.elconfidencial.com/espana/) | rss | feed |  |
| press | [Cinco Días](https://feeds.elpais.com/mrss-s/pages/ep/site/cincodias.elpais.com/portada) | rss | discovered  |  |
| press | [El Economista](https://www.eleconomista.es/rss/rss-empresas.php) | rss | feed chrome-tls |  |
| press | [Cinco Días](https://feeds.elpais.com/mrss-s/pages/ep/site/cincodias.elpais.com/portada) | rss | discovered  | discover feed |
| press | [Vozpópuli](https://www.vozpopuli.com) | html | 321 KB | discover feed |
| register | [Abogacía General del Estado](https://www.mjusticia.gob.es/es/ministerio/organismos-entidades/abogacia-general) | dead | HTTP 404 | defends Spain in ISDS |

## Italy

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [Gazzetta Ufficiale](https://www.gazzettaufficiale.it) | html | 41 KB |  |
| press | [Il Sole 24 Ore](https://www.ilsole24ore.com/rss/italia.xml) | rss | feed |  |
| press | [Milano Finanza](https://www.milanofinanza.it) | html | 243 KB | discover feed |
| register | [Avvocatura dello Stato](https://www.avvocaturastato.it) | dead | HTTP 403 |  |

## Romania

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Ziarul Financiar](https://www.zf.ro/rss) | rss | feed |  |
| press | [Profit.ro](https://www.profit.ro/rss) | rss | feed |  |
| press | [Economica.net](https://www.economica.net/feed) | rss | discovered  | discover feed |
| register | [Ministry of Finance](https://mfinante.gov.ro) | html | 328 KB | defends Romania in ISDS |

## Poland

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Puls Biznesu](https://www.pb.pl/rss) | html | 70 KB |  |
| press | [Rzeczpospolita](https://www.rp.pl/rss_main) | rss | feed |  |
| register | [Prokuratoria Generalna](https://www.gov.pl/web/prokuratoria) | html | 28 KB | defends Poland in ISDS |

## Nigeria

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| tenders | [Bureau of Public Procurement](https://www.bpp.gov.ng) | html | 179 KB |  |
| regulator | [NUPRC upstream regulator](https://www.nuprc.gov.ng) | html | 73 KB |  |
| regulator | [Mining Cadastre Office](https://miningcadastre.gov.ng) | html | 135 KB |  |
| exchange | [NGX](https://ngxgroup.com) | html | 63 KB |  |
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
| press | [Business Daily](https://www.businessdailyafrica.com/bd/rss.xml) | rss | discovered  |  |
| press | [The Star](https://www.the-star.co.ke/rss) | dead | HTTP 404 |  |
| press | [Business Daily](https://www.businessdailyafrica.com/bd/rss.xml) | rss | discovered  | discover feed |
| press | [The Star](https://www.the-star.co.ke) | html | 350 KB | discover feed |
| press | [Nation](https://nation.africa/kenya/rss.xml) | rss | discovered  | discover feed |

## Tanzania

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| regulator | [Mining Commission](https://www.tumemadini.go.tz) | html | 81 KB insecure-tls |  |
| press | [The Citizen](https://www.thecitizen.co.tz/rss.xml) | rss | discovered  |  |
| press | [The Citizen](https://www.thecitizen.co.tz/rss.xml) | rss | discovered  | discover feed |

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
| exchange | [JSE SENS](https://www.jse.co.za) | html | 227 KB chrome-tls |  |
| press | [Business Day](https://www.businesslive.co.za/arc/outboundfeeds/rss/) | rss | discovered  |  |
| press | [Moneyweb](https://www.moneyweb.co.za/feed/) | rss | feed |  |
| press | [Business Day](https://www.businesslive.co.za/arc/outboundfeeds/rss/) | rss | discovered  | discover feed |
| press | [Daily Maverick](https://www.dailymaverick.co.za/rss) | rss | discovered  | discover feed |
| regulator | [DMRE](https://www.dmre.gov.za) | error | ConnectTimeout | mining rights |

## Mozambique

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Club of Mozambique](https://clubofmozambique.com/feed/) | rss | feed |  |

## Egypt

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| exchange | [Egyptian Exchange](https://www.egx.com.eg) | html | 6 KB |  |
| press | [Enterprise](https://enterpriseam.com/egypt/feed/) | rss | discovered  | the best daily on Egyptian business |
| press | [Ahram Online](https://english.ahram.org.eg/rss) | dead | HTTP 404 |  |
| press | [Daily News Egypt](https://www.dailynewsegypt.com/feed/) | rss | feed |  |
| press | [Ahram Online](https://english.ahram.org.eg) | html | 158 KB chrome-tls | discover feed |
| press | [Mada Masr](https://www.madamasr.com/rss) | rss | discovered  | discover feed |
| regulator | [GAFI](https://www.gafi.gov.eg) | html | 1011 KB | investment authority |

## Algeria

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [APS](https://www.aps.dz/en/?format=feed) | html | 229 KB |  |
| press | [TSA](https://www.tsa-algerie.com/feed/) | rss | discovered  | discover feed |

## Morocco

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Médias24](https://medias24.com/feed/) | dead | HTTP 403 |  |
| press | [Le360](https://fr.le360.ma) | html | 1594 KB | discover feed |
| press | [L'Economiste](https://www.leconomiste.com) | dead | HTTP 403 | discover feed |

## UAE

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The National](https://www.thenationalnews.com/rss) | dead | HTTP 404 |  |
| press | [The National](https://www.thenationalnews.com) | html | 1780 KB | discover feed |
| press | [Gulf News](https://gulfnews.com/feed) | rss | discovered  | discover feed |

## Saudi Arabia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Arab News](https://www.arabnews.com/rss) | rss | discovered chrome-tls |  |
| press | [Argaam](https://www.argaam.com/en) | html | 1275 KB | discover feed |

## Qatar

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The Peninsula](https://thepeninsulaqatar.com/rss) | html | 90 KB |  |
| press | [Gulf Times](https://www.gulf-times.com) | html | 181 KB | discover feed |

## Iraq

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Iraq Business News](https://www.iraq-businessnews.com/feed/) | rss | feed |  |
| press | [Rudaw](https://www.rudaw.net/english) | html | 594 KB | discover feed |

## India

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| gazette | [eGazette](https://egazette.gov.in) | html | 66 KB insecure-tls |  |
| exchange | [BSE corporate announcements](https://www.bseindia.com/corporates/ann.html) | html | 13 KB | arbitration disclosures; has an API |
| press | [Economic Times](https://economictimes.indiatimes.com/rssfeedsdefault.cms) | rss | feed |  |
| press | [Mint](https://www.livemint.com/rss/companies) | rss | feed |  |
| press | [Bar & Bench](https://www.barandbench.com/feed) | rss | feed | legal |
| press | [LiveLaw](https://www.livelaw.in/google_feeds.xml) | rss | discovered  | legal |
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
| exchange | [IDX](https://www.idx.co.id) | dead | HTTP 403 |  |
| press | [Kontan](https://www.kontan.co.id/rss) | html | 39 KB |  |
| press | [Bisnis.com](https://www.bisnis.com/rss) | dead | HTTP 404 |  |
| press | [Hukumonline](https://www.hukumonline.com/rss) | dead | HTTP 404 | legal |
| press | [Jakarta Post](https://www.thejakartapost.com/rss) | dead | HTTP 404 |  |
| press | [Bisnis.com](https://www.bisnis.com) | html | 382 KB | discover feed |
| press | [Hukumonline](https://www.hukumonline.com) | html | 589 KB | discover feed |
| press | [The Jakarta Post](https://www.thejakartapost.com) | html | 153 KB | discover feed |
| press | [Katadata](https://katadata.co.id/rss) | rss | discovered  | discover feed |

## Vietnam

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [VnExpress International](https://e.vnexpress.net/rss/business.rss) | rss | feed |  |
| press | [VietnamNet](https://vietnamnet.vn/en) | html | 98 KB | discover feed |

## Malaysia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The Edge](https://theedgemalaysia.com/rss) | dead | HTTP 404 |  |
| press | [The Edge Malaysia](https://theedgemalaysia.com) | html | 248 KB | discover feed |
| press | [The Star](https://www.thestar.com.my) | html | 301 KB | discover feed |

## Philippines

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [BusinessWorld](https://www.bworldonline.com/feed/) | rss | feed |  |
| press | [Inquirer Business](https://business.inquirer.net/rss) | rss | discovered chrome-tls | discover feed |

## Korea

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Korea Economic Daily](https://www.kedglobal.com/rss) | rss | feed |  |
| press | [Korea JoongAng Daily](https://koreajoongangdaily.joins.com/rss) | dead | HTTP 404 |  |
| press | [Korea JoongAng Daily](https://koreajoongangdaily.joins.com) | html | 354 KB | discover feed |
| press | [The Korea Herald](https://www.koreaherald.com/rss/newsAll) | rss | discovered  | discover feed |
| register | [Ministry of Justice ISDS](https://www.moj.go.kr/moj_eng/1746/subview.do) | html | 6 KB | Korea publishes its ISDS cases |

## Global

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [ICSID docket API](https://icsid.worldbank.org/api/cases/pending) | wired |  |  |
| register | [UNCITRAL Transparency Registry](https://www.uncitral.org/transparency-registry/registry/index.jspx) | html | 73 KB | notices under the Mauritius Convention |
| register | [PCA cases](https://pca-cpa.org/en/cases/) | html | 129 KB | client-rendered |
| register | [italaw](https://www.italaw.com) | dead | HTTP 403 | awards and decisions; Cloudflare |
| register | [UNCTAD ISDS Navigator](https://investmentpolicy.unctad.org/investment-dispute-settlement) | dead | HTTP 403 | Cloudflare |
| courts | [CourtListener / RECAP](https://www.courtlistener.com/api/rest/v4/search/) | wired |  |  |
| exchange | [SEC EDGAR full-text](https://efts.sec.gov/LATEST/search-index) | wired |  |  |
| tenders | [TED](https://api.ted.europa.eu/v3/notices/search) | wired |  |  |
| exchange | [LSE RNS](https://www.londonstockexchange.com/news) | html | 53 KB | no keyword feed |
| exchange | [ASX announcements](https://www.asx.com.au/markets/trade-our-cash-market/announcements) | html | 133 KB | per-company only |
| exchange | [SEDAR+](https://www.sedarplus.ca) | html | 15 KB chrome-tls | Canadian filings; client-rendered |
| press | [GAR](https://globalarbitrationreview.com/rss) | wired |  |  |
| press | [IAReporter](https://www.iareporter.com/feed/) | wired |  |  |
| press | [Law360 International Arbitration](https://www.law360.com/internationalarbitration/rss) | rss | feed | paywalled headlines |
| press | [Lexology arbitration](https://www.lexology.com/rss) | dead | HTTP 404 |  |
| press | [Omni Bridgeway news](https://omnibridgeway.com/news) | html | 23 KB | funder |
| press | [Litigation Capital Management](https://www.lcmfinance.com/rss) | rss | discovered  | funder |
| press | [ICC news](https://iccwbo.org/feed/) | rss | feed | institution |
| press | [LCIA news](https://www.lcia.org/News/news.aspx) | html | 76 KB | institution |
| press | [VIAC news](https://www.viac.eu/feed/) | rss | discovered  | institution |
| press | [DIS news](https://www.disarb.org/en/news) | dead | HTTP 403 | institution |
| press | [CRCICA news](https://crcica.org/feed/) | rss | discovered  | institution |
| press | [CIETAC news](http://www.cietac.org/index.php?m=Article&a=index&id=1&l=en) | dead | HTTP 404 | institution |
| press | [KCAB International](http://www.kcabinternational.or.kr/rss.xml) | rss | discovered chrome-tls | institution |
| press | [JCAA news](https://www.jcaa.or.jp/en/news/) | dead | HTTP 423 | institution |
| press | [DIAC news](https://www.diac.com/en/feed) | rss | discovered  | institution |
| press | [ISTAC news](https://istac.org.tr/rss) | rss | discovered  | institution |
| press | [Russian Arbitration Center](https://centerarbitr.ru/rss) | rss | discovered  | institution |
| press | [CAM Santiago](https://www.camsantiago.cl/noticias/) | dead | HTTP 403 | institution |
| press | [CAM-CCBC](https://www.ccbc.org.br/feed/) | rss | discovered  | institution |
| press | [AAA-ICDR news](https://www.adr.org/news) | html | 431 KB | institution |
| press | [Energy Charter Secretariat](https://www.energycharter.org/media/news/) | dead | HTTP 404 | treaty body; case statistics |
| press | [UNCITRAL news](https://uncitral.un.org/en/news) | html | 109 KB |  |
| press | [EFILA blog](https://efilablog.org/feed/) | dead | HTTP 404 | investment law |
| press | [Global Legal Chronicle](https://www.globallegalchronicle.com/feed/) | rss | feed | deals and cases with counsel named |
| press | [CDR News](https://www.cdr-news.com/rss) | rss | feed | disputes press |
| press | [Global Legal Post](https://www.globallegalpost.com/rss) | rss | feed |  |
| press | [Legal Business](https://www.legalbusiness.co.uk/feed/) | rss | feed |  |
| press | [The Lawyer](https://www.thelawyer.com/feed/) | rss | feed |  |
| press | [Asian Legal Business](http://www.legalbusinessonline.com/rss.xml) | rss | discovered  |  |
| press | [Latin Lawyer](https://latinlawyer.com/rss) | rss | feed | GAR's sister title |
| press | [Africa Legal](https://www.africa-legal.com/rss) | dead | HTTP 404 |  |
| press | [JD Supra - arbitration](https://www.jdsupra.com/rss/arbitration/) | dead | HTTP 404 |  |
| press | [Mondaq - arbitration](https://www.mondaq.com/rss/arbitration-dispute-resolution) | dead | HTTP 404 |  |
| press | [Pinsent Masons Out-Law](https://www.pinsentmasons.com/out-law/news/rss) | dead | HTTP 404 |  |
| courts | [England - Find Case Law (Commercial Court Atom)](https://caselaw.nationalarchives.gov.uk/atom.xml?court=ewhc%2Fcomm&order=-date) | rss | feed | s.67/68/69 challenges, enforcement |
| courts | [England - judiciary.uk judgments](https://www.judiciary.uk/feed/) | rss | feed |  |
| courts | [Netherlands - rechtspraak open data](https://data.rechtspraak.nl/uitspraken/zoeken?q=arbitrage&max=20) | rss | feed | open API; Hague set-aside cases |
| courts | [Switzerland - Federal Supreme Court](https://www.bger.ch/ext/eurospider/live/de/php/aza/http/index.php?lang=de&type=simple_query&query_words=4A_) | html | 0 KB insecure-tls | every award challenge in Switzerland |
| courts | [France - Cour de cassation news](https://www.courdecassation.fr/en/actualites) | html | 0 KB |  |
| courts | [Singapore - SICC judgments](https://www.sicc.gov.sg/hearings-judgments/judgments) | html | 234 KB |  |
| courts | [Singapore - eLitigation judgments](https://www.elitigation.sg/gd/Home/Index) | html | 50 KB |  |
| courts | [Hong Kong - judiciary legal reference](https://legalref.judiciary.hk/lrs/common/ju/judgment.jsp) | html | 57 KB |  |
| courts | [India - Supreme Court (Indian Kanoon feed)](https://indiankanoon.org/feeds/latest/supremecourt/) | dead | HTTP 403 |  |
| courts | [India - Delhi High Court (Indian Kanoon feed)](https://indiankanoon.org/feeds/latest/delhi/) | dead | HTTP 403 | s.34/s.48 arbitration matters |
| courts | [Australia - Federal Court (AustLII feed)](https://www.austlii.edu.au/rss/au/cases/cth/FCA.xml) | dead | HTTP 403 |  |
| courts | [Canada - Ontario Court of Appeal (CanLII feed)](https://www.canlii.org/en/on/onca/rss_new.xml) | rss | feed |  |
| courts | [Germany - BGH press](https://www.bundesgerichtshof.de/SiteGlobals/Functions/RSSFeed/DE/RSSNewsfeed/RSSNewsfeed.xml) | dead | HTTP 404 |  |
| courts | [Ireland - judgments](https://www.courts.ie/judgments) | html | 137 KB |  |
| courts | [Kenya Law - judgments](https://new.kenyalaw.org/judgments/) | html | 45 KB |  |
| press | [Omni Bridgeway - ASX announcements](https://omnibridgeway.com/investors/asx-announcements) | html | 23 KB | funder; funded claims disclosed |
| press | [LCM - RNS](https://www.lcmfinance.com/rss) | rss | discovered  | funder |
| press | [Therium news](https://therium.com/?feed=rss2) | rss | discovered  | funder |
| press | [Harbour news](https://www.harbourlitigationfunding.com/harbour-is-the-largest-privately-owned-litigation-funder/feed/) | rss | discovered chrome-tls | funder |
| press | [Nivalion news](https://nivalion.com/en/feed/) | rss | discovered  | funder |
| press | [Deminor news](https://www.deminor.com/en/news/) | html | 168 KB | funder |
| press | [White & Case news](https://www.whitecase.com/news) | html | 282 KB chrome-tls | firm |
| press | [Freshfields](https://www.freshfields.com/en/our-thinking/) | html | 540 KB | firm |
| press | [Debevoise insights](https://www.debevoise.com/insights) | html | 38 KB | firm |
| press | [King & Spalding news](https://www.kslaw.com/news-and-insights) | html | 255 KB | firm |
| press | [Curtis news](https://www.curtis.com/news) | html | 157 KB | firm |
| press | [Foley Hoag news](https://foleyhoag.com/rss) | rss | discovered  | firm |
| press | [Volterra Fietta news](https://www.volterrafietta.com/rss) | rss | discovered  | firm |
| press | [Withers insight](https://www.withersworldwide.com/en-gb/insight) | html | 148 KB | firm |
| press | [Hogan Lovells news](https://www.hoganlovells.com/en/news) | html | 130 KB | firm |
| press | [Latham news](https://www.lw.com/en/news) | html | 88 KB | firm |
| press | [Sidley news](https://www.sidley.com/en/newslanding) | html | 201 KB | firm |
| press | [Arnold & Porter news](https://www.arnoldporter.com/rss/news) | rss | discovered  | firm |
| press | [Quinn Emanuel news](https://www.quinnemanuel.com/the-firm/news-events/) | html | 61 KB | firm |
| press | [Boies Schiller news](https://www.bsfllp.com/news) | html | 63 KB | firm |
| press | [HSF Kramer](https://www.hsfkramer.com/notes) | dead | HTTP 403 | firm |
| press | [Clifford Chance news](https://www.cliffordchance.com/rss.xml) | rss | discovered  | firm |
| press | [A&O Shearman news](https://www.aoshearman.com/en/news) | html | 333 KB | firm |
| press | [Dechert](https://www.dechert.com/knowledge.html) | html | 73 KB | firm |
| press | [Jones Day news](https://www.jonesday.com/en/news) | html | 89 KB | firm |
| press | [Baker McKenzie newsroom](https://www.bakermckenzie.com/en/newsroom) | html | 170 KB | firm |
| press | [DLA Piper news](https://www.dlapiper.com/en/news) | html | 134 KB | firm |
| press | [Norton Rose Fulbright news](https://www.nortonrosefulbright.com/en/news) | html | 116 KB | firm |
| press | [Mayer Brown news](https://www.mayerbrown.com/en/news) | html | 131 KB | firm |
| press | [Steptoe news](https://www.steptoe.com/en/news-publications) | dead | HTTP 404 | firm |
| press | [Gibson Dunn news](https://www.gibsondunn.com/feed/) | rss | discovered chrome-tls | firm |
| press | [Cleary news](https://www.clearygottlieb.com/news-and-insights) | html | 115 KB | firm |
| press | [WilmerHale insights](https://www.wilmerhale.com/en/insights) | html | 46 KB | firm |
| press | [Lalive news](https://www.lalive.law/rss) | rss | discovered  | firm |
| press | [Derains & Gharavi](https://www.derainsgharavi.com/feed/) | rss | discovered  | firm |
| press | [Chaffetz Lindsey](https://www.chaffetzlindsey.com/rss) | rss | discovered  | firm |
| press | [Uría Menéndez news](https://www.uria.com/rss/all) | rss | discovered  | firm |
| press | [Garrigues news](https://www.garrigues.com/rss.xml) | rss | discovered  | firm |
| press | [Sayenko Kharenko news](https://sk.ua/rss) | rss | discovered  | firm, Ukraine |
| press | [Asters news](https://asters.com/news/) | html | 12 KB insecure-tls | firm, Ukraine |
| press | [GRATA International news](https://gratanet.com/news) | html | 362 KB | firm, Central Asia |
| press | [AEQUO news](https://aequo.ua/news) | html | 260 KB | firm, Ukraine |
| exchange | [GlobeNewswire - ICSID](https://www.globenewswire.com/RssFeed/keyword/ICSID) | error | ReadTimeout | keyword feed |
| exchange | [GlobeNewswire - investment treaty](https://www.globenewswire.com/RssFeed/keyword/investment%20treaty) | error | ReadTimeout | keyword feed |
| exchange | [GlobeNewswire - notice of arbitration](https://www.globenewswire.com/RssFeed/keyword/notice%20of%20arbitration) | error | ReadTimeout | keyword feed |
| exchange | [GlobeNewswire - arbitration award](https://www.globenewswire.com/RssFeed/keyword/arbitration%20award) | error | ReadTimeout | keyword feed |
| exchange | [GlobeNewswire - expropriation](https://www.globenewswire.com/RssFeed/keyword/expropriation) | error | ReadTimeout | keyword feed |
| exchange | [Newsfile (Canadian juniors)](https://www.newsfilecorp.com/newsroom/rss) | dead | HTTP 404 |  |
| exchange | [ACCESSWIRE](https://www.accesswire.com/rss/newsroom) | dead | HTTP 404 |  |
| exchange | [Business Wire - legal](https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeGVpRXg==) | rss | feed |  |
| exchange | [Investegate (LSE RNS)](https://www.investegate.co.uk/rss.aspx) | html | 106 KB |  |
| exchange | [TSX - Market Activity](https://www.tsx.com/news) | html | 100 KB |  |
| register | [EBRD news](https://www.ebrd.com/news.html) | html | 148 KB | project disputes |
| register | [IFC disclosures](https://disclosures.ifc.org) | html | 76 KB |  |
| register | [MIGA news](https://www.miga.org/news) | dead | HTTP 404 | political risk claims |
| register | [OECD investment news](https://www.oecd.org/en/topics/investment.html) | dead | HTTP 403 |  |

## Tajikistan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Asia-Plus](https://asiaplus.news/feed/) | rss | discovered  | discover feed |

## Mongolia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Montsame](https://montsame.mn/en) | html | 242 KB | discover feed |
| regulator | [Mineral Resources and Petroleum Authority](https://mrpam.gov.mn) | html | 213 KB |  |

## Moldova

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [IPN](https://ipn.md/feed/) | rss | discovered  | discover feed |

## Belarus

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [BelTA](https://eng.belta.by) | html | 129 KB | discover feed |

## Hungary

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Portfolio.hu](https://www.portfolio.hu/rss/all.xml) | rss | discovered  | discover feed |

## Czechia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Hospodářské noviny](https://hn.cz/?m=rss) | rss | discovered  | discover feed |
| register | [Ministry of Finance - arbitration](https://www.mfcr.cz/en/) | html | 103 KB | publishes ISDS cases |

## Slovakia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Denník N](https://dennikn.sk/rss) | rss | discovered  | discover feed |

## Croatia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Jutarnji list](https://www.jutarnji.hr/feed) | rss | discovered  | discover feed |

## Slovenia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [STA](https://english.sta.si) | dead | HTTP 403 | discover feed |

## Serbia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [N1](https://n1info.rs/feed) | rss | discovered  | discover feed |

## Bosnia and Herzegovina

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Klix](https://www.klix.ba) | dead | HTTP 403 | discover feed |

## Montenegro

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Vijesti](https://www.vijesti.me/rss) | rss | discovered  | discover feed |

## North Macedonia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [MIA](https://mia.mk/feed) | rss | discovered  | discover feed |

## Albania

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Albanian Daily News](https://albaniandailynews.com) | html | 68 KB | discover feed |

## Bulgaria

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Novinite](https://www.novinite.com/services/news_rdf.php) | rss | discovered  | discover feed |

## Greece

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Kathimerini](https://www.ekathimerini.com) | html | 577 KB | discover feed |

## Cyprus

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Cyprus Mail](https://cyprus-mail.com/feed) | rss | discovered  | discover feed |

## Latvia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [LSM](https://eng.lsm.lv/rss) | rss | discovered  | discover feed |

## Lithuania

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [LRT](https://www.lrt.lt/?rss) | rss | discovered  | discover feed |

## Estonia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [ERR](https://news.err.ee/rss) | rss | discovered  | discover feed |

## Germany

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Handelsblatt](https://www.handelsblatt.com) | html | 1968 KB | discover feed |
| press | [JUVE](https://www.juve.de/rss) | rss | discovered  | legal press; discover feed |

## France

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Les Echos](https://www.lesechos.fr) | dead | HTTP 403 | discover feed |
| press | [Décideurs Juridiques](https://www.decideurs-juridiques.com/juridiques.feed?type=rss) | rss | discovered  | discover feed |

## Netherlands

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Het Financieele Dagblad](https://fd.nl/?rss) | rss | discovered  | discover feed |

## Switzerland

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [NZZ](https://www.nzz.ch) | html | 967 KB | discover feed |

## United Kingdom

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Financial Times - law](https://www.ft.com/rss/home/international) | rss | discovered  | discover feed |
| press | [Law Gazette](https://www.lawgazette.co.uk/13505.rss) | rss | discovered  | discover feed |

## Israel

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Globes](https://en.globes.co.il/WebService/Rss/RssFeeder.asmx/FeederNode?iID=942) | rss | discovered  | discover feed |

## Jordan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Jordan Times](https://jordantimes.com) | dead | HTTP 403 | discover feed |

## Lebanon

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [L'Orient Today](https://today.lorientlejour.com) | html | 114 KB | discover feed |

## Kuwait

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Kuwait Times](https://www.kuwaittimes.com) | html | 284 KB | discover feed |

## Oman

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Times of Oman](https://timesofoman.com/feed/) | rss | discovered  | discover feed |

## Bahrain

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Gulf Daily News](https://www.gdnonline.com) | html | 689 KB | discover feed |

## Libya

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Libya Observer](https://libyaobserver.ly) | html | 150 KB | discover feed |

## Tunisia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [TAP](https://www.tap.info.tn/en) | html | 95 KB insecure-tls | discover feed |

## Ethiopia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Addis Standard](https://addisstandard.com) | dead | HTTP 403 | discover feed |

## Uganda

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Daily Monitor](https://www.monitor.co.ug/rss.xml) | rss | discovered  | discover feed |

## Rwanda

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The New Times](https://www.newtimes.co.rw) | html | 201 KB | discover feed |

## Zimbabwe

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [NewsDay](https://newsday.co.zw/feed/) | rss | discovered  | discover feed |
| press | [The Herald](https://www.heraldonline.co.zw/feed/) | rss | discovered  | discover feed |

## Namibia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The Namibian](https://www.namibian.com.na/feed/) | rss | discovered  | discover feed |

## Botswana

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Mmegi](https://www.mmegi.bw) | html | 358 KB | discover feed |

## Madagascar

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [L'Express de Madagascar](https://www.lexpress.mg/feeds/posts/default) | rss | discovered  | discover feed |

## Guinea

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Guinéenews](https://guineenews.org/feed/) | rss | discovered  | discover feed |

## Mali

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Maliweb](https://www.maliweb.net) | html | 240 KB | discover feed |

## Burkina Faso

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Lefaso.net](https://lefaso.net/spip.php?page=backend) | rss | discovered  | discover feed |

## Niger

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [ActuNiger](https://www.actuniger.com) | html | 259 KB | discover feed |

## Côte d'Ivoire

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Abidjan.net](https://news.abidjan.net) | html | 396 KB | discover feed |

## Cameroon

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Journal du Cameroun](https://www.journalducameroun.com) | error | ConnectTimeout | discover feed |
| press | [Investir au Cameroun](https://www.investiraucameroun.com/index.php/component/obrss/fullrss) | rss | discovered  | discover feed |

## Gabon

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Gabonreview](https://www.gabonreview.com/feed) | rss | discovered  | discover feed |

## Angola

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Angop](https://www.angop.ao/en) | html | 249 KB | discover feed |

## Senegal

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [APS](https://aps.sn/feed/) | rss | discovered  | discover feed |

## Bangladesh

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The Daily Star](https://www.thedailystar.net/rss.xml) | rss | discovered  | discover feed |

## Sri Lanka

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Daily FT](https://www.ft.lk) | html | 265 KB chrome-tls | discover feed |

## Nepal

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Kathmandu Post](https://kathmandupost.com/rss) | rss | discovered  | discover feed |

## Thailand

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Bangkok Post](https://www.bangkokpost.com) | html | 197 KB | discover feed |

## Cambodia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Khmer Times](https://www.khmertimeskh.com/feed/) | rss | discovered  | discover feed |

## Japan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Nikkei Asia](https://asia.nikkei.com) | html | 595 KB | discover feed |

## China

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Caixin Global](https://www.caixinglobal.com) | html | 93 KB | discover feed |

## Taiwan

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Focus Taiwan](https://focustaiwan.tw) | html | 99 KB | discover feed |

## Papua New Guinea

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Post-Courier](https://www.postcourier.com.pg/feed/) | rss | discovered  | discover feed |

## Australia

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| register | [DFAT - ISDS](https://www.dfat.gov.au/trade/investment/investor-state-dispute-settlement) | error | ReadTimeout | cases against Australia |
| press | [AFR](https://www.afr.com) | html | 1171 KB | discover feed |
| press | [Lawyerly](https://www.lawyerly.com.au) | dead | HTTP 503 | discover feed |

## Canada

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The Globe and Mail](https://www.theglobeandmail.com) | html | 2784 KB | discover feed |
| press | [Northern Miner](https://www.northernminer.com/feed/) | rss | discovered  | discover feed |
| press | [Mining.com](https://www.mining.com/rss) | rss | discovered  | discover feed |

## United States

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Reuters Legal](https://www.reuters.com/legal/) | dead | HTTP 401 | discover feed |
| press | [Law360 - International Arbitration](https://www.law360.com/internationalarbitration/rss) | wired |  |  |

## Guatemala

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Prensa Libre](https://www.prensalibre.com/feed/) | rss | discovered  | discover feed |

## Honduras

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [El Heraldo](https://www.elheraldo.hn) | html | 478 KB | discover feed |

## El Salvador

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [El Diario de Hoy](https://www.elsalvador.com/rss.xml) | rss | discovered  | discover feed |

## Nicaragua

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Confidencial](https://confidencial.digital) | dead | HTTP 403 | discover feed |

## Costa Rica

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [La Nación](https://www.nacion.com/rss) | rss | discovered  | discover feed |

## Panama

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [La Prensa](https://www.prensa.com/arc/outboundfeeds/rss/) | rss | discovered  | discover feed |

## Dominican Republic

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Diario Libre](https://www.diariolibre.com/rss/portada.xml) | rss | discovered  | discover feed |

## Jamaica

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [The Gleaner](https://jamaica-gleaner.com/rss.xml) | rss | discovered  | discover feed |

## Guyana

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [Stabroek News](https://www.stabroeknews.com) | html | 226 KB | discover feed |

## Paraguay

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [ABC Color](https://www.abc.com.py) | html | 898 KB | discover feed |
| press | [Última Hora](https://www.ultimahora.com) | html | 397 KB | discover feed |

## Uruguay

| Type | Source | Status | Detail | Note |
|---|---|---|---|---|
| press | [El Observador](https://www.elobservador.com.uy) | dead | HTTP 403 | discover feed |
