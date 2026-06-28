#!/usr/bin/env python
"""
search_term_miner.py — find wasted search terms and propose ready-to-copy negatives

Usage:
    python search_term_miner.py terms.json

Input JSON:
{
  "brand_terms": ["acme", "acme nail"],        # YOUR OWN house brand — never block
  "carried_brands": ["kupa","chaun legend","kiara sky","dnd","opi","sns"],
                                               # brands the store RESELLS (from the catalog / feed `brand` field).
                                               # A search for a brand you SELL is buying intent, NOT a competitor.
  "brands_with_own_campaign": ["dnd","opi"],   # carried brands that ALREADY have a dedicated campaign.
                                               # For a catch-all (e.g. "Lite"), blocking these ROUTES traffic to
                                               # the specialist campaign (anti-cannibalization) — legitimate.
                                               # A carried brand WITHOUT its own campaign must NEVER be blocked:
                                               # the catch-all is its only home (it's there because it isn't
                                               # split out YET, not because it's a competitor).
  "min_spend": 10,
  "terms": [{"term":"diy acrylic nails","cost":24.5,"conversions":0,"conv_value":0}, ...]
}

Flags terms with >min_spend AND 0 conversions, categorizes them, and proposes negatives already wrapped
([exact] / "phrase"). Respects the "what NOT to block" rules (own brand / CARRIED brand / store / coupon)
from optimization-playbook.md. Business-agnostic. THE RESELLER RULE: never auto-negate a brand the store
sells — at most route it (if it has its own campaign) or flag it as a split candidate (if it doesn't).
"""
import argparse
import json
import sys

CATS = {
    "informational": ["how to", "how do", "diy", "tutorial", "what is", "for beginners", "learn", "guide"],
    "job-seeker": ["job", "jobs", "career", "hiring", "salary", "school", "certification", "training"],
    "location": ["near me", "walk in", "directions", "closest", "open now"],
    # NOTE: bare "free" is intentionally NOT here — in product verticals it's almost always a product
    # ATTRIBUTE ("HEMA-free", "TPO-free", "cruelty-free"), not free-intent. Require the piracy pairing.
    "free-intent": ["crack", "torrent", "download", "for free", "keygen"],
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


def brand_hit(tl, brands):
    """Return the first carried/own brand whose name appears as a token-ish substring in the term."""
    for b in brands:
        if b and b in tl:
            return b
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
    carried = [b.lower() for b in (data.get("carried_brands") or [])]
    own_camp = set(b.lower() for b in (data.get("brands_with_own_campaign") or []))

    wasted, protected, proposed = [], [], {}
    brand_kept, carried_protect, route_neg, competitor_cand = [], [], [], []
    total_waste = 0.0

    for row in data.get("terms") or []:
        term = (row.get("term") or "").strip()
        cost = row.get("cost", 0) or 0
        conv = row.get("conversions", 0) or 0
        if not term or cost <= min_spend or conv > 0:
            continue
        tl = term.lower()

        # 1) OWN brand — never block (your own traffic / brand defense)
        if any(b in tl for b in brand):
            brand_kept.append((cost, term))
            continue

        # 2) CARRIED brand — a brand you RESELL. A search for it is buying intent, never a "competitor".
        cb = brand_hit(tl, carried)
        if cb:
            if cb in own_camp:
                # has its own campaign → blocking in the catch-all ROUTES traffic to the specialist camp
                route_neg.append((cost, term, cb))
                proposed.setdefault(f"route-to-{cb}-campaign", set()).add(wrap(term, exact=True))
            else:
                # no dedicated campaign → the catch-all is its only home. NEVER block. Split candidate.
                carried_protect.append((cost, term, cb))
            continue

        # 3) Protected commercial modifiers — review, don't reflexively block
        if any(p in tl for p in PROTECT):
            protected.append((term, cost))
            continue

        # 4) Pattern waste (info / job / location / piracy) — safe to negate on the signal word
        cat = categorize(term)
        if cat:
            total_waste += cost
            wasted.append((cost, term, cat))
            sig = next((p for p in CATS.get(cat, []) if p in tl), term)
            proposed.setdefault(cat, set()).add(wrap(sig, exact=False))
            continue

        # 5) Everything else = a NON-carried term. Could be a true competitor brand OR generic irrelevant.
        #    Do NOT assert "competitor" — flag for human confirmation that the store doesn't sell it.
        total_waste += cost
        wasted.append((cost, term, "unclassified"))
        competitor_cand.append((cost, term))

    wasted.sort(key=lambda r: -r[0])
    print(f"\n=== Search-term mining (wasted = >${min_spend} spend, 0 conv) ===")
    print(f"Wasted spend flagged: ${total_waste:,.2f} across {len(wasted)} terms\n")
    for cost, term, cat in wasted[:20]:
        print(f"  ${cost:>8,.2f}  [{cat}]  {term}")

    print("\n--- Proposed negatives (ready-to-copy, grouped) ---")
    print("# SAFE pattern negatives (info / job-seeker / location / piracy) + routing for brands with own camp.")
    for cat, items in proposed.items():
        print(f"\n# {cat}")
        for it in sorted(items):
            print(it)

    if competitor_cand:
        print("\n--- ⚠ Competitor / unclassified CANDIDATES — CONFIRM the store does NOT sell these before blocking ---")
        print("  (Not auto-proposed. If it's a brand/product you carry, it is buying intent — do NOT block.)")
        for cost, term in sorted(competitor_cand, reverse=True)[:15]:
            print(f"  ${cost:>8,.2f}  {term}")

    if route_neg:
        rt = sum(c for c, _, _ in route_neg)
        print(f"\n--- Routing negatives — carried brand WITH its own campaign ({len(route_neg)} terms, ${rt:,.2f}) ---")
        print("  Block in the catch-all ONLY to route to the dedicated campaign (anti-cannibalization). Not waste.")
        for cost, term, cb in sorted(route_neg, reverse=True)[:10]:
            print(f"  ${cost:>8,.2f}  [{cb}]  {term}")

    if carried_protect:
        cp = sum(c for c, _, _ in carried_protect)
        print(f"\n--- 🛑 CARRIED brand, NO dedicated campaign — NEVER block ({len(carried_protect)} terms, ${cp:,.2f}) ---")
        print("  These sell brands you stock; the catch-all is their only home. 0 conv = stock/PDP/feed issue OR")
        print("  a SPLIT-into-own-campaign candidate once volume justifies it — NOT a negative.")
        for cost, term, cb in sorted(carried_protect, reverse=True)[:12]:
            print(f"  ${cost:>8,.2f}  [{cb}]  {term}")

    if protected:
        print("\n--- Protected (do NOT auto-block — review; often convert) ---")
        for term, cost in protected[:10]:
            print(f"  ${cost:>8,.2f}  {term}")

    if brand_kept:
        bt = sum(c for c, _ in brand_kept)
        print(f"\n--- Own-brand terms — KEEP, never block ({len(brand_kept)} terms, ${bt:,.2f}) ---")
        print("  (0-conv brand terms are brand intent/defense, not waste. Review only for a tracking gap.)")
        for cost, term in sorted(brand_kept, reverse=True)[:8]:
            print(f"  ${cost:>8,.2f}  {term}")

    if not wasted:
        print("\nNo non-brand wasted terms to block — search-term hygiene is clean.")
    print()


if __name__ == "__main__":
    main()
