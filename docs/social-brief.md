# ArbRadar — context for a social media post

Prepared 20 September 2026. Figures are taken from the repository on that date.

## What it is

ArbRadar is an email newsletter on news and developments in international
arbitration, published by CaseLens. Each story in the email opens on a plain
web page that can be shared. It covers investor-State disputes and commercial
arbitration (construction, energy, mining, pharma, telecoms, shipping, finance,
insurance, aviation, defence, agribusiness, tech).

It is written for people who practise arbitration: partners and counsel in
private practice, in-house disputes teams, funders and arbitrators. It reports;
it does not pitch.

## Why it exists

The established services report a dispute once it is public and, usually, once
counsel has been instructed. ArbRadar is built to notice a dispute earlier and
from more places: a notice of dispute buried in a company's securities filing,
a government tendering for arbitration counsel, a licence revoked in a
provincial gazette, a docket entry at ICSID, an asset seizure reported only in
the local language.

## What makes it different

1. **It reads the record, not just the reports.** Primary sources read on every
   run: the ICSID docket (counsel on record, tribunal, latest procedural step),
   the PCA case list, SEC EDGAR full-text (companies disclosing arbitration in
   their filings), US federal dockets (s.1782 discovery, enforcement, sovereign
   immunity), the EU and Ukrainian procurement portals (States hiring
   arbitration counsel), and the Canadian and US treaty-case registers.

2. **Depth per country.** A verified, editable source map of 609 sources across
   182 countries and 12 sectors: press, official gazettes, regulators, stock
   exchanges, courts, case registers and procurement portals. Every source is
   listed with its status, so a reader can see exactly what is checked.

3. **Languages the usual services skip.** News is searched in 42 languages
   across 125 national editions, and the national press is read in 44,
   including Armenian, Georgian, Azerbaijani, Uzbek, Ukrainian, Russian,
   Turkish, Arabic, Vietnamese and Indonesian, alongside English, French,
   Spanish and Portuguese.

4. **State measures before they become claims.** Expropriations, licence
   revocations, windfall taxes, sanctions and asset seizures are tracked as a
   category of their own, because treaty claims tend to follow them.

5. **Appointment intelligence.** An appointment ledger built from the ICSID
   docket: 1,158 cases, 3,195 tribunal seats, 632 arbitrators; the twenty most
   appointed arbitrators hold 27 per cent of all seats; 181 tribunal
   reconstitutions, nine of them successful disqualifications.

6. **Plain design.** Light, simple, built to render in every email client.
   Every headline carries an explanation of who, what and when. No promotional
   framing, no dark mode, no dashboard.

## Numbers safe to quote

| Figure | Value |
|---|---|
| Sources mapped | 609 |
| Countries covered | 118 |
| Sectors tracked | 12 |
| Languages searched | 14 |
| National news editions | 36 |
| Primary records read directly | 8 |
| ICSID cases in the appointment ledger | 1,158 |
| Tribunal seats analysed | 3,195 |

## Stage

Working prototype. Sample issues exist for 18 and 20 September 2026. The site is
not yet publicly hosted and there is no public sign-up page yet. All sources are
free and public; nothing is scraped from behind a paywall or a bot challenge.

## What to say and what to avoid

- Say "earlier and wider", "reads the record", "sources the usual services do
  not check". Avoid "better than GAR" or naming competitors; practitioners
  will judge that themselves and a public comparison invites a reply.
- Say "published by CaseLens" and "curated". Do not say "AI-written": the
  editorial model tier is not switched on yet, and the audience distrusts it.
- Do not say "launched" or "subscribe now" until a sign-up page exists. A
  soft call to action works: "Reply or message me if you would like the first
  issues", or "Tell me which country or sector you want covered".
- Keep the tone factual. The readers are lawyers; adjectives cost credibility.

## Suggested visuals

- A screenshot of the 20 September issue, cropped to the masthead and lead
  story (out/issue-2026-09-20.html).
- The source map page (docs/sources.html), which shows the per-country depth
  at a glance.
- The ArbRadar wordmark with "Published by CaseLens" beneath it.

## Hashtags

#InternationalArbitration #ISDS #InvestmentArbitration #CommercialArbitration
#Arbitration #LegalTech #CaseLens

## Draft posts

**LinkedIn, long form**

> Most arbitration news reaches you after counsel has been instructed. We have
> been building something that looks earlier.
>
> ArbRadar is a newsletter from CaseLens on news and developments in
> international arbitration, investor-State and commercial. It reads the record
> directly: the ICSID docket, the PCA case list, SEC filings in which companies
> disclose disputes, US court dockets, and the procurement portals where States
> hire arbitration counsel. Behind that sits a verified map of 609 sources in
> 118 countries, from official gazettes and regulators to local press in 14
> languages, including Armenian, Georgian, Azerbaijani, Uzbek and Vietnamese.
>
> Each item says who, what and when, in plain language, and opens on a page you
> can share. Every source we check is listed, so you know what is covered and
> what is not.
>
> The first issues are ready. If you would like to see them, or want a country
> or sector added, tell me in the comments or by message.

**LinkedIn, short**

> New from CaseLens: ArbRadar, a newsletter on international arbitration that
> reads the record rather than the reports. ICSID and PCA dockets, SEC filings,
> court dockets, procurement portals and local press in 44 languages, across
> 1,900 sources in 182 countries. Plain design, plain language, every source
> listed. Message me if you want the first issues.

**X / Twitter**

> ArbRadar: a newsletter on international arbitration built from the primary
> record. ICSID, PCA, SEC filings, court dockets, State tenders and local press
> in 44 languages, 1,900 sources, 182 countries. Published by CaseLens. First
> issues ready; DM for a copy.


## The numbers, as of 25 September 2026

Use these, and only these, on any panel or slide; they are counted from the
map, not estimated.

| Figure | Value | Counted from |
|---|---|---|
| Sources read every run | 1,975 | 922 feeds, 840 feedless outlets read through Google News and their front pages, 64 record pages, 24 wired registers/courts/tenders, 125 Google News editions |
| Sources on the map (probed) | 1,871 | 1,681 press outlets and 190 registers, gazettes, regulators, exchanges, courts and tender portals |
| Countries | 182 | every State on the map has five or more press sources |
| Languages, press feeds | 44 | distinct languages in sources.yaml |
| Languages, news search | 42 | Google News editions swept |
| Languages, site sweep | 50 | dispute terms for the feedless press |

Round "1,975" to "1,900+" on a panel if a round figure reads better; never
round up. `python -m tools.sourcemap --map` prints the country line; the rest
are in this table's second column.
