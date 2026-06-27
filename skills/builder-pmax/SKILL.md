---
name: google-ads-builder-pmax
description: >
  Builds a complete Performance Max campaign blueprint: chooses a split strategy (campaign-level + asset-
  group-level), then designs asset groups, listing groups, ad copy (headlines/long headlines/descriptions),
  search themes, audience signals, sitelinks, negatives, image/video briefs, budget/bidding ramp, landing-
  page requirements, and an Editor-ready workbook. Generalized for any business: reads account-context.yaml,
  no brand/vertical hardcoding. Use when the user says "build pmax", "performance max", "create a pmax
  campaign", "pmax blueprint".
---

# Google Ads — Builder: Performance Max

Design a launch-ready PMax campaign from context + plan + catalog. Output is intern-ready. The highest-
leverage decision is the **split strategy** (STEP 4) — get that right before designing assets.

## Operating rules
- Read everything from `account-context.yaml` (brand_terms, margin_tiers, guardrails, data_source, AOV,
  budget) and the `plan` output. No brand/vertical hardcoding.
- Write all output to the **working directory**, never into the plugin.
- Verify every Final URL is live before it enters the blueprint (campaigns fail on 404 / too-broad URLs).
- Enforce guardrails (brand exclusion not brand negatives; conversion goals at campaign level; don't
  reference paused/out-of-stock products).

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — per-URL HEAD 200 checks (STEP 5); the `spec_to_xlsx.py` render; Google-accurate char-count validation passes.
- **Routine (`sonnet`)** — STEP 2 catalog research (product types, counts, prices, best-sellers, URL map), STEP 3 expansion performance pull. Dispatch as `general-purpose` sub-agents; **return raw catalog/URL data, don't design**.
- **Judge (main session)** — STEP 4 the split choice (the soul), STEP 5 asset-group + listing-group design, STEP 6 ad copy + search themes, STEP 7 audience signals, the guardrail enforcement. Catalog pulls and char-counts are mechanical; voice and strategy are not.

## STEP 1 — Inputs
From the user + `plan`: which products/lines, the campaign's daily budget, and target ROAS phase. If the
user is vague ("build pmax for X"), infer the rest from context and the catalog.

## STEP 2 — Research catalog & website
Via the `data_source` connector/API (Shopify/Woo/...), pull product types, counts, price distribution,
and best sellers. **Verify collection/landing URLs are live** (no 404, correct content) and record a URL
map. Capture the website's product-type taxonomy (it may differ from the feed `product_type` — check both).
If the connector is down, use the fallback chain (env creds / hub / browse) per `setup`; flag and continue.

## STEP 3 — Performance data (expansion only)
If campaigns already exist, pull revenue by product type, top landing pages, and search-term signals; note
lessons to avoid repeating (listing-group bleed, budget starvation, sitelink cross-contamination, copy
referencing dead products, over-broad URLs). Skip for a brand-new launch.

## STEP 4 — CHOOSE THE SPLIT (the soul) — see `${CLAUDE_PLUGIN_ROOT}/references/pmax-split-strategies.md`
1. **Present the menu** — campaign-level axes (margin tier · best-seller-vs-catalog · brand · category ·
   new-customer · season · consolidate) and asset-group-level axes (product type · audience · price/
   collection tier · attribute/compliance · format/bundle). Explain the level principle: campaign level
   controls budget+bidding; asset-group level controls creative+listing groups.
2. **Recommend 2-3 objectively** using the account's own numbers (NOT a fixed preference):
   - Compute **budget capacity**: max campaigns the budget can feed ≈ expected monthly conversions ÷ 20
     (learning floor). NEVER propose more campaigns than the budget feeds (starvation anti-pattern).
   - If `margin_tiers` differ materially → margin-tier split earns the campaign level (different tROAS).
   - Large catalog with clear winners → best-seller-vs-long-tail. Many small brands → category pools volume.
   - Expansion already over-fragmented near the learning floor → recommend consolidation.
   - Each option states: campaign-level axis, AG-level axis, budget per campaign vs its learning floor,
     and the trade-off. Let the user choose.
3. **Apply default architecture**: brand exclusion + separate Branded Search; conversion goals at campaign
   level; FUE + auto-created assets OFF unless justified.
4. **Testing intent → `experiments`**: compare splits one variable at a time, don't spawn random campaigns.

