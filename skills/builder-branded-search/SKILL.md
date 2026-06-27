---
name: google-ads-builder-branded-search
description: >
  Builds a Branded Search campaign — defensive coverage on the business's own brand terms plus optional
  competitor conquesting — with trademark-aware ad copy and the brand-exclusion coordination that keeps
  PMax/Shopping from cannibalizing brand traffic. Emits a human .xlsx plus a campaign-spec.json
  (branded_search). Reads account-context.yaml. Use when the user says "branded search", "brand campaign",
  "defend my brand", "competitor conquesting", "bid on my own name".
---

# Google Ads — Builder: Branded Search

A focused Search campaign to (1) defend your own brand at near-certain ROAS and (2) optionally conquest
competitors. Pushes cleanly via Editor CSV. Builds on `builder-search` patterns with brand-specific rules.

## Operating rules
- Read `brand_terms` and `competitor_terms` from `account-context.yaml` (set by `setup`). Read guardrails.
- Write to the working directory: `blueprint.xlsx` + `campaign-spec.json`
  (`campaign_type: "branded_search"`, `ad_groups[]`).
- **Coordinate brand exclusion**: ensure PMax/Shopping have brand exclusion applied so they don't claim
  brand conversions (clean attribution). Honor the `pmax-brand-exclusion` guardrail.

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — per-URL 200 checks; char-count validation; brand-misspelling expansion.
- **Routine (`sonnet`)** — pulling competitor domains from auction insights as conquesting candidates. Dispatch as `general-purpose`; **return raw candidates, don't decide**.
- **Judge (main session)** — STEP 1-2 ad-copy (brand-led, trademark-aware — **never a competitor TM in ad text**), STEP 3 separation, bidding, the brand-exclusion coordination call. Trademark safety is judgment; never delegate it.

## STEP 1 — Brand-defense ad group(s)
- Keywords from `brand_terms` (own brand + variants + common misspellings), Exact + Phrase. No broad.
- Copy uses your own brand prominently, your USPs, and your real offers. Target high impression share at
  low CPC (brand intent converts cheaply).
- RSA: up to 15 headlines (≤30) / 4 descriptions (≤90), keyword-led, with CTA.

## STEP 2 — Competitor conquesting — optional, trademark-aware, a SEPARATE campaign
- Only if `competitor_terms` exist and the user wants it. **Emit it as its OWN campaign-spec, not an ad group
  inside the brand-defense campaign** — because bid strategy is campaign-level and conquesting needs
  **Maximize Conversions**, not the defense campaign's Target Impression Share. (You do NOT want to bid to
  dominate a competitor's SERP at absolute-top 90% — expensive, low-intent.)
- Keywords from `competitor_terms` (Phrase/Exact).
- **Trademark rules**: do NOT put a competitor's trademark in the ad TEXT (headlines/descriptions/paths) —
  only as keywords. Emit the competitor terms as a spec-level `trademark_avoid[]` so the validator BLOCKS any
  in ad text. Lead with YOUR differentiators ("wholesale pricing", "free shipping", a **price extension** with
  your real prices on the competitor SERP), not the competitor's name. Expect lower CTR/QS, higher CPC.
- Add YOUR `brand_terms` as negatives so conquesting never overlaps the brand-defense campaign.

## STEP 3 — Negatives & separation (Search levels: campaign OR ad-group)
- **Negatives can sit at campaign level OR ad-group level** in Search (unlike PMax = campaign-only). Use
  campaign-level for account-wide junk (job-seeker, DIY, location) and **ad-group-level** only where it does
  real work — here, negate `brand_terms` in the conquesting ad group so defense and conquesting never
  cross-serve. Don't duplicate the same negative at both levels; pick the narrowest level that achieves it.
- Keep brand-defense and conquesting ad groups cleanly separated.
- **Extensions, likewise, can be campaign OR ad-group level in Search** (PMax forces campaign-level). Default
  to campaign-level; only push sitelinks/callouts down to ad-group level if the groups are different enough to
  need distinct ones (e.g. brand-specific vs conquesting sitelinks) — and only if it's worth the upkeep.

## STEP 4 — Bidding (Search ≠ PMax — pick a brand-appropriate strategy, NOT a "learning ramp")
- **Check what the account already does for brand first.** If a brand campaign exists, read its
  `bidding_strategy_type` (a healthy brand campaign commonly runs `TARGET_IMPRESSION_SHARE`) and match it — don't reinvent.
- **Brand defense → Target Impression Share** (absolute top of page, ~90%, with a max-CPC bid limit). The goal
  is to dominate your own brand SERP cheaply, not to maximize value. Brand has history, so do NOT frame it as
  "maximize conversion value, no target, learning" — that's a cold-prospecting default, wrong for brand.
  (Maximize Conversions is an acceptable alternative if you'd rather optimize to conversion volume.)
- **Conquesting → Maximize Conversions** (watch CPA, don't over-invest). It's colder and pricier than brand.
- **Bid strategy is CAMPAIGN-level.** Brand defense and conquesting want *different* strategies, so once
  conquesting has real budget, **split it into its own campaign** rather than forcing both under one strategy.

## STEP 4b — Conversion goal (use the account's REAL action — never invent one)
**Pull the enabled conversion actions** (`conversion_action.name`, `primary_for_goal`) and use the account's
actual primary purchase action by name — e.g. a store's only purchase action may be the store-channel
purchase (Shopify's "Google & YouTube" channel tracks website purchases, Search-driven ones included), so the
Search campaign optimizes on THAT, not a made-up name. Set `conversion_goals.scope:
"campaign"`. If no web-purchase primary exists for Search, flag it for the operator to create.

## STEP 5 — Output + verification
Emit `campaign-spec.json` (`branded_search`, `ad_groups[]` as in `builder-search`) + `blueprint.xlsx`.
Set `campaign.status: "paused"`, `conversion_goals.scope: "campaign"`. Build the `extensions` block the same
way as `builder-pmax` STEP 7b — sitelinks, callouts, structured snippets (the store carries many brands, so a
`Brands` snippet IS correct here, unlike a single-brand PMax), and a **concrete `prices` asset built from real
store data** (don't leave it a placeholder — pull "From" prices per category and a live URL each; a price
extension is especially strong on a brand/conquesting SERP). On a conquesting campaign, **emit a
`trademark_avoid` list** (the competitor terms) at the spec level — the validator BLOCKS any ad text
containing one, enforcing the no-competitor-TM-in-copy rule.

Render the human workbook from the spec (the shared renderer handles ad_groups → an AG sheet per ad group
with keywords, RSA, negatives, paths):
`python ${CLAUDE_PLUGIN_ROOT}/skills/builder-pmax/scripts/spec_to_xlsx.py <campaign-spec.json> --output blueprint.xlsx`

Verify with `validate_spec.py`: RSA limits/counts (Google-accurate counting,
`${CLAUDE_PLUGIN_ROOT}/references/google-ads-formatting.md`), keyword/negative match types (no broad),
**no `trademark_avoid` term in any ad text** (enforced), brand_terms negated in conquesting groups, Final
URLs live (200). Hand the JSON to `pusher` → Editor CSV (`spec_to_editor_csv.py`) + ready-to-copy blocks
(`spec_to_paste.py`).

## Coordination note for the operator
Branded Search + PMax brand exclusion are two halves of one decision: PMax excludes brand traffic, this
campaign captures it deliberately. Surface this so reporting and credit stay clean.

## To build / refine later
- [ ] Auto-generate brand misspellings; pull competitor domains from auction insights.
