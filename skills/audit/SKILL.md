---
name: google-ads-audit
description: >
  Audits and scores an existing Google Ads account across conversion tracking, wasted spend, account
  structure, keywords/Quality Score, ads & assets (incl. PMax, AI Max, Demand Gen), and settings.
  Read-only. Generalized fork of the ads-google audit: reads everything from account-context.yaml and
  applies the operator's guardrails — no brand/vertical hardcoding. Use when the user says "audit",
  "score my account", "what's wrong with my ads", "wasted spend", "account review", "health check".
---

# Google Ads — Audit

Read-only diagnostic. Score the account, surface issues by severity, and — critically — **never fire a
finding on an unverified assumption**. Reuse the live MCP detection proven in `setup`.

## STEP 0 — Load context (MANDATORY, before any scoring)
1. Read `account-context.yaml` from the working directory. If missing, run `setup` first.
2. Pull from it: `google_ads.customer_id`, `brand_terms`, `competitor_terms`, `margin_tiers`,
   `data_source` (for landing-page URL checks), `measurement`, and **`guardrails`**.
3. Output is written to the **working directory** (`GOOGLE-ADS-AUDIT.md`), never into the plugin.

## ⚠️ The six guards (apply to EVERY check — they prevent the most common wrong findings)
These are generic; `guardrails` in the context may strengthen or add to them. Honor both.

