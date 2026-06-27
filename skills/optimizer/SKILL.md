---
name: google-ads-optimizer
description: >
  Acts on a running account to improve performance: campaign tiering, search-term mining into negatives,
  budget reallocation, target ROAS/CPA adjustments, bid-strategy changes, asset refresh, and consolidation.
  Diagnoses root cause (not just symptoms) and produces a dated action plan. Proposes changes — applies via
  pusher with approval. Generalized fork of a production optimizer; reads account-context.yaml, respects
  guardrails and margin tiers. Use when the user says "optimize", "improve ROAS", "lower CPA", "add
  negatives", "raise tROAS", "reallocate budget", "fix underperformers", "weekly ads review".
---

# Google Ads — Optimizer (act)

Find what's dragging the account and fix it — with data backing and root-cause reasoning, not symptom
swatting. The optimizer **proposes** changes; it applies them only through `pusher` (approval gate). For a
scored health check use `audit`; this skill is about performance and money.

## Operating rules
- Every recommendation has data backing (specific numbers, not vague advice).
- Read everything from `account-context.yaml` (margin_tiers, brand_terms, guardrails, AOV). **If the context
  is missing, run `setup` first — never optimize a live account without it.**
- **Read the context `connections` block first.** If store/GA4 is `missing`, do the in-platform analysis and
  label every true-ROAS / store-revenue conclusion **UNVERIFIED — connect store/GA4**; never fabricate a
  store-revenue figure to compute "true ROAS". Prefer guiding the user to connect over guessing.
- **3-source attribution** (see `${CLAUDE_PLUGIN_ROOT}/references/optimization-playbook.md`): store revenue = ground truth;
  Google Ads in-platform = for Smart Bidding; GA4 = channel mix. A 20-35% Ads-vs-GA4 gap is normal.
- Honor guardrails: change-event cooldown, ignore paused, margin-tier ROAS. Don't flag a house-brand line
  for low ROAS above its tier `min_roas`.

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — running `tiering.py` and `search_term_miner.py` (scripts return their own output).
- **Routine (`sonnet`)** — STEP 1 performance pull + store/GA4 fetch; STEP 3 dual-source search-term pull (per-PMax `campaign_search_term_insight` loop). Dispatch as `general-purpose` sub-agents; **return raw, don't conclude**.
- **Judge (main session)** — tier verdicts, what to block vs keep (esp. never-block-brand), STEP 5 profitability call, STEP 6 root-cause, STEP 7 dated action plan. The numbers come cheap; the decisions stay here.

## STEP 1 — Collect performance
**Scope to the active set first** (ENABLED + impressions in the window) — never tier or "optimize" a
campaign that hasn't served in the period; entity `status=ENABLED` can include long-dead campaigns' assets
(see ${CLAUDE_PLUGIN_ROOT}/skills/audit/references/gaql-notes.md). Then pull campaign performance, search terms (≤30d or explicit dates),
and asset-group performance via the MCP; pull store revenue + GA4 channel mix via the data-source/GA4
fallback chain. Note what's unavailable.

## STEP 2 — Tier campaigns
Classify Gold / Silver / Bronze / Dead by ROAS **relative to the margin-tier target**, plus conversion
volume per period. Output a ranked verdict table (Scale / Keep / Reduce / Pause / Kill) with the numbers.
Runnable: `python ${CLAUDE_PLUGIN_ROOT}/skills/optimizer/scripts/tiering.py campaigns.json [--target-roas T]` (margin-tier aware;
flags learning risk + pause-candidate savings).

## STEP 3 — Mine search terms → negatives (BOTH sources)
Pull from **both**: `search_term_view` (Search/Branded) AND `campaign_search_term_insight` looped **per
active PMax/Demand-Gen campaign** (requires a single `campaign_id` filter — see gaql-notes.md; it returns
categories + conv/value, not per-term cost). `search_term_view` does NOT contain PMax terms, so PMax-heavy
accounts need the insight or you'll miss most of the spend. Find top spend, top revenue, wasted (Search:
>$10 spend & 0 conv; PMax: irrelevant categories with clicks but no conversions). Propose Exact/Phrase
negatives in themed lists; respect the "what NOT to block" rules (store / coupon / cheap-brand) in the
playbook; **never block brand terms** (brand intent, even at 0 conv). Catch cross-brand leakage via
`brand_terms`.
Runnable: `python ${CLAUDE_PLUGIN_ROOT}/skills/optimizer/scripts/search_term_miner.py terms.json` → wasted spend + categorized,
ready-to-copy wrapped negatives, with protected terms held back for review.

## STEP 4 — Asset groups / creative
Flag asset groups with ROAS below the tier target and meaningful spend, POOR ad strength (ENABLED + has
impressions — GUARD-4), and URL overlap. Recommend creative refresh via `assets`.

