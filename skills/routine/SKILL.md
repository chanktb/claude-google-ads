---
name: google-ads-routine
description: >
  The daily/weekly/monthly/quarterly operating rhythm for a Google Ads account. Orchestrates tracker
  (observe) and optimizer (act) at the right cadence, remembers when each was last run, auto-surfaces
  overdue checks, and gates every action behind explicit preconditions (only act when ALL are met, else
  wait). Use when the user says "daily routine", "weekly review", "what should I check today", "routine",
  "what's due", "ongoing management", "what can I change now".
---

# Google Ads — Routine (cadence + decision gates)

This is the operating rhythm, not a new analysis engine: it **calls `tracker` and `optimizer`** at the
right cadence, **remembers history**, and **gates actions** so nothing changes unless its preconditions
are met. It answers: "what do I check today, what am I allowed to change, and under what conditions."

## STEP 0 — Read state + build today's agenda
1. Load `account-context.yaml` (esp. `guardrails`, `margin_tiers`, `campaign_defaults`).
2. Run the history engine:
   `python "${CLAUDE_PLUGIN_ROOT}/skills/routine/scripts/routine_state.py" [--today YYYY-MM-DD]`
   It reads `routine-state.json` in the working dir and prints what's **DUE / OVERDUE** per cadence.
3. **Run everything that's due or overdue — not just what the user asked.** If the user says "daily" but
   the weekly/monthly is overdue (they haven't checked in a while), run those too and say so. This is the
   "it remembers and nags" behavior: long gap → the overdue cadence surfaces automatically.

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — STEP 0 `routine_state.py` run (agenda) and the `--mark` stamp after acting.
- **Routine / Judge** — inherited from the skills this orchestrates: `tracker` and `optimizer` carry their own per-STEP tiers (collection is Routine, verdicts are Judge).
- **Judge (main session)** — the **decision gates** (every precondition check, +10% vs WAIT), reading the cooldown from guardrails, and deciding what overdue work to run. The agenda is cheap; the gate is judgment — **never delegate a gate**.

## Cadence checklists (each calls existing skills — don't re-implement)
- **Daily (~15 min) — health check, NOT optimization.** Via `tracker`: spend/CPC/clicks vs yesterday,
  budget pacing, disapprovals/policy, paused-by-error, sudden anomalies. Goal = spot what's BROKEN. No
  performance changes off one day of data.
- **Weekly (1-2h) — via `optimizer`:** **search-term review (mandatory, both sources)** — pull
  `search_term_view` (covers Search/Branded campaigns) AND PMax/Demand-Gen **search category insights**
  (`campaign_search_term_insight`; search_term_view does NOT contain PMax terms). Feed both to
  `search_term_miner.py`. **Never propose blocking brand terms** (brand intent = your own traffic, even at
  0 conv). Then: budget pacing + reallocate to top performers, campaign tiering, automated-rules check.
  Apply the decision gates below.
- **Monthly (2-4h):** the full **money-leak sweep** — run D1-D14 in
  `${CLAUDE_PLUGIN_ROOT}/references/diagnostic-playbook.md`: bid/target health (decode
  `bidding_strategy_system_status`; lower tROAS if `LIMITED_BY_INVENTORY`, scale if `LIMITED_BY_BUDGET` on-target),
  budget allocation (shift low-ROAS→high-ROAS), geo waste, dayparting, structure, Quality Score, PMax channel
  distribution (D8), ad copy/assets/extensions (D9). Any tROAS/budget move follows the **Scaling Ladder**
  (one variable, cooldowns). Plus conversion-tracking audit (`measurement`), attribution review. Pull a fresh
  `audit` if drift is suspected.
- **Quarterly:** strategic `audit` + `plan` alignment to business goals.

## Decision gates — only act when ALL preconditions hold (else WAIT and say which failed)
Read the spacing/cooldown from the context `guardrails` (the `change-event-cooldown` rule), don't hardcode it.

| Action | Preconditions (ALL must hold) | Step |
|--------|-------------------------------|------|
| **Scale budget UP** | ROAS ≥ margin-tier target · campaign is budget-limited (lost IS to budget / capping) · **no budget change within the context cooldown** · not reversing a recent decrease · not in Learning · ≥~15 conv/week | **+10% (gentle), never bigger** |
| **Raise target ROAS** | ≥15 conv/week · ≥2 weeks since last target change · ROAS stable above current target · no recent `change_event` | **+0.1x per step** |
| **Add negative keyword** | term >$10 spend AND 0 conv (or clearly irrelevant) · NOT in the protected set (store/coupon/cheap-brand) | exact/phrase, ready-to-copy |
| **Scale budget DOWN** | ROAS < target sustained (not one bad day) · not in Learning · not reversing a recent increase within cooldown | **PMax: pause low-ROAS asset groups, do NOT cut budget** |
| **Pause campaign / asset group** | Dead tier (ROAS < ~0.5× target) sustained · checked non-paid (organic/email) revenue contribution first | PMax → pause the asset group, not the campaign budget |

Rules of the road (see `${CLAUDE_PLUGIN_ROOT}/references/optimization-playbook.md`): **never reverse budget
direction within the cooldown window** (went up → stay up or hold); **hold the cooldown between changes** so
Smart Bidding stabilizes; **prefer Mondays** for budget changes (cleaner weekday pacing). If a precondition
fails, do NOT act — report the action as "WAIT — needs: <the failing condition>".

## After acting — record it
Stamp the cadence so history stays accurate:
`python "${CLAUDE_PLUGIN_ROOT}/skills/routine/scripts/routine_state.py" --mark weekly --actions "raised <campaign> budget +10%; added 4 negatives"`
Account mutations still go through `pusher` (approval gate): the optimizer serializes the gated actions into a
`change-set.json`, and `pusher` validates (`validate_changeset.py` — the cooldown gate re-checks the spacing
this routine just decided) + renders `CHANGE-PLAN.md`. The routine proposes + gates; it doesn't push silently.

## Scheduling (optional)
Pairs with cron/scheduled agents: a daily cron runs the daily health check; a Monday cron runs the weekly
routine. The history engine means even ad-hoc runs catch up anything overdue.

## To build / refine later
- [ ] A one-line "what changed since last run" diff from the log.
