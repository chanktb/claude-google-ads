#!/usr/bin/env python
"""
spec_to_pmax_checklist.py — render an ordered, paste-ready Google Ads UI build checklist for a PMax spec

Usage:
    python spec_to_pmax_checklist.py <campaign-spec.json> [--output checklist.md]

PMax can't be imported via Editor CSV, so the pusher's Mode-A path for PMax is a GUIDED build: this turns
the campaign-spec.json into a click-by-click checklist with every value paste-ready (negatives wrapped,
char counts Google-accurate, listing-group tree as include/exclude steps). Campaign is built PAUSED.
Business-agnostic.
"""
import argparse
import json
import sys
import unicodedata

WRAP = {"exact": lambda t: f"[{t}]", "phrase": lambda t: f'"{t}"', "broad": lambda t: f"{t}"}


def wrap(term, mt):
    return WRAP.get((mt or "broad").lower(), WRAP["broad"])(term)


def glen(s):
    s = unicodedata.normalize("NFC", str(s or "")).strip()
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def listing_steps(node, depth, out):
    if not isinstance(node, dict):
        return
    pad = "  " * depth
    if node.get("type") == "subdivision":
        out.append(f"{pad}- [ ] Subdivide on **{node.get('dimension')} = {node.get('value')}**")
        for ch in node.get("children") or []:
            listing_steps(ch, depth + 1, out)
    else:
        act = (node.get("action") or "").upper()
        label = "Everything else" if node.get("dimension") == "other" else f"{node.get('dimension')} = {node.get('value')}"
        out.append(f"{pad}- [ ] {act}: {label}")


def block(items, limit=None):
    lines = []
    for i, t in enumerate(items or [], 1):
        c = f" ({glen(t)})" if limit else ""
        flag = "  <-- OVER LIMIT" if limit and glen(t) > limit else ""
        lines.append(f"{i}.{c} {t}{flag}")
    return "\n".join(lines) if lines else "(none)"


def render(spec):
    camp = spec.get("campaign", {})
    bidding = camp.get("bidding", {})
    o = []
    o.append(f"# PMax build checklist — {camp.get('name','(unnamed)')}")
    o.append("Build in the Google Ads UI. Campaign stays **PAUSED**; review, then enable. "
             "Char counts are Google-accurate; paste blocks as-is.\n")

    o.append("## 1. Create the campaign")
    o.append(f"- [ ] New campaign → campaign type **Performance Max**")
    o.append(f"- [ ] Conversion goals (set at **campaign level**): {camp.get('conversion_goals',{}).get('goals')}")
    o.append(f"- [ ] Campaign name: `{camp.get('name','')}`")
    o.append(f"- [ ] Bidding: **{bidding.get('strategy')}**" +
             (f" — Target ROAS **{bidding.get('target_roas')}**" if bidding.get("target_roas") else " (no target during learning)"))
    o.append(f"- [ ] Daily budget: **{camp.get('daily_budget')}** {spec.get('account',{}).get('currency','')}")
    o.append(f"- [ ] Locations: {camp.get('geo_targeting')}   Languages: {camp.get('language_targeting')}")
    o.append(f"- [ ] **Final URL expansion: OFF**")
    o.append(f"- [ ] **Automatically created assets: OFF**")
    be = camp.get("brand_exclusion", {})
    if be.get("enabled"):
        o.append(f"- [ ] **Brand exclusion: ON** — apply a brand list with: {be.get('brand_list_terms') or '(your brand terms)'}")
    o.append("")

    for i, ag in enumerate(spec.get("asset_groups") or [], 1):
        o.append(f"## 2.{i} Asset group: {ag.get('name','(unnamed)')}")

        o.append("### Products (listing group)")
        steps = []
        listing_steps(ag.get("listing_group"), 0, steps)
        o += steps or ["- [ ] (set listing group)"]

        o.append("### Final URL & display paths")
        o.append(f"- [ ] Final URL: {ag.get('final_url')}  *(verify 200, no redirect, matches these products)*")
        o.append(f"- [ ] Display paths: {' / '.join(ag.get('display_paths') or [])}")

        o.append("### Headlines (≤30) — paste")
        o.append("```\n" + block(ag.get("headlines"), 30) + "\n```")
        o.append("### Long headlines (≤90) — paste")
        o.append("```\n" + block(ag.get("long_headlines"), 90) + "\n```")
        o.append("### Descriptions (≤90; #1 ≤60) — paste")
        o.append("```\n" + block(ag.get("descriptions"), 90) + "\n```")

        o.append("### Images / videos to upload")
        for im in ag.get("image_assets") or []:
            o.append(f"- [ ] image/{im.get('role')} {im.get('spec')} — source: {im.get('source')}")
        for vd in ag.get("video_assets") or []:
            o.append(f"- [ ] video/{vd.get('orientation')} {vd.get('spec')} — source: {vd.get('source')}")

        sls = ag.get("sitelinks") or []
        if sls:
            o.append("### Sitelinks (text ≤25, desc ≤35)")
            for sl in sls:
                o.append(f"- [ ] {sl.get('text')} | {sl.get('description1')} | {sl.get('description2')} | {sl.get('final_url')}")

        o.append("### Search themes (up to 50) — paste")
        o.append("```\n" + ("\n".join(ag.get("search_themes") or []) or "(none)") + "\n```")

        sig = ag.get("audience_signal") or {}
        if any(sig.values()):
            o.append("### Audience signal")
            for stype, vals in sig.items():
                for v in vals or []:
                    o.append(f"- [ ] {stype}: {v}")
        o.append("")

    negs = spec.get("campaign_negatives") or []
    if negs or spec.get("shared_negative_lists"):
        o.append("## 3. Campaign negative keywords — paste (Campaign settings > Negative keywords)")
        o.append("```\n" + "\n".join(wrap(n.get("text"), n.get("match_type")) for n in negs) + "\n```")
        for sl in spec.get("shared_negative_lists") or []:
            o.append(f"- [ ] also apply shared list: {sl}")
        o.append("")

    o.append("## 4. Review & finish")
    o.append("- [ ] Ad strength Good+ on each asset group")
    o.append("- [ ] No listing-group overlap (each product in one asset group)")
    o.append("- [ ] Campaign saved **PAUSED** — review, then enable")
    return "\n".join(o) + "\n"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    if spec.get("campaign_type") not in ("performance_max", "demand_gen"):
        sys.exit(f"This checklist targets PMax/Demand Gen specs (got '{spec.get('campaign_type')}').")
    text = render(spec)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {args.output}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
