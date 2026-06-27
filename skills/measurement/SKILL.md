---
name: google-ads-measurement
description: >
  Validates conversion tracking BEFORE any spend — the #1 failure point in Google Ads accounts.
  Checks conversion actions (purchase/lead), counting settings, primary vs secondary, double-count risk
  by source (store channel e.g. Shopify vs GA4 import vs gtag), enhanced conversions, server-side/CAPI, and value
  tracking — and judges them HOLISTICALLY (which actions each campaign actually fires) before any verdict.
  Use when the user says "conversion tracking", "is my tracking right", "GA4 import", "enhanced
  conversions", "why are my conversions wrong", or as the gate before plan/builder.
---

# Google Ads — Measurement (tracking gate)

Prove conversion tracking is correct and trustworthy, or block `plan`/`builder-*` until it is. Reuse the
live MCP detection from `setup`. **Never raise an alarm from the action list alone.**

## STEP 0 — Load context
**If `account-context.yaml` is missing, run `setup` first — don't validate tracking on an unconfigured account.**
Read `account-context.yaml`: `google_ads.customer_id`, `conversion_actions`, `measurement.*`,
`data_source` (for value sanity), `business.model/vertical` (lead vs purchase expectations). Output goes
to the working directory; update the context's `conversion_actions` + `measurement.*` as you verify them.

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — STEP 0 context read; the conversion-action list pull.
- **Routine (`sonnet`)** — STEP 1 per-campaign conversion segmentation (`segments.conversion_action_name`), STEP 3 Ads/GA4/store value pulls. Dispatch as `general-purpose` sub-agents; **return raw, don't conclude**.
- **Judge (main session)** — the WHOLE-picture verdict, every is-it-a-problem call, the double-count judgment, the PASS/WARN/FAIL that gates plan/builder. **Never let a cheap tier raise the alarm** — that holistic judgment is the entire point of this skill.

## STEP 1 — Build the WHOLE picture before concluding (mandatory)
A conversion list read in isolation lies. The same flag is fine or fatal depending on context. Do all four:

1. **Actions** — enabled conversion actions: name, category, primary_for_goal, counting_type,
   value_settings.default_value (value tracking on/off), source. (Omit `conversion_action.type` if the MCP
   rejects it; see ${CLAUDE_PLUGIN_ROOT}/skills/audit/references/gaql-notes.md.) **Decode the enums:**
   `category` 4=PURCHASE · 6=LEAD · 5=SIGNUP · 3=PAGE_VIEW · 8=ADD_TO_CART · 9=BEGIN_CHECKOUT ·
   11=PHONE_CALL_LEAD · 13=SUBMIT_LEAD_FORM · 16=GET_DIRECTIONS · 18=CONTACT · 19=ENGAGEMENT · 20=STORE_VISIT;
   `counting_type` 2=ONE (one per click) · 3=EVERY (many per click). For ecommerce, the working primary
   should be category=PURCHASE with EVERY counting + value tracking on.
2. **Usage** — which actions each ACTIVE campaign actually fires/optimizes for: segment conversions by
   `segments.conversion_action_name` per campaign over 30-90 days (explicit `YYYY-MM-DD` dates). An action
   no campaign fires is inert.
3. **Source & double-count** — map each value-carrying action to a source
   (store channel, e.g. Shopify Google&YouTube "App Purchase" / WooCommerce / GA4 import / gtag /
   Merchant Center). Two value
   purchases both PRIMARY and both firing = double count. One primary + one secondary = correct.
   See `${CLAUDE_PLUGIN_ROOT}/references/conversion-tracking-logic.md`.
4. **Verdict** — only now, per the rules below.

## What is / isn't a problem
- ✅ Campaigns optimize toward the real working purchase action → healthy, even if other purchase actions
  exist as secondary. A second purchase action kept secondary (e.g. GA4 web purchase alongside the channel
  App Purchase) is the CORRECT anti-double-count setup, not a bug.
- ✅ "Junk" actions (menu views, directions, calls, store visits, app micro-events) flagged primary but
  fired by NO active campaign → harmless. Note for awareness; do not alarm.
- ✅ Cross-brand action sitting secondary and unused → harmless; note it.
- 🔴 Two value-carrying purchase actions BOTH primary and BOTH firing in the same campaigns → real
  double-count. Flag.
- 🔴 The action campaigns optimize for is a low-value engagement action, not the purchase action → flag.
- 🔴 No working purchase/lead conversion at all, or value tracking off for ecommerce → flag.

## STEP 2 — Other checks
- **Counting type**: `one` for leads (avoid form-spam inflation); `every` for ecommerce purchases.
- **Value tracking**: on for ecommerce; sane currency.
- **Enhanced Conversions / Consent Mode v2 / server-side (CAPI)**: the API/MCP usually CANNOT confirm
  these — mark them **verify-in-UI**, not FAIL. State the ceiling if confirmed.
- **Conversion lag**: are conversions still trickling in (long lag windows)? Note if attribution looks cut.

## STEP 3 — Value sanity cross-check
When more than one source is available, compare and report the gap (don't silently pick one):
- **Google Ads** attributed value/conversions for the primary purchase action (30-90d).
- **GA4** purchase value for the same window (via GA4 MCP / API / a connected GA4 client).
- **Store** net sales (Online Store channel only — exclude draft/POS/TikTok/marketplace;
  see audit/references or aov-and-sales-sourcing.md).
A large divergence (>35% Ads vs GA4) is itself a finding (attribution, tagging, or channel-mix issue).

## Data sources & fallback (graceful, but NO fabrication)
Read the context `connections` block. GA4/store via MCP → API creds → a connected client/script. Missing
GA4/store does NOT block measurement — you can still judge the Google-Ads-side setup. **But report only the
Ads number and mark the value cross-check `UNVERIFIED — connect GA4/store`; NEVER estimate the missing
side to "complete" the comparison** (a fabricated GA4/store figure is worse than an honest gap). If the
source is merely unwired, prefer guiding the user to connect it over skipping.

## Output — verdict + notes (to the working dir)
- **Notes for awareness** — the harmless-but-worth-knowing items (inert primaries, unused cross-brand
  actions). Frame as notes, never alarms.
- **Verdict**: PASS / WARN / FAIL with specific fixes. Only genuine 🔴 problems gate downstream.
  **FAIL blocks `plan` and `builder-*`.**
- Update `account-context.yaml`: refresh `conversion_actions` (with the verified primary + source) and
  `measurement.*` flags (enhanced_conversions, server_side, ga4.enabled).

## To build / refine later
- [ ] A runnable helper to pull the per-campaign conversion segmentation + format the verdict.
- [ ] Reuse the shared HTML report module (see DECISIONS) when it exists.
