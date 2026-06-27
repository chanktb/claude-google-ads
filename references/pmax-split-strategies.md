# PMax split strategies — the menu, the levels, and the recommendation logic

Reusable, business-agnostic reference for `builder-pmax`. "How to split a PMax campaign" is the highest-
leverage design decision. This file is account-neutral: the builder offers the whole menu and recommends
objectively from the account's own numbers.

## The level principle (decides WHERE each axis goes)
- **Campaign level controls BUDGET + BIDDING (tROAS/tCPA).** Put the axis you most want to control money
  and ROAS by here.
- **Asset-group level controls CREATIVE/MESSAGING + listing groups** (no separate budget). Put secondary,
  relevance-driven axes here.

So "which split" really means "which axis at the campaign level, and which at the asset-group level."

## Campaign-level axes (each gets its own budget + tROAS)
| Axis | Use when | Trade-off |
|------|----------|-----------|
| **Margin tier** (the exact tiers come from `margin_tiers` in context — e.g. house-brand vs third-party vs accessories) | Margins differ materially across lines | Best PROFIT alignment — different tROAS per tier; mixes brands/categories within a tier |
| **Best-seller vs long-tail** (hero SKUs vs catalog, via feed custom_label) | Large catalog with clear winners | Concentrates budget on proven SKUs; needs feed labeling; long-tail campaign is discovery (lower ROAS OK) |
| **Supplier/product brand** | Creative differs by brand; customers search by brand | Clean per-brand creative & attribution; BUT small-volume brands starve learning |
| **Product category** (cross-brand) | Many small brands; category-level intent | Pools volume for healthy learning; less brand-specific creative |
| **New vs existing customer** (High-Value New Customer mode) | Enough first-party data; want true acquisition | Stops PMax just harvesting existing customers; needs customer-match lists + volume for two campaigns |
| **Season / collection** | Time-boxed launches (holiday, new collection) | Protects evergreen learning; short-lived, manage as temporary |
| **Consolidate (anti-split)** | Account over-fragmented; many starved campaigns | Max signal pooling → fastest learning, least control; split inside via asset groups + listing groups |

## Asset-group-level axes (creative + listing groups, share the campaign budget)
- **Product type** (the default AG split) — use the store's OWN catalog categories from `data_source`
  (e.g. for an apparel store: tops / bottoms / outerwear / accessories; for a beauty store: gel / dip / tools).
- **Audience-led** — distinct buyer segments needing distinct messaging (only if creative truly differs).
- **Price / collection tier** — premium vs value.
- **Attribute / compliance** — any attribute with genuine distinct demand (e.g. organic / vegan / FDA-cleared /
  HEMA-free, depending on the store's niche).
- **Format / bundle** — kits/sets/combos vs singles (different AOV and buyer).

## Default architecture (NOT optional — apply unless the operator overrides)
- **Brand exclusion on PMax + a separate Branded Search campaign.** Keeps PMax from claiming cheap brand
  conversions (inflated ROAS) and keeps attribution clean. (Honor any `pmax-brand-exclusion` guardrail.)
- **Conversion goals set at the campaign level**, not account level (avoids goal leakage).
- **Final URL Expansion OFF** and **Automatically Created Assets OFF** unless justified.

## Recommendation logic (objective, account-driven — recommend 2-3, never "all")
1. **Budget capacity first.** Estimate expected monthly conversions (daily_budget × 30 ÷ expected CPA, or
   from account data). Max campaigns the budget can feed ≈ monthly conversions ÷ 20 (learning minimum
   ~15-30 conv/mo each). **Never recommend a split that creates more campaigns than the budget can feed**
   — that is the starvation anti-pattern.
2. **Margin structure.** If `margin_tiers` are materially different, a **margin-tier campaign split**
   earns the campaign level (lets you run different tROAS). If margins are uniform, this axis adds little.
3. **Catalog shape.** Large catalog with identifiable winners → **best-seller-vs-long-tail** is strong.
   Many small brands → **category** split pools volume better than per-brand.
4. **Existing structure (expansion).** If the account already runs many small per-brand campaigns near the
   learning floor, recommend **consolidating** toward margin-tier or category, with brand at AG level.
5. **Output**: 2-3 ranked options, each stating the campaign-level axis, the AG-level axis, the budget
   each campaign would get vs its learning floor, and the trade-off. Then let the user choose.

## Testing (don't "test" by spawning random campaigns)
When the user wants to compare splits, route through `experiments`: change ONE variable at a time
(e.g. brand-split vs margin-tier-split, or tROAS level), 50/50, with a defined runtime and success metric.

## Anti-patterns to refuse
- Over-fragmentation: more campaigns than the budget can feed (starved learning everywhere).
- A product appearing in more than one asset group / campaign (listing-group overlap → self-competition).
- Per-brand campaign split when margins differ MORE than brands do (you're controlling the wrong axis).
- Audience-based asset groups whose creative is identical (no reason to split).
