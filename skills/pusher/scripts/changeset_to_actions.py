#!/usr/bin/env python
"""
changeset_to_actions.py — render a VALIDATED change-set.json into operator actions

Usage:
    python changeset_to_actions.py <change-set.json> [--output-dir .]

Emits (into output-dir):
  - CHANGE-PLAN.md          ordered, checkboxed operator plan (the deliverable), grouped by push path,
                            each step with its data reason + discipline note; a summary with total $/mo.
  - negatives-editor.csv    Google Ads Editor import for Search/Branded negatives (if any).
  - negatives-paste.txt     ready-to-paste negatives wrapped [exact] / "phrase" (campaign + shared list).

Run validate_changeset.py FIRST — this renderer assumes the safety gates already passed. It still marks any
within-cooldown scale action as HELD (defense in depth) rather than a do-now step. Business-agnostic.
"""
import argparse
import csv
import json
import os
import sys

MATCH_CSV = {"exact": "Exact", "phrase": "Phrase"}


def wrap(text, mt):
    return f"[{text}]" if mt == "exact" else (f'"{text}"' if mt == "phrase" else text)


def held_scale(a):
    """A budget/target move whose target is still in cooldown — must not be applied yet."""
    return a.get("type") in ("adjust_budget", "adjust_target_roas") and bool((a.get("target") or {}).get("within_cooldown"))


