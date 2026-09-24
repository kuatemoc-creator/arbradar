"""Command line entry point."""
import argparse
import datetime as dt
import os
import json
import logging
import sys

from . import config, db, email_html, enrich, llm, pipeline, render, send as sender


def _log(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)-7s %(name)s: %(message)s")


def cmd_fetch(args, settings, conn):
    stats = pipeline.ingest(conn, settings, days=args.days,
                            only=args.source.split(",") if args.source else None)
    total = sum(stats.values())
    for name, n in sorted(stats.items(), key=lambda kv: -kv[1]):
        print("  {:16} {:>4} new".format(name, n))
    print("{} new items".format(total))
    return 0


def cmd_export(args, settings, conn):
    """Fetch the sources the cloud cannot reach and write them for the relay."""
    from . import relay
    names = args.source.split(",") if args.source else list(relay.BLOCKED_IN_CLOUD)
    counts = relay.export(names, days=args.days or 7, path=args.out)
    for name, n in counts.items():
        print("  {:16} {:>4} items".format(name, n))
    print("wrote {}".format(args.out))
    return 0


def cmd_import(args, settings, conn):
    """Store relayed items as if they had been fetched here."""
    import os
    from . import relay
    if not os.path.exists(args.file):
        print("no relay file at {}".format(args.file))
        return 0
    new = relay.import_file(conn, settings, args.file)
    for name, n in new.items():
        print("  {:16} {:>4} new".format(name, n))
    print("{} new items from the relay".format(sum(new.values())))
    return 0


