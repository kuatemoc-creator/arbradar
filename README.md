# Arbitration Radar

A newsletter engine for arbitration practitioners **looking for cases to take**.

GAR and IAReporter are journalism: they report what happened, usually once
counsel has already been instructed. This is aimed a step earlier — at the point
where a mandate is still open. Items are ranked by *likelihood of available work*,
not by news value.

## The signal ladder

Scoring weight is highest where counsel is least likely to be appointed yet:

| Event | Weight | Why it ranks there |
|---|---|---|
| Notice of intent / dispute | 100 | The cooling-off period is running and counsel is being chosen now. |
| State tendering for counsel | 90 | A State or state enterprise is procuring arbitration counsel: the dispute exists and the instruction is open. |
| Counsel replaced or withdrawn | 88 | A party has parted with its lawyers mid-case: the mandate is open now, with the file already built. |
| s.1782 discovery application | 85 | Someone is gathering evidence for an arbitration that has not yet been reported. |
| New case registered | 80 | Registration comes first; the respondent side and co-counsel are often still to be settled. |
| Enforcement / recognition | 78 | Enforcement needs counsel in every jurisdiction where the assets sit. |
| Emergency or interim relief | 74 | An emergency arbitrator, a freezing order or an anti-suit injunction means a dispute is live this week and someone needs counsel in a second forum. |
| Annulment / set-aside | 72 | A second mandate, and usually a different team from the merits. |
| State measure against a foreign investor | 70 | A licence, contract, tax or regulatory action against a foreign investor of means: the fact pattern of a treaty claim, before any notice. |
| Commercial arbitration | 68 | A contract dispute has gone, or is going, to arbitration: EPC, JV, supply, licence, charter, offtake. |
| Award issued | 55 | The award starts the clock on annulment and enforcement. |
| Expropriation / licence / sanctions event | 52 | Events of this kind tend to produce a treaty claim within a year or two. |
| Counsel instructed | 48 | Lead counsel is taken; local counsel, co-counsel, expert and arbitrator roles usually are not. |
| Treaty signature / denunciation | 45 | Treaty changes move the deadlines for everyone with an investment covered by it. |
| Third-party funding | 42 | A funded claimant has the money to instruct. |
| Settlement or discontinuance | 40 | The money moves and the parties are free: a settlement to paper, enforce or unwind, and a client whose counsel relationship has just ended. |
| Arbitration law or rules changed | 35 | A new arbitration act, seat reform or rule revision: the client alert every practice writes, and the reason seats move. |
| Tribunal constituted / challenge | 35 | Who sits, and who put them there, is worth knowing before the next appointment. |
| Appointment | 32 | Who now sits on the tribunal, runs the institution or leads the practice. |
| Lateral move / team change | 30 | A move opens conflicts and makes clients reachable. |
| Commentary / analysis | 10 | Context rather than a lead. |

`score = weight × recency_decay × source_tier × (1 + watchlist_boost)
         + amount_bonus + unrepresented_bonus`

Recency half-life is 6 days. `unrepresented_bonus` applies **only** to primary
records (dockets, registries, filings), where absence of counsel is evidence —
a press summary that omits counsel is silence, not evidence.

## The daily run

`.github/workflows/daily.yml` runs every day at 22:00 Yerevan time on GitHub
Actions: it restores the database from the `state` branch and the day archive
from the published site, fetches every source, applies the rules, builds the
issue, publishes the site to `gh-pages`, and saves the database back. The
built issue is kept as a workflow artifact for 30 days. Add
`ANTHROPIC_API_KEY` (and optionally `COURTLISTENER_TOKEN`) under Settings →
Secrets and variables → Actions to switch on the model tiers. `tools/daily.sh`
is the same run for a laptop.

## Hosting the site and collecting sign-ups

The site in `out/site` is static, so any static host serves it. The included
route is GitHub Pages on a CaseLens subdomain:

1. Create a GitHub repository and add it as `origin`.
2. Set `site_url: https://arbradar.caselens.tech` in `config.yaml`. The article
   builder then writes a `CNAME` file and the email deep-links to the site.
3. Run `tools/publish_site.sh`. It rebuilds the article pages and pushes them to
   a `gh-pages` branch.
4. On GitHub: Settings → Pages → deploy from `gh-pages`, custom domain
   `arbradar.caselens.tech`, enforce HTTPS.
5. In the caselens.tech DNS, add a CNAME record `arbradar` → `<user>.github.io`.

Cloudflare Pages or Netlify work the same way: point them at the `gh-pages`
branch, or upload `out/site` directly.

Sign-ups: pick a list provider that also sends and handles unsubscribes
(Buttondown, MailerLite, Kit and Beehiiv all give a plain form endpoint), then
set `signup_url` and `signup_field` in `config.yaml`. The site index shows a
subscribe box, the provider stores the addresses with double opt-in, and
`unsubscribe_url` in `config.yaml` should point at the provider's link so every
email carries it.

