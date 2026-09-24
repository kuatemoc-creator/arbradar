# Backlog

The working list for ArbRadar. This file, not the chat, is where the state of
the work lives: update it with every commit that moves an item.

Legend: **[me]** the assistant does it from this repo; **[Aram]** / **[CTO]** needs
the owner's accounts or DNS.

## Open

1. **Style corpus from the inbox** [me] — archiving in progress (264 of about
   440 emails on 24 September, 11:30). Raw text stays in `data/newsletters/`
   (gitignored: subscription content; thread ids in `docs/style-corpus/index.json`
   so it can be re-fetched); `tools/newsletter_corpus.py` writes the derived
   corpus and `docs/style-corpus/README.md`; `docs/house-style.md` is written
   from it. Left: finish the archive, regenerate the numbers, rerun
   `tools/wordlist.py`.
2. **Apply the house style** [me] — done on 24 September for what the rules can
   do: sentence-case headlines from a measured word list, whole-sentence
   explanations within 45 words, one headline size, headline-only stories in
   In brief, no firm-newsletter filler, GAR/IAReporter copies of one story
   clustered. Left: the section names stay as they are until the user says
   otherwise; the model-written tier needs the API key (10).
3. **24 September issue** [me] — the local fetch finished; build, publish the
   site (`tools/publish_site.sh`), push state (`tools/push_state.sh`), send
   to aram@caselens.tech from Gmail.
4. **GAR's 22 September stories missing from the cloud database** [me] —
   "Ukraine instructs boutique…", "UK judge… Yukos", "Malaysian investor…"
   were in the feed but never entered the cloud DB. The run now starts at
   18:00 UTC (GAR publishes about 16:00 UTC). Check the next run; if still
   missing, trace `fetch_log` for the GAR feed.
5. **Send the daily issue from the cloud run** [me + Aram] — the workflow
   builds and publishes but does not send. Aram wants it automatic with an
   approval from the phone, Gmail only. Proposed shape: the run sends a
   preview to Aram and saves the issue as a Gmail draft with the list in BCC;
   Aram taps Send. Later, a "reply SEND" gate. Needs a Gmail route usable
   from GitHub Actions (an app password or OAuth credentials as secrets).
6. **PCA case list blocked from GitHub Actions (403)** [me] — done 24 September:
   `tools/relay.sh` fetches PCA (and the court sites the runner cannot reach)
   on the Mac, pushes a `relay` branch, and the cloud run imports it. A
   LaunchAgent (`tools/com.caselens.arbradar-relay.plist`, 20:30 Yerevan) runs
   it daily. UNCTAD and italaw show a human-verification box even to a real
   browser; they stay reference links, not sources.
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

- 24 Sept: five event types a rainmaker watches for that the taxonomy lacked
  (counsel replaced, emergency or interim relief, counsel instructed,
  settlement, law reform), plus capital-control, bank-resolution, insolvency
  and political-risk-insurance patterns. `build --date` rebuilds a past day as
  of that day; 22-24 September rebuilt.

- Cloud daily run at 18:00 UTC with state persisted on the `state` branch.
- Per-day site archive with day switcher and subscribe box; sources page.
- Court coverage beyond the US (FCL, SLW, CanLII, rechtspraak, RIS, BGH,
  DIFC, AIFC, Peachjam); people and appointments section.
- One type scale in the email and on the site; trade-press score floor.
- `arbradar/style.py` helpers; first style corpus from the GAR RSS feed.
