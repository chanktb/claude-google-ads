# Diagnostic playbook — the money-leak engine

The high-value brain of the suite. `audit` runs these to PRODUCE findings; `optimizer` turns each into an
action; `routine` runs them on cadence. The difference between a cheap "score 85/100" audit and a sellable
one is HERE: every diagnostic maps a **signal → GAQL → threshold → diagnosis → prescription → discipline →
$ impact**, so the output is a dated to-do that saves money, not a grade.

Business-agnostic: thresholds are defaults; read margin/vertical/guardrails from `account-context.yaml` and
adjust. Reuse the six GUARDs (audit/SKILL.md) and the three-source-negatives rule (gaql-notes.md) — never
fire on an unverified or incomplete pull.

## Output — the Money-Leak Report (rank by $/month recoverable)
Each finding is one row:

| field | meaning |
|-------|---------|
| **Leak** | one-line symptom in the operator's language ("budget burns 10pm at 0.4x ROAS") |
| **Evidence** | the actual numbers pulled (cost, conv, ROAS, IS, target) — never vague |
| **Diagnosis** | the distinguished root cause (not the symptom) — why THIS and not a look-alike |
| **$ / month** | estimated recoverable/at-risk spend, with the formula shown (never fabricated) |
| **Fix** | exact steps (UI path / negative list / target value), paste-ready |
| **Discipline** | step size · cooldown · conversion-floor gate · "wait vs act" |
| **Confidence** | High / Investigate — small-sample geo/daypart = Investigate, not Cut |

Sort by `$ / month` descending. Lead the report with the top 3 as Quick Wins.

## Cross-cutting discipline (applies to every prescription)
- **tROAS/tCPA changes:** ≤0.2–0.3x (or 10–15%) per step; wait ~2 weeks; need ≥15 conv/wk. Conversion floors:
  <30 conv/mo → Maximize Conversions (no target); 30+ → tCPA; 50+ → tROAS. Below floor, **consolidate, don't target**.
- **Budget changes:** +10–15% per step; hold the `change-event-cooldown`; never reverse direction inside it;
  prefer Mondays.
- **Cooldown is law:** never flag/act on a campaign with a recent `change_event` in the window. Check first.
- **Confidence gate:** require ≥100 impressions or ≥10 clicks (or ~1 conversion cycle) before calling a geo,
  daypart, or search term "bad". Small samples = Investigate.
- **Aug 17 2026 Google change:** tROAS/tCPA campaigns "Limited by budget" that OVER-perform their target will
  be auto-adjusted to deliver closer to target (spend more, ROAS drops toward target). If all campaigns beat
  target with headroom, factor this in before manually lowering targets — Google may do it for you.

---

## D1 — Bid strategy & target health (the biggest single lever)

**Pull (per active campaign):** `campaign.bidding_strategy_type`, `campaign.bidding_strategy_system_status`,
`campaign.maximize_conversion_value.target_roas`, `campaign.maximize_conversions.target_cpa_micros`,
`campaign.bidding_strategy` (non-null = portfolio), `campaign.manual_cpc.enhanced_cpc_enabled`,
`campaign_budget.amount_micros`, `metrics.cost_micros/conversions/conversions_value`,
`metrics.search_impression_share`, `metrics.search_rank_lost_impression_share`. Compute
**achieved ROAS = conversions_value / (cost_micros/1e6)** and **spend/budget ratio**.

> **CRITICAL caveat (research-confirmed):** `search_budget_lost_impression_share` is INCOMPATIBLE with
> Maximize Conversions / Maximize Conversion Value (those spend full budget by design) and is UNAVAILABLE for
> PMax (PMax exposes only `search_impression_share`). So for Smart Bidding / PMax, **do NOT diagnose budget
> constraint from budget-lost-IS** — use spend-vs-budget ratio + `bidding_strategy_system_status`.
> Budget-lost-IS is only trustworthy on Manual-CPC Search campaigns.

**`bidding_strategy_system_status` is the single fastest diagnostic — decode it first:**

| Status | Meaning | Action |
|--------|---------|--------|
| `ENABLED` | healthy | none |
| `LEARNING_*` (NEW / SETTING_CHANGE / BUDGET_CHANGE / COMPOSITION_CHANGE / CONVERSION_*) | in learning after a change | **WAIT — cooldown active**, don't judge or act |
| `LIMITED_BY_BUDGET` | budget-capped (the GOOD problem) | if ROAS ≥ target → scale budget +10–15% |
| `LIMITED_BY_INVENTORY` | **tROAS too high OR targeting too narrow** | lower target −0.2–0.3x, or widen targeting |
| `LIMITED_BY_DATA` | starved of conversions (below floor) | consolidate / drop target / use Max Conversions |
| `LIMITED_BY_CPC_BID_CEILING` | a max-CPC cap is blocking | raise/remove the bid cap |
| `MISCONFIGURED_CONVERSION_TYPES/SETTINGS` | tracking broken | fix tracking (→ measurement) before anything |

**Breakeven ROAS = 1 ÷ gross-margin** (40% margin → 2.5x; 30% → 3.33x; 50% → 2.0x). A tROAS below breakeven
buys money-losing conversions; a healthy target sits a cushion (≈1.2–1.5×) above breakeven, read against
`margin_tiers`.

