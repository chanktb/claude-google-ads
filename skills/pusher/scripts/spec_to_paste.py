#!/usr/bin/env python
"""
spec_to_paste.py — render ready-to-copy keyword / negative / search-theme blocks from a campaign-spec.json

Usage:
    python spec_to_paste.py <campaign-spec.json> [--output paste.txt]

Solves the recurring time-sink: keywords and negatives that are classified by match type but NOT wrapped,
so the operator has to re-format before pasting. Here every term is wrapped the way the Google Ads UI /
Editor parse it — paste the block straight in.

Match-type wrappers:  Exact -> [term]   Phrase -> "term"   Broad -> term (bare)
PMax search themes are NOT match-typed (one short phrase per line).
"""
import argparse
import json
import sys

WRAP = {"exact": lambda t: f"[{t}]", "phrase": lambda t: f'"{t}"', "broad": lambda t: f"{t}"}


def wrap(term, match_type):
    return WRAP.get((match_type or "broad").lower(), WRAP["broad"])(term)


def render(spec):
    out = []
    ctype = spec.get("campaign_type")
    camp = spec.get("campaign", {})
    out.append(f"=== Campaign: {camp.get('name','(unnamed)')}  [{ctype}] ===")
    out.append("Paste each block into the matching Google Ads UI / Editor field. Terms are pre-wrapped.\n")

    negs = spec.get("campaign_negatives") or []
    if negs:
        out.append("--- CAMPAIGN NEGATIVE KEYWORDS (Campaign > Negative keywords) ---")
        out += [wrap(n.get("text"), n.get("match_type")) for n in negs]
        for sl in spec.get("shared_negative_lists") or []:
            out.append(f"# also apply shared list: {sl}")
        out.append("")

    if ctype in ("search", "branded_search"):
        for ag in spec.get("ad_groups") or []:
            out.append(f"--- AD GROUP: {ag.get('name','(unnamed)')} ---")
            kws = ag.get("keywords") or []
            if kws:
                out.append("Keywords:")
                out += [wrap(k.get("text"), k.get("match_type")) for k in kws]
            agn = ag.get("negatives") or []
            if agn:
                out.append("Negative keywords (ad group):")
                out += [wrap(n.get("text"), n.get("match_type")) for n in agn]
            out.append("")
    elif ctype in ("performance_max", "demand_gen"):
        for ag in spec.get("asset_groups") or []:
            themes = ag.get("search_themes") or []
            if themes:
                out.append(f"--- ASSET GROUP: {ag.get('name','(unnamed)')} - search themes (max 50) ---")
                out += [str(t) for t in themes]
                out.append("")

    return "\n".join(out).rstrip() + "\n"


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
    text = render(spec)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {args.output}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
