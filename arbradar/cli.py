"""Command line entry point."""
import argparse
import datetime as dt
import json
import logging
import sys

from . import config, db, llm, pipeline, render, send as sender


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


def cmd_enrich(args, settings, conn):
    if not settings.use_llm:
        print("ANTHROPIC_API_KEY not set - using rule-based classification only.")
    counts = pipeline.enrich(conn, settings)
    print("triaged={triaged} dropped={dropped} extracted={extracted}".format(**counts))
    print("rescored {} items".format(pipeline.rescore(conn, settings)))
    return 0


def cmd_build(args, settings, conn):
    pipeline.rescore(conn, settings)
    items = pipeline.select(conn, settings)
    if not items:
        print("Nothing scored above {} in the last {} days.".format(
            settings.min_score, settings.lookback_days))
        return 1
    date = dt.date.today().isoformat()

    if settings.use_llm and not args.no_llm:
        print("Writing issue with {} ...".format(settings.editor_model))
        try:
            text = llm.write_issue(items, settings.editor_model,
                                   settings.newsletter_name, date, effort=args.effort)
        except Exception as exc:                      # noqa: BLE001 - boundary
            print("editorial pass failed ({}); falling back to template".format(exc))
            text = render.fallback_markdown(items, settings.newsletter_name, date)
    else:
        text = render.fallback_markdown(items, settings.newsletter_name, date)

    paths = render.write_issue(text, items, settings, date=date)
    subject = "{} - {}".format(settings.newsletter_name, date)
    cur = conn.execute(
        "INSERT INTO issues (number, created_at, subject, html_path, md_path, item_count) "
        "VALUES ((SELECT COALESCE(MAX(number),0)+1 FROM issues),?,?,?,?,?)",
        (dt.datetime.now().isoformat(timespec="seconds"), subject,
         paths["html"], paths["md"], len(items)))
    issue_id = cur.lastrowid
    conn.executemany("UPDATE items SET issue_id=? WHERE id=?",
                     [(issue_id, it["id"]) for it in items])
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
    print(sender.send(row["html_path"], row["md_path"], row["subject"],
                      settings, dry_run=not args.confirm))
    if args.confirm:
        conn.execute("UPDATE issues SET sent_at=? WHERE id=?",
                     (dt.datetime.now().isoformat(timespec="seconds"), row["id"]))
        conn.commit()
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
    sub.add_parser("build", parents=[common, llm_opts], help="write an issue")
    r = sub.add_parser("run", parents=[common, llm_opts], help="fetch + enrich + build")
    r.add_argument("--source")
    t = sub.add_parser("top", parents=[common], help="inspect the ranking")
    t.add_argument("--limit", type=int, default=25)
    t.add_argument("--why", action="store_true")
    s = sub.add_parser("send", parents=[common], help="email the latest issue")
    s.add_argument("--confirm", action="store_true", help="actually send")

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
    handler = {"fetch": cmd_fetch, "enrich": cmd_enrich, "build": cmd_build,
               "run": cmd_run, "top": cmd_top, "send": cmd_send}[args.cmd]
    return handler(args, settings, conn)


if __name__ == "__main__":
    sys.exit(main())
