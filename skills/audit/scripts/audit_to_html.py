#!/usr/bin/env python
"""
audit_to_html.py — render a polished, self-contained, client-ready HTML report from an audit-result.json

Usage:
    python audit_to_html.py <audit-result.json> --output report.html
    python audit_to_html.py <audit-result.json> --fragment        # print inner HTML only (for embedding)

Single-file delivery: inline CSS + inline SVG, no external dependencies, email-safe. Light theme with a
gradient hero, an SVG score donut, category score bars, severity-coded findings, and quick wins.
Business-agnostic — all content comes from the JSON.
"""
import argparse
import html
import json
import math
import sys

SEV = {"Critical": "#c0392b", "High": "#e67e22", "Medium": "#d4a017", "Low": "#7f8c8d"}
GRADE = {"A": "#1e8e5a", "B": "#2E86C1", "C": "#c8860a", "D": "#d9622b", "F": "#c0392b"}


def e(s):
    return html.escape(str(s if s is not None else ""))


def score_color(v):
    return ("#1e8e5a" if v >= 90 else "#2E86C1" if v >= 75 else
            "#c8860a" if v >= 60 else "#d9622b" if v >= 40 else "#c0392b")


def badge(sev):
    return f'<span class="badge" style="background:{SEV.get(sev,"#7f8c8d")}">{e(sev)}</span>'


def donut(score, grade):
    r, cx = 64, 80
    circ = 2 * math.pi * r
    dash = circ * max(0, min(100, score)) / 100
    col = score_color(score)
    return f'''<svg width="160" height="160" viewBox="0 0 160 160" role="img" aria-label="Health score {score}">
  <circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="#e6edf5" stroke-width="14"/>
  <circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="{col}" stroke-width="14" stroke-linecap="round"
    stroke-dasharray="{dash:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cx})"/>
  <text x="{cx}" y="{cx-4}" text-anchor="middle" font-size="40" font-weight="800" fill="#1b2733">{score}</text>
  <text x="{cx}" y="{cx+22}" text-anchor="middle" font-size="14" fill="#5b6b7b">/ 100</text>
</svg>'''


def cat_card(c):
    score = c.get("score", 0)
    col = score_color(score)
    fixable = c.get("fixable") or []
    unver = c.get("unverified") or []
    rows = ""
    for f in fixable:
        rows += f'''<div class="finding">
          <div class="ftop">{badge(f.get("severity"))}<span class="fid">{e(f.get("id"))}</span>
            <span class="fstatus">{e(f.get("status"))}</span>
            {f'<span class="fpts">+{e(f.get("points"))} pts</span>' if f.get("points") else ""}</div>
          <div class="ftitle">{e(f.get("title"))}</div>
          <div class="ffix">{e(f.get("fix"))}</div></div>'''
    unrows = ""
    for u in unver:
        unrows += f'<li>{badge(u.get("severity"))} <b>{e(u.get("id"))}</b> {e(u.get("title"))} — <i>{e(u.get("note"))}</i></li>'
    unblock = f'<div class="unver"><div class="unlabel">Unverified (check in UI — not counted as fail)</div><ul>{unrows}</ul></div>' if unrows else ""
    return f'''<section class="card">
      <div class="chead">
        <div><h3>{e(c.get("name"))}</h3><span class="weight">weight {e(c.get("weight"))}%</span></div>
        <div class="cscore" style="color:{col}">{score}</div>
      </div>
      <div class="bar"><div class="barfill" style="width:{max(0,min(100,score))}%;background:{col}"></div></div>
      {rows or '<div class="allgood">No fixable issues — nicely done.</div>'}
      {unblock}
    </section>'''


