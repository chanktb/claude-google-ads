#!/usr/bin/env python
"""
forecaster.py — budget -> conversions / CPA / ROAS bands

Usage:
    python forecaster.py --budget 80 --cpc 1.20 --cvr 0.03 --aov 99 [--days 30] [--target-roas 3.0]

Derive CPC/CVR from the account's own recent data when possible; use benchmark bands only for new accounts
(see references/forecasting-and-benchmarks.md). Output is a BAND (+/-20%), never a single promise.
Business-agnostic.
"""
import argparse
import sys


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, required=True, help="daily budget")
    ap.add_argument("--cpc", type=float, required=True)
    ap.add_argument("--cvr", type=float, required=True, help="conversion rate as a decimal, e.g. 0.03")
    ap.add_argument("--aov", type=float, required=True)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--target-roas", type=float, default=None)
    a = ap.parse_args()

    monthly_budget = a.budget * a.days
    clicks = monthly_budget / a.cpc if a.cpc else 0
    conv = clicks * a.cvr
    revenue = conv * a.aov
    roas = revenue / monthly_budget if monthly_budget else 0
    cpa = monthly_budget / conv if conv else 0

    print(f"\n=== Forecast ({a.days} days) ===")
    print(f"Inputs: budget {a.budget}/day (={monthly_budget:.0f}), CPC {a.cpc}, CVR {a.cvr*100:.1f}%, AOV {a.aov}\n")

    def band(label, mid, fmt):
        lo, hi = mid * 0.8, mid * 1.2
        print(f"  {label:<14} {fmt(lo)}  ..  {fmt(mid)}  ..  {fmt(hi)}")

    money = lambda v: f"{v:,.0f}"
    band("Clicks", clicks, money)
    band("Conversions", conv, lambda v: f"{v:,.0f}")
    band("Revenue", revenue, lambda v: f"${v:,.0f}")
    band("ROAS", roas, lambda v: f"{v:.2f}x")
    band("CPA", cpa, lambda v: f"${v:,.2f}")

    max_camps = conv / 20 if conv else 0
    print(f"\nLearning capacity: ~{conv:.0f} conv/mo -> the budget can feed about "
          f"{max(1,int(max_camps))} campaign(s)/asset group(s) at the ~20-conv learning floor.")
    if max_camps < 1:
        print("  ! Below one learning unit — consolidate, don't split.")
    if a.target_roas:
        verdict = "on track" if roas >= a.target_roas else "below target"
        print(f"Target ROAS {a.target_roas}x: mid-case is {verdict} (mid ROAS {roas:.2f}x).")
    print("\nBands are estimates (+/-20%); derive CPC/CVR from real account data when available.\n")


if __name__ == "__main__":
    main()