## Sources

| Source | Type | What it gives you |
|---|---|---|
| **ICSID docket** (`/api/cases/`) | Primary | 300+ pending cases: counsel on record, tribunal, treaty invoked, sector, and `lastproc` — the latest procedural step with its date. A live docket, not a news feed. |
| **CourtListener / RECAP** | Primary | US federal dockets: s.1782 applications, petitions to confirm/vacate. Returns party, attorney **and firm** names. |
| **Courts outside the US** | Primary | Judgment feeds and open APIs: England and Wales (Find Case Law), Singapore (catchwords), Canada (CanLII), Netherlands (rechtspraak), Austria (RIS), Germany (BGH), DIFC, AIFC and eleven African law reports. Set-aside, enforcement, stays, anti-suit relief, arbitrator challenges. |
| **SEC EDGAR full-text** | Primary | Disputes disclosed in 8-K/6-K/20-F filings, often weeks ahead of the trade press. |
| RSS | Reported | GAR, IAReporter, Kluwer, Jus Mundi, IISD, institutions. |
| PCA | Primary | Case list and press releases, relayed from a machine Cloudflare lets in (`tools/relay.sh`); GitHub's runners are refused. |
| **National press**, 182 States | Reported | The business press, paper of record, legal press and wire of every State that can be a respondent: `tools/outlets.py` lists them, `tools/discover.py` finds and verifies each one's feed and wires it into `sources.yaml`. Read every run, filtered to dispute language in the feed's own language. Five or more feeds per State is the floor; `SOURCES.md` shows where it is not met yet. |
| **Google News editions**, 124 | Reported | One edition per State in its own language, swept with the dispute and State-measure terms in that language, plus an English query per State. |
| **GDELT** | Reported | Global press with country tagging, for the States whose press has no feeds. |

All free and unauthenticated. No API key is required to run the system.

## Models

Three tiers, because volume drops sharply at each stage:

| Stage | Model | Runs on |
|---|---|---|
| Triage | `claude-haiku-4-5` | every raw item, batched 20/call |
| Extraction | `claude-sonnet-5` | survivors only |
| Editorial | `claude-fable-5-1` | once per issue |

Without `ANTHROPIC_API_KEY` the system falls back to rule-based classification
and a deterministic template. It still works — it is just blunter.

## Usage

```bash
export ANTHROPIC_API_KEY=sk-ant-...      # optional but a large quality jump
./.venv/bin/python -m arbradar.cli run --days 7

./.venv/bin/python -m arbradar.cli fetch --days 7    # ingest only
./.venv/bin/python -m arbradar.cli enrich            # triage + extract
./.venv/bin/python -m arbradar.cli build             # write the issue
./.venv/bin/python -m arbradar.cli top --why         # inspect the ranking
./.venv/bin/python -m arbradar.cli send              # dry run by default
./.venv/bin/python -m arbradar.cli send --confirm    # actually send
```

Issues are written to `out/` as Markdown and email-safe HTML. **Nothing is ever
emailed as a side effect of building** — `send` is a separate command and dry-runs
unless you pass `--confirm`.

## Review UI

```bash
./.venv/bin/python -m arbradar.cli serve      # http://127.0.0.1:8765
```

Three screens:

- **Review** — every candidate ranked, with the reason it ranked there (watchlist
  hits, counsel status, event type). Filter by event type, source, text or window.
  `pin` forces an item into the next issue regardless of score; `kill` removes it
  permanently. Pinned and killed decisions persist across runs.
- **Preview** — the built issue rendered exactly as it will arrive in the inbox,
  with the send controls above it.
- **Issues** — the archive, and which ones were actually sent.

Bound to `127.0.0.1`. It is a desk tool, not a public service — do not expose it.

## Sending

The list lives at a provider, not in this repo: sign-up confirmation,
unsubscribes, bounces and sender reputation are the provider's job. The daily
run hands the finished issue to Buttondown as a draft (`arbradar.cli send
--draft`, needs `BUTTONDOWN_API_KEY`), the editor approves it there, and the
subscribe box on the site posts to Buttondown's form endpoint (`signup_url` in
`config.yaml`). SMTP below is for a test send to yourself.

Two rails, depending on who is receiving.

### Small internal list (up to ~30 known recipients)

Gmail SMTP with an app password. Gmail rejects your normal password, so:

1. Google Account → Security → 2-Step Verification (must be on)
2. → App passwords → generate one for "Mail"
3. Put the 16-character value in the environment, never in `config.yaml`:

```bash
export SMTP_USER=you@yourfirm.com
export SMTP_PASSWORD='xxxx xxxx xxxx xxxx'
```

```yaml
# config.yaml
recipients: [partner1@firm.com, partner2@firm.com]
smtp: {host: smtp.gmail.com, port: 587, user: you@yourfirm.com, from: you@yourfirm.com}
```

