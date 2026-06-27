---
name: google-ads-builder-search
description: >
  Builds a standard Search campaign blueprint: ad-group structure (tight theming), keyword lists with
  match types, responsive search ads (RSAs), negative keyword lists, extensions, and bidding. Emits a human
  .xlsx plus a campaign-spec.json (ad_groups variant) the pusher can export to Google Ads Editor. Reads
  account-context.yaml; no hardcoding. Use when the user says "build search", "search campaign", "keyword
  campaign", "create search ads".
---

# Google Ads — Builder: Search

Design a launch-ready Search campaign. Unlike PMax, Search **pushes cleanly via Google Ads Editor CSV** —
so the campaign-spec maps almost 1:1 to an import file.

## Governing principle — Search is the CONTROL layer over PMax's DISCOVERY
On a PMax/Shopping-heavy account, PMax is the **discovery engine**: it serves broad and surfaces which queries
actually convert. A non-brand Search campaign exists to take **control** of those proven winners — explicit
keywords, bids, match types, and RSA messaging instead of a black box. So the keyword plan is a **harvest of
the account's whole search-term data (Search + PMax), not a catalog brainstorm.** Concretely:
- **Source from both:** `search_term_view` (exact terms + cost, Search/Shopping only) AND
  `campaign_search_term_insight` per PMax (converting *category* themes + conversions — NOT per-term cost or
  exact verbatim, so it's directional; you still choose the exact keyword from the theme).
- **Harvest into EXACT — that's the actual control lever.** An exact-match keyword identical to a query
  outranks PMax for that query; phrase/broad may not. So proven converters go in as **exact**, not phrase.
- **Harvest selectively.** Pull queries where control pays off (volume / value / margin / needs distinct
  messaging — e.g. high-AOV equipment). Leave long-tail one-off converters in PMax; thousands of exacts is
  overhead with no control gain.
- **Coordinate, don't double-pay.** Once a query is an exact in Search, PMax de-prioritizes it; judge
  **incrementality**, not shifted credit.

## Operating rules
- Read context (brand_terms, competitor_terms, guardrails, vertical, budget) + the `plan` output.
- Write to the working directory. Emit BOTH `blueprint.xlsx` (human) and `campaign-spec.json`
  (`campaign_type: "search"`, with `ad_groups[]`).
- Verify every Final URL is live. Enforce guardrails (conversion goals at campaign level; ENABLED-only).

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — per-URL 200 checks; the char-count validation pass; keyword dedupe.
- **Routine (`sonnet`)** — pulling the **dual-source search-term data** (`search_term_view` + `campaign_search_term_insight` per active PMax, incl. the catch-all) + catalog/services + Keyword Planner volume. Dispatch as `general-purpose`; **return raw converting terms, don't theme**.
- **Judge (main session)** — STEP 2 ad-group theming, STEP 3 match-type strategy, STEP 4 RSA copy (via `assets`), STEP 5 brand/non-brand separation. The keyword *data* is cheap; the *structure* is judgment.

## STEP 1 — Inputs (start from the harvest, not the catalog)
From `plan` + context: daily budget and bidding target. **The keyword universe is the whole-account
search-term harvest** (STEP 3), filtered to the converting queries worth controlling — the catalog/services
only *supplement* it and confirm landing pages. If there's no PMax/Search history to harvest (a true cold
launch), say so and lean on Keyword Planner + catalog, starting Phrase/Exact.

## STEP 2 — Ad-group theming (tight)
Group keywords by tight intent themes (one offer/intent per ad group) so the ad copy can match the query.
Derive themes from the catalog/services + real search terms where available. Avoid dumping unrelated
keywords together (theme coherence drives Quality Score). SKAG only if a term truly warrants isolation;
otherwise themed groups.

