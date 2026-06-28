#!/usr/bin/env python
"""
d14_product_report.py — render the D14 product/feed check (Ads shopping_performance_view × store inventory)
into ONE self-contained, visual HTML the operator can act on immediately: every product is a CLICKABLE link
to its live storefront URL, with SKU, price, availability, inventory policy, clicks and a burn bar.

INPUT: the per-item JSON the D14 pull produces (one row per burning product, store-inventory-joined). Default
shape (every field optional — the renderer degrades gracefully; unknown fields ignored):
[
  {
    "campaign": "Lite", "title": "...", "brand": "kupa",
    "cost_30d": 83.67, "clicks_30d": 36, "imp_30d": 6692,
    "product_onlineStoreUrl": "https://store/products/handle",   # the clickable check URL
    "variant_sku": "KUPA-RG", "variant_price": "385.13", "variant_compareAtPrice": null,
    "variant_inventoryPolicy": "DENY",
    "total_available_all_locations": 1,                          # (falls back to variant_inventoryQuantity)
    "classification": "OOS_DENY|LOW_STOCK|IN_STOCK_NEEDS_PDP_AUDIT",
    "reason": "..."
  }, ...
]

USAGE:
  python d14_product_report.py shopify_inventory_check.json --out-dir . \
        [--account "ND Nail Supply"] [--window "2026-05-29 → 2026-06-27 (30d)"] [--source "..."]
Writes D14-PRODUCT-CHECK.html next to the input (or in --out-dir).
"""
import json, sys, argparse, os, html

sys.stdout.reconfigure(encoding="utf-8")

# Classification metadata: order, label, palette (matches AUDIT.html: red/amber/blue), action.
CLASS = {
    "OOS_DENY": (0, "🚫 Out of stock — store refuses orders", "#ef4444", "#fef2f2", "#b91c1c",
                 "Exclude from the feed now — PMax is paying for clicks the store can't fulfill."),
    "LOW_STOCK": (1, "⚠️ Low stock — going OOS imminently", "#f59e0b", "#fffbeb", "#b45309",
                  "Restock to a sane buffer OR exclude from the feed."),
    "IN_STOCK_NEEDS_PDP_AUDIT": (2, "🔍 In stock — needs PDP / price / intent audit", "#3b82f6", "#eff6ff", "#1d4ed8",
                  "Investigate the PDP: price competitiveness, photos, reviews, payment badges, intent match."),
}
DEF_CLASS = (9, "Other", "#64748b", "#f1f5f9", "#475569", "Review.")


def esc(x):
    return html.escape("" if x is None else str(x), quote=True)


def num(x, d=0.0):
    try:
        return float(x)
    except Exception:
        return d


def money(x):
    return f"${num(x):,.2f}"


def avail_of(it):
    v = it.get("total_available_all_locations")
    if v is None:
        v = it.get("variant_inventoryQuantity", it.get("product_totalInventory"))
    try:
        return int(v)
    except Exception:
        return None


def avail_cell(it):
    a = avail_of(it)
    if a is None:
        return '<span style="color:#64748b">—</span>'
    if a < 0:
        return f'<b style="color:#b91c1c">{a} ⚠ oversold</b>'
    if a == 0:
        return '<b style="color:#b91c1c">0</b>'
    if a <= 3:
        return f'<b style="color:#b45309">{a}</b>'
    return f'<span style="color:#059669">{a}</span>'


def price_cell(it):
    p = it.get("variant_price")
    cap = it.get("variant_compareAtPrice")
    if p in (None, ""):
        return "—"
    out = f"${num(p):,.2f}"
    if cap not in (None, "", "0", 0) and num(cap) > num(p):
        out = f'<span style="text-decoration:line-through;color:#94a3b8">${num(cap):,.0f}</span> {out}'
    return out


def title_link(it):
    t = esc(it.get("title") or it.get("variant_sku") or "(untitled)")
    url = it.get("product_onlineStoreUrl") or it.get("url")
    if url:
        return f'<a href="{esc(url)}" target="_blank" rel="noopener" style="color:#1d4ed8;text-decoration:none;font-weight:600">{t} ↗</a>'
    return f'<b>{t}</b>'


