# Backlog

The working list for ArbRadar. This file, not the chat, is where the state of
the work lives: update it with every commit that moves an item.

Legend: **[me]** the assistant does it from this repo; **[Aram]** / **[CTO]** needs
the owner's accounts or DNS.

## Open

1. **Style corpus from the inbox** [me] — in progress. Read every GAR and
   IAReporter newsletter in the inbox in full (Gmail connector), keep the raw
   text locally in `data/newsletters/` (private, gitignored: it is their
   subscription content), and commit the derived corpus to `docs/style-corpus/`:
   subjects, section names, every headline, and the shape of each standfirst.
   Done when at least 100 newsletters are in it and `docs/house-style.md` is
   rewritten from that set rather than from the RSS feed.
2. **Apply the house style** [me] — `style.headline()` for every headline and
   `style.sentences()` for every explanation in `arbradar/email_html.py` and
   `arbradar/site.py`; sections named Also / Filings / People. Known defect:
   `headline()` over-lowercases ("Delhi High court"); keep Court, Tribunal,
   Bank and similar after a proper noun. Depends on 1 for the wording rules.
3. **24 September issue** [me] — the local fetch finished; build, publish the
   site (`tools/publish_site.sh`), push state (`tools/push_state.sh`), send
   to aram@caselens.tech from Gmail.
4. **GAR's 22 September stories missing from the cloud database** [me] —
   "Ukraine instructs boutique…", "UK judge… Yukos", "Malaysian investor…"
   were in the feed but never entered the cloud DB. The run now starts at
   18:00 UTC (GAR publishes about 16:00 UTC). Check the next run; if still
   missing, trace `fetch_log` for the GAR feed.
5. **Send the daily issue from the cloud run** [me + Aram] — the workflow
   builds and publishes but does not send. Needs a mail route usable from
   GitHub Actions (SMTP app password or a provider API key as a repository
   secret) and a send step in `.github/workflows/daily.yml`.
6. **PCA case list blocked from GitHub Actions (403)** [me] — works locally,
   403 from the runner. Fetch locally and push into the state branch, or rely
   on Jus Mundi / GAR for PCA cases. No bot-challenge evasion.
7. **DNS** [CTO] — Route 53: CNAME `arbradar` → `kuatemoc-creator.github.io`
   (TTL 300). Do not touch the Namecheap nameservers. Then repo Settings →
   Pages → Enforce HTTPS once the certificate is issued. Until then email
   links fall back to the github.io address.
8. **Sender alias** [Aram] — create `arbradar@caselens.tech` in Google
   Workspace; then set the sender in `config.yaml`.
9. **Mailing-list provider** [Aram] — the subscribe box posts to
   `signup_url` / `signup_field` in `config.yaml` and falls back to a mailto
   link. Pick a provider (Buttondown, MailerLite, Brevo…), create the form,
   set both values.
10. **ANTHROPIC_API_KEY** [Aram] — add as an Actions secret; the editorial
    tiers (model-written summaries and story pages) are dormant without it.

## Done recently

- Cloud daily run at 18:00 UTC with state persisted on the `state` branch.
- Per-day site archive with day switcher and subscribe box; sources page.
- Court coverage beyond the US (FCL, SLW, CanLII, rechtspraak, RIS, BGH,
  DIFC, AIFC, Peachjam); people and appointments section.
- One type scale in the email and on the site; trade-press score floor.
- `arbradar/style.py` helpers; first style corpus from the GAR RSS feed.
