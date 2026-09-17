"""Local review UI.

The point is editorial control: you see every candidate ranked, with the reason
it ranked there, and you pin or kill items before an issue is built. Nothing is
sent from here without an explicit confirmation step.

Bound to 127.0.0.1 - this is a private desk tool, not a public service.
"""
import datetime as dt
import html
import json
import os
from typing import Any, Dict, List

from flask import Flask, jsonify, redirect, request, url_for

from . import config, db, llm, pipeline, render, send as sender
from .taxonomy import EVENT_TYPES

app = Flask(__name__)
SETTINGS = config.load()

SHELL = """<!doctype html><html><head><meta charset="utf-8">
<title>Arbitration Radar - review</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
 :root{{--bg:#f7f6f3;--card:#fff;--ink:#1a1a1a;--mut:#6b6b6b;--line:#e3ded3;--accent:#7a1f2b;--gold:#8a7a5c}}
 *{{box-sizing:border-box}}
 body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
 header{{background:var(--card);border-bottom:3px solid var(--accent);padding:14px 22px;position:sticky;top:0;z-index:10;
   display:flex;gap:18px;align-items:baseline;flex-wrap:wrap}}
 header h1{{font:600 15px/1 -apple-system,sans-serif;letter-spacing:.18em;text-transform:uppercase;margin:0;color:var(--accent)}}
 header .sub{{color:var(--mut);font-size:12px}}
 nav{{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}}
 a.btn,button.btn{{background:var(--accent);color:#fff;border:0;border-radius:4px;padding:7px 13px;font-size:13px;
   cursor:pointer;text-decoration:none;display:inline-block}}
 a.btn.ghost,button.btn.ghost{{background:#fff;color:var(--ink);border:1px solid var(--line)}}
 main{{padding:20px 22px;max-width:1500px;margin:0 auto}}
 .bar{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}}
 .bar input,.bar select{{padding:6px 9px;border:1px solid var(--line);border-radius:4px;font-size:13px;background:#fff}}
 table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:6px;overflow:hidden}}
 th{{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--gold);
   padding:9px 10px;border-bottom:1px solid var(--line);white-space:nowrap}}
 td{{padding:9px 10px;border-bottom:1px solid #f0ece3;vertical-align:top}}
 tr:hover td{{background:#fbfaf7}}
 tr.out td{{opacity:.35}}
 .sc{{font-weight:700;font-variant-numeric:tabular-nums;font-size:15px}}
 .ev{{display:inline-block;font-size:11px;padding:2px 7px;border-radius:99px;background:#f0ece3;color:#5a4a2c;white-space:nowrap}}
 .ttl{{font-weight:600;color:var(--ink);text-decoration:none}} .ttl:hover{{color:var(--accent)}}
 .meta{{color:var(--mut);font-size:12px;margin-top:3px}}
 .tag{{color:var(--accent);font-size:11px}}
 .act button{{border:1px solid var(--line);background:#fff;border-radius:4px;padding:3px 7px;cursor:pointer;font-size:12px}}
 .act button.on{{background:var(--accent);color:#fff;border-color:var(--accent)}}
 iframe{{width:100%;height:calc(100vh - 150px);border:1px solid var(--line);border-radius:6px;background:#fff}}
 .flash{{background:#efe7d8;border:1px solid var(--gold);padding:9px 13px;border-radius:5px;margin-bottom:14px;font-size:13px}}
 code{{background:#f0ece3;padding:1px 5px;border-radius:3px;font-size:12px}}
</style></head><body>
<header><h1>Arbitration Radar</h1><span class="sub">{sub}</span>
<nav>{nav}</nav></header><main>{body}</main>
<script>
async function mark(id, field){{
  const r = await fetch('/api/mark/'+id+'/'+field, {{method:'POST'}});
  const d = await r.json();
  const row = document.getElementById('r'+id);
  row.classList.toggle('out', d.excluded==1);
  document.getElementById('pin'+id).classList.toggle('on', d.pinned==1);
  document.getElementById('ex'+id).classList.toggle('on', d.excluded==1);
}}
</script></body></html>"""


