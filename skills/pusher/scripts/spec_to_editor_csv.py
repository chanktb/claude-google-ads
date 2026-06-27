#!/usr/bin/env python
"""
spec_to_editor_csv.py — render a Google Ads Editor import CSV from a Search/Branded campaign-spec.json

Usage:
    python spec_to_editor_csv.py <campaign-spec.json> --output editor-import.csv

Produces one row per entity using Google Ads Editor's column conventions (Criterion Type carries both
keyword match types and negatives). Import via Editor: Account > Import > From file, then REVIEW before
posting. Editor's accepted headers can change between versions — verify the mapping on import.

Search / Branded Search only (these push cleanly via Editor). PMax is mostly API-or-UI (see pusher SKILL).
Business-agnostic. Campaign is emitted PAUSED.
"""
import argparse
import csv
import json
import sys

COLUMNS = (
    ["Campaign", "Campaign Type", "Campaign Daily Budget", "Bid Strategy Type",
     "Ad Group", "Keyword", "Criterion Type", "Ad type"]
    + [f"Headline {i}" for i in range(1, 16)]
    + [f"Description {i}" for i in range(1, 5)]
    + ["Path 1", "Path 2", "Final URL", "Status"]
)

BID_MAP = {
    "maximize_conversions": "Maximize conversions",
    "maximize_conversion_value": "Maximize conversion value",
    "target_cpa": "Target CPA",
    "target_roas": "Target ROAS",
    "target_impression_share": "Target impression share",
    "maxconv-then-tcpa": "Maximize conversions",
    "maxconv-value-then-troas": "Maximize conversion value",
}
MATCH = {"exact": "Exact", "phrase": "Phrase", "broad": "Broad"}


def row(**kw):
    return {c: kw.get(c, "") for c in COLUMNS}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    ctype = spec.get("campaign_type")
    if ctype not in ("search", "branded_search"):
        sys.exit(f"This generator handles Search/Branded specs only (got '{ctype}'). PMax = guided/API.")

    camp = spec.get("campaign", {})
    cname = camp.get("name", "Campaign")
    bidding = camp.get("bidding", {})
    bid = BID_MAP.get(bidding.get("strategy"), "Maximize conversions")
    rows = []

    # Campaign row (always Paused on create)
    rows.append(row(Campaign=cname, **{"Campaign Type": "Search",
                "Campaign Daily Budget": camp.get("daily_budget", ""),
                "Bid Strategy Type": bid, "Status": "Paused"}))

    # Campaign-level negatives
    for n in spec.get("campaign_negatives") or []:
        mt = MATCH.get(n.get("match_type"), "Phrase")
        rows.append(row(Campaign=cname, Keyword=n.get("text"),
                        **{"Criterion Type": f"Campaign Negative {mt}"}))

    for ag in spec.get("ad_groups") or []:
        ag_name = ag.get("name", "Ad Group")
        rows.append(row(Campaign=cname, **{"Ad Group": ag_name, "Status": "Paused"}))

        for kw in ag.get("keywords") or []:
            rows.append(row(Campaign=cname, **{"Ad Group": ag_name},
                            Keyword=kw.get("text"),
                            **{"Criterion Type": MATCH.get(kw.get("match_type"), "Phrase")}))

        for n in ag.get("negatives") or []:
            mt = MATCH.get(n.get("match_type"), "Phrase")
            rows.append(row(Campaign=cname, **{"Ad Group": ag_name}, Keyword=n.get("text"),
                            **{"Criterion Type": f"Negative {mt}"}))

        rsa = ag.get("rsa") or {}
        if rsa:
            heads = [h.get("text", "") for h in rsa.get("headlines") or []][:15]
            descs = [d.get("text", "") for d in rsa.get("descriptions") or []][:4]
            paths = (rsa.get("paths") or []) + ["", ""]
            ad = row(Campaign=cname, **{"Ad Group": ag_name, "Ad type": "Responsive search ad",
                     "Final URL": rsa.get("final_url", ""), "Path 1": paths[0], "Path 2": paths[1],
                     "Status": "Paused"})
            for i, h in enumerate(heads, 1):
                ad[f"Headline {i}"] = h
            for i, d in enumerate(descs, 1):
                ad[f"Description {i}"] = d
            rows.append(ad)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        wtr = csv.DictWriter(f, fieldnames=COLUMNS)
        wtr.writeheader()
        wtr.writerows(rows)

    print(f"Wrote {args.output}: {len(rows)} rows ({ctype}).")
    print("Import via Google Ads Editor: Account > Import > From file. REVIEW before posting.")
    print("Campaign is PAUSED. Verify the column mapping on import (Editor headers vary by version).")


if __name__ == "__main__":
    main()
