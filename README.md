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
| Notice of intent / dispute | 100 | Cooling-off period running; counsel being chosen now |
| s.1782 application | 85 | Discovery ahead of, or at the very start of, an arbitration |
| New case registered | 80 | Respondent-side and co-counsel roles often still open |
| Enforcement / recognition | 78 | Needs local counsel in every enforcement jurisdiction |
| Annulment / set-aside | 72 | Fresh mandate, distinct team from the merits phase |
| Expropriation / licence / sanctions | 60 | Treaty claim often follows in 6–24 months |
| Award issued | 55 | Starts the annulment and enforcement clock |
| Treaty signature / denunciation | 45 | Sunset-clause races |
| Third-party funding | 42 | A funded claimant is a buyer of legal services |
| Tribunal constituted / challenge | 35 | Appointment and conflicts intelligence |
| Lateral move | 30 | Conflicts open up; clients become reachable |
| Commentary | 10 | Context, not a lead |

`score = weight × recency_decay × source_tier × (1 + watchlist_boost)
         + amount_bonus + unrepresented_bonus`

Recency half-life is 6 days. `unrepresented_bonus` applies **only** to primary
records (dockets, registries, filings), where absence of counsel is evidence —
a press summary that omits counsel is silence, not evidence.

## Sources

| Source | Type | What it gives you |
|---|---|---|
| **ICSID docket** (`/api/cases/`) | Primary | 300+ pending cases: counsel on record, tribunal, treaty invoked, sector, and `lastproc` — the latest procedural step with its date. A live docket, not a news feed. |
| **CourtListener / RECAP** | Primary | US federal dockets: s.1782 applications, petitions to confirm/vacate. Returns party, attorney **and firm** names. |
| **SEC EDGAR full-text** | Primary | Disputes disclosed in 8-K/6-K/20-F filings, often weeks ahead of the trade press. |
| RSS | Reported | GAR, IAReporter, Kluwer, Jus Mundi, IISD, institutions. |
| PCA | Reported | News page only — the case list is client-rendered and not exposed via its REST API. |

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

## Tuning

`config.yaml` holds the watchlists. The weights are additive multipliers, so
`Armenia: 1.2` makes an Armenian matter rank roughly twice as high as an
otherwise identical one. This is the main thing to tune.

## Known gaps

- PCA and UNCTAD sit behind client-side rendering / Cloudflare; the UNCITRAL
  Transparency Registry is the better route and is not yet wired in.
- No stock-exchange feeds yet (LSE RNS, ASX, SEDAR) — these carry notices of
  intent from junior miners, the single best early signal.
- `amount_usd` is only populated when the extraction tier runs.