| Diagnosis | Signature | Fix | Discipline |
|-----------|-----------|-----|-----------|
| **tROAS too HIGH (unachievable → starves)** | spend ≪ budget · achieved ROAS far BELOW target · (Search) rank-lost-IS high + budget-lost-IS ~0 · status `LIMITED` | LOWER target toward recent achieved ROAS | −0.2–0.3x per step, wait 2wk |
| **tROAS too LOW (spends, thin)** | spends full budget · achieved ≈ a low target · achieved ROAS < breakeven (=1/gross-margin) | RAISE target toward profit | +0.1–0.3x per step, 2wk gap |
| **Achieved but CAPPED (leaves money)** | achieved ROAS ≫ target · spend ≈ budget (Smart Bidding) OR budget-lost-IS high (Manual) | SCALE: +10–15% budget; consider lowering target slightly to buy volume at still-profitable ROAS | gentle step, Monday |
| **Wrong strategy** | ECPC present (`enhanced_cpc_enabled=true`, dead since Mar 2025) OR Manual CPC with ≥30 conv/mo | move to Smart Bidding (MaxConv → add target at floor) | don't force if <30 conv/mo |
| **Fragmented learning** | several campaigns same goal each <30 conv/mo, all erratic | pool into a **portfolio** tROAS/tCPA (not PMax — unsupported) | needs ≥50 conv/mo pooled |

**The distinguishing question for underspend:** is it the *target* choking delivery, or genuinely *low demand*?
On Search, `rank_lost_IS` high + `budget_lost_IS` ~0 + `LIMITED` = target ceiling (lower it). IS ≥95% =
saturation (no more volume to buy). On Smart Bidding/PMax where budget-lost-IS is blind: spend ≪ budget with
achieved ≥ target → target ceiling; spend ≪ budget with low IS and few impressions → low demand/targeting.

---

## D2 — Budget pacing & allocation

**Pull:** budgets + spend per campaign (above), `bidding_strategy_system_status`, ROAS per campaign, recent
`change_event`. (Shared budgets: check `campaign_budget` shared across campaigns.)

- **Misallocation (the classic pattern):** a LOW-ROAS campaign spends freely at/near its cap while a
  HIGH-ROAS campaign has headroom or is `LIMITED`. **Fix:** shift budget from the low-ROAS to the high-ROAS
  campaign (it earns more per $). $ impact = reallocated spend × (high ROAS − low ROAS). Discipline: +10–15%
  step, Monday, respect cooldown, marginal-ROAS test ($100 incremental for 7d) if unsure.
- **Capped winner:** high ROAS + at budget cap (spend≈budget) + on-target 14d+ → +10–15% budget.
- **Over-funded saturator:** IS ≥90% + CPA/cost rising → STOP adding budget; reallocate AWAY (diminishing returns).
- **Underspender:** spend < ~90% of budget sustained → run the D1 underspend logic (target vs demand vs bids
  vs QS vs disapprovals vs learning vs billing). Don't just "raise budget" — find which cause.
- **Shared-budget trap:** multiple campaigns on one shared budget fragment delivery; the strongest may starve.

---

## D3 — Geo / location waste ("places they never buy")

**Pull:** `geographic_view` with `geographic_view.location_type` (2 = AREA_OF_INTEREST, 3 = LOCATION_OF_PRESENCE),
`segments.geo_target_region` / `geo_target_city`, metrics, scoped to active set + window. Resolve IDs via
`geo_target_constant` (`geo_target_constant.canonical_name`). Also pull
`campaign.geo_target_type_setting.positive_geo_target_type` and location `campaign_criterion` (negatives).

| Diagnosis | Threshold | Fix |
|-----------|-----------|-----|
| **Geo spends, never buys** | a region with cost > ~2–3× target CPA AND 0 conversions | add a **location exclusion** for that region |
| **Weak geo ROAS** | region ROAS < ~50% of blended, sustained, with material cost | location **bid −%** (supported on Search AND PMax) or exclude |
| **"Presence or Interest" leak** | `positive_geo_target_type` = `PRESENCE_OR_INTEREST` (enum **5**) or `SEARCH_INTEREST` (enum **6**) — serves people merely *interested* in the area — OR meaningful `location_type=2` (AREA_OF_INTEREST) spend. **NOTE: enum 7 = PRESENCE = the correct setting, NOT a leak.** | switch targeting to **PRESENCE** ("people in your targeted locations") |
| **Serving where you don't ship** | spend in regions/countries outside the fulfillment area | exclude those locations |

**Confidence:** roll small states up; a state with 30 clicks / 0 conv is Investigate, not Cut. Need ≥100 impr
or ≥10 clicks. PMax geo control is limited to exclusions (no per-geo bid). Smart Bidding already shades bids
by geo — only act on a *persistent, material* gap.

---

## D4 — Ad schedule / dayparting ("hours that convert terribly")

**Pull:** active campaigns segmented by `segments.day_of_week` (MONDAY=2 … SUNDAY=8) and `segments.hour` (0–23)
+ metrics, over the window. Existing schedule: `campaign_criterion` `ad_schedule`. (This pull is large —
hour×day×campaign — let it overflow to a file and aggregate app-side; sum ROAS per hour and per day.)

