# PMax best practices

Reusable, business-agnostic reference for `builder-pmax`. Pairs with `pmax-split-strategies.md` (which
covers how to split). This covers the per-element rules once the split is chosen.

## Asset groups
- One AG tells ONE consistent story: headlines, images, video, and landing page all about one thing.
- Avoid duplicate AGs (same products, different audience) — performance converges to one average.
- Each AG needs ~15-30 conversions/month to learn. Below ~5/month, merge it.
- Final URL Expansion OFF (else Google can route traffic to any page — lost control).
- Automatically Created Assets OFF (else off-message auto copy).

## Listing groups (Shopping product feed)
```
All Products → Subdivide
  └ Brand = X → Subdivide
    └ Product Type = A → Include
    └ Product Type = B → Include
    └ Everything Else → EXCLUDE
  └ Everything Else → EXCLUDE
```
- Every subdivision level needs an "Everything Else" node, defaulting to EXCLUDED.
- Each product in exactly ONE asset group (no overlap → no self-competition).
- Don't target individual product IDs — target groups. Avoid >1,000 listing groups.
- Verify feed `product_type` matches the names used in the plan; fix via custom labels if not.

## Audience signals
- Signals are HINTS, not hard targeting — Google still serves outside them; they speed learning.
- Priority: customer-match lists → website visitors → high-value lists → custom segments (search terms /
  competitor URLs) → in-market → demographics (weakest).
- Each AG gets DISTINCT signals reflecting its intent. Combine behavioral + intent; avoid demographics alone.

## Ad copy
| Asset | Count | Max chars |
|-------|-------|-----------|
| Headline | up to 15 | 30 |
| Long headline | up to 5 | 90 |
| Description | up to 5 | 90 (keep #1 ≤60) |
| Search theme | up to 50 | (short phrases) |

Count characters the Google way (see `google-ads-formatting.md`), not naive `len()`.
- Lead with the buyer's qualifier (e.g. professional/wholesale/bulk for B2B; value/selection for B2C).
- Use real best-seller product names (high search volume). Emphasize selection, in-stock, shipping.
- Avoid generic claims ("best quality") and off-audience language.
- Search themes: distinct per AG, no overlap; mix brand + best-sellers + intent + generic + location +
  seasonal.

## Sitelinks / callouts / structured snippets (CAMPAIGN level in PMax)
- In PMax these extensions attach at the **campaign** (or account) level — NOT the asset group (Google
  enforces this). Put them in `spec.extensions`, never under an asset group. (Search is the exception, where
  sitelinks may be campaign- or ad-group-level.)
- Scale the count with how many asset groups / product areas the campaign covers (~1-2 sitelinks per area,
  total ~6-10, Google cap ~20). Each sitelink has two descriptions (unlocks more ad formats).
- Limits: sitelink text 25 chars; each description 35; callout ≤25; structured-snippet value ≤25.

## Image & video specs
| Asset | Min | Recommended | Count |
|-------|-----|-------------|-------|
| Landscape 1.91:1 | 600×314 | 1200×628 | 1+ (3-5 rec) |
| Square 1:1 | 300×300 | 1200×1200 | 1+ (3-5 rec) |
| Portrait 4:5 | 480×600 | 960×1200 | 2+ rec |
| Logo landscape 4:1 | 512×128 | 1200×300 | 1 |
| Logo square 1:1 | 128×128 | 1200×1200 | 1 |
- Video: 16:9 + 9:16, 10-60s (15-30s optimal). Custom video outperforms auto-generated.

## Budget & bidding ramp
- Learning: Maximize Conversion Value, NO target. Then Target ROAS once volume matures.
- Raise tROAS ≤0.3x per step; wait ~2 weeks between steps; need ~15 conv/week first; cut if ROAS drops
  >20% after a raise. Cross-check Google Ads vs GA4 (20-35% gap is normal; >35% investigate).
- Each campaign wants enough budget to clear its learning floor; below that, consolidate.

## Default architecture
- Brand exclusion on PMax + separate Branded Search (clean attribution).
- Conversion goals at campaign level, not account level.