def fmt_money(n):
    try:
        return f"${float(n):,.0f}"
    except (TypeError, ValueError):
        return "—"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("changeset")
    ap.add_argument("--output-dir", default=".")
    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    with open(args.changeset, encoding="utf-8") as f:
        cs = json.load(f)
    if cs.get("kind") != "change-set":
        sys.exit("Not a change-set (kind != 'change-set').")

    actions = cs.get("actions") or []
    acct = cs.get("account") or {}

    # --- Negatives → Editor CSV (Search/Branded) + paste (all) ---
    csv_rows, paste_groups = [], {}
    for a in actions:
        if a.get("type") != "add_negatives":
            continue
        tgt = a.get("target") or {}
        camp = tgt.get("campaign", "")
        scope = a.get("scope", "campaign")
        dest = a.get("list_name") if scope == "shared_list" else camp
        key = f"{'List' if scope == 'shared_list' else 'Campaign'}: {dest}"
        for n in a.get("negatives") or []:
            mt = n.get("match_type", "phrase")
            paste_groups.setdefault(key, []).append(wrap(n.get("text", ""), mt))
            # Editor CSV: only Search/Branded campaign-scope negatives import cleanly.
            if tgt.get("campaign_type") in ("search", "branded_search") and scope == "campaign":
                csv_rows.append({"Campaign": camp, "Keyword": n.get("text", ""),
                                 "Criterion Type": f"Campaign Negative {MATCH_CSV.get(mt, 'Phrase')}",
                                 "Status": "Enabled"})

    csv_path = paste_path = None
    if csv_rows:
        csv_path = os.path.join(args.output_dir, "negatives-editor.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["Campaign", "Keyword", "Criterion Type", "Status"])
            w.writeheader()
            w.writerows(csv_rows)
    if paste_groups:
        paste_path = os.path.join(args.output_dir, "negatives-paste.txt")
        with open(paste_path, "w", encoding="utf-8") as f:
            for key, terms in paste_groups.items():
                f.write(f"# {key}\n" + "\n".join(terms) + "\n\n")

    # --- CHANGE-PLAN.md ---
    L = []
    L.append("# Change Plan — operator actions")
    L.append(f"Account `{acct.get('customer_id','?')}` · {len(actions)} actions · "
             f"source: {(cs.get('provenance') or {}).get('source_report','optimizer')}")
    L.append("\n> Apply behind the approval gate. Budget/target moves create no spend surprise; "
             "negatives only remove waste. Nothing here enables a paused campaign.\n")

    # Summary
    hard = sum(float(a.get("est_impact_per_mo") or 0) for a in actions)
    by_type = {}
    for a in actions:
        by_type[a.get("type")] = by_type.get(a.get("type"), 0) + 1
    L.append("## Summary")
    L.append(f"- **Est. recoverable / gained:** {fmt_money(hard)}/mo (sum of itemized impacts)")
    L.append("- **Actions by type:** " + ", ".join(f"{k} ×{v}" for k, v in sorted(by_type.items())))
    held = [a for a in actions if held_scale(a)]
    if held:
        L.append(f"- **⚠ HELD by cooldown:** {len(held)} scale move(s) — defer until the campaign's "
                 "cooldown clears; do NOT apply now.")
    L.append("")

    # Negatives section
    neg_actions = [a for a in actions if a.get("type") == "add_negatives"]
    if neg_actions:
        L.append("## 1. Negatives (remove wasted spend)")
        if csv_path:
            L.append(f"- [ ] Import **{os.path.basename(csv_path)}** via Google Ads Editor → Account → "
                     "Import → From file → REVIEW → post (Search/Branded campaign negatives).")
        if paste_path:
            L.append(f"- [ ] Shared lists / PMax campaign negatives: paste from **"
                     f"{os.path.basename(paste_path)}** into the right list/campaign in the UI.")
        for a in neg_actions:
            tgt = a.get("target") or {}
            dest = a.get("list_name") if a.get("scope") == "shared_list" else tgt.get("campaign")
            terms = ", ".join(wrap(n.get("text", ""), n.get("match_type", "phrase"))
                              for n in a.get("negatives") or [])
            L.append(f"  - `{dest}` ({a.get('scope','campaign')}): {terms}")
            L.append(f"    - _why:_ {a.get('reason','')}")
        L.append("")

    # UI-applied actions, ordered by impact
    ui_types = ["pause", "exclude_geo", "exclude_products", "exclude_placements",
                "adjust_budget", "adjust_target_roas", "add_extensions", "add_audience_signal",
                "add_assets", "replace_asset"]
    titles = {
        "pause": "Pause dead weight", "exclude_geo": "Exclude weak geos",
        "exclude_products": "Exclude burning products (listing-group)",
        "exclude_placements": "Exclude placements (account-level)",
        "adjust_budget": "Budget moves", "adjust_target_roas": "Target ROAS steps",
        "add_extensions": "Add extensions (free SERP real estate)",
        "add_audience_signal": "Add audience signals", "add_assets": "Add creative assets",
        "replace_asset": "Replace low assets",
    }
    steps = {
        "pause": "UI → Campaigns/Asset groups → select the entity → Edit → Pause.",
        "exclude_geo": "UI → campaign → Settings → Locations → add as EXCLUDED (PMax has no per-geo bid).",
        "exclude_products": "UI → PMax campaign → asset group → Listing groups → subdivide → set the SKU to Excluded.",
        "exclude_placements": "UI → Account → Content/Placement exclusions → add the placements.",
        "adjust_budget": "UI → campaign → Budget → set the new daily budget (prefer a Monday).",
        "adjust_target_roas": "UI → campaign → Bidding → edit the Target ROAS.",
        "add_extensions": "UI → campaign → Assets → add sitelinks / callouts / structured snippets.",
        "add_audience_signal": "UI → PMax → asset group → Audience signal → add the seed.",
        "add_assets": "UI → asset group → Assets → add the headlines/images/video.",
        "replace_asset": "UI → asset group → Assets → remove the LOW asset, add the replacement.",
    }
    n_sec = 2 if neg_actions else 1
    for t in ui_types:
        items = [a for a in actions if a.get("type") == t]
        if not items:
            continue
        items.sort(key=lambda a: -float(a.get("est_impact_per_mo") or 0))
        L.append(f"## {n_sec}. {titles[t]}")
        n_sec += 1
        for a in items:
            tgt = a.get("target") or {}
            where = tgt.get("campaign", "")
            sub = tgt.get("asset_group") or tgt.get("ad_group")
            if sub:
                where += f" › {sub}"
            head = where
            if t == "adjust_budget":
                head += f" · {fmt_money(a.get('current_daily'))}→{fmt_money(a.get('new_daily'))}/day ({a.get('direction','')})"
            elif t == "adjust_target_roas":
                head += f" · tROAS {a.get('current')}→{a.get('new')}"
            elif t == "pause":
                head += f" · pause {a.get('entity','')}"
            imp = a.get("est_impact_per_mo")
            tag = " **[⚠ HELD — cooldown, defer]**" if held_scale(a) else ""
            L.append(f"- [ ] **{head}**"
                     + (f" — {fmt_money(imp)}/mo" if imp else "") + tag)
            L.append(f"  - _how:_ {steps[t]}")
            L.append(f"  - _why:_ {a.get('reason','')}")
            details = []
            if t == "exclude_geo":
                details = [loc.get("name", "") for loc in a.get("locations") or []]
            elif t == "exclude_products":
                details = [f"{p.get('title','')} [{p['item_id']}]" if p.get("item_id") else p.get("title", "")
                           for p in a.get("products") or []]
            elif t == "add_extensions":
                if a.get("sitelinks"): details.append(f"sitelinks: {len(a['sitelinks'])}")
                if a.get("callouts"): details.append("callouts: " + "; ".join(a["callouts"]))
                if a.get("snippets"): details.append(f"snippets: {len(a['snippets'])}")
            elif t == "add_audience_signal":
                s = a.get("signal") or {}
                details = [f"{s.get('kind','')}: {s.get('value','')}"]
            if details:
                L.append("  - _items:_ " + " | ".join(d for d in details if d))
        L.append("")

    L.append("---")
    L.append("After applying: hand monitoring to `tracker`; re-audit after the cooldown to confirm lift. "
             "Re-run `/google-ads-optimize` next cycle for the next change-set.")

    plan_path = os.path.join(args.output_dir, "CHANGE-PLAN.md")
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    print(f"Wrote {plan_path}")
    if csv_path:
        print(f"Wrote {csv_path} ({len(csv_rows)} negative rows)")
    if paste_path:
        print(f"Wrote {paste_path}")
    print(f"\n{len(actions)} actions · {fmt_money(hard)}/mo itemized"
          + (f" · {len(held)} HELD by cooldown" if held else ""))
    print("Render only — apply behind the approval gate; campaigns stay as-is until the operator acts.")


if __name__ == "__main__":
    main()