- **GUARD-1 Conversions — check the WHOLE picture, not the action list.** Inspect *campaign-level*
  conversion goals + which actions each active campaign actually fires (segment by
  `segments.conversion_action_name`), and each action's source. A primary action no campaign uses is
  inert; a second purchase action kept *secondary* (e.g. GA4 purchase alongside the Shopify channel "App
  Purchase") is the CORRECT anti-double-count setup, not a bug. Only flag a real micro-conversion goal
  or two value-carrying purchase sources both primary and both firing.
  **Before flagging ANY conversion-action contamination (out-of-brand / micro / duplicate), check
  `primary_for_goal`.** A non-primary action does not enter Smart Bidding and does not affect performance —
  it's harmless; surface it as a NOTE (tidy-up), never a scored finding. Only a PRIMARY out-of-brand/micro
  action that an active campaign optimizes toward is a real issue. See `${CLAUDE_PLUGIN_ROOT}/references/conversion-tracking-logic.md`.
- **GUARD-2 Negatives — FOUR sources, merge ALL.** (1) `campaign_criterion` (negative=true) — campaign-level;
  (2) `campaign_shared_set` → `shared_set` → `shared_criterion` — SHARED LISTS (the bulk: e.g. "Account Level
  Negative", "OPI Negative", brand blocks); (3) `customer_negative_criterion` — ACCOUNT-LEVEL negatives applied
  account-wide; (4) `campaign_criterion.brand_list.shared_set` — brand exclusions. Only flag a gap if terms are
  absent across ALL FOUR; if a shared/account list covers them, cite it, don't flag. **A `campaign_criterion`-only
  pull is the #1 false-positive in this audit — it looks "thin" when coverage is actually 100+ terms/campaign.**
  After merging all four, declare `pulled:[...,"negatives_complete"]` so the report renders a real verdict;
  without that assertion a campaign-only bundle renders VERIFY (re-pull), never a false "weak negatives".
- **GUARD-3 Budget scaling — check `change_event` first.** Before recommending a budget/bid increase,
  pull recent change history (~14d). A recent budget/bid/asset/structure change → recommend cooldown,
  not scale. (Strengthen with any `change-event-cooldown` guardrail in context.)
- **GUARD-4 Ad strength — confirm ENABLED + impressions.** Before flagging POOR ad strength, confirm
  `ad_group.status` AND `ad_group_ad.status` are ENABLED and the group has impressions. Paused =
  intentional; do not flag.
- **GUARD-5 ROAS — apply margin tiers from context.** Read `margin_tiers`; a line with a tier accepts its
  `min_roas` (house brands run lower ROAS by design). Never apply a generic ROAS threshold to such a
  line or a strategic campaign. If unsure, ASK rather than flag.
- **GUARD-6 No false "absence".** MCP results can be truncated (token cap or your `limit`). Before
  claiming "no video / no signal / no negative / no X", re-query filtered on the enum NAME (e.g.
  `field_type = 'YOUTUBE_VIDEO'`) or pull with returned-rows < limit (proof of completeness). NEVER
  infer presence/absence by decoding enum integers from memory. Track failed fetches as a G-SYS1
  diagnostic; never silently skip a check — explain why data is unavailable.

## Audit scope — only what's LIVE in the window (build this FIRST, before any check)
Establish the **active campaign set**: campaigns that are ENABLED **AND had impressions > 0 during the
audit window**. Exclude removed, paused, and ENABLED-but-dormant (zero-impression / long-off) campaigns.
Then **scope EVERY other pull to that set** — asset groups, ad groups, ads/ad-strength, keywords, search
terms. Entity-level `status = ENABLED` is NOT sufficient: a campaign turned off years ago can still contain
ENABLED asset groups / ad groups, and auditing them produces stale, misleading findings. Filter downstream
queries by `campaign.id IN (active set)`, or pull them WITH metrics over the window and drop zero-impression
rows app-side (metrics can't go in a GAQL WHERE). Never audit a campaign that hasn't served in the window.

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — STEP 0 context read; the `money_leak_report.py` render (→ the single `AUDIT.html`) after the Judge writes `audit-result.json`; single URL/landing 200 checks.
- **Routine (`sonnet`)** — build the active-campaign set; the account data-bundle pull (campaigns, assets, change history); the dual-source search-term pull (per-PMax `campaign_search_term_insight` loop). Dispatch as `general-purpose` sub-agents (they keep MCP); tell them to **return raw rows, not score**.
- **Judge (main session)** — applying GUARD-1…6, every PASS/WARN/FAIL call, the score, the Gap-to-100 ledger, Quick Wins. **Never delegate a guard or a verdict** — a Scout pulls numbers, the Judge says what they mean.

## Process
1. **Pre-flight**: load context + guards; **build the active campaign set** (above); stage the GUARD data
   pulls (campaign conversion goals, merged negatives, `change_event`, `ad_group.status`) scoped to it.
2. **Collect** account data via the Google Ads MCP, **scoped to the active campaign set**. Honor GAQL gotchas
   in `${CLAUDE_PLUGIN_ROOT}/skills/audit/references/gaql-notes.md` (dedup keywords; ENABLED-only +
   impressions-in-window; explicit YYYY-MM-DD date ranges; `search_term_view` can't use a 90-day DURING).
   **MANDATORY pulls — a missing one = a false finding, not a clean account (this is the checklist a dispatched
   Scout MUST be handed in full):**
   - campaigns + metrics (active set), budgets, bidding strategy + tROAS
   - conversion_action (account) + per-campaign `segments.conversion_action_name` usage (GUARD-1)
   - asset_group / ad_group_ad ad-strength; keyword_view + Quality Score (deduped)
   - **campaign extensions coverage** (D9): `SELECT campaign.id, campaign.status, campaign_asset.field_type,
     campaign_asset.status FROM campaign_asset WHERE campaign.status='ENABLED' AND campaign_asset.status='ENABLED'`.
     `field_type` gives the coverage (SITELINK / CALLOUT / STRUCTURED_SNIPPET / PRICE / IMAGE). **Two gotchas,
     both seen live:** (1) `campaign.status` MUST be in the SELECT because it's filtered (else
     `EXPECTED_REFERENCED_FIELD_IN_SELECT_CLAUSE`); (2) do NOT also select `asset.type` here — it throws
     INVALID_ARGUMENT on many MCPs (pull asset text separately if needed). Count `field_type` **per campaign**
     (not just presence) so "thin extensions" findings use real counts. If it still errors, flag extensions
     **UNVERIFIED — verify in UI**, never assume present/absent.
   - search terms **both** sources: `search_term_view` + per-PMax `campaign_search_term_insight`
   - **negatives from ALL FOUR sources (GUARD-2) — NOT just `campaign_criterion`:**
     (a) `campaign_shared_set` (which shared lists attach to each campaign — **count only `status=2` ENABLED;
     many lists are `status=3` REMOVED/old**) → `shared_criterion` (the terms in each ENABLED list);
     (b) `customer_negative_criterion` (account-level negatives applied to every campaign — a separate resource,
     easy to miss; the first ND pull omitted it and produced a false "weak negatives" finding that had to be
     corrected mid-audit). A brand block / cross-brand block / location block usually lives in a SHARED or
     ACCOUNT-level list, so a `campaign_criterion`-only pull shows "no negatives" when coverage is actually
     extensive. **Never flag G07/G14/G-PM5/G-PM6 (brand exclusion / negative coverage) without having pulled
     `shared_criterion` AND `customer_negative_criterion`. After merging, declare `pulled:[...,"negatives_complete"]`.**
   - **PMax Brand exclusions are a SEPARATE layer from negative keywords — pull them explicitly:**
     `campaign_criterion` selecting `campaign_criterion.brand_list.shared_set` + `.negative`
     (filter `campaign_criterion.brand_list.shared_set IS NOT NULL`), then resolve each `shared_set.name`.
     These rows have an EMPTY `keyword.text`, so a keyword-text-only pull DROPS them and you'll wrongly
     report "no brand exclusion". Check whether a brand list matching the own brand (a list named after the
     own brand) is excluded on each PMax campaign. An account can run BOTH a brand negative-keyword list AND a brand-list
     exclusion (belt-and-suspenders) — read both before judging.
   - `change_event` (~14d)
   - **channel split** (D8): `segments.ad_network_type` per campaign — **this WORKS for PMax too** (network 2
     Search/Shopping dominates; small YouTube/Display/cross). NEVER report channel as "verify in UI". Pull
     `metrics.conversions` alongside cost — a cost-only pull makes every network look like 0-conv burn.
   - **device split** (D10): `segments.device` per campaign (2 Mobile · 3 Tablet · 4 Desktop · 5 CTV · 6 Other).
   - **dayparting** (D3/D4): `segments.hour` + `segments.day_of_week` per campaign + metrics — for the hourly
     heatmap and best/worst hour/day. And **ad schedule**: `campaign_criterion.ad_schedule.*` + `bid_modifier`
     (a flat `bid_modifier=0` across the window = NO dayparting bid strategy — a real opportunity finding).
   - **geo — ALL regions** (D3): `geographic_view` scoped to active campaigns, `metrics.cost_micros > 0`, **no
     top-N limit**. Then resolve EVERY `segments.geo_target_region` id to a name via `geo_target_constant`
     (id, name, canonical_name). Raw `geoTargetConstants/NNNNN` ids in the report = an unfinished pull, never ship them.
   - **asset TEXT + per-asset metrics** (D9) — pull the TEXT and cost, NOT just counts (a counts-only pull is
     wrong; the verbatim text + per-asset spend is what surfaces "this headline spent $X at 0 conv"):
     `SELECT campaign.id, asset_group_asset.field_type, asset.text_asset.text, metrics.cost_micros,
     metrics.conversions, metrics.conversions_value, metrics.clicks FROM asset_group_asset WHERE
     campaign.status='ENABLED' AND asset_group_asset.status='ENABLED' AND segments.date BETWEEN ...` (HEADLINE
     ft2 / DESCRIPTION ft3 / LONG_HEADLINE ft18). `asset_group_asset` DOES return per-asset metrics — a
     text-only or count-only pull just *looks* empty (gaql-notes). For **Search RSAs**, `ad_group_ad.ad.
     responsive_search_ad.headlines` is a RepeatedComposite the serializer can't return — get RSA asset text +
     metrics from **`ad_group_ad_asset_view`** instead (don't write "verify in UI"). The ONLY genuine UI-only
     asset field is `asset_group_asset.performance_label` (UNRECOGNIZED on some API versions).
   - **extension TEXT** (D9) — not just field_type counts: pull the sitelink/callout/snippet/price **text**
     so the report shows the actual extensions. Either `campaign_asset` joined to the `asset` text fields
     (`asset.sitelink_asset.link_text`, `asset.callout_asset.callout_text`, `asset.structured_snippet_asset.values`,
     `asset.price_asset.*`) or the `asset` resource by id. bundle key `ext_text:[{campaign_id,field_type,text}]`.
   - **conversion lag** (D12): `segments.conversion_lag_bucket` — the "can I trust short-window ROAS?" gate.
   - **settings & measurement that DO read** (pull these — they were once wrongly punted to UI): **location type**
     `campaign.geo_target_type_setting.positive_geo_target_type` — **official enum: 5=PRESENCE_OR_INTEREST,
     6=SEARCH_INTEREST (both leaks → recommend Presence-only), 7=PRESENCE (correct, NOT a leak)**. Do NOT invert
     this: 7 is the GOOD value. (Verified live + against the v21 proto 2026-06-28.) **Enhanced Conversions** `customer.conversion_tracking_setting.enhanced_conversions_for_leads_enabled`
     + `.accepted_customer_data_terms`; **final URLs** via `landing_page_view` / `expanded_landing_page_view`;
     **RSA text + per-asset metrics** via `ad_group_ad_asset_view`; **placement exclusions** via
     `campaign_criterion.placement.url`; **content-label exclusions** (digital content labels DV-G/PG/T/MA) via
     `campaign_criterion` WHERE `type='CONTENT_LABEL'` (`content_label.type`) — **this READS; an empty result =
     none configured, NOT unreadable** (do not punt it to UI). bundle key `content_labels:[{campaign_id,content_label_type}]`.
     (Exact queries: `references/gaql-notes.md`.)
   - **⚠️ "verify in UI" is ONLY these confirmed-blocked fields** (every variant tested 2026-06-28) — do NOT
     mark anything else UI-only: Final URL Expansion toggle (`url_expansion_opt_out` UNRECOGNIZED), asset
     automation (`asset_automation_settings` PROHIBITED/RepeatedComposite), the **video brand-safety inventory
     mode** (`campaign.video_brand_safety_suitability` UNRECOGNIZED on this version — Expanded/Standard/Limited),
     PMax `asset_group_asset.performance_label` (UNRECOGNIZED — use
     `asset_group.ad_strength` + per-asset cost/conv), and **Consent Mode v2 / server-side-CAPI** (tag-side by
     design — verify in GTM, NOT a pull failure). EVERYTHING ELSE is in the API: a fetch that returns nothing =
     wrong method (field/resource/missing `metrics.*`/enum-to-drop), **retry** — see `references/gaql-notes.md`.
     A "we can't see it, check the UI" on API-available data is the #1 way this audit loses a user's trust.
   - **GAQL gotcha:** any field used in a `WHERE` filter MUST also appear in the `SELECT` clause, or the API
     returns `EXPECTED_REFERENCED_FIELD_IN_SELECT_CLAUSE` (e.g. filtering on `campaign.status` requires
     selecting it). If a field is rejected, drop just that field and re-run — don't abandon the whole pull.
   - **COMPLETENESS — loop every campaign, never truncate.** Per-campaign pulls (`asset_group_signal`,
     `asset_group_asset`, `campaign_search_term_insight`) must cover **ALL** PMax/Search campaigns — do NOT stop
     "to save time" at the first few. A partial pull (e.g. signals for 3 of 7 PMax) makes the generator emit
     FALSE "0 audience signals" findings for the un-pulled ones. Big results: save to a file + parse, don't drop.
   - **DECLARE what you pulled.** `bundle.json` MUST carry a top-level **`pulled: [...]`** listing every
     dimension you FULLY pulled (all campaigns) — e.g. `["active_campaigns","channel","device","geo","dayparting",
     "schedule","extensions","signals","negatives","assets","products","conversion_lag","change_events"]`.
     **Omit any dimension you could not complete** — the generator renders those VERIFY ("not pulled — re-run")
     instead of fabricating GOOD/FIX. Honesty-by-construction: an absent `pulled` entry is safe; a half-filled
     dimension passed off as complete is what burns the user.
3. **Validate coverage**: confirm ≥30 days of data and a Search Terms Report before scoring; if a source
   is down, degrade gracefully (flag it, continue) per the fallback chain in `setup`.
4. **Evaluate** each applicable check as PASS / WARNING / FAIL — applying GUARD-1…6 so nothing fires on an
   assumption. Use `${CLAUDE_PLUGIN_ROOT}/skills/audit/references/google-audit-checks.md` for the check catalog and severities.
5. **Score** per `${CLAUDE_PLUGIN_ROOT}/skills/audit/references/scoring-system.md` (weighted by severity × category).
6. **Report** with the per-category Gap-to-100 ledger and an action plan.

## Money-Leak deep-dive (MANDATORY — this is what makes the audit worth paying for)
Beyond scoring, run the money-leak diagnostics in `${CLAUDE_PLUGIN_ROOT}/references/diagnostic-playbook.md`
(D1 bid/target health · D2 budget pacing & allocation · D3 geo waste · D4 dayparting · D5 search-term/spam/
wrong-brand · D6 structure/setup · D7 Quality Score · D8 PMax channel/placement · D9 ad copy/assets/extensions ·
D10 settings hygiene · D11 audience signals/search themes · D12 conversion-lag gate · D13 change-history timeline ·
**D14 product feed & Shopping performance**). **For ECOM, D14 is the highest-$ diagnostic.** It has THREE
layers, each from a different source — degrade cleanly, don't lump them as "needs Merchant":
  1. **Product PERFORMANCE/identity (Ads, always available)** — `shopping_performance_view` returns full product
     data through the Merchant LINK (item_id, title, brand, type, condition + cost/impr/conv). The "which product
     burns / converts" leak. The products ARE in Google Ads — never say "no product data".
  2. **Out-of-stock (STORE connector)** — cross-ref the spending item_ids against the store's live inventory
     (Shopify/Woo). OOS spenders = pure waste, and this needs NO Merchant connector — only the store you already
     connected. Do this whenever a store is connected.
  3. **Approval STATUS (Merchant Content API only)** — disapproved / GTIN / policy issues are NOT a GAQL field.
     If a Merchant connector is present, pull it; if not, flag ONLY this layer as verify-via-Merchant (not the
     whole of D14). Each diagnostic yields a **Money-Leak Report** row: leak · evidence
(real numbers) · diagnosis (root cause, not symptom) · **$/month at risk** (formula shown) · exact fix ·
discipline · confidence. Decode `bidding_strategy_system_status` FIRST (one field separates budget-capped vs
tROAS-too-high vs starved vs learning). A generic "score 85" without these specific, dollar-quantified leaks is
the low-value audit we are explicitly NOT shipping. The diagnostics feed both the category scores and the
Money-Leak Report in the output.

**One-command pipeline (model-tier dispatch) → ONE comprehensive report:** dispatch a **Routine** sub-agent
(`general-purpose`, sonnet) to run the PULL MANIFEST in
`${CLAUDE_PLUGIN_ROOT}/skills/audit/scripts/money_leak_report.py` (its docstring lists every GAQL query + the
`bundle.json` schema) → it writes `bundle.json`. **Write `audit-result.json` (the score — STEP 5) into the SAME
directory** so the generator merges score + money-leak. Then **Scout**-run
`python ${CLAUDE_PLUGIN_ROOT}/skills/audit/scripts/money_leak_report.py bundle.json --out-dir <workdir>` to
generate `MONEY-LEAK-REPORT.md` + `DETAILED-ACCOUNT-REPORT.md` AND the **single comprehensive `AUDIT.html`** —
score donut + grade, the 6 weighted category bars (fixable/unverified findings), money-leak $ chart + findings,
a **visual per-campaign section** (ROAS-vs-target bar with target tick, status pill, channel-split bar,
extension/signal chips), Merchant feed table, quick wins, change timeline, verify-in-UI. It auto-detects
`audit-result.json` next to the bundle (or pass `--audit-result`); without it AUDIT.html degrades to
money-leak-only. **AUDIT.html is THE — and the ONLY — HTML deliverable: one file, score + full check + leaks +
per-campaign visuals together.** Do not render any second HTML report (no `audit-report.html`); there is exactly
one HTML output per audit.
Then the **Judge** (you) adds verify-in-UI verdicts. **When a pull returns nothing, assume wrong method (field
name / resource / missing `metrics.*` / repeated-enum serialize), not an API limit — retry before writing
"verify-in-UI"** (see gaql-notes principle).

## What to analyze (category weights)
- **Conversion Tracking (25%)** — campaign-level goals (GUARD-1), Enhanced Conversions, Consent Mode v2,
  value tracking, attribution, offline import (lead gen), conversion lag. Cross-check Google Ads vs GA4
  (flag >35% divergence) when `measurement.ga4` is enabled.
- **Wasted Spend / Negatives (20%)** — review search terms from **BOTH sources** (`search_term_view` does
  NOT contain PMax terms): `search_term_view` for Search/Branded campaigns + `campaign_search_term_insight`
  **looped per active PMax/Demand-Gen campaign** (it requires a single `campaign_id` filter; see
  gaql-notes.md). Merged negative coverage (GUARD-2), brand/non-brand separation (use `brand_terms`), broad
  match only with Smart Bidding, geo precision. Source negatives from actual irrelevant search terms; prefer
  Exact/Phrase; recommend shared lists. Only flag wasted on Search terms with >$10 spend AND 0 conv; for
  PMax, flag irrelevant categories with clicks but no conversions. **Never propose blocking brand terms.**
- **Account Structure (15%)** — business-logic organization, tightly themed ad groups, ≥3 RSAs/group,
  PMax asset-group/signal structure, naming consistency.
- **Keywords & Quality Score (15%)** — match-type strategy, QS distribution (≥7 target), cannibalization
  (watch cross-campaign + use `brand_terms`), impression share. Apply the legacy-BMM heuristic (BROAD +
  Manual CPC = legacy, not intentional broad).
- **Ads & Assets (15%)** — RSA headlines/descriptions count & strength (GUARD-4), pin discipline,
  extensions (sitelinks/callouts/snippets/image), PMax/AI Max/Demand Gen specifics (below).
- **Settings & Targeting (10%)** — Smart Bidding vs deprecated ECPC, budget pacing, ad schedule, device
  adjustments, location = "Presence" not "Presence or Interest", network settings.

## Deep dives (only if those campaign types exist)
- **PMax** — asset-group diversity, audience signals, URL-expansion control, search themes, Insights tab,
  and **brand handling — VERIFY, don't just "confirm"**. When a Brand Search campaign runs alongside PMax,
  do NOT flag "missing brand exclusion" on the surface. First DIG IN and check ALL THREE block mechanisms:
  (a) **campaign-level negative keywords** (`campaign_criterion`, `negative=true`, type KEYWORD);
  (b) a **shared negative list** (`campaign_shared_set` → `shared_criterion`) — brand blocks are MOST often a
  named shared list (e.g. "Brand Keywords — do not apply to Branded campaign") applied to PMax + non-brand campaigns
  and excluded from the Branded campaign; (c) a **brand-exclusion brand list** (brand-list criteria). Check
  whether the account's `brand_terms` are actually blocked by ANY of these.
  **If brand is already blocked → it's a PASS; re-score, don't flag.** Only flag G07/G-PM3 if brand
  terms are genuinely unblocked (and corroborate with G-PM3: are >15% of PMax conversions on brand terms?).
  Honor any `pmax-brand-exclusion` guardrail.
- **AI Max for Search** — `campaign.ai_max_setting.enable_ai_max`, broad-match+Smart-Bidding combo, search
  term matching distribution, AI Brief, text-customization rules, FUE controls, brand exclusions. DSA/ACA
  auto-migration pre-flight (Sept 2026) — stage LOW→HIGH risk; strong negatives are a prerequisite.
- **Demand Gen** — video+image asset mix, audience signals, funnel-aligned conversion goals (no frequency
  capping — monitor manually).

## Key thresholds
| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| Quality Score (avg) | ≥7 | 5-6 | <5 |
| CTR (Search) | ≥6.66% | 3-6.66% | <3% |
| CVR (Search) | ≥7.52% | 3-7.52% | <3% |
| CPC (Search) | ≤$5.26 | $5.26-8.00 | >$8.00 |
| Wasted Spend | <10% | 10-20% | >20% |
| Ad Strength | Good+ | Average | Poor |
(Thresholds are **ecommerce-Search defaults** and niches vary widely — apparel ≠ electronics ≠ supplements.
**Derive bands from the account's OWN historical data first**; fall back to these only for a brand-new account,
and state the basis. Never FAIL a campaign on a benchmark its niche legitimately runs below.)

## Report architecture — PER-CAMPAIGN VISUAL EXPLAINER (see `${CLAUDE_PLUGIN_ROOT}/references/per-campaign-report-template.md`)
The audit is a **per-campaign visual explainer**, not a generic account summary. Document order: **Account
panel → one chart-rich block per active campaign → Action Plan**.

**The 3-step rule for EVERY item — ① DATA shown → ② VERDICT (GOOD / WATCH / FIX / VERIFY) → ③ ACTION (only
if needed).** There is NO separate "money-leak summary" block: the leak IS the verdict+action on the section
it belongs to (evaluated inline). Every quantitative metric renders as its own **inline-SVG chart**, never a
wall of text:
- ROAS vs target → **semicircle gauge** (fill = ROAS, tick = target) · Budget pacing → **radial ring**
- Channel mix → **donut** · Device & Geo → **horizontal bars colored by ROAS** · Schedule → **24-hour heatmap**
- Extension/signal counts → **meter bars** vs the recommended count.
Each campaign block shows a **scorecard** (N good · N watch · N fix · N verify) and covers: performance +
decoded `bidding_strategy_system_status`, channel, device, geo, schedule, products × Merchant, audience
signals + search themes, ad copy (headline/description text), extensions **with text**, negatives + shared
lists, final URLs/FUE, change/cooldown — each field marked **[API]** or **[VERIFY]** (read-only API can't
see it). The **account panel lists & rates EVERY account-level setting** (conversion tracking, Enhanced
Conv, Consent, account/brand negative lists, Content Suitability, structure, conversion-lag) the same 3-step
way. **Localize per campaign**; only cross-campaign / account-wide items (budget misallocation, tracking,
content suitability, structure) sit in the account panel. Flat/modern style (no heavy gradients).

The blueprint (every section, its chart, data source, verdict thresholds) is
`references/per-campaign-report-template.md`. The generator (`money_leak_report.py`) builds it: account
panel + Σ(campaign block) + action plan → one self-contained `AUDIT.html`. It auto-detects `audit-result.json`
next to the bundle for the score + the account panel's category verdicts.

## Output — `GOOGLE-ADS-AUDIT.md` (to the working dir)
1. **Health Score** 0-100 + grade, with the six category bars.
2. **Per-category Gap-to-100 ledger** (MANDATORY for any category < 100). Split every non-PASS into:
   - 🔧 **Fixable (verified)** — check ID, status, severity, **points recoverable**, concrete fix.
   - 🔍 **Unverified** — API/MCP can't see it (Enhanced Conversions recording, Consent Mode mode, gtag
     firing). Do NOT score as FAIL; mark "verify in UI" and state the ceiling if confirmed. A low score
     driven by unverified items is not breakage — say so.
3. **Money-Leak Report** (the headline deliverable) — the D1-D14 findings as rows ranked by $/month
   recoverable, each with evidence + root-cause diagnosis + exact fix + discipline + confidence. Top 3 = Quick
   Wins. This is what the operator reads first.
4. **Detailed Account Report** (the differentiated value — granular, not just a score). Beyond the summary:
   - **Account summary** + *what is protecting it* (e.g. "no Display burn BECAUSE Content Suitability blocks junk
     apps" — explain the cause, don't just report the healthy symptom).
   - **Per active campaign**, a deep ledger: bidding/tROAS + **decoded `bidding_strategy_system_status`**, ROAS
     vs target, channel split (D8), device split (D10), geo top/bottom (D3), dayparting flags (D4), extension
     inventory — sitelinks/callouts/snippets counts (D9), ad-copy notes incl. duplicates/Ad-Strength (D9), and
     the **settings layer (D10)** — Final URL Expansion + URL exclusions, asset automation / text customization,
     text/brand guideline (exists? appropriate?), content-suitability / placement exclusions, device exclusions.
     **Mark each field API-read or verify-in-UI.**
   - **Per-campaign Verify-in-UI checklist** — the settings the read-only API can't see (FUE, asset automation,
     content suitability, text-guideline content) listed as explicit checkboxes. Never silently skip a setting.
5. Wasted-spend estimate (monthly $), PMax/AI Max notes.
6. **Findings feed `optimizer` and `plan`** — but audit itself changes nothing.

### Also emit a structured result — it feeds the ONE comprehensive HTML report
- Write **`audit-result.json`** (schema: `${CLAUDE_PLUGIN_ROOT}/templates/audit-result.json`): health_score, grade, per-category
  scores + fixable/unverified findings, quick_wins, wasted_spend_monthly, notes. **Put it next to `bundle.json`.**
- The client report is **`AUDIT.html`** from `money_leak_report.py` (above): a **per-campaign visual explainer**
  that auto-merges this score JSON (account panel + category verdicts) with the per-campaign chart blocks
  (gauge / ring / donut / bars / heatmap) where every item is **data → verdict → action**. ONE self-contained
  file. **Do NOT ship the score and the money-leak as two separate HTML files** — the audit is one document.
- **There is exactly ONE HTML report: `AUDIT.html`.** The old score-only `audit_to_html.py`/`audit-report.html`
  path has been REMOVED — do not look for it or generate a second file.

## To build / refine later
- [x] **Per-campaign visual-explainer `AUDIT.html`** — `scripts/money_leak_report.py` renders the chart-rich,
  data→verdict→action report (gauge/ring/donut/bars/heatmap + account panel + scorecards). This is the SOLE HTML
  report; the legacy `audit_to_html.py` was removed. Done.
- [x] Full granular check-ID catalog (G01…G61 + extensions) in `${CLAUDE_PLUGIN_ROOT}/skills/audit/references/google-audit-checks.md`. Done.
- [ ] Vertical-specific benchmark bands in `${CLAUDE_PLUGIN_ROOT}/references/`.
- [ ] Per-keyword QS + RSA pin/headline-count detail for Search campaigns (currently summarized).
- [ ] Geo as a US choropleth (currently colored bars).
