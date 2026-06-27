#!/usr/bin/env python
"""
tiering.py — classify campaigns Gold / Silver / Bronze / Dead by ROAS vs target (margin-tier aware)

Usage:
    python tiering.py campaigns.json [--target-roas 3.0]

Input JSON:
{
  "target_roas": 3.0,                       // global default (or pass --target-roas)
  "margin_tiers": [                          // optional, from account-context
    {"name":"house-brand","min_roas":1.5},
    {"name":"distributed","min_roas":4.0}
  ],
  "campaigns": [
    {"name":"PMax Brand A","cost":6000,"conv_value":18000,"conversions":180,"tier":"distributed"},
    ...
  ]
}

Verdict per campaign uses ROAS relative to its tier target (GUARD-5: a high-margin line accepts a lower
ROAS). Also flags learning risk (<15 conversions). Business-agnostic.
"""
import argparse
import json
import sys


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--target-roas", type=float, default=None)
    a = ap.parse_args()
    with open(a.input, encoding="utf-8") as f:
        data = json.load(f)

    g_target = a.target_roas or data.get("target_roas") or 3.0
    tiers = {t["name"]: t.get("min_roas", g_target) for t in (data.get("margin_tiers") or [])}
    rows = []
    for c in data.get("campaigns") or []:
        cost = c.get("cost", 0) or 0
        roas = (c.get("conv_value", 0) / cost) if cost else 0
        target = tiers.get(c.get("tier"), g_target)
        if cost == 0:
            verdict = "IDLE"
        elif roas >= target * 1.2:
            verdict = "GOLD · scale"
        elif roas >= target:
            verdict = "SILVER · keep"
        elif roas >= target * 0.5:
            verdict = "BRONZE · reduce/fix"
        else:
            verdict = "DEAD · pause"
        learn = "  ⚠ learning (<15 conv)" if (c.get("conversions", 0) < 15 and cost > 0) else ""
        rows.append((cost, c.get("name"), roas, target, c.get("conversions", 0), verdict, learn))

    rows.sort(key=lambda r: -r[0])
    print(f"\n=== Campaign tiering (global target {g_target}x" +
          (f", tiers: {list(tiers)}" if tiers else "") + ") ===\n")
    print(f"  {'Campaign':<26}{'Cost':>10}{'ROAS':>8}{'Tgt':>7}{'Conv':>7}  Verdict")
    for cost, name, roas, target, conv, verdict, learn in rows:
        print(f"  {str(name)[:25]:<26}{cost:>10,.0f}{roas:>8.2f}{target:>7.1f}{conv:>7.0f}  {verdict}{learn}")
    dead = [r for r in rows if r[5].startswith("DEAD")]
    if dead:
        print(f"\nPause candidates (Dead): {', '.join(str(r[1]) for r in dead)} "
              f"— save ~{sum(r[0] for r in dead):,.0f}/period. Check non-paid revenue before pausing.")
    print()


if __name__ == "__main__":
    main()