| Diagnosis | Threshold | Fix |
|-----------|-----------|-----|
| **Bad daypart** | an hour/day with material cost AND ROAS < ~40–50% of blended (or CPA ≫ target), sustained | ad-schedule **bid −%** on the weak window (supported on **both Search and PMax** via the campaign ad-schedule criterion's `bid_modifier`), or tighten/pause that window |
| **No schedule despite a clear pattern** | ads run 24/7 flat while specific hours/days are consistently weak | add an ad schedule covering the strong windows |

**Caveats (research-confirmed):** PMax and Smart Bidding do NOT support hour/day bid adjustments — only Search
(manual or with bid modifiers) does; Smart Bidding *should* already adjust by time-of-day, so only act when the
weak window is **persistent + material** across ≥1 conversion cycle, not a one-month blip. Frame as "investigate
+ consider schedule", not an automatic cut, unless the loss is large and stable.

---

## D5 — Search-term waste: irrelevant · wrong-brand · spam

**Pull BOTH sources** (gaql-notes.md): `search_term_view` (Search/Branded — has `cost_micros`) +
`campaign_search_term_insight` per PMax campaign (`category_label`, conv/value — **NO cost_micros**, so PMax
"waste" = high-click/0-conv categories, prioritized by clicks not $).

| Diagnosis | Threshold | Fix (match type) |
|-----------|-----------|-----|
| **Irrelevant, spends, 0 conv** | term cost > **2–3× target CPA** (ecom) / 4–5× (B2B) AND 0 conv, with ≥10 clicks or ≥100 impr | **phrase** negative (default); exact for a single high-volume query; broad for a whole unwanted concept |
| **Wrong-brand leakage** | query contains a competitor / a brand you DON'T sell | phrase negative on non-conquest campaigns. **NEVER** own brand. **Keep** resold product brands you sell — word-boundary match, not substring |
| **Spam buckets** | matches a junk taxonomy (below) | themed **shared** negative list (account-level) |
| **Broad-match bleed** | broad keyword pulling irrelevant terms | add negatives or tighten to phrase/exact; broad ONLY with Smart Bidding |
| **PMax irrelevant category** | `category_label` with clicks but 0 conv, clearly off-topic | PMax campaign-level negative (limit 10k since Mar 2025; shared lists since Aug 2025) — note: only blocks Search+Shopping inventory, not Display/YT/Gmail |

**Spam taxonomy (reusable account-level negatives):** job-seeker (jobs/careers/salary/hiring/resume) ·
free/cheap (free/cheap/discount/coupon — only if your offer has no free tier) · DIY/how-to (how to/tutorial/
diy/what is) · academic (research paper/study/thesis) · review/compare (reviews/vs/alternatives — keep these
for conquest campaigns) · geo-spam (out-of-area, "near me" for non-local) · B2B↔B2C mismatch — apply ONLY if
the store is one-sided per `business.model` (a wholesale-only store blocks personal/student; a retail-only
store blocks wholesale/bulk; a store selling to BOTH blocks neither) · universal junk
(torrent/cracked/free download/porn/scam).

**Discipline:** Google defaults new negatives to EXACT in the UI (verify before saving — phrase is usually
right). Test 1 week; if conversions drop, the term was carrying legit traffic → revert/demote. Before negating,
run Optmyzr's pre-pause check: match type? assisted conversions? intent in the full query? landing-page fit?
**Hidden-terms reality:** 25–35% of search spend hides below privacy thresholds; coverage = Σ search_term_view
cost ÷ Σ campaign cost — report it so the operator knows how much is unseen.

---

## D6 — Structure & setup hygiene

- **Fragmentation below the learning floor:** campaigns/asset-groups each <15–30 conv/period → consolidate
  (more volume → better learning → then optimize).
- **Brand/non-brand mixed:** >50% brand keywords in a "non-brand" campaign → split brand out (own campaign) so
  cheap brand conversions don't flatter non-brand ROAS.
- **Conversion-goal scope:** `conversion_goal_campaign_config.goal_config_level` — CUSTOMER (account-default,
  cross-campaign learning) vs CAMPAIGN (isolated). Account-level is fine UNLESS a rogue/junk action sits primary
  at account level (then every CUSTOMER-level campaign bids toward it) → move the affected campaign to CAMPAIGN
  scope to quarantine. (Honor the `conversion-goal-campaign-scope` guardrail.)
- **PMax hygiene:** Final URL Expansion ON without URL exclusions / page feed → traffic leaks to About/blog/FAQ;
  auto-created text assets (`asset_automation_settings`: TEXT_ASSET_AUTOMATION / FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION
  = OPTED_IN) drifting off-brand; single asset group where volume supports intent-segmentation. Verify before
  flagging — a deliberate campaign-level split (1 AG each) is fine.

---

## D7 — Quality Score (hidden CPC tax)

**Pull:** `keyword_view` → `ad_group_criterion.quality_info.quality_score` + `.creative_quality_score`
(ad relevance) + `.post_click_quality_score` (landing page) + `.search_predicted_ctr` (expected CTR). Enums:
BELOW_AVERAGE / AVERAGE / ABOVE_AVERAGE. Weight QS by impressions (only count impression>0 keywords).

Low QS → higher CPC for the same position = money burned silently. **Diagnose by the weak component:**
expected-CTR below avg → rewrite headlines / tighten ad-group theme; ad-relevance below avg → put the keyword
in the headline; landing-page below avg → fix LP speed/mobile/relevance. Don't "raise bids" to mask low QS —
that's the expensive non-fix. Threshold: avg QS < 6 (or >25% of spend on QS ≤4 keywords) = act.

---

## D8 — PMax channel & placement distribution (where the money actually goes)

The single most common wrong assumption is "Display burns my PMax budget." **Don't assume — pull the split and
name the real surface.** In one live test, classic Display (CONTENT) was ~$0; the small non-Search burn was
in **Maps + Discover** — you'd have wasted effort "optimizing Display" that wasn't the problem.

**Pull:** `campaign` (PMax) + `segments.ad_network_type` (+ `segments.ad_using_product_data`,
`segments.ad_using_video`) + metrics, over the window. **Decode the enum:** `2`=Search · `3`=Search Partners ·
`4`=Display(CONTENT) · `8`=YouTube · `11`=Gmail · `12`=Discover · `13`=Maps · `7`=MIXED. **Caveat:** PMax
channel split is only populated for dates **≥ 2026-06-01 (API v23+)** — earlier dates return MIXED (7), so a
window before that can't be diagnosed by channel. For *where* ads showed (site/app/video), use
`performance_max_placement_view` (`placement`, `placement_type` WEBSITE/MOBILE_APPLICATION/YOUTUBE_VIDEO,
`target_url`) — but it returns **impressions ONLY** (no cost/conv per placement), so flag high-impression junk
apps for exclusion, not by $.

**Diagnose:** cost + conv + ROAS per channel. Healthy = most spend on **Search/Shopping (type 2)**, especially
feed-driven (`ad_using_product_data=true`). Burn = a non-Search channel with clicks/cost and ~0 conv. Name it
(YouTube vs Discover vs Maps vs Gmail vs Display) — they have different levers.

**Levers (precise — this is the value; most "fixes" people try DON'T work on PMax):**
- ✅ **Account-level placement exclusion lists** (sites / YouTube channels-videos / app package names) — works,
  but account-wide only (can't scope to one PMax campaign). Tools → Brand Safety → Placement Exclusions.
- ✅ **Mobile-app-category + content-suitability exclusions** (Content Suitability Center) — blunt, blocks
  whole categories (Games/Entertainment) and inventory tiers.
- ✅ **Campaign-level negatives** — but **Search/Shopping inventory ONLY**; zero effect on Display/YouTube/
  Gmail/Discover/Maps. (Lists can't attach to PMax; individual campaign negatives can, 10k limit.)
- ⚠️ **Feed-only PMax** (drop ALL creative assets → ~90% of impressions shift to Shopping/Search) — effective
  but UNSUPPORTED workaround; Google may auto-gen assets. True channel isolation = a Standard Shopping campaign.
- 🔬 **Search-Partner / Display opt-out** — alpha only (≈2026), not GA, no API; don't build on it.
- ❌ **Does NOT work:** per-channel bid adjustment; opting out of YouTube/Discover/Gmail/Maps; per-campaign
  placement exclusions; negative-keyword lists on PMax.

**Discipline:** only act if the non-Search burn is MATERIAL. If it's small (e.g. $30–50/mo), say so and DON'T
spend effort — the levers are blunt and account-wide, and Maps/Discover have almost no direct lever. Finding
"your channel mix is healthy, don't touch it" is itself a valuable, money-saving conclusion.

## D9 — Ad copy, assets & extensions (analyze + test, don't guess)

**Pull:** PMax → `asset_group_asset.{field_type, performance_label}` + `asset.text_asset.text`. RSA →
`ad_group_ad_asset_view.{field_type, performance_label}` + metrics, and `ad_group_ad.ad.responsive_search_ad.
{headlines,descriptions}` + `ad_group_ad.ad_strength`. Extensions → `campaign_asset.field_type`
(13 SITELINK · 11 CALLOUT · 12 STRUCTURED_SNIPPET · 10 PROMOTION · 17 PRICE · 18 BUSINESS_NAME) and the
asset-group equivalents. `performance_label` enum = BEST / GOOD / LOW / LEARNING / PENDING.
> **Per-asset METRICS work — pull them (this is the "what converts vs what burns" report).**
> `asset_group_asset` accepts `metrics.{clicks,cost_micros,conversions,conversions_value}` alongside
> `field_type` + `asset.text_asset.text` (verified live; filter one `field_type` at a time, order by cost).
> The `performance_label` field is rejected on some/older MCP versions (UNRECOGNIZED_FIELD) — if so, rank by
> **cost + clicks + CTR** instead of the label. Don't claim a label you couldn't pull.
> **PMax asset-conversion CAVEAT:** PMax UNDER-ATTRIBUTES conversions to individual assets — most of a
> campaign's conversions won't tie to any one headline (live example: a campaign had 249 conv but ~6 attributed across 33
> headlines). So asset-level **cost is reliable; asset-level conv is sparse** — NEVER kill an asset on
> 0-attributed-conv alone. Read the *pattern* (which themes earn clicks/CTR + the few attributed conv) and
> validate with **Asset Experiments**, not by pausing single assets.
> **Final URL Expansion check:** the UI "Expanded final URL assets" report shows where FUE actually sent each
> asset's traffic + per-URL cost/conv. A classic leak: most assets expand to the **homepage** (cost, ~0 conv)
> while the few that expand to specific product/collection pages convert (observed live). Fix: set the asset
> group's Final URL to a specific collection (not the homepage), and/or add URL exclusions / a page feed so FUE
> favors product pages. (Per-asset expanded-URL may be UI-only on read-only MCPs → verify-in-UI.)

| Diagnosis | Threshold | Fix |
|-----------|-----------|-----|
| **Missing/thin extensions** | <4 sitelinks, no callouts (target **8–10**), no structured snippets (4+ values) | add them — free SERP real estate + CTR lift; sitelinks 6+ with descriptions documented +3.5% conv |
| **Duplicate / low-variety headlines** | repeated headline text; <11 distinct in a PMax AG | dedupe; aim **5 brand + 5 benefit + 5 offer** = 15 distinct (repetition kills Ad Strength) |
| **Below PMax asset minimums** | <3 headlines / <1 long headline / <2 descriptions / <1 image per ratio / <1 logo / <1 video | fill to recommended (11+ / 2+ / 4+ / 4+ each / 1+ / 1+) |
| **LOW-labeled assets** | `performance_label = LOW`, asset live ≥2–3 weeks | replace — but **1–2 per asset type per week** (swapping more at once destabilizes the AG and makes results unreadable); edit-in-place, don't delete/recreate |
| **POOR ad strength** | ad_group_ad.ad_strength POOR, ENABLED + impressions (GUARD-4) | add headlines/assets toward Good/Excellent (+15% conv avg Poor→Excellent) |
| **Over-pinning** | a single headline pinned to one slot | pin 2–3 variants to the same slot (single pin locks ~67% of that slot's testing) |

**Testing methodology — ONE variable per 14-day window (this is the discipline that separates real optimization
from theater):**
- PMax creative → **Asset Experiments** (control vs treatment sets, 4–6 weeks, AG locked during the test).
- RSA copy → **Ad Variations** (low reset risk). Campaign settings → **Experiments / drafts**.
- Min runtime before judging: RSA 4 weeks or 100+ conv/variant; PMax assets 4–6 weeks; campaign experiments
  2–4 weeks + 30–50 conv/variant.
- **Anti-pattern:** changing all headlines + pausing keywords + adjusting bids + adding extensions in one week,
  then crediting any move to "optimization". Log every change with timestamp + reason; one change per window.

## D10 — PMax campaign SETTINGS & hygiene (the granular layer most audits skip)

The biggest PMax leaks often live in **settings, not metrics** — and several are NOT readable on a read-only /
older MCP, so the audit must **CHECK them via a UI walkthrough (verify-in-UI), never skip them** (GUARD-6).
This layer is the differentiated value: a generic health-check scores metrics and misses that Final URL
Expansion is dumping budget on the privacy-policy page, or text customization is writing "treat yourself" to
wholesale buyers. **The reason an account does or doesn't burn on Display is HERE** — so check the cause, don't
just report the symptom.

| Setting | How to read | What to check / fix |
|---------|-------------|---------------------|
| **Device performance** | `segments.device` (2 Mobile · 3 Tablet · 4 Desktop · **5 Connected TV** · 6 Other) + metrics | flag any device with material cost + ~0 conv (classic: Connected TV, tablet). Lever: PMax device EXCLUSION is limited (Beta/partial) — note what's possible; Search/Standard can bid −% by device. |
| **Content Suitability + placement exclusions** | usually NOT API-readable → **verify-in-UI** (+ account-level exclusion lists via shared sets) | THE reason Display/app inventory does/doesn't burn. Check: Content Suitability Center (digital-content labels, sensitive types, **inventory mode Standard vs Limited**, **mobile-app-category exclusions**) + Tools → Placement Exclusion Lists. **Absent = the Display-burn root cause → set them.** If channel mix looks healthy, ATTRIBUTE it to this and confirm it's in place (don't just say "healthy"). |
| **Final URL Expansion + URL exclusions** | `campaign.url_expansion_opt_out` (often NOT readable here → verify-in-UI) | if FUE is ON without URL exclusions / a page feed, traffic leaks to About/blog/FAQ/policy pages. Pull `performance_max_placement_view.target_url` (where it went) + the UI URL report; add URL exclusions or a page feed for irrelevant pages. |
| **Asset automation / Text customization** | `campaign.asset_automation_settings` (often NOT readable → verify-in-UI); `campaign.brand_guidelines_enabled` IS readable | if auto-created text / text customization is ON, Google AI writes headlines/descriptions from the landing page — it MUST be governed by a **Text/Brand Guideline**. Check it EXISTS and is APPROPRIATE: **term exclusions** (block off-brand/wrong-intent words) + **messaging restrictions** (e.g. "don't imply we're a salon", "no consumer language", "no $ amounts"). Missing/wrong guideline = off-brand AI copy. |
| **Brand guidelines content** | `brand_guidelines_enabled` (bool) readable; the term/messaging lists usually verify-in-UI | confirm the exclusions match the business (wholesale vs retail, brand terms, competitor terms). A strong example: ~20+ term exclusions + messaging restrictions tuned to the audience. |

**Rule:** API-read what you can; for everything else, emit a **UI verify checklist** (per campaign) — a setting
you couldn't read is "verify in UI", never "fine". This is also where you explain WHY a metric looks the way it
does (healthy Display = content-suitability is set, not luck).

## D11 — PMax audience signals & search themes (is the campaign well-fed?)

PMax flies on the seeds you give it. **Pull `asset_group_signal`** scoped to **ENABLED asset groups in the
active set** (`asset_group_signal.search_theme.text` + `asset_group_signal.audience.audience`; the `.type`
enum is rejected on some MCPs — infer: a row with `search_theme.text` = a search theme, a row with
`audience.audience` = an audience signal). **GUARD-4 applies — paused asset groups still return signals; a
multi-AG account (often with paused AGs, see the 1-AG-per-campaign pattern) will mislead you if you don't
scope to ENABLED.**

| Diagnosis | Threshold | Fix |
|-----------|-----------|-----|
| **No audience signal on an active AG** | 0 audience signals | add ≥1 seed: customer-match → website-visitors → high-value list → custom segment (search/competitor). Signals are SEEDS, not hard targeting — PMax expands beyond them. |
| **Thin / no search themes** | <5 (target up to **50**/AG) | add specific, intent-led themes (product/shade/use-case), not generic. Distinct per AG. |
| **Generic theme quality** | vague one-word themes only | prefer specific, multi-word themes over single-word generics, tailored to the account's OWN product/service vocabulary + converting search-term data (a brand+attribute+use-case theme beats a bare category word). The converting data is the benchmark — never an example account. |

## D12 — Conversion lag (can you trust the short-window ROAS?)

This gates EVERY ROAS-based finding: if conversions arrive slowly, recent-window ROAS *understates* and you'd
wrongly judge new campaigns/changes too early. **Pull `segments.conversion_lag_bucket` + metrics** (buckets:
2=<1day · 3=1-2d · 4=2-3d · … · 8=6-7d · 9+ = beyond 7 days). Compute **% same-day** (bucket 2) and **% within
7 days** (buckets 2-8).

- **Low lag** (most same-day; e.g. one account ran ~91% same-day, ~99.9% within 7d) → short-window ROAS is
  trustworthy; safe to evaluate on a 7-day window and act faster.
- **High lag** (>~15-20% of conversions beyond 7 days) → recent ROAS is understated. Do NOT judge new
  campaigns or post-change performance on a 7-day window — use 30-day, wait a full lag-tail, or import offline
  conversions. Flag any "underperforming" finding whose window is shorter than the lag tail as *premature*.

This isn't an action to push — it's the **methodology gate** that tells you which window the rest of the
report can be trusted on. State the lag profile up top.

## D13 — Change-history timeline (cooldown + whipsaw)

**Pull `change_event`** — `change_date_time`, `change_resource_type` (5=CAMPAIGN · 6=CAMPAIGN_BUDGET ·
2=AD · 3=AD_GROUP · 4=AD_GROUP_CRITERION · 7=CAMPAIGN_CRITERION), `user_email`, `campaign.name`. **Hard API
limit: start date can't be older than 30 days** (START_DATE_TOO_OLD — use ≥ today−30, a method constraint not
an absence).

| Diagnosis | Signal | Action |
|-----------|--------|--------|
| **Inside cooldown** | a campaign changed within ~7-14d | do NOT scale/judge it yet (feeds GUARD-3 + the Scaling Ladder). Name the date + what changed. |
| **Whipsawing** | same campaign's budget/target changed 3+ times in the window | over-tinkering destabilizes Smart Bidding and makes cause unreadable → advise HOLDING; one change per cooldown. (example: a campaign's budget changed 3× in 30d.) |
| **Unexpected operator / automated rule** | changes by an unfamiliar `user_email` or automated `client_type` | confirm intent; reconcile with the change log. |

Output a dated timeline (most-recent first) so the operator sees exactly what changed and when — this is also
how you correlate a performance shift with its cause instead of guessing.

## D14 — Product feed & Shopping performance (the ecom FOUNDATION most ad-audits skip)

For an ecommerce account this is often the **biggest controllable lever** — and a "Products" tab the campaign
UI surfaces (Products / Diagnostics / Promotions). Two halves; do both.

**A) Product PERFORMANCE — Google Ads side (available via the Ads MCP, no Merchant access needed).** Pull
`shopping_performance_view`: `segments.product_item_id` + `segments.product_title` + metrics, scoped to active
Shopping/PMax campaigns. Aggregate per product (a SKU appears under several campaigns).
- **0-conv burners** — products with cost > ~2-3× target CPA AND 0 conversions (≥10 clicks for significance):
  the single biggest controllable ecom leak. Direct $ waste. (live example: high-ticket drill colour variants
  ~$312/mo at 0 conv; big multi-pack "Set" collection SKUs; ~$665/mo total in the top slice.)
- **Non-buyable pages getting clicks** — swatch / colour-chart / lookbook "products" that draw clicks but ~0
  buys (live example: a "swatches" collection page = 342 clicks, $36, 0 conv). Exclude from Shopping or fix the
  destination — people are browsing colours, not buying that item.
- **Weak-ROAS products** — below breakeven / the margin tier.
- **Lever (PMax/Shopping):** you can't bid per product, but you CAN exclude items, restructure listing groups,
  or split winners into their own asset group / campaign and starve the losers.

**B) Feed HEALTH — Merchant Center side (check BEFORE excluding a burner).** A product burning at 0 conv is
often **out-of-stock, disapproved, missing GTIN, or has a price/availability mismatch** — the ROOT CAUSE, not
"a bad product". Pull: account diagnostics (active vs disapproved counts), the disapproved list (split real
disapprovals `servability=disapproved` from informational `unaffected` updates), per-product status. **A feed
problem caps ROAS regardless of bidding/copy** — fix the feed first.
- **The key distinction (this is the value):** cross-check each 0-conv burner's Merchant availability —
  **OOS → restock or exclude** (ad spend on unbuyable stock is pure waste); **IN STOCK but 0-conv → it's
  price / consideration / relevance, NOT a feed issue** (a different fix: exclude, or accept it as a high-ticket
  considered item). Don't treat the two the same. (live example: a high-ticket "Complete" SKU ($425) was OOS →
  restock/exclude; an in-stock $385 device was expensive-but-available → a price/intent problem.)
> **Connection note + how to run it:** the Ads `shopping_performance_view` works on the standard Google Ads MCP.
> The Merchant side needs Google Merchant Center + a Merchant connector — and a Meta *catalog* MCP is NOT Google
> Merchant. If a custom Google Merchant MCP exists but isn't loaded as a tool, you can still **run its functions
> directly** via its venv (e.g. `from server import get_account_diagnostics, list_disapproved_products,
> search_products` with the ADC token) — connection ≠ only "loaded MCP tool". **GOTCHAs:** (1) the Ads
> `segments.product_item_id` does NOT map 1:1 to the Merchant Content-API `productId` (`online:lang:country:offerId`)
> — a direct `get_product_status` 404s; **join by product TITLE instead**. (2) Content API v2.1 has no
> server-side title search → client-side scan of the whole catalog (22k+ items at 250/page ≈ 90 pages); wrap
> each page in retry/skip (a transient 500 on one page shouldn't kill the scan).

**Foundational:** for ecom, Merchant Center linked + a healthy feed is the prerequisite to everything else.
Scoring bidding/copy while the feed is broken optimizes the wrong layer. **Discipline:** significance gate
(≥10 clicks) before calling a product wasted; always cross-check Merchant status before excluding — it may be
a fixable OOS/disapproval, not a bad product.

## The Scaling Ladder — grow spend without breaking the ROAS you already have

The hardest real-world problem: a campaign sells at a LOWER tROAS than you want but volume is uneven and won't
scale; raise the target and it stops selling. The fix is a disciplined ladder — **one variable at a time, with
cooldowns**, so every result stays READABLE: you never judge a change faster than the conversion lag, and you
always know which move caused a shift. (Note: budget changes are NOT on Google's official Learning-status
trigger list; support.google.com/google-ads/answer/6263057 lists only new strategy / setting change /
composition change, and Google's own PM has said modest budget changes don't reset learning. The ladder's
justification is demand headroom + measurement discipline, not a feared "budget reset".)

**Prerequisites:** ≥15 conv/30d to run tROAS at all, **≥50 conv/30d before tightening** (and before each
subsequent step). Below that, the campaign learns nothing stable — consolidate / grow volume first, don't set a
target. **Initialize tROAS ~20% BELOW your historical achieved ROAS** (delivered 5.0x → start 4.0x) to give the
algorithm room to find volume before you tighten.

**The two iron rules:**
1. **Budget first, then target — NEVER both in the same week.** Two moving variables = the model re-learns the
   inventory landscape AND the bid constraint at once, and you can't tell which caused a shift. (Practitioner
   consensus, not a single Google article — but mechanically sound.)
2. **Never reverse direction inside the cooldown.** Up then down within the window resets the clock and confuses
   the model.

**Budget steps:** ≤**+20%** per step, hold **7–14 days** (7 high-volume, 14 low). The clearest green light:
status `LIMITED_BY_BUDGET` AND ROAS ≥ target → scale +20%, repeat while the signal holds. If ROAS dips after a
raise but recovers within ~2 weeks → hold and continue; if it never recovers in ~3 weeks → fall back to the last
stable budget.

**tROAS steps:** tighten **+10–15%** / loosen **−15–20%** per step, wait **≥14 days** (1–2 conversion cycles;
longer if conversion lag >5 days). Keep steps small: a target edit IS a bid-strategy setting change (the one
category Google's Learning-trigger list does cover), and a big jump makes the next 2 weeks of results
unreadable. The 10–20% step size itself is practitioner consensus, no official threshold exists (Google's
Search guidance even says targets may be changed freely).
Tighten only after 14+ days at/above the current target; loosen only when ROAS is >20% above target for 14+ days
AND budget scaling is already maxed.

**Low-volume / volatile:** consolidate adjacent low-volume campaigns into a portfolio to pool data; judge on
**14-day rolling windows, not daily noise**; account for conversion lag (use 30-day or import offline conv before
judging); wait for 50 conv/30d before each step.

**Don't break what works — freeze everything else during the 7–14d learning window:** no new ad groups, no
bulk keyword pauses, no sweeping copy changes, no targeting/structure edits. Use **seasonality adjustments** for
short events (≤14 days — the sanctioned way to pre-inform Smart Bidding, and they expire automatically) instead of a temporary target
change; use **data exclusions** to scrub outages/tracking-gaps/one-off spikes so the model doesn't learn a
distorted baseline.

**The ladder (encode this):**
```
≥50 conv/30d?  NO → Max Conversions (no target), grow volume, re-check in 4 weeks.
               YES ↓
LIMITED_BY_BUDGET and ROAS ≥ target?
   YES → +20% budget, hold 7d, loop. If ROAS stays >30% above target 14d+ after budget maxed → loosen tROAS −15–20%, hold 14d.
   NO  ↓
ROAS ≥ target and NOT budget-limited?      → hold; if it persists 14d → loosen tROAS −15–20% to expand, hold 14d.
ROAS within ±20% of target?                 → hold. Healthy. Do not touch.
ROAS < target by >20% for >14d?             → DON'T cut budget first: check conv-lag/data/seasonality;
                                              if real → tighten tROAS +10–15%, hold 14d; >3 steps still failing = structural, not bidding.
After ANY change: freeze other variables 14d · never reverse inside the window · judge on 14-day rolling averages.
```

## Estimating $/month (show the formula, never fabricate)
- **Daypart / geo waste** = cost_in_bad_segment × (1 − segment_ROAS / blended_ROAS), i.e. the value shortfall vs
  if that spend performed at the account average. For a 0-conv segment, the at-risk spend is the full cost.
- **Search-term waste** = Σ cost of flagged 0-conv terms (direct).
- **Misallocation gain** = reallocated_spend × (high_ROAS − low_ROAS) (extra conversion value per $ moved).
- **tROAS-too-high** = (budget − current_spend) × expected_ROAS_at_lower_target (recoverable volume), labelled
  an estimate with the assumed achievable ROAS shown.
- Always state the window (30d) and that figures are directional, not guaranteed.

---

## GAQL field quick-reference (validated)
- **Bid/target:** `campaign.bidding_strategy_type`, `campaign.bidding_strategy_system_status` (LIMITED…),
  `campaign.maximize_conversion_value.target_roas`, `campaign.maximize_conversions.target_cpa_micros`,
  `campaign.manual_cpc.enhanced_cpc_enabled`, portfolio via `bidding_strategy.target_roas.target_roas`.
- **IS (Search/Manual only for budget/rank):** `metrics.search_impression_share`,
  `metrics.search_budget_lost_impression_share` (campaign-level only; NOT with MaxConv/MaxConvValue; NOT PMax),
  `metrics.search_rank_lost_impression_share`. Values are fractions 0–0.9 (capped 0.9001); IS 0.1–1.
- **Geo:** `geographic_view.location_type` (2=interest,3=presence), `segments.geo_target_region/geo_target_city`,
  `geo_target_constant.canonical_name`, `campaign.geo_target_type_setting.positive_geo_target_type`.
- **Schedule:** `segments.day_of_week` (Mon=2…Sun=8), `segments.hour` (0–23), `campaign_criterion.ad_schedule.*`.
- **Search terms:** `search_term_view.search_term` + metrics; `campaign_search_term_insight.category_label`
  (+conv/value, no cost; one `campaign_id` per query).
- **Goal scope:** `conversion_goal_campaign_config.goal_config_level` (CUSTOMER/CAMPAIGN), `campaign_conversion_goal.*`.
- **QS:** `ad_group_criterion.quality_info.{quality_score,creative_quality_score,post_click_quality_score,search_predicted_ctr}`.
- **PMax automation:** `campaign.asset_automation_settings` (TEXT_ASSET_AUTOMATION / FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION, OPTED_IN/OUT).
- **PMax channel:** `segments.ad_network_type` (2 Search · 3 Search Partners · 4 Display · 8 YouTube · 11 Gmail
  · 12 Discover · 13 Maps · 7 Mixed); `segments.ad_using_product_data`, `segments.ad_using_video`. Channel
  split valid only for dates ≥ 2026-06-01 (else MIXED). **Placement (impressions only):**
  `performance_max_placement_view.{placement,placement_type,target_url,display_name}`.
- **Assets/copy:** `asset_group_asset.field_type` (2 HEADLINE · 3 DESCRIPTION · 11 CALLOUT · 12 STRUCTURED_SNIPPET
  · 13 SITELINK · 7 YOUTUBE_VIDEO · 5 MARKETING_IMAGE …) + `asset.text_asset.text`; extensions at campaign level
  via `campaign_asset`; RSA via `ad_group_ad.ad.responsive_search_ad.{headlines,descriptions}`.
