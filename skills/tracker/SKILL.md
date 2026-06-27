---
name: google-ads-tracker
description: >
  Monitors live campaigns — especially newly launched ones in the learning phase. Reports budget pacing,
  learning-phase status, delivery, and anomalies (sudden CPC/CPA/ROAS swings, conversion drops, disapproved
  assets). Observe-only: it alerts, it never changes the account. Reads account-context.yaml. Use when the
  user says "how's my campaign doing", "pacing", "learning phase", "is it spending", "monitor", "anomaly",
  "what changed".
---

# Google Ads — Tracker (observe only)

Watch live campaigns and surface what's happening. **Changes nothing in the account** — that's the
`optimizer`'s job. Especially useful right after a `pusher` launch (the learning window).

## Operating rules
- Observe-only: report and alert, never mutate. Read everything from `account-context.yaml`.
- Honor guardrails: a `change-event-cooldown` means don't raise an anomaly right after a deliberate change.
- No false absence (GUARD-6 from audit): prove completeness before reporting "no delivery / no conversions".

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — STEP 0 context read; identifying newly-launched vs established by start date.
- **Routine (`sonnet`)** — STEP 1 per-campaign performance + `change_event` pull. Dispatch as a `general-purpose` sub-agent; **return raw rows + the daily trend, don't flag**.
- **Judge (main session)** — STEP 2-4 learning-phase read, pacing call, and especially anomaly-vs-expected (apply the cooldown — a recent deliberate change is NOT an anomaly). The pull is cheap; deciding what's normal variance vs a real alert is judgment.

## STEP 0 — Load
Read `account-context.yaml` (customer_id, guardrails, margin_tiers for ROAS context). **If it's missing,
run `setup` first — never observe on an unconfigured/half-connected account.** Identify which
campaigns are newly launched (recent `change_event` / start date) vs established.

## STEP 1 — Pull recent performance
Per campaign over the relevant window (explicit YYYY-MM-DD dates): spend, conversions, conv value, ROAS,
CPC, CPA, impression share, and the daily trend. Pull recent `change_event` history too.

## STEP 2 — Learning-phase status (new campaigns)
- Is the campaign accumulating conversions toward the learning floor (~15-30/period)? Project days-to-exit.
- Flag campaigns stuck below the floor (will never stabilize at current budget → note for `optimizer` to
  consolidate, but tracker only flags).
- During learning, do NOT read short-term ROAS swings as problems — say so explicitly.

## STEP 3 — Pacing & delivery
- Budget utilization: spending in full, underspending, or limited-by-budget?
- Impression share lost to budget vs rank.
- Delivery gaps (disapprovals, eligibility, $0-spend asset groups) — verify before claiming absence.

## STEP 4 — Anomaly detection
- Week-over-week swings in CPC / CPA / ROAS / conversions beyond a sensible band.
- Sudden conversion drop (possible tracking break → route to `measurement`).
- Disapproved assets / policy issues / ad-strength drops.
- **Apply the cooldown**: if a recent `change_event` explains the swing, note it as expected, not an anomaly.

## STEP 5 — Report & hand off
- A short status: pacing, learning status, and any real anomalies (with the cooldown applied).
- Frame routine variance as normal; reserve alerts for genuine issues.
- Hand actionable findings to `optimizer` (to act) or `measurement` (if tracking looks broken).

## To build / refine later
- [ ] Reuse the shared HTML report module (see DECISIONS) for a monitoring dashboard.