```bash
./.venv/bin/python -m arbradar.cli send --to you@yourfirm.com   # dry run
./.venv/bin/python -m arbradar.cli send --to you@yourfirm.com --confirm   # real test
./.venv/bin/python -m arbradar.cli send --confirm               # to the list
```

`send` dry-runs unless you pass `--confirm`. Building an issue never sends anything.

### Real subscriber list (external readers)

**Do not use Gmail SMTP for this.** A newsletter going to lawyers you do not
personally know needs unsubscribe handling, bounce processing, sender
authentication (SPF/DKIM/DMARC) and an archive. Without them you will land in
spam and, depending on jurisdiction, breach direct-marketing rules.

Use a sending platform and push the built HTML to it. Buttondown and Beehiiv both
have simple APIs; Mailchimp works too. The issue HTML is already email-safe
(tables, inline styles), so it drops straight in. Ask and I will wire the adapter.

## Pre-dispute sources

`gnews` sweeps Google News RSS with a bank of distress queries (notice of dispute,
notice of intent, expropriation, licence revoked, nationalisation, ECT claims) plus
one query per State the gazetteer knows, so a country is covered even when the
story never says "arbitration". `gdelt` does the same across non-English press
with country tagging, throttled to GDELT's one-request-per-five-seconds limit.

The same story is then looked for in the State's own press. `SOURCES.md` (and
`sources.html` on the site) is the map: for each State, every feed that is
read, the Google News editions swept, and, in one muted line, what was tried
and does not answer to a script (a page with no feed, an HTTP 403, a bot
challenge). Those are not sources; they are the gaps, kept visible so they get
closed. To add outlets, edit `tools/outlets.py` and run
`python -m tools.discover`; to re-check the registers and courts, run
`python -m tools.sourcemap --probe`.

Syndicated coverage is clustered into one story per development (`pipeline.cluster`):
the best-scored version leads, the other outlets hang off it as "also reported by".
Items with different case numbers are never merged.

## Appointment intelligence

```bash
./.venv/bin/python -m arbradar.cli intel        # -> out/intel.json + summary
```

Mines the full ICSID corpus (1,158 cases, 3,195 seats) for who appoints whom:
claimant/respondent lean per arbitrator, every disqualification and resignation
with dates, firm-to-arbitrator repeat pairings, tribunals constituted in the last
year, and a counsel league table split by side.

## Shareable articles

```bash
./.venv/bin/python -m arbradar.cli articles --limit 6   # -> out/site/
```

One standalone page per story from the latest issue, in the CaseLens house style,
with an index. Static HTML - host it as an Artifact, on GitHub Pages, or on your
own domain. `manifest.json` accumulates across issues so the index becomes an archive.

## Tuning

`config.yaml` holds the watchlists. The weights are additive multipliers, so
`Armenia: 1.2` makes an Armenian matter rank roughly twice as high as an
otherwise identical one. This is the main thing to tune.

## House style and the corpus behind it

`docs/house-style.md` is measured from the trade press, not guessed: the GAR
daily briefings and IAReporter headline emails in the editor's inbox, archived
verbatim under `data/newsletters/raw/<source>/<thread>.txt` (local only, they
are subscription content; the thread ids in `docs/style-corpus/index.json`
let anyone re-fetch them from Gmail). `python tools/newsletter_corpus.py`
parses the archive into `docs/style-corpus/` (index, every headline, the
measurements, a readable README); `python tools/wordlist.py` rebuilds
`arbradar/data/lowercase-words.txt`, the word list `style.headline()` uses to
turn a Title Case headline into sentence case without touching names. The
build applies the rules itself (case, whole-sentence explanations, one type
scale, headline-only stories in In brief); the editorial model gets the whole
style file in its brief.

## Groundedness

Nothing prints that a cited source does not say. `arbradar/grounding.py` runs
last in every build: each sentence of an explanation is matched against the
item's own text, the corroborating outlets' text and the page text read for
it; a sentence whose content words and numbers are not found near-verbatim in
one of those is dropped, and a cut-off fragment is dropped. An entry that
loses all its sentences prints as a headline and a source line. The same gate
vets anything the model tier writes, so the model may compress the sources
but never add to them. `out/grounding-<date>.json` records what was kept and
dropped for every entry of every day.

## Known gaps

- UNCTAD's ISDS Navigator and italaw put a human-verification box in front of
  every visitor, including a real browser. We do not click through such boxes,
  so neither is fetched. Both are compilations of the same cases ICSID, the PCA
  and the trade press already give us, months later; they stay reference links.
- PCA refuses GitHub's runner addresses (403) but not an ordinary connection, so
  the case list is relayed from the Mac before each cloud run (`tools/relay.sh`,
  `relay` branch, `arbradar.cli import`). On a day the Mac is off, the cloud
  builds without the PCA.
- No stock-exchange feeds yet (LSE RNS, ASX, SEDAR) — these carry notices of
  intent from junior miners, the single best early signal.
- `amount_usd` is only populated when the extraction tier runs.
