"""Command line entry point."""
import argparse
import datetime as dt
import os
import re
import json
import logging
import sys

from . import config, db, pipeline, send as sender


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
    """Today's issue, or a past day's with --date: one pipeline, in arbradar/build.py."""
    from . import build
    try:
        out = build.build_issue(conn, settings, date=args.date, force=args.force, use_llm=not args.no_llm)
    except build.Refused as exc:
        print("refused: {}".format(exc))
        return 1
    if not out["items"]:
        return 1
    print("\n{} items\n  {}".format(len(out["items"]), out["paths"]["html"]))
    return 0


def cmd_test(args, settings, conn):
    """The same build, recorded nowhere: out/test-issue-<date>.html and .eml to
    read before anything goes to readers. No issue row, no day file, no item marked."""
    from . import build
    out = build.build_issue(conn, settings, date=args.date, use_llm=not args.no_llm, dry_run=True)
    if not out["items"]:
        return 1
    eml = sender.write_eml(out["paths"]["html"], None, out["subject"], settings, None)
    print("\ntest issue: {} items, {} leads, {} enforcement\n  {}\n  {}\n  subject: {}".format(
        len(out["items"]), len(out["leads"]), len(out["enforcement"]), out["paths"]["html"], eml, out["subject"]))
    return 0


def cmd_rebuild(args, settings, conn):
    """Past days rebuilt in order after the range is cleared, so no stale later day steers an earlier one."""
    from . import build
    try:
        built = build.rebuild_range(conn, settings, args.start, args.end, force=args.force, use_llm=not args.no_llm)
    except build.Refused as exc:
        print("refused: {}".format(exc))
        return 1
    print("\nrebuilt {} days: {}".format(len(built), ", ".join(b["date"] for b in built)))
    return 0


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


def _edited(date: str) -> bool:
    """True when the editor pass (the model) read the issue of that date."""
    from .config import OUT_DIR
    path = os.path.join(OUT_DIR, "editor-{}.json".format(date))
    try:
        with open(path, encoding="utf-8") as fh:
            return bool(json.load(fh).get("llm_pass"))
    except (OSError, ValueError):
        return False


def cmd_send(args, settings, conn):
    row = conn.execute("SELECT * FROM issues ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        print("no issue built yet - run `build` first")
        return 1
    to = [x.strip() for x in args.to.split(",")] if getattr(args, "to", None) else None
    # Nothing goes to readers that the editor pass has not read. A draft for
    # the editor's own approval is allowed; a publish or a real send is not,
    # unless --force says a person has read it instead.
    m = re.search(r"issue-(\d{4}-\d{2}-\d{2})", row["html_path"] or "")
    issue_date = m.group(1) if m else ""
    outward = bool(getattr(args, "publish", False) or getattr(args, "confirm", False))
    if outward and not _edited(issue_date) and not getattr(args, "force", False):
        print("refused: the editor pass has not read issue {} (no ANTHROPIC_API_KEY at build time). "
              "Rebuild with the key, or pass --force after reading out/editor-{}.json yourself.".format(issue_date, issue_date))
        return 1
    if getattr(args, "draft", False) or getattr(args, "publish", False):
        from . import provider
        with open(row["html_path"], encoding="utf-8") as fh:
            html_doc = fh.read()
        res = provider.draft(row["subject"], html_doc, publish=bool(getattr(args, "publish", False)))
        print("provider: {}".format(", ".join("{}={}".format(k, v) for k, v in res.items() if v)))
        if res.get("status") == "published":
            conn.execute("UPDATE issues SET sent_at=? WHERE id=?", (dt.datetime.now().isoformat(timespec="seconds"), row["id"]))
            conn.commit()
        return 0 if res.get("status") != "error" else 1
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
    b = sub.add_parser("build", parents=[common, llm_opts], help="write an issue")
    b.add_argument("--date", default=None, help="rebuild a past day as of that day (YYYY-MM-DD)")
    b.add_argument("--force", action="store_true", help="rebuild a day that was already sent")
    t2 = sub.add_parser("test", parents=[common, llm_opts], help="build an issue and record nothing: out/test-issue-<date>.html")
    t2.add_argument("--date", default=None, help="as of that day (YYYY-MM-DD); default today")
    rb = sub.add_parser("rebuild", parents=[common, llm_opts], help="rebuild a range of past days in order, cleared first")
    rb.add_argument("--from", dest="start", required=True, help="first day (YYYY-MM-DD)")
    rb.add_argument("--to", dest="end", required=True, help="last day (YYYY-MM-DD)")
    rb.add_argument("--force", action="store_true", help="rebuild days that were already sent")
    t = sub.add_parser("top", parents=[common], help="inspect the ranking")
    t.add_argument("--limit", type=int, default=25)
    t.add_argument("--why", action="store_true")
    s = sub.add_parser("send", parents=[common], help="email the latest issue")
    s.add_argument("--force", action="store_true", help="send an issue the editor pass has not read (you have read it)")
    s.add_argument("--confirm", action="store_true", help="actually send")
    s.add_argument("--to", help="override recipients (comma separated)")
    s.add_argument("--eml", action="store_true", help="write an .eml file instead of sending")
    s.add_argument("--draft", action="store_true", help="hand the issue to the list provider as a draft (BUTTONDOWN_API_KEY)")
    s.add_argument("--publish", action="store_true", help="send the issue to the list through the provider at once")
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
    handler = {"fetch": cmd_fetch, "export": cmd_export, "import": cmd_import, "enrich": cmd_enrich, "build": cmd_build,
               "test": cmd_test, "rebuild": cmd_rebuild, "reclassify": cmd_reclassify, "top": cmd_top, "send": cmd_send,
               "serve": cmd_serve, "intel": cmd_intel, "articles": cmd_articles}[args.cmd]
    return handler(args, settings, conn)


if __name__ == "__main__":
    sys.exit(main())