def cmd_email(args, settings, conn):
    """Render out/issue-<date>.html from the saved day (out/site/data/<date>.json),
    pulling the day from the published site first when it is newer there."""
    import json
    import subprocess
    from . import site
    from .config import live_site_url, OUT_DIR, ROOT
    date = args.date or dt.date.today().isoformat()
    path = site.day_file(date)
    try:
        raw = subprocess.run(["git", "show", "origin/gh-pages:data/{}.json".format(date)],
                             capture_output=True, text=True, cwd=ROOT)
        if raw.returncode == 0 and raw.stdout.strip():
            os.makedirs(site.DATA, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(raw.stdout)
            print("day {} taken from the published site".format(date))
    except Exception:                                 # noqa: BLE001 - offline is fine
        pass
    if not os.path.exists(path):
        print("no saved day for {}".format(date))
        return 1
    with open(path, encoding="utf-8") as fh:
        day = json.load(fh)
    base = live_site_url(settings)
    items = day.get("stories") or []
    for it in items:
        it["site_link"] = "{}/{}".format(base, it["slug"]) if (base and it.get("slug")) else None
    built = email_html.build(items, day.get("records") or {}, settings, date)
    out = os.path.join(OUT_DIR, "issue-{}.html".format(date))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(built["html"])
    print("{}\n  subject: {}".format(out, built["subject"]))
    return 0


def cmd_reclassify(args, settings, conn):
    n = pipeline.reclassify(conn, settings, days=args.days or 21)
    print("reclassified {} items".format(n))
    return 0


def cmd_enrich(args, settings, conn):
    if not settings.use_llm:
        print("ANTHROPIC_API_KEY not set - using rule-based classification only.")
    counts = pipeline.enrich(conn, settings)
    print("triaged={triaged} dropped={dropped} extracted={extracted}".format(**counts))
    print("rescored {} items".format(pipeline.rescore(conn, settings)))
    return 0


def cmd_build(args, settings, conn):
    # A rebuild on the same day replaces that day's issue; otherwise the second
    # build sees only what the first one left over.
    if getattr(args, "date", None):
        pipeline.AS_OF = dt.date.fromisoformat(args.date)
    today = pipeline.as_of().isoformat()
    prior = [r[0] for r in conn.execute("SELECT id FROM issues WHERE substr(created_at,1,10)=?", (today,))]
    if prior:
        marks = ",".join("?" * len(prior))
        conn.execute("UPDATE items SET issue_id=NULL WHERE issue_id IN ({})".format(marks), prior)
        conn.execute("DELETE FROM issues WHERE id IN ({})".format(marks), prior)
        conn.commit()
    pipeline.rescore(conn, settings)
    items = pipeline.select(conn, settings)
    if not items:
        print("Nothing scored above {} in the last {} days.".format(
            settings.min_score, settings.lookback_days))
        return 1
    date = today

    filled = enrich.enrich(conn, items)
    if filled:
        print("filled in text for {} headline-only stories".format(filled))
    # Every printed headline carries an explanation. A story that is still only a
    # headline after enrichment is left out; the records (tier 1) always have prose.
    from .outlets import is_trade_press

    def _with_text(rows):
        gone = [it for it in rows if (it.get("source_tier") or 2) != 1
                and not is_trade_press(it.get("source") or "", it.get("url") or "")
                and not enrich.relevant_summary(it.get("title_en") or it.get("title") or "", email_html.summary_of(it))]
        if gone:
            print("left out {} headline-only stories: {}".format(len(gone), "; ".join(it["title"][:50] for it in gone)))
        return [it for it in rows if it not in gone]

    items = _with_text(items)
    if len(items) < 3:
        # A thin day: as an exception, reach one day further back for stories that
        # were never printed, and give them the same enrichment.
        have = {it["id"] for it in items}
        more = [it for it in pipeline.select(conn, settings, extra_days=1) if it["id"] not in have]
        if more:
            enrich.enrich(conn, more)
            more = _with_text(more)
            for it in more:
                it["flag_reason"] = ((it.get("flag_reason") or "") + " | held over from the previous day").strip(" |")
            print("thin day: held over {} stories from the previous day".format(len(more)))
            items = (items + more)[:settings.max_items_per_issue]
    if not items:
        print("Nothing with an explanation to print today.")
        return 1
    # A trade-press headline that still has no text goes to 'In brief', after
    # every story that can be explained; it is never the lead or a development.
    def _docket_text(text: str) -> bool:
        # "MISCELLANEOUS CASE INITIATING DOCUMENT - MOTION for Discovery": a docket
        # entry, not an explanation. Mostly capitals means it reads as one.
        letters = [c for c in text if c.isalpha()]
        return bool(letters) and sum(1 for c in letters if c.isupper()) > 0.35 * len(letters)

    for it in items:
        text = email_html.summary_of(it)
        it["brief_only"] = not enrich.relevant_summary(it.get("title_en") or it.get("title") or "", text) or _docket_text(text[:200])
    items = [it for it in items if not it["brief_only"]] + [it for it in items if it["brief_only"]]
    from .config import live_site_url
    base = live_site_url(settings)
    if settings.site_url and not base:
        print("site host does not resolve yet; email links go to the sources")
    for it in items:
        it["site_link"] = "{}/{}".format(base, render.story_slug(it, date)) if base else None
    # The leads: pre-dispute hints from outside the trade press, with their own
    # slots. Then every story and lead is chased into other outlets and the
    # explanation built from what they add.
    from . import followup
    leads = pipeline.select_leads(conn, settings, items, limit=5)
    if leads:
        enrich.enrich(conn, leads)
        leads = [it for it in leads if enrich.relevant_summary(it.get("title_en") or it.get("title") or "", email_html.summary_of(it))
                 or followup.load(it.get("corroboration"))]
    chased = 0
    for it in [x for x in items if not x.get("brief_only")] + leads:
        stored = followup.load(it.get("corroboration"))
        if stored or chased >= 14:
            it["corroboration"] = stored
            continue
        found = followup.corroborate(it)
        chased += 1
        it["corroboration"] = found["sources"]
        if found["story"] and len(found["story"]) > len(email_html.summary_of(it) or ""):
            it["story"] = found["story"]
        conn.execute("UPDATE items SET corroboration=?, story=? WHERE id=?",
                     (json.dumps(found["sources"], ensure_ascii=False), it.get("story") or None, it["id"]))
    conn.commit()
    leads = [it for it in leads if email_html.summary_of(it) or it.get("story")]
    if chased:
        print("chased {} stories into other outlets; {} leads".format(chased, len(leads)))
    extras = pipeline.record_extras(conn, settings, items)
    extras["leads"] = leads
    built = email_html.build(items, extras, settings, date)
    if settings.use_llm and not args.no_llm:
        print("Writing issue with {} ...".format(settings.editor_model))
        try:
            text = llm.write_issue(items, settings.editor_model,
                                   settings.newsletter_name, date, effort=args.effort)
            text += "\n\n" + "\n".join(render.record_sections(extras))
        except Exception as exc:                      # noqa: BLE001 - boundary
            print("editorial pass failed ({}); falling back to template".format(exc))
            text = render.fallback_markdown(items, settings.newsletter_name, date, settings, extras=extras)
    else:
        text = render.fallback_markdown(items, settings.newsletter_name, date, settings, extras=extras)

    paths = render.write_issue(text, items, settings, date=date, html_doc=built["html"])
    subject = built["subject"]
    from . import site
    site.write_day(date, items, extras, settings, subject)     # the day the web site shows
    cur = conn.execute(
        "INSERT INTO issues (number, created_at, subject, html_path, md_path, item_count) "
        "VALUES ((SELECT COALESCE(MAX(number),0)+1 FROM issues),?,?,?,?,?)",
        (today + dt.datetime.now().isoformat(timespec="seconds")[10:], subject,
         paths["html"], paths["md"], len(items)))
    issue_id = cur.lastrowid
    conn.executemany("UPDATE items SET issue_id=? WHERE url=? OR id=?",
                     [(issue_id, a["url"], it["id"]) for it in items + leads
                      for a in ([{"url": it["url"]}] + (it.get("also") or []))])
    conn.commit()

    print("\n{} items\n  {}\n  {}".format(len(items), paths["md"], paths["html"]))
    return 0


def cmd_run(args, settings, conn):
    cmd_fetch(args, settings, conn)
    cmd_enrich(args, settings, conn)
    return cmd_build(args, settings, conn)


def cmd_top(args, settings, conn):
    pipeline.rescore(conn, settings)
    rows = conn.execute(
        "SELECT * FROM items WHERE relevant=1 ORDER BY score DESC LIMIT ?",
        (args.limit,)).fetchall()
    for r in rows:
        it = db.row_to_dict(r)
        print("{:>7.1f}  {:<22} {:<26} {}".format(
            it["score"], (it.get("event_type") or "")[:22],
            (it.get("source") or "")[:26], it["title"][:74]))
        if args.why:
            print("         {}".format(json.dumps(it.get("score_detail") or {})))
    return 0


def cmd_send(args, settings, conn):
    row = conn.execute("SELECT * FROM issues ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        print("no issue built yet - run `build` first")
        return 1
    to = [x.strip() for x in args.to.split(",")] if getattr(args, "to", None) else None
    if getattr(args, "eml", False):
        print("wrote " + sender.write_eml(row["html_path"], row["md_path"], row["subject"], settings, to))
        return 0
    print(sender.send(row["html_path"], row["md_path"], row["subject"],
                      settings, recipients=to, dry_run=not args.confirm))
    if args.confirm:
        conn.execute("UPDATE issues SET sent_at=? WHERE id=?",
                     (dt.datetime.now().isoformat(timespec="seconds"), row["id"]))
        conn.commit()
    return 0


def cmd_intel(args, settings, conn):
    """Appointment intelligence from the full ICSID corpus -> out/intel.json + summary."""
    import os
    from . import intel
    from .config import OUT_DIR
    cases = intel.load_cases()
    rows = intel.appointments(cases)
    table = intel.arbitrator_table(rows)
    recon = intel.reconstitutions(cases)
    recent = intel.recent_appointments(rows, days=365)
    data = {"generated": dt.date.today().isoformat(),
            "totals": {"cases": len(cases), "seats": len(rows), "arbitrators": len(table),
                       "concentration": intel.concentration(table)},
            "arbitrators": table[:60], "reconstitutions": recon,
            "recent": recent, "affinity": intel.firm_affinity(rows, min_count=2),
            "counsel": intel.counsel_table(rows)[:60]}
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "intel.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)

    print("{} cases, {} seats, {} arbitrators; top 20 hold {:.1%} of seats".format(
        len(cases), len(rows), len(table), data["totals"]["concentration"]["top_n_share"]))
    print("\nBusiest, with claimant lean (1.0 = only ever claimant-appointed):")
    for r in table[:args.limit]:
        print("  {:<30} {:>4} seats  {:>3} pending  lean {:.2f}".format(
            r["arbitrator"][:30], r["total"], r["pending"], r["claimant_lean"]))
    dq = [r for r in recon if r["reason"] == "disqualification"]
    print("\nDisqualifications on record: {}".format(len(dq)))
    for r in dq[:5]:
        print("  {}  {:<26} {}  {}".format(r["date"], r["outgoing"][:26], r["case"], r["respondent_state"][:28]))
    print("\nfull data: {}".format(path))
    return 0


def cmd_articles(args, settings, conn):
    from . import articles
    out = articles.build(conn, settings, limit=args.limit, use_llm=not args.no_llm)
    print("{} pieces written, {} on the site\n  {}/index.html".format(
        out["written"], len(out.get("days") or []), out["site"]))
    return 0


def cmd_serve(args, settings, conn):
    from .web import serve
    print("Review UI on http://{}:{}  (Ctrl-C to stop)".format(args.host, args.port))
    serve(host=args.host, port=args.port)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="arbradar",
                                description="Arbitration mandate intelligence")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--days", type=int, default=None, help="lookback window")

    # Shared so `--days` works before or after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--days", type=int, default=None, help="lookback window")
    llm_opts = argparse.ArgumentParser(add_help=False)
    llm_opts.add_argument("--no-llm", action="store_true")
    llm_opts.add_argument("--effort", default="high",
                          choices=["low", "medium", "high", "xhigh", "max"])

    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", parents=[common], help="pull from sources")
    f.add_argument("--source")
    x = sub.add_parser("export", parents=[common], help="fetch the sources the cloud cannot reach, for the relay")
    x.add_argument("--source", help="adapters to run (default: the ones GitHub's runners are refused by)")
    x.add_argument("--out", default="out/relay.jsonl")
    m = sub.add_parser("import", parents=[common], help="store relayed items")
    m.add_argument("--file", default="data/relay.jsonl")
    sub.add_parser("enrich", parents=[common], help="LLM triage + extraction")
    sub.add_parser("reclassify", parents=[common], help="re-run the rule classifier after a taxonomy change")
    e = sub.add_parser("email", parents=[common], help="render the email for a saved day, from the published site")
    e.add_argument("--date", default=None)
    b = sub.add_parser("build", parents=[common, llm_opts], help="write an issue")
    b.add_argument("--date", default=None, help="rebuild a past day as of that day (YYYY-MM-DD)")
    r = sub.add_parser("run", parents=[common, llm_opts], help="fetch + enrich + build")
    r.add_argument("--source")
    t = sub.add_parser("top", parents=[common], help="inspect the ranking")
    t.add_argument("--limit", type=int, default=25)
    t.add_argument("--why", action="store_true")
    s = sub.add_parser("send", parents=[common], help="email the latest issue")
    s.add_argument("--confirm", action="store_true", help="actually send")
    s.add_argument("--to", help="override recipients (comma separated)")
    s.add_argument("--eml", action="store_true", help="write an .eml file instead of sending")
    i = sub.add_parser("intel", parents=[common], help="ICSID appointment intelligence")
    i.add_argument("--limit", type=int, default=15)
    a = sub.add_parser("articles", parents=[common, llm_opts], help="short shareable pieces -> out/site")
    a.add_argument("--limit", type=int, default=6)
    w = sub.add_parser("serve", parents=[common], help="local review UI")
    w.add_argument("--port", type=int, default=8765)
    w.add_argument("--host", default="127.0.0.1")

    argv = list(sys.argv[1:] if argv is None else argv)
    args = p.parse_args(argv)
    _log(args.verbose)
    settings = config.load()
    if args.days:
        settings.lookback_days = args.days
    else:
        args.days = settings.lookback_days
    if not hasattr(args, "source"):
        args.source = None

    conn = db.connect()
    handler = {"fetch": cmd_fetch, "export": cmd_export, "import": cmd_import, "enrich": cmd_enrich, "build": cmd_build, "reclassify": cmd_reclassify, "email": cmd_email,
               "run": cmd_run, "top": cmd_top, "send": cmd_send,
               "serve": cmd_serve, "intel": cmd_intel, "articles": cmd_articles}[args.cmd]
    return handler(args, settings, conn)


if __name__ == "__main__":
    sys.exit(main())