def shell(body: str, sub: str = "", active: str = "") -> str:
    nav = ""
    for label, endpoint in (("Review", "index"), ("Preview", "preview"), ("Issues", "issues")):
        cls = "btn" if active == endpoint else "btn ghost"
        nav += '<a class="{}" href="{}">{}</a>'.format(cls, url_for(endpoint), label)
    nav += ('<form method="post" action="{}" style="display:inline">'
            '<button class="btn ghost" name="go" value="1">Fetch now</button></form>').format(url_for("do_fetch"))
    nav += ('<form method="post" action="{}" style="display:inline">'
            '<button class="btn" name="go" value="1">Build issue</button></form>').format(url_for("do_build"))
    return SHELL.format(sub=html.escape(sub), nav=nav, body=body)


def _row(it: Dict[str, Any]) -> str:
    ev = EVENT_TYPES.get(it.get("event_type") or "commentary", {})
    detail = it.get("score_detail") or {}
    hits = detail.get("watchlist_hits") or []
    counsel = it.get("counsel") or []
    if counsel:
        cn = "counsel: " + html.escape(", ".join(counsel[:2]))
    elif (it.get("source_tier") or 2) == 1:
        cn = '<span class="tag">no counsel on record</span>'
    else:
        cn = '<span style="color:#aaa">counsel not stated</span>'

    bits = [html.escape(it.get("source") or ""), html.escape(str(it.get("published_at") or "")[:10])]
    if (it.get("lang") or "en") != "en":
        bits.append('<span class="tag">{}</span>'.format(html.escape(it.get("country") or it["lang"])))
    if it.get("institution"):
        bits.append(html.escape(it["institution"]))
    if it.get("treaty"):
        bits.append(html.escape(it["treaty"][:60]))
    if it.get("amount_usd"):
        bits.append("US${:,.0f}m".format(it["amount_usd"] / 1e6))
    if hits:
        bits.append('<span class="tag">watchlist: {}</span>'.format(html.escape(", ".join(hits[:4]))))

    return """<tr id="r{id}" class="{cls}">
  <td class="sc">{score}</td>
  <td><span class="ev" title="{why}">{ev}</span></td>
  <td><a class="ttl" href="{url}" target="_blank" rel="noopener">{title}</a>
      <div class="meta">{bits} &middot; {cn}</div></td>
  <td class="act" style="white-space:nowrap">
    <button id="pin{id}" class="{pon}" onclick="mark({id},'pinned')" title="Always include">pin</button>
    <button id="ex{id}" class="{eon}" onclick="mark({id},'excluded')" title="Never include">kill</button></td>
</tr>""".format(
        id=it["id"], cls="out" if it.get("excluded") else "",
        score="{:.0f}".format(it.get("score") or 0),
        ev=html.escape(ev.get("label", "")), why=html.escape(ev.get("why", "")),
        url=html.escape(it.get("url") or "#"),
        title=html.escape(it.get("title_en") or it.get("title") or "")[:160],
        bits=" &middot; ".join(bits), cn=cn,
        pon="on" if it.get("pinned") else "", eon="on" if it.get("excluded") else "")