## STEP 5 — Cross-reference store + GA4 (true profitability)
True ROAS = store revenue (by product/vendor) ÷ Google Ads spend. If a line's TOTAL store revenue (all
channels) is below its Ads spend, it's losing money regardless of in-platform ROAS. Surface channel mix
(how much is organic/direct/email) so pausing decisions account for non-paid revenue.

## STEP 5.5 — Run the seven money-leak diagnostics (the core engine)
Work through D1-D14 in `${CLAUDE_PLUGIN_ROOT}/references/diagnostic-playbook.md` against the active set: D1 bid/
target health (decode `bidding_strategy_system_status` first — budget-capped vs tROAS-too-high vs starved vs
learning; breakeven ROAS = 1/margin), D2 budget pacing & allocation (misallocation: shift $ low-ROAS→high-ROAS),
D3 geo waste, D4 dayparting, D5 search-term/spam/wrong-brand, D6 structure, D7 Quality Score, **D8 PMax
channel/placement distribution** (don't assume "Display burns it" — pull `segments.ad_network_type`, name the
real surface; most levers DON'T work on PMax), **D9 ad copy/assets/extensions** (missing sitelinks/callouts,
duplicate headlines, LOW assets). Each becomes a prescription with a real $ impact, a step size, and a cooldown
gate. **Caveat baked in:** budget-lost-IS is blind on Smart Bidding/PMax — diagnose budget constraint via
spend-vs-budget + system_status, not budget-lost-IS. **For any tROAS/budget scale move, follow the Scaling
Ladder** (budget first then target, never both same week, ≤+20% budget / 10–20% target steps, 14-day cooldowns,
never reverse inside the window).

## STEP 6 — Diagnose root cause (System Thinking)
Don't stop at symptoms. For each problem ask "why" until you reach the cause (e.g. low ROAS → irrelevant
search terms → missing negatives → no weekly review process). Check interactions: campaigns competing for
the same queries, cross-brand budget leakage, over-reliance on paid vs organic. Project the cost of
inaction vs the savings from fixing.

## STEP 7 — Action plan
Produce a dated plan in three buckets, each item with: what to do · exact UI/Editor steps · why (data) ·
status checkbox.
- **Today**: pause Dead campaigns, cut budget on Bronze, add negative lists, fund under-invested branded.
- **Tomorrow**: review yesterday; raise tROAS **≤0.2-0.3x** (only if ≥15 conv/week, else consolidate first);
  scale Gold (+budget gradually); plan consolidations.
- **2-week roadmap**: dated timeline, each action typed (urgent/optimize/plan).
Respect the tROAS step-up discipline and change-event cooldown throughout.

## STEP 8 — Emit the change-set (the pusher hand-off)
Serialize the action plan into a **`change-set.json`** (contract: `${CLAUDE_PLUGIN_ROOT}/references/change-set.md`;
template: `${CLAUDE_PLUGIN_ROOT}/templates/change-set.json`) — a typed list of edits to the LIVE account
(`add_negatives`, `exclude_geo`, `exclude_products`, `adjust_budget`, `adjust_target_roas`, `pause`,
`add_extensions`, `add_audience_signal`, `exclude_placements`). This is distinct from a builder's
`campaign-spec.json` (which creates a NEW campaign).
- Every action carries a `reason` (the $ leak / numbers), its `diagnostic` D-code, `est_impact_per_mo`, and a
  `push_path`. Express a budget **reallocation** as a pair (a `down`/`pause` on the source + an `adjust_budget`
  `up` on the receiver) so each leg is gated on its own.
- **Encode the discipline in the data, don't rely on prose:** mark `target.within_cooldown: true` for any
  campaign with a recent `change_event` (D13) or under the `change-event-cooldown` guardrail, set
  `target.last_change_direction`, and pass `conv_per_week` on a tROAS raise. The pusher's validator BLOCKS a
  scale move on a within-cooldown target — so a campaign that "shouldn't scale yet" must NOT carry a do-now
  scale action (defer it to the prose roadmap, or omit it). PMax scales DOWN by **pausing** a low-ROAS asset
  group, never a budget cut.
- The optimizer **proposes** the change-set; it never writes. Hand it to `pusher` (or `/google-ads-push`),
  which validates (`validate_changeset.py`) and renders operator actions (`changeset_to_actions.py`) behind
  the approval gate.

## Applying changes
Account mutations go through `pusher` (approval gate + spend cap). The optimizer prepares the change-set
(STEP 8); it does not write to the account directly.

## To build / refine later
- [x] Runnable analyzers: `scripts/tiering.py` + `scripts/search_term_miner.py`. Done.
- [x] Emit changes as a structured change-set the pusher can consume (STEP 8 → `change-set.json`;
  validated/rendered by pusher's `validate_changeset.py` + `changeset_to_actions.py`). Done.