def render_inner(d):
    score = d.get("health_score", 0)
    grade = d.get("grade", "")
    acct = d.get("account", {})
    cats = d.get("categories") or []
    qwins = d.get("quick_wins") or []
    notes = d.get("notes") or []
    gcol = GRADE.get(grade, "#2E86C1")

    qrows = "".join(
        f'''<div class="qwin"><div class="qtop">{badge(q.get("severity"))}<span class="qmin">{e(q.get("minutes"))} min</span></div>
        <div class="qtitle">{e(q.get("title"))}</div><div class="qimpact">{e(q.get("impact"))}</div></div>'''
        for q in qwins)
    noterows = "".join(f"<li>{e(n)}</li>" for n in notes)
    waste = d.get("wasted_spend_monthly")
    waste_html = (f'<div class="kpi"><div class="kval">{e(acct.get("currency","$"))} {e(waste)}</div>'
                  f'<div class="klbl">est. wasted / month</div></div>') if waste else ""

    style = '''<style>
    .gar{--ink:#1b2733;--mut:#5b6b7b;--line:#e6edf5;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
      color:var(--ink);max-width:980px;margin:0 auto;padding:0 18px 56px;line-height:1.5;}
    .gar *{box-sizing:border-box;}
    .gar .hero{background:linear-gradient(135deg,#1B4F72,#2E86C1);color:#fff;border-radius:18px;padding:30px 32px;margin:22px 0;
      display:flex;gap:28px;align-items:center;flex-wrap:wrap;box-shadow:0 10px 30px rgba(27,79,114,.25);}
    .gar .hero h1{margin:0 0 4px;font-size:25px;}
    .gar .hero .sub{opacity:.85;font-size:14px;margin-bottom:14px;}
    .gar .hero .donutwrap{background:#fff;border-radius:14px;padding:8px;}
    .gar .grade{display:inline-block;font-size:22px;font-weight:800;background:#fff;color:''' + gcol + ''';
      border-radius:10px;padding:2px 14px;margin-left:8px;}
    .gar .kpis{display:flex;gap:14px;flex-wrap:wrap;margin-top:6px;}
    .gar .kpi{background:rgba(255,255,255,.14);border-radius:10px;padding:10px 14px;}
    .gar .kval{font-size:20px;font-weight:700;}
    .gar .klbl{font-size:12px;opacity:.85;}
    .gar .headline{font-size:15px;background:#eef4fb;border-left:4px solid #2E86C1;border-radius:8px;padding:12px 16px;margin:0 0 22px;}
    .gar h2{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin:30px 0 12px;}
    .gar .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:16px;}
    .gar .card{border:1px solid var(--line);border-radius:14px;padding:18px;background:#fff;box-shadow:0 2px 8px rgba(20,40,60,.04);}
    .gar .chead{display:flex;justify-content:space-between;align-items:flex-start;}
    .gar .chead h3{margin:0;font-size:16px;}
    .gar .weight{font-size:12px;color:var(--mut);}
    .gar .cscore{font-size:30px;font-weight:800;line-height:1;}
    .gar .bar{height:8px;background:var(--line);border-radius:6px;margin:12px 0 14px;overflow:hidden;}
    .gar .barfill{height:100%;border-radius:6px;}
    .gar .finding{border-top:1px solid var(--line);padding:10px 0;}
    .gar .ftop{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--mut);}
    .gar .fid{font-weight:700;color:var(--ink);} .gar .fstatus{font-weight:600;}
    .gar .fpts{margin-left:auto;background:#eafaf0;color:#1e8e5a;border-radius:6px;padding:1px 8px;font-weight:700;}
    .gar .ftitle{font-weight:600;margin:3px 0;} .gar .ffix{font-size:14px;color:var(--mut);}
    .gar .allgood{color:#1e8e5a;font-size:14px;padding:6px 0;}
    .gar .unver{margin-top:10px;background:#fafbfd;border:1px dashed var(--line);border-radius:8px;padding:8px 12px;}
    .gar .unlabel{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin-bottom:4px;}
    .gar .unver ul{margin:0;padding-left:16px;font-size:13px;} .gar .unver li{margin:3px 0;}
    .gar .badge{color:#fff;font-size:11px;font-weight:700;border-radius:6px;padding:1px 8px;}
    .gar .qgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;}
    .gar .qwin{border:1px solid var(--line);border-left:4px solid #c8860a;border-radius:10px;padding:14px;background:#fff;}
    .gar .qtop{display:flex;justify-content:space-between;align-items:center;}
    .gar .qmin{font-size:12px;color:var(--mut);} .gar .qtitle{font-weight:700;margin:6px 0 2px;}
    .gar .qimpact{font-size:13px;color:var(--mut);}
    .gar .notes{font-size:14px;color:var(--mut);background:#fafbfd;border-radius:10px;padding:10px 18px;}
    .gar .foot{text-align:center;color:var(--mut);font-size:12px;margin-top:30px;}
    @media(max-width:520px){.gar .hero{padding:22px;}.gar .grid,.gar .qgrid{grid-template-columns:1fr;}}
    </style>'''

    return f'''{style}<div class="gar">
      <div class="hero">
        <div class="donutwrap">{donut(score, grade)}</div>
        <div style="flex:1;min-width:240px">
          <h1>{e(acct.get("name","Account"))} — Google Ads Health<span class="grade">{e(grade)}</span></h1>
          <div class="sub">Customer {e(acct.get("customer_id"))} · {e(d.get("period",""))} · {e(d.get("generated",""))}</div>
          <div class="kpis">{waste_html}
            <div class="kpi"><div class="kval">{len([f for c in cats for f in (c.get("fixable") or [])])}</div><div class="klbl">fixable findings</div></div>
            <div class="kpi"><div class="kval">{len(qwins)}</div><div class="klbl">quick wins</div></div>
          </div>
        </div>
      </div>
      {f'<div class="headline">{e(d.get("headline"))}</div>' if d.get("headline") else ""}
      <h2>Category breakdown</h2>
      <div class="grid">{"".join(cat_card(c) for c in cats)}</div>
      {f'<h2>Quick wins</h2><div class="qgrid">{qrows}</div>' if qrows else ""}
      {f'<h2>Notes</h2><div class="notes"><ul>{noterows}</ul></div>' if noterows else ""}
      <div class="foot">Generated by claude-google-ads · scores are weighted by severity × category · unverified items are not counted as failures.</div>
    </div>'''


def full_doc(inner, title):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title></head><body style="margin:0;background:#f6f8fb">{inner}</body></html>')


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--output", default=None)
    ap.add_argument("--fragment", action="store_true")
    args = ap.parse_args()
    with open(args.result, encoding="utf-8") as f:
        data = json.load(f)
    inner = render_inner(data)
    if args.fragment:
        sys.stdout.write(inner)
        return
    title = f"{data.get('account',{}).get('name','Account')} — Google Ads Audit"
    out = args.output or "audit-report.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(full_doc(inner, title))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