def bar(val, mx, color):
    w = 0 if mx <= 0 else max(2, round(val / mx * 100))
    return (f'<span style="display:inline-block;width:120px;height:8px;background:#eef2f7;border-radius:99px;'
            f'vertical-align:middle;overflow:hidden;margin-right:6px"><span style="display:block;height:100%;'
            f'width:{w}%;background:{color};border-radius:99px"></span></span>')


def prod_table(items, color):
    mx = max((num(i.get("cost_30d")) for i in items), default=0.0)
    rows = []
    for it in sorted(items, key=lambda x: -num(x.get("cost_30d"))):
        pol = (it.get("variant_inventoryPolicy") or "").upper()
        pol_pill = (f'<span style="font-size:10.5px;font-weight:700;background:#fef2f2;color:#b91c1c;'
                    f'border-radius:999px;padding:2px 8px">DENY</span>' if pol == "DENY"
                    else (f'<span style="font-size:10.5px;color:#64748b">{esc(pol)}</span>' if pol else ""))
        camp = esc(it.get("campaign") or it.get("campaign_name") or "")
        camp_pill = (f'<span style="font-size:10.5px;font-weight:600;background:#0f172a;color:#fff;'
                     f'border-radius:999px;padding:2px 8px">{camp}</span>') if camp else ""
        reason = esc(it.get("reason") or "")
        rsn = f'<div style="font-size:11.5px;color:#64748b;margin-top:3px">{reason}</div>' if reason else ""
        cost = num(it.get("cost_30d"))
        rows.append(f"""<tr>
<td style="padding:9px 10px;border-top:1px solid #eef1f5">{title_link(it)} {camp_pill}{rsn}</td>
<td style="padding:9px 10px;border-top:1px solid #eef1f5;font-family:ui-monospace,Menlo,monospace;font-size:12px;white-space:nowrap">{esc(it.get('variant_sku') or '—')}</td>
<td style="padding:9px 10px;border-top:1px solid #eef1f5;text-align:right;white-space:nowrap">{price_cell(it)}</td>
<td style="padding:9px 10px;border-top:1px solid #eef1f5;text-align:center;white-space:nowrap">{avail_cell(it)}{('<br>'+pol_pill) if pol_pill else ''}</td>
<td style="padding:9px 10px;border-top:1px solid #eef1f5;text-align:right">{int(num(it.get('clicks_30d')))}</td>
<td style="padding:9px 10px;border-top:1px solid #eef1f5;white-space:nowrap;text-align:right">{bar(cost,mx,color)}<b>{money(cost)}</b></td>
</tr>""")
    return ("""<table style="width:100%;border-collapse:collapse;font-size:13px">
<thead><tr style="text-align:left;color:#64748b;font-size:11.5px;text-transform:uppercase;letter-spacing:.03em">
<th style="padding:6px 10px">Product (click to open ↗)</th><th style="padding:6px 10px">SKU</th>
<th style="padding:6px 10px;text-align:right">Price</th><th style="padding:6px 10px;text-align:center">Avail</th>
<th style="padding:6px 10px;text-align:right">Clicks</th><th style="padding:6px 10px;text-align:right">Burn 30d</th>
</tr></thead><tbody>""" + "".join(rows) + "</tbody></table>")


def build(items, account, window, source):
    total_burn = sum(num(i.get("cost_30d")) for i in items)
    groups = {}
    for it in items:
        groups.setdefault(it.get("classification") or "Other", []).append(it)
    order = sorted(groups.items(), key=lambda kv: CLASS.get(kv[0], DEF_CLASS)[0])
    concrete = sum(num(i.get("cost_30d")) for k, g in groups.items()
                   for i in g if k in ("OOS_DENY", "LOW_STOCK"))

    def kpi(label, val, col="#0f172a"):
        return (f'<div style="background:#f8fafc;border:1px solid #eef1f5;border-radius:10px;padding:9px 14px">'
                f'<div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.03em">{label}</div>'
                f'<div style="font-size:18px;font-weight:700;color:{col}">{val}</div></div>')

    H = [f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(account)} — D14 Product Check</title></head>
