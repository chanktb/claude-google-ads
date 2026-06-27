#!/usr/bin/env python
"""
search_term_miner.py — find wasted search terms and propose ready-to-copy negatives

Usage:
    python search_term_miner.py terms.json

Input JSON:
{
  "brand_terms": ["acme", "acme nail"],
  "min_spend": 10,
  "terms": [{"term":"diy acrylic nails","cost":24.5,"conversions":0,"conv_value":0}, ...]
}

Flags terms with >min_spend AND 0 conversions, categorizes them, and proposes negatives already wrapped
([exact] / "phrase"). Respects the "what NOT to block" rules (store / coupon / cheap-brand) from
optimization-playbook.md. Business-agnostic.
"""
import argparse
import json
import sys

CATS = {
    "informational": ["how to", "how do", "diy", "tutorial", "what is", "for beginners", "learn", "guide"],
    "job-seeker": ["job", "jobs", "career", "hiring", "salary", "school", "certification", "training"],
    "location": ["near me", "walk in", "directions", "closest", "open now"],
    "free-intent": ["free", "crack", "torrent", "download"],
}
# Do NOT auto-block these (often convert) unless clearly irrelevant.
PROTECT = ["store", "coupon", "discount code", "promo code", "cheap"]


def wrap(term, exact=True):
    return f"[{term}]" if exact else f'"{term}"'


def categorize(term):
    t = term.lower()
    for cat, pats in CATS.items():
        if any(p in t for p in pats):
            return cat
    return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    a = ap.parse_args()
    with open(a.input, encoding="utf-8") as f:
        data = json.load(f)

    min_spend = data.get("min_spend", 10)
    brand = [b.lower() for b in (data.get("brand_terms") or [])]
    wasted, protected, proposed, brand_kept = [], [], {}, []
    total_waste = 0.0

    for row in data.get("terms") or []:
        term = (row.get("term") or "").strip()
        cost = row.get("cost", 0) or 0
        conv = row.get("conversions", 0) or 0
        if not term or cost <= min_spend or conv > 0:
            continue
        tl = term.lower()
        if any(b in tl for b in brand):
            brand_kept.append((cost, term))   # brand intent — NEVER block (your own traffic)
            continue
        if any(p in tl for p in PROTECT):
            protected.append((term, cost))   # don't reflexively block — review
            continue
        total_waste += cost
        cat = categorize(term) or "irrelevant"
        wasted.append((cost, term, cat))
        # pattern categories -> phrase negative on the signal word; else exact on the full term
        if cat in ("informational", "job-seeker", "location", "free-intent"):
            sig = next((p for p in CATS.get(cat, []) if p in tl), term)
            proposed.setdefault(cat, set()).add(wrap(sig, exact=False))
        else:
            proposed.setdefault("irrelevant", set()).add(wrap(term, exact=True))

    wasted.sort(key=lambda r: -r[0])
    print(f"\n=== Search-term mining (wasted = >${min_spend} spend, 0 conv) ===")
    print(f"Wasted spend flagged: ${total_waste:,.2f} across {len(wasted)} terms\n")
    for cost, term, cat in wasted[:20]:
        print(f"  ${cost:>8,.2f}  [{cat}]  {term}")

    print("\n--- Proposed negatives (ready-to-copy, grouped) ---")
    for cat, items in proposed.items():
        print(f"\n# {cat}")
        for it in sorted(items):
            print(it)

    if protected:
        print("\n--- Protected (do NOT auto-block — review; often convert) ---")
        for term, cost in protected[:10]:
            print(f"  ${cost:>8,.2f}  {term}")
    if brand_kept:
        bt = sum(c for c, _ in brand_kept)
        print(f"\n--- Brand terms — KEEP, never block ({len(brand_kept)} terms, ${bt:,.2f}) ---")
        print("  (0-conv brand terms are brand intent/defense, not waste. Review only for a tracking gap.)")
        for cost, term in sorted(brand_kept, reverse=True)[:8]:
            print(f"  ${cost:>8,.2f}  {term}")
    if not wasted:
        print("\nNo non-brand wasted terms to block — search-term hygiene is clean.")
    print()


if __name__ == "__main__":
    main()