## STEP 3 — Keywords & match types (the core of a Search campaign — get this right)
Keyword identification + match type is where Search wins or wastes money. Do it deliberately:
- **Ground keywords in the account's REAL search-term data — both sources, MANDATORY. Do NOT invent keywords
  from the catalog alone.** This is the #1 builder-search mistake. `search_term_view` covers only Search/
  Branded; on a PMax-heavy account it returns almost nothing (or only brand terms), so you MUST ALSO pull
  `campaign_search_term_insight` looped **per active PMax campaign** — especially the generic/catch-all PMax,
  which is where non-brand intent actually lives (brand-specific PMax campaigns return only their own brand's
  terms). Build ad groups around what genuinely CONVERTS in that data, not category names you guessed.
  (Same dual-source rule the optimizer uses — see `${CLAUDE_PLUGIN_ROOT}/references/optimization-playbook.md`.)
  Then supplement with Keyword Planner volume and catalog/services. Group tightly by intent (one theme per AG).
  - *Worked example:* on one live account, catalog-derived ad groups MISSED the highest-AOV real intent — a
    high-ticket equipment category ($500+/conv) — while over-weighting a thin low-volume theme. The PMax
    catch-all's `campaign_search_term_insight` surfaced the equipment + attribute demand the catalog guess
    never would. Let the converting data, not the catalog, decide the ad groups.
  - **Resold-brand category terms** that already convert in PMax (e.g. a specific third-party brand's product
    line) are usually PMax's job — don't rebuild them as non-brand Search ad groups (you'd cannibalize PMax).
    Non-brand Search should target the GENERIC / ATTRIBUTE / EQUIPMENT intent PMax under-serves.
- **Match-type strategy**: **Exact** for proven converters — *especially queries harvested from PMax, where
  exact is what wrests control back from the black box*; **Phrase** for controlled expansion; **Broad ONLY
  with Smart Bidding** (never broad on Manual CPC — the legacy-BMM trap). Don't over-rely on broad.
  **Smart Bidding is necessary but not sufficient for broad** — broad needs *conversion history* to steer, so
  a brand-new campaign with zero converters starts Phrase/Exact even on Maximize Conversions, and opens broad
  only after it has data. (Live example: a PMax-heavy account's `search_term_view` showed zero non-brand converters →
  Phrase/Exact, not broad.)
- Dedupe by (ad_group + text + match_type).
- **Match type is ALWAYS output ready-to-copy** — wrapped `[exact]` / `"phrase"` / broad — so it pastes
  straight into the UI/Editor with no re-formatting (`spec_to_paste.py`; `${CLAUDE_PLUGIN_ROOT}/references/google-ads-formatting.md`).

## STEP 4 — RSAs (via `assets`)
One strong RSA per ad group: up to **15 headlines (≤30 chars)** and **4 descriptions (≤90 chars)**, themed
to the ad group. Pin discipline: pin only must-include/legal claims; over-pinning kills RSA flexibility.
Include the keyword intent in headlines + a clear CTA and value prop. Aim for "Good/Excellent" ad strength.

## STEP 5 — Negatives & brand separation
- Campaign + **shared negative lists** (themed: informational/DIY, job-seeker, location, cross-brand,
  irrelevant). Source from real irrelevant search terms; prefer Exact/Phrase, never broad negatives.
- **Separate brand vs non-brand**: keep brand_terms out of non-brand ad groups (route brand to
  `builder-branded-search`). Respect the "what NOT to block" rules (store/coupon/cheap-brand) from the
  optimization playbook.

## STEP 6 — Bidding ramp
From `campaign_defaults.bidding_ramp`: typically Maximize Conversions (no target) during learning →
tCPA/tROAS once volume matures. Respect step-up discipline + change-event cooldown.

## STEP 7 — Extensions
Sitelinks (≥4, with descriptions), callouts (≥4), structured snippets, and image/call/location assets where
relevant. Don't claim an extension is absent without proof (GUARD-6).

## STEP 8 — Output + verification
Emit `blueprint.xlsx` (campaign overview + per-ad-group keywords/RSA/negatives + extensions + bidding +
checklist) and `campaign-spec.json` with `ad_groups[]` (name, theme, keywords[{text,match_type}],
negatives[], rsa{final_url, headlines[{text,pinned}], descriptions[{text,pinned}], paths[]}, extensions).
Set `campaign.status: "paused"`, `conversion_goals.scope: "campaign"`. Put any sitelinks/callouts/snippets in
the campaign-level `extensions` block (not per ad group). Render the workbook with the shared renderer (it
handles `ad_groups` → one AG sheet per ad group with keywords/RSA/negatives/paths):
`python ${CLAUDE_PLUGIN_ROOT}/skills/builder-pmax/scripts/spec_to_xlsx.py <campaign-spec.json> --output blueprint.xlsx`
Verify with `validate_spec.py`: RSA char limits + counts (≤15/≤4) using **Google-accurate counting**
(`${CLAUDE_PLUGIN_ROOT}/references/google-ads-formatting.md`), keyword match types valid, every Final URL live (200, no
redirect, group-specific), negatives Exact/Phrase. Hand the JSON to `pusher` → Editor CSV
(`spec_to_editor_csv.py`) + ready-to-copy keyword/negative blocks (`spec_to_paste.py`).

## To build / refine later
- [ ] Shared the RSA generator with `assets`; Editor CSV mapping lives in `pusher`.
