# Optimization playbook

Reusable, business-agnostic reference for `optimizer` (and `tracker` for context). Generalized from a
production ecommerce optimizer — the principles apply to any ecommerce niche.

## Three-source attribution (don't treat any single number as truth)
| Source | Use it for | Do NOT use it for |
|--------|-----------|-------------------|
| **Store revenue** (Shopify/Woo/...) | Ground truth — real money, true ROAS, product/vendor profitability | — |
| **Google Ads in-platform** | Letting Smart Bidding work; in-account decisions | Reporting "actual" results to stakeholders |
| **GA4** | Channel mix + attribution paths | Treating as the single source of truth |

A 20-35% gap between Google Ads and GA4 ROAS is **normal methodology difference** when tracking is set up
correctly (Enhanced Conversions + Consent Mode v2 + correct conversion actions). It is NOT a tracking bug.

**Only suspect broken tracking when**: gap > ~50%, OR Enhanced Conversions off/unverified, OR Consent Mode
still Basic/not deployed, OR the tag isn't firing on key pages. Otherwise route ROAS questions to the
store-revenue ground truth, not GA4.

## Target ROAS step-up discipline (the most common way to wreck an account)
1. Never raise tROAS more than ~0.2-0.3x in one step.
2. Wait ~2 weeks between steps.
3. Need ~15-30 conversions/week first; if below, **consolidate before raising** (more volume → better
   learning → then raise).
4. Cut immediately if ROAS drops >20% after a raise.
Raising the target too fast shrinks the audience → fewer clicks → less data → the algorithm goes blind →
ROAS falls (negative loop).

## Budget-pacing & scaling discipline
1. **Scale gently — +10% per step** (not 20%, not 100%). Big jumps force Smart Bidding to re-forecast.
2. **Hold the cooldown between changes** — use the account's `change-event-cooldown` guardrail (don't
   hardcode a number); let bidding stabilize before the next move.
3. **Never reverse direction within the cooldown** — if you raised budget, the next move is up or hold,
   not down (and vice-versa). Reversing whipsaws the algorithm.
4. **Prefer Mondays** for budget changes — weekday pacing is more predictable and you get a full business
   week of data before the weekend auction mix shifts.
5. **PMax: scale DOWN by pausing low-ROAS asset groups, NOT by cutting the budget.** PMax budget funds
   asset-group exploration; trimming it starves exploration and locks the campaign into a narrow mix.

### How Google's daily budget actually works (it's a target, not a ceiling)
Your "daily budget" is an **average target**, not a hard per-day cap. On a high-opportunity day Google may
spend **up to 2× your daily budget**, then spend less on slow days to even out. Over a month it won't exceed
**~30.4 × your daily budget** (30.4 = average days per month). So $100/day can show $180 one day and $40 the
next, but the monthly total stays ≈ $3,040. Don't panic at a single over-spend day — judge pacing over the
month, not the day.

## Campaign tiering (verdicts)
| Tier | Signal | Action |
|------|--------|--------|
| Gold | ROAS ≥ target × ~1.2 | Scale (+budget gradually) |
| Silver | around target | Keep, optimize |
| Bronze | below target | Review (reduce/restructure) |
| Dead | ROAS < ~0.5× target or $0 spend | Pause/kill |
Always read targets against `margin_tiers` — a high-margin (house) line can sit at a lower ROAS and still
be Gold for its tier. Never apply one ROAS bar across different margins.

## Search-term mining → negatives (what NOT to block)
Source negatives from real irrelevant search terms (>$10 spend, 0 conversions). Prefer Exact/Phrase, never
broad-match negatives. Group into themed lists (informational/DIY, job-seeker, location, cross-brand).
**Two sources — cover both:** `search_term_view` returns Search/Branded terms only; PMax/Demand-Gen terms
live in `campaign_search_term_insight` (query per campaign_id). A PMax-heavy account audited via
`search_term_view` alone shows almost no terms — you'd miss the real spend.

**Do not reflexively block**:
- **Your own brand terms** — brand intent is your traffic/defense; NEVER propose blocking them, even at
  0 conversions (a 0-conv brand term is a tracking-gap to review, not waste to cut). **Match brand on word
  boundaries, not substring**: a reseller's product brands often CONTAIN the own brand as a substring (e.g. an
  own brand "AB" sitting inside resold "FAB"/"CAB") — substring-matching mislabels product-category searches as
  brand and corrupts both the never-block list and the brand-cannibalization %. Exclude known resold
  product-brand names first.
- **CARRIED brands — brands the store RESELLS (the #1 false-positive for distributors).** A search for a brand
  you stock is BUYING INTENT, never a "competitor". Three buckets, not two: (a) carried brand **with its own
  campaign** → block in a catch-all ONLY to *route* to the specialist campaign (anti-cannibalization), label it
  "route", not "competitor"; (b) carried brand **without a dedicated campaign** → **NEVER block** — the catch-all
  is its only home (it's there because it isn't split out yet); a 0-conv carried-brand term is a stock/PDP/feed
  fix or a SPLIT-into-own-campaign candidate, not a negative; (c) **not carried** → a competitor *candidate*,
  confirm the store doesn't sell it before blocking. Build the carried-brand list from the catalog/feed `brand`
  values, and the "has own campaign" set from existing campaign names.
- "store" alone (e.g. "<category> supply store" can convert very well) — only block "store near me" intent.
- "coupon / discount code / promo code" — high-intent bottom-funnel; often strong ROAS. Only block if the
  term lacks brand intent AND has 0 conversions.
- "cheap / budget <brand>" — price-sensitive buyers convert in both B2C and B2B (esp. wholesale/value
  stores); check CTR + CVR before blocking, don't assume "cheap" = junk.

## PMax bidding & scheduling caveats
PMax **does** support location AND ad-schedule bid adjustments (campaign-criterion `bid_modifier`, since 2024) —
it is NOT exclusion-only. Use ad-schedule bid modifiers for dayparting and location bid modifiers for geo on PMax
just as on Search. (What PMax does not expose is keyword-level bidding.)

## Conversion-volume floor
A campaign/asset group/ad group wants ~15-30 conversions/period to let Smart Bidding learn. Below ~10,
consolidate rather than starve. This gates both scaling and target raises.