<body style="margin:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,Arial;color:#0f172a;background:#f6f8fb">
<div style="max-width:1080px;margin:0 auto;padding:22px 18px 60px">
<div style="background:#fff;border:1px solid #eef1f5;border-radius:18px;padding:18px 22px;box-shadow:0 1px 3px rgba(15,23,42,.05)">
<div style="font-size:12px;color:#64748b;font-weight:600;letter-spacing:.04em">D14 · PRODUCT &amp; FEED CHECK</div>
<h1 style="margin:4px 0 6px;font-size:24px">{esc(account)} — zero-conversion product burn</h1>
<div style="font-size:12.5px;color:#64748b">{esc(window)}{(' · '+esc(source)) if source else ''}</div>
<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px">
{kpi('Products burning', f'{len(items)}')}
{kpi('Total burn 30d', money(total_burn), '#b91c1c')}
{kpi('Concrete recoverable', money(concrete)+'/30d', '#b45309')}
{''.join(kpi(CLASS.get(k,DEF_CLASS)[1].split(' ')[0]+' '+k.replace('_',' ').title(), f"{len(g)} · "+money(sum(num(i.get('cost_30d')) for i in g)), CLASS.get(k,DEF_CLASS)[4]) for k,g in order)}
</div></div>
<div style="font-size:12.5px;border-radius:10px;padding:11px 14px;margin:14px 0;background:#fef2f2;border:1px solid #fecaca;color:#991b1b">
<b>{len(items)} products burned {money(total_burn)} / 30d with zero conversions.</b>
Concrete OOS + low-stock waste = <b>{money(concrete)}/30d</b> — PMax is paying for clicks the store can't fulfill (or will run out of within days).
</div>"""]

    for k, g in order:
        _, label, col, bg, txt, action = CLASS.get(k, DEF_CLASS)
        gb = sum(num(i.get("cost_30d")) for i in g)
        H.append(f"""<div style="background:#fff;border:1px solid #eef1f5;border-radius:18px;box-shadow:0 1px 3px rgba(15,23,42,.05);margin:14px 0;overflow:hidden">
<div style="background:{bg};border-bottom:1px solid #eef1f5;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
<div style="font-weight:700;color:{txt}">{esc(label)}</div>
<div style="font-size:13px;color:{txt}"><b>{len(g)}</b> products · <b>{money(gb)}</b>/30d</div></div>
<div style="padding:6px 8px 12px">{prod_table(g, col)}
<div style="font-size:12.5px;color:#475569;padding:8px 10px 2px"><b>Action:</b> {esc(action)}</div></div></div>""")

    # full SKU appendix — every product, one place, all clickable
    H.append("""<div style="background:#fff;border:1px solid #eef1f5;border-radius:18px;box-shadow:0 1px 3px rgba(15,23,42,.05);margin:14px 0;overflow:hidden">
<div style="padding:12px 16px;border-bottom:1px solid #eef1f5;font-weight:700">Full SKU list — all burning products (click any to open the live page ↗)</div>
<div style="padding:6px 8px 12px">""" + prod_table(items, "#94a3b8") + "</div></div>")

    H.append(f'<div style="text-align:center;color:#94a3b8;font-size:11.5px;margin-top:20px">Generated by claude-google-ads · D14 product check · {esc(account)}</div>')
    H.append("</div></body></html>")
    return "".join(H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="per-item D14 inventory-join JSON (list)")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--account", default="Account")
    ap.add_argument("--window", default="last 30 days")
    ap.add_argument("--source", default="Google Ads shopping_performance_view × store inventory")
    a = ap.parse_args()
    data = json.load(open(a.input, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("items") or data.get("products") or data.get("result") or []
    out_dir = a.out_dir or os.path.dirname(os.path.abspath(a.input))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "D14-PRODUCT-CHECK.html")
    open(out, "w", encoding="utf-8").write(build(data, a.account, a.window, a.source))
    print(f"Wrote {out} ({len(data)} products)")


if __name__ == "__main__":
    main()
