# references/ — shared, vertical-agnostic knowledge base

Reference material used across skills. Unlike `account-context.yaml` (business-specific), everything here
is generic and reusable for any account.

Current files:
- `diagnostic-playbook.md` — **the money-leak engine** (the high-value brain): D1-D14 diagnostics
  (bid/target health · budget pacing · geo · dayparting · search-term/spam · structure · Quality Score · PMax
  channel/placement · ad copy/assets/extensions · settings hygiene · audience signals/search themes ·
  conversion-lag gate · change-history timeline · product feed & Shopping) + the **Scaling Ladder** (grow
  spend without breaking ROAS), each signal→GAQL→threshold→diagnosis→fix→discipline→$impact. Decodes
  `bidding_strategy_system_status` + the `ad_network_type` channel enum; documents the budget-lost-IS-blind-on-
  Smart-Bidding caveat and which PMax channel levers actually work. audit/optimizer/routine all run this.
- `per-campaign-report-template.md` — **the audit's render blueprint**: the per-campaign VISUAL-EXPLAINER
  structure (account panel → chart block per campaign → action plan), every item rendered **data → verdict
  (GOOD/WATCH/FIX/VERIFY) → action**, each quantitative metric as a chart (gauge/ring/donut/bars/heatmap),
  with a per-campaign scorecard. Drives `skills/audit/scripts/money_leak_report.py`.
- `model-tier-dispatch.md` — **how the suite spends compute**: tier work by cognitive load (Scout/Routine/
  Judge → haiku/sonnet/opus), "collect cheap, decide expensive", the delegation idiom + MCP-access caveat.
  Every skill carries a per-STEP tier table that points here.
- `pmax-split-strategies.md` — the split menu + recommendation logic (builder-pmax's "soul").
- `pmax-best-practices.md` — asset groups, listing groups, audience signals, copy angle mix.
- `optimization-playbook.md` — tiering, search-term mining (both sources, never-block-brand), budget pacing,
  tROAS step-up discipline, daily-budget mechanics.
- `google-ads-formatting.md` — Google-accurate char counting (NFC, CJK=2, hidden chars), ready-to-copy
  match-type wrapping, Final-URL-per-AG rules, 2026 asset limits.
- `conversion-tracking-logic.md` — holistic conversion judgment (primary/secondary, double-count by source).
- `aov-and-sales-sourcing.md` — derive AOV from Online-Store sales, not the Google Ads shortcut.
- `forecasting-and-benchmarks.md` — CPC/CVR/ROAS bands + forecast math (used by plan + experiments).
- `vertical-defaults.md` — per-vertical campaign-type priority + smart defaults.
- `campaign-spec.md` — the builder→pusher JSON contract (NEW campaigns) + pushability matrix.
- `change-set.md` — the optimizer→pusher JSON contract (EDITS to live campaigns): action taxonomy
  (negatives/geo/product exclusions, budget/target moves, pause, extensions, signals), the safety-discipline
  gates the pusher enforces (cooldown · ±10% budget · ≤0.3x tROAS · never-block-brand · PMax-pause-not-cut),
  and per-action pushability.