## STEP 5 — Asset group design (per chosen split)
For each AG: name, the products it covers, % revenue (from data or estimate), a verified Final URL, display
paths, FUE OFF, auto-assets OFF. **Listing groups** scope products via Brand/Product-Type subdivisions with
an "Everything Else = EXCLUDED" node at every level. Each product belongs to exactly ONE asset group (no
overlap). Cross-check feed `product_type` matches the names used in the plan.

**Final URL per AG — don't guess** (`${CLAUDE_PLUGIN_ROOT}/references/google-ads-formatting.md` §4): pick the most specific LIVE
category/collection page for that AG's products (never the homepage), HEAD-check it returns 200 (no redirect
chain / 404), confirm it matches the AG's listing group, and pull candidates from the catalog/sitemap. If no
specific page exists, FLAG it — never silently fall back to a generic page.

## STEP 6 — Ad copy & search themes (per AG)
Per AG, write: 15 headlines (≤30), 5 long headlines (≤90), 5 descriptions (≤90; keep **description #1 ≤60**
for the short-description surface), and up to **50 search themes** (raised from 25 in 2025) — distinct per
AG, no overlap. **Count characters the Google way** per `${CLAUDE_PLUGIN_ROOT}/references/google-ads-formatting.md`.
**Search themes must be GROUNDED in real CONVERTING-search data + the catalog — not invented from the brand
name, and NOT copied from whatever an existing campaign happens to use.** The measuring stick is universal and
business-agnostic: **what actually converts.** (Copying an existing account's signals bakes in one business's
habits and breaks for a new account or a different vertical — a B2C retailer and a B2B wholesaler need totally
different themes.)
- **Derive themes from the converting data:** converting categories in `campaign_search_term_insight` (per
  PMax) + converting terms in `search_term_view`. The data already reveals the right register — a retailer's
  converters read like "gel polish for beginners / at-home gel kit", a wholesaler's like "bulk nail supplies /
  distributor" — so let the converting data set the tone, don't assume it.
- **Let `business.model` / `vertical` from context confirm the register** (b2c retail vs b2b/wholesale vs
  leadgen). Read it; never hardcode one.
- Cross-check the real catalog; never seed a theme for a product the store doesn't stock.
- *Optional* same-account context: if the account already runs PMax, `asset_group_signal` on its AGs can be a
  supplementary hint — but it is NOT the standard (it may be poorly built and is account-specific). Converting
  data + catalog + context win.
Pull voice/offers/best-sellers from context + catalog via `assets`. (Angle mix:
`${CLAUDE_PLUGIN_ROOT}/references/pmax-best-practices.md`.)

## STEP 7a — Audience signals (per ASSET GROUP)
Seed from the business's OWN converting-customer data, strongest first: a **customer-match list of actual
purchasers / high-value converters**, then a converting website-visitor or custom segment where it genuinely
helps. The number and type follow what the data supports — **don't invent generic in-market/demographic seeds
with no converting evidence, and don't copy another campaign's recipe** (audiences are first-party and
business-specific). If first-party lists don't exist yet, say so and start with the strongest available
converting signal. Audience signals are an **AG-level** field — they live in the AG sheet alongside listing
groups and creative.

## STEP 7b — Extensions (CAMPAIGN level — not per AG)
**In PMax, sitelinks/callouts/structured snippets attach at the CAMPAIGN (or account) level, NOT the asset
group.** Put them in `spec.extensions`, never under an asset group (the validator warns if it finds sitelinks
on an AG). Build all of these — the `audit` checks for them, so a blueprint missing them ships a known gap:
- **Sitelinks**: campaign-level, but **scale the count with how many asset groups / product areas the
  campaign covers** — aim for ~1-2 sitelinks per AG area so each line gets representation, total ~6-10 (Google
  minimum 4, hard cap ~20). They're still added ONCE at the campaign, not duplicated per AG. text ≤25, two
  descriptions ≤35, a LIVE final_url (HEAD-check 200), pointing at real category/collection pages.
- **Callouts** (4-10, ≤25 each): non-clickable, brand-level value props (shipping, pricing model, authenticity,
  dispatch). These do NOT scale with AG count — they describe the whole business.
- **Structured snippets** (≥1 set, header from Google's fixed list — Amenities/Brands/Courses/Models/
  Service catalog/Styles/Types/…, ≥3 values, ≤25 each). **Header must match the values semantically or Google
  disapproves:** use **`Brands` ONLY when the campaign carries multiple real brands** (e.g. a multi-brand
  catch-all). For a **single-brand** campaign the product lines are NOT brands — use **`Types`** (or `Styles`/
  `Service catalog`) instead. Putting a brand's product lines under `Brands` is a common disapproval cause.
