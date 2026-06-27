---
name: google-ads-plan
description: >
  Plans a Google Ads launch or expansion: how to split budget, which campaign types to run (Search,
  Branded Search, Performance Max, Demand Gen) and in what order, expected conversions/CPA/ROAS given
  budget and AOV, and a phased ramp roadmap. Reads context + audit + measurement; forecasts from real
  account data when available, benchmarks when not. Use when the user says "plan", "budget", "what
  campaigns should I run", "how should I launch Google Ads", "media plan", "campaign mix", "forecast".
---

# Google Ads — Plan

Turn a budget + business context into a concrete plan and an honest forecast. Read everything from the
context and the audit/measurement outputs — no hardcoding, no guessing where data exists.

## STEP 0 — Load context + GATE
1. Read `account-context.yaml` (budget, AOV, margin_tiers, brand_terms, vertical, guardrails) and the
   latest `audit` + `measurement` outputs from the working directory.
2. **Measurement gate**: if `measurement` = FAIL, STOP — do not plan spend on broken tracking. Tell the
   user to fix tracking first. WARN is allowed but carried into the plan as a risk note.
3. Confirm `campaign_defaults.daily_budget` (or ask). Output is written to the working directory.

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — the `forecaster.py` run; reading existing campaign budgets.
- **Routine (`sonnet`)** — STEP 1 mode-detection pull (existing campaigns + spend), STEP 4 deriving CPC/CVR from account data. Dispatch as `general-purpose` sub-agents; **return raw, don't decide the mode**.
- **Judge (main session)** — STEP 0 measurement gate, the campaign mix + sequencing, budget split, forecast interpretation (band not promise), ramp roadmap, risks. The data is cheap; the plan is judgment.

## STEP 1 — Detect mode: LAUNCH vs EXPANSION
Read existing ENABLED campaigns + their spend/performance. The plan differs sharply:
- **LAUNCH** (no/low history) — start simple, lean on benchmarks, conservative ranges, one or two
  campaign types, no target ROAS during learning.
- **EXPANSION** (established account) — read actual scale and find gaps. **Read the real budget scale,
  don't assume small** (e.g. a mature account may run $1k+/day across many campaigns). Recommend
  additions/reallocations against what already exists, not a from-scratch structure.
State which mode you detected and why.

## STEP 2 — Campaign mix (which types, in what order)
Use the vertical priority in `${CLAUDE_PLUGIN_ROOT}/references/vertical-defaults.md` + what's missing in the account:
- ecommerce: PMax/Shopping → Branded Search → Search → Demand Gen.
- leadgen / saas / b2b: (Branded) Search → Search → Demand Gen.
Justify each: goal it serves (acquisition / defense / scale), and why now. Coordinate **Branded Search +
PMax brand exclusion** so they don't cannibalize (honor `pmax-brand-exclusion` guardrail).
- **Non-brand Search is a HARVEST/CONTROL layer on PMax discovery, not a from-scratch keyword bet.** Recommend
  it once PMax has *discovered* converting non-brand queries worth controlling (high volume/value/margin, or
  needing distinct messaging — check the dual-source search-term data: `search_term_view` +
  `campaign_search_term_insight` per PMax). If there's nothing proven to harvest yet, hold Search and let PMax
  keep discovering. When you do recommend it, hand `builder-search` the harvest list, not a category list.

## STEP 3 — Budget split + learning minimums
- Split the daily budget across chosen types by goal and expected efficiency.
- **Learning minimum**: each campaign / asset group / ad group needs ~15-30 conversions/month to exit
  learning. With a limited budget, run FEWER campaigns well rather than starving many. Compute the max
  number of campaigns/AGs the budget can actually feed and say so.
- Apply `margin_tiers`: high-margin lines can run at lower ROAS; reflect that in the split.

## STEP 4 — Forecast (derive, don't guess) — see `${CLAUDE_PLUGIN_ROOT}/references/forecasting-and-benchmarks.md`
- **EXPANSION**: derive CPC and CVR from the account's own recent data; project
  clicks = budget / CPC, conversions = clicks × CVR, revenue = conversions × AOV, ROAS = revenue / spend,
  CPA = spend / conversions. Present as a band, not a point estimate.
- **LAUNCH**: use vertical benchmark bands; present WIDE ranges and label them estimates with stated
  assumptions. Never present a benchmark forecast as a promise.
- Always show the inputs (CPC, CVR, AOV, budget) **with their source**. If AOV is not verified from store
  data (context `connections.store = missing`), say so and label the revenue/ROAS line **UNVERIFIED —
  connect store for a real AOV**; use a clearly-flagged provisional only with the user's OK. Never present a
  guessed AOV as fact — it silently distorts every revenue/ROAS number downstream.
- Runnable helper: `python ${CLAUDE_PLUGIN_ROOT}/skills/plan/scripts/forecaster.py --budget B --cpc C --cvr R --aov A
  [--target-roas T]` → prints conv/revenue/ROAS/CPA bands + learning capacity (how many campaigns the
  budget can feed).

## STEP 5 — Ramp roadmap
Phase the bidding per `campaign_defaults.bidding_ramp` (e.g. Maximize Conversion Value with no target
during learning → Target ROAS once volume matures). Respect ramp discipline: don't set a target before
enough conversions; raise tROAS ≤0.3x per step with a wait between steps; honor `change-event-cooldown`.

## STEP 6 — Success criteria + risks
- Define what "working" means per campaign (target CPA/ROAS by phase, learning-exit timeline).
- List risks (measurement WARNs, thin budget vs learning minimum, seasonality).

## Output — `GOOGLE-ADS-PLAN.md` (to the working dir)
- Mode (launch/expansion) + rationale.
- Campaign mix + sequencing.
- Budget split table + max-campaigns-the-budget-can-feed.
- Forecast band with inputs shown.
- Ramp roadmap + success criteria + risks.
- **Hand off**: for each chosen campaign type, point to the matching `builder-*` skill.

## To build / refine later
- [x] Runnable forecaster (`scripts/forecaster.py`). Done.
