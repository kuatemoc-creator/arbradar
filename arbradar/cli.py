"""Command line entry point."""
import argparse
import datetime as dt
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
    today = dt.date.today().isoformat()
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
    date = dt.date.today().isoformat()

    filled = enrich.enrich(conn, items)
    if filled:
        print("filled in text for {} headline-only stories".format(filled))
    # Every printed headline carries an explanation. A story that is still only a
    # headline after enrichment is left out; the records (tier 1) always have prose.
    textless = [it for it in items if not email_html.summary_of(it) and (it.get("source_tier") or 2) != 1]
    if textless:
        print("left out {} headline-only stories: {}".format(len(textless), "; ".join(it["title"][:50] for it in textless)))
        items = [it for it in items if it not in textless]
    if not items:
        print("Nothing with an explanation to print today.")
        return 1
    from .config import live_site_url
    base = live_site_url(settings)
    if settings.site_url and not base:
        print("site host does not resolve yet; email links go to the sources")
    for it in items:
        it["site_link"] = "{}/{}".format(base, render.story_slug(it, date)) if base else None
    extras = pipeline.record_extras(conn, settings, items)
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
        (dt.datetime.now().isoformat(timespec="seconds"), subject,
         paths["html"], paths["md"], len(items)))
    issue_id = cur.lastrowid
    conn.executemany("UPDATE items SET issue_id=? WHERE url=? OR id=?",
                     [(issue_id, a["url"], it["id"]) for it in items
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
    sub.add_parser("enrich", parents=[common], help="LLM triage + extraction")
    sub.add_parser("reclassify", parents=[common], help="re-run the rule classifier after a taxonomy change")
    sub.add_parser("build", parents=[common, llm_opts], help="write an issue")
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
    handler = {"fetch": cmd_fetch, "enrich": cmd_enrich, "build": cmd_build, "reclassify": cmd_reclassify,
               "run": cmd_run, "top": cmd_top, "send": cmd_send,
               "serve": cmd_serve, "intel": cmd_intel, "articles": cmd_articles}[args.cmd]
    return handler(args, settings, conn)


if __name__ == "__main__":
    sys.exit(main())
