---
name: google-ads-builder-demand-gen
description: >
  Builds a Demand Gen campaign blueprint — audience-led, creative-heavy campaigns across YouTube, Discover,
  and Gmail. Covers audience strategy (your-data, lookalikes, custom segments), image and video creative
  sets, ad formats, and the upper/mid-funnel measurement caveats. Emits a human .xlsx plus a campaign-spec
  .json (demand_gen). Reads account-context.yaml. Use when the user says "demand gen", "demand generation",
  "youtube campaign", "discovery ads", "top of funnel".
---

# Google Ads — Builder: Demand Gen

An audience-led, creative-heavy campaign for awareness/consideration. Different from PMax/Search: the
audience and creative are the levers, and measurement is upper-funnel.

## Operating rules
- Read context (audiences available, brand, vertical, budget) + the `plan` output.
- Write to the working directory: `blueprint.xlsx` + `campaign-spec.json` (`campaign_type: "demand_gen"`,
  asset-group-style creative groups).
- Set expectations: this is funnel-building, not last-click harvesting.

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — per-URL 200 checks; creative-spec/size validation; pulling available audience lists.
- **Routine (`sonnet`)** — pulling customer-match/visitor lists + high-value seeds for lookalikes. Dispatch as `general-purpose`; **return raw lists, don't strategize**.
- **Judge (main session)** — STEP 2 audience strategy, STEP 3 creative direction (via `assets`), STEP 4 funnel/measurement framing, bidding. Audience *inventory* is cheap; audience *strategy* and creative are judgment.

## STEP 1 — Inputs
Funnel goal (awareness/consideration/action), budget, and the products/message to feature.

## STEP 2 — Audience strategy
- **Your data**: customer-match lists, website/app visitors (retarget).
- **Lookalikes**: from high-value customer seeds.
- **Custom segments**: by search behavior or competitor/site interest (`competitor_terms`).
- **Interest/demographic** layers as broad context. Combine behavioral + intent; avoid demographics alone.

## STEP 3 — Creative sets (via `assets`)
Build per format: single image, carousel, and video (combined image+video drives more conversions than
video-only at similar CPA). Provide briefs/specs and on-screen CTA. Strong, diverse creative IS the
targeting lever here.

## STEP 4 — Ad formats, funnel role & measurement caveats
- Map creatives to formats (YouTube in-feed/Shorts, Discover, Gmail).
- **No frequency capping** in Demand Gen — monitor reach vs frequency manually.
- Attribution leans on view-through / brand-lift; don't judge it on last-click ROAS alone. State this.

## STEP 5 — Bidding
Maximize Conversions (or value) aligned to the funnel goal; consider brand-lift/awareness objectives for
pure top-funnel. Respect ramp discipline + change-event cooldown.

## STEP 6 — Output + verification
Emit `blueprint.xlsx` + `campaign-spec.json`. Set `campaign.status: "paused"`,
`conversion_goals.scope: "campaign"`. Verify creative specs/limits, audience signals present and distinct,
Final URLs live. Hand the JSON to `pusher` (Demand Gen is mostly API-or-UI — guided build in Mode A).

## To build / refine later
- [ ] Brand-lift / awareness objective configuration.