@app.route("/")
def index():
    conn = db.connect()
    pipeline.rescore(conn, SETTINGS)
    q = request.args.get("q", "").strip()
    ev = request.args.get("event", "")
    src = request.args.get("source", "")
    days = int(request.args.get("days", SETTINGS.lookback_days))
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()

    sql = ("SELECT * FROM items WHERE relevant=1 "
           "AND COALESCE(published_at, substr(fetched_at,1,10)) >= ?")
    params: List[Any] = [cutoff]
    if q:
        sql += " AND (title LIKE ? OR summary LIKE ?)"
        params += ["%" + q + "%"] * 2
    if ev:
        sql += " AND event_type = ?"
        params.append(ev)
    if src:
        sql += " AND source = ?"
        params.append(src)
    sql += " ORDER BY COALESCE(pinned,0) DESC, score DESC LIMIT 400"
    items = [db.row_to_dict(r) for r in conn.execute(sql, params)]

    sources = [r[0] for r in conn.execute(
        "SELECT DISTINCT source FROM items ORDER BY source")]
    opts = lambda vals, cur: "".join(
        '<option value="{0}"{1}>{0}</option>'.format(html.escape(v), " selected" if v == cur else "")
        for v in vals)

    bar = """<form class="bar" method="get">
      <input name="q" value="{q}" placeholder="search title or summary" size="28">
      <select name="event"><option value="">all event types</option>{evs}</select>
      <select name="source"><option value="">all sources</option>{srcs}</select>
      <input name="days" value="{days}" size="3" title="lookback days">
      <button class="btn ghost">Filter</button>
      <span style="color:#6b6b6b">{n} items &middot; min score for inclusion: {mn}</span>
    </form>""".format(q=html.escape(q), evs=opts(EVENT_TYPES.keys(), ev),
                      srcs=opts(sources, src), days=days, n=len(items), mn=SETTINGS.min_score)

    rows = "".join(_row(it) for it in items) or '<tr><td colspan="4">No items. Try “Fetch now”.</td></tr>'
    body = bar + ('<table><tr><th>Score</th><th>Signal</th><th>Item</th><th></th></tr>'
                  + rows + "</table>")
    flash = request.args.get("msg")
    if flash:
        body = '<div class="flash">{}</div>'.format(html.escape(flash)) + body
    return shell(body, sub="ranked by likelihood of an open mandate", active="index")


@app.post("/api/mark/<int:item_id>/<field>")
def mark(item_id: int, field: str):
    if field not in ("pinned", "excluded"):
        return jsonify(error="bad field"), 400
    conn = db.connect()
    cur = conn.execute("SELECT COALESCE({},0) FROM items WHERE id=?".format(field),
                       (item_id,)).fetchone()
    new = 0 if cur and cur[0] else 1
    updates = {field: new}
    if field == "pinned" and new:
        updates["excluded"] = 0
    if field == "excluded" and new:
        updates["pinned"] = 0
    db.update_item(conn, item_id, **updates)
    conn.commit()
    row = conn.execute("SELECT COALESCE(pinned,0) p, COALESCE(excluded,0) e "
                       "FROM items WHERE id=?", (item_id,)).fetchone()
    return jsonify(pinned=row["p"], excluded=row["e"])


@app.post("/fetch")
def do_fetch():
    conn = db.connect()
    stats = pipeline.ingest(conn, SETTINGS, days=SETTINGS.lookback_days)
    if SETTINGS.use_llm:
        pipeline.enrich(conn, SETTINGS)
    pipeline.rescore(conn, SETTINGS)
    return redirect(url_for("index", msg="Fetched {} new items.".format(sum(stats.values()))))


@app.post("/build")
def do_build():
    conn = db.connect()
    pipeline.rescore(conn, SETTINGS)
    items = pipeline.select(conn, SETTINGS)
    if not items:
        return redirect(url_for("index", msg="Nothing qualified - lower min_score or widen the window."))
    date = dt.date.today().isoformat()
    if SETTINGS.use_llm:
        try:
            text = llm.write_issue(items, SETTINGS.editor_model,
                                   SETTINGS.newsletter_name, date)
        except Exception as exc:                      # noqa: BLE001 - boundary
            text = render.fallback_markdown(items, SETTINGS.newsletter_name, date, SETTINGS)
    else:
        text = render.fallback_markdown(items, SETTINGS.newsletter_name, date, SETTINGS)
    paths = render.write_issue(text, items, SETTINGS, date=date)
    subject = "{} - {}".format(SETTINGS.newsletter_name, date)
    cur = conn.execute(
        "INSERT INTO issues (number, created_at, subject, html_path, md_path, item_count) "
        "VALUES ((SELECT COALESCE(MAX(number),0)+1 FROM issues),?,?,?,?,?)",
        (dt.datetime.now().isoformat(timespec="seconds"), subject,
         paths["html"], paths["md"], len(items)))
    conn.executemany("UPDATE items SET issue_id=? WHERE id=?",
                     [(cur.lastrowid, it["id"]) for it in items])
    conn.commit()
    return redirect(url_for("preview"))