- **Prices** (recommended — build it, don't leave empty): a price asset of `type` from Google's list
  (`Product categories`/`Product tiers`/`Brands`/`Services`/…), a `price_qualifier` (`From`/`Up to`/`Average`),
  `currency`, and **3-8 items** each `{header ≤25, description ≤25, price, final_url}`. **Pull real prices from
  the `data_source`** (min/"From" price per product category) and a LIVE URL per item — don't invent numbers.
  For a single-brand campaign, `type: "Product categories"` with the brand's lines is the natural fit.
- **Promotions** — leave as a **placeholder** (empty array + a `_promotions_placeholder` note) unless a sale is
  actually live; don't fabricate a sale. The operator adds it (occasion, % / $ off, code, dates) at sale time.

## STEP 8 — Support
- **Negatives** (campaign level): cross-brand, intent-mismatch (e.g. B2C/DIY for a B2B store — per
  `business.model`), location, competitor, irrelevant — sourced
  from real search terms where available; prefer Exact/Phrase; recommend shared lists. Block queries for
  product lines the store does NOT stock (avoids paying for traffic you can't fulfil).
- **Budget & bidding ramp**: from `campaign_defaults.bidding_ramp` (Maximize Conversion Value, no target,
  during learning → Target ROAS once volume matures). Respect ramp discipline + change_event cooldown.
- **Creative brief per AG** (AG-level): `business_name`, `call_to_action`, and for each image/video asset a
  **specific shot brief** (subject + setting + props + composition + what to leave for overlay), NOT a generic
  "1200x628 TODO". Pull subjects from the catalog's real best-sellers; never brief a product the store doesn't
  stock. **Landing-page requirements** checklist for the web admin (mobile-first, trust signals, no
  cross-product, schema).

## STEP 9 — Output: TWO artifacts (human + machine) + verification
Emit BOTH:
1. **`blueprint.xlsx`** — the human/intern view, organized **by where each thing lives in PMax** (5 sheet
   types):
   - **Overview** (campaign): budget, bid strategy + tROAS phase, geo/lang, brand exclusion, conversion goal +
     scope, FUE/auto-assets, split strategy + rationale, an AG summary, and campaign-level asset counts.
   - **Extensions** (campaign): sitelinks + callouts + structured snippets + promotion/price PLACEHOLDERS —
     all in one sheet, because in PMax these are campaign-level.
   - **AG: \<name\>** (one sheet per asset group): headlines/long/descriptions (with Google-accurate char-count
     coloring) + search themes + audience signals + listing group + creative brief (business name, CTA,
     per-image/video shot briefs) — everything that rides with the asset group, together.
   - **Negative Keywords** (campaign): campaign negatives + shared lists, ready-to-copy.
   - **Checklist**: the build + QA gate (PAUSED, budget, conversion scope, brand exclusion, URLs live, listing
     Everything-Else, counts/limits, extensions present, images provided, then ENABLE).
2. **`campaign-spec.json`** — the machine contract the `pusher` consumes (schema:
   `${CLAUDE_PLUGIN_ROOT}/templates/campaign-spec.json`, documented in `${CLAUDE_PLUGIN_ROOT}/references/campaign-spec.md`). The pusher reads THIS,
   never the spreadsheet. Set `campaign.status: "paused"`, `conversion_goals.scope: "campaign"`,
   `brand_exclusion.enabled: true`, extensions at the **campaign level** (`spec.extensions`), and
   `provenance.verified: false` (the pusher flips it after validating).

Render the workbook FROM the spec (single source of truth):
`python ${CLAUDE_PLUGIN_ROOT}/skills/builder-pmax/scripts/spec_to_xlsx.py <campaign-spec.json> --output blueprint.xlsx`

Verify: per-AG counts (≤15/≤5/≤5/≤50 themes), all char limits (Google-accurate), all URLs live, no
listing-group overlap (a product in exactly one AG), **extensions at the CAMPAIGN level** (sitelinks +
callouts + structured snippets present), distinct audience signals per AG, guardrails satisfied. Hand off the
JSON to `pusher`.

## To build / refine later
- [x] Data-driven xlsx generator (`scripts/spec_to_xlsx.py`) — renders the workbook from the spec. Done.
- [ ] Richer sheet styling / an intern-checklist sheet generated from the spec.