@app.route("/preview")
def preview():
    conn = db.connect()
    row = conn.execute("SELECT * FROM issues ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return shell('<p>No issue built yet. Press <b>Build issue</b>.</p>', active="preview")
    recips = SETTINGS.recipients or []
    send_box = """<form class="bar" method="post" action="{act}">
        <b>{n} items</b> &middot; subject: <code>{subj}</code>
        <button class="btn ghost" name="mode" value="test">Send test to myself</button>
        <button class="btn" name="mode" value="live" onclick="return confirm('Send to {r} recipient(s)?')">Send to list ({r})</button>
      </form>""".format(act=url_for("do_send"), n=row["item_count"],
                        subj=html.escape(row["subject"] or ""), r=len(recips))
    msg = request.args.get("msg")
    flash = '<div class="flash">{}</div>'.format(html.escape(msg)) if msg else ""
    return shell(flash + send_box +
                 '<iframe src="{}"></iframe>'.format(url_for("raw_issue")),
                 sub=row["subject"] or "", active="preview")


@app.route("/issue.html")
def raw_issue():
    conn = db.connect()
    row = conn.execute("SELECT * FROM issues ORDER BY id DESC LIMIT 1").fetchone()
    if not row or not os.path.exists(row["html_path"]):
        return "no issue", 404
    return open(row["html_path"], encoding="utf-8").read()


@app.post("/send")
def do_send():
    conn = db.connect()
    row = conn.execute("SELECT * FROM issues ORDER BY id DESC LIMIT 1").fetchone()
    mode = request.form.get("mode")
    me = (SETTINGS.smtp or {}).get("user") or os.environ.get("SMTP_USER", "")
    if mode == "test":
        result = sender.send(row["html_path"], row["md_path"],
                             "[TEST] " + row["subject"], SETTINGS,
                             recipients=[me] if me else [], dry_run=False)
    else:
        result = sender.send(row["html_path"], row["md_path"], row["subject"],
                             SETTINGS, dry_run=False)
        conn.execute("UPDATE issues SET sent_at=? WHERE id=?",
                     (dt.datetime.now().isoformat(timespec="seconds"), row["id"]))
        conn.commit()
    return redirect(url_for("preview", msg=result))


@app.route("/issues")
def issues():
    conn = db.connect()
    rows = conn.execute("SELECT * FROM issues ORDER BY id DESC LIMIT 50").fetchall()
    if not rows:
        return shell("<p>No issues yet.</p>", active="issues")
    tr = "".join(
        "<tr><td class='sc'>#{n}</td><td>{subj}</td><td>{c} items</td>"
        "<td>{sent}</td><td><a class='ttl' href='file://{p}' target='_blank'>open file</a></td></tr>".format(
            n=r["number"], subj=html.escape(r["subject"] or ""), c=r["item_count"],
            sent=r["sent_at"] or "<span style='color:#aaa'>not sent</span>", p=r["html_path"])
        for r in rows)
    return shell("<table><tr><th>#</th><th>Subject</th><th>Size</th><th>Sent</th><th></th></tr>"
                 + tr + "</table>", active="issues")


def serve(host: str = "127.0.0.1", port: int = 8765, debug: bool = False):
    app.run(host=host, port=port, debug=debug)
