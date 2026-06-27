---
name: google-ads-experiments
description: >
  Designs disciplined A/B tests for Google Ads — campaign-level splits (bidding, brand exclusion, new-
  customer mode, split structure) and asset-group/ad-group-level splits — changing one variable at a time
  with a feasibility check, clear success criteria, and minimum runtime. Prevents "testing by spawning
  random campaigns". Reads account-context.yaml. Use when the user says "experiment", "A/B test", "split
  test", "which works better", "test budget/bidding/audience".
---

# Google Ads — Experiments

Turn a "let's test X" into a clean experiment: one variable, enough volume to learn something, a defined
readout. This is how the split menus in the builders get validated — not by guessing.

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — STEP 2 `significance.py` run.
- **Routine (`sonnet`)** — pulling conversions-per-arm estimates / recent volume for the feasibility check. Dispatch as `general-purpose`; **return raw numbers**.
- **Judge (main session)** — STEP 1 variable choice, STEP 3 design + decision rule, STEP 4 platform mapping, STEP 5 readout call (against the pre-stated rule, not early noise). The power math is mechanical; designing a test that can conclude is judgment.

## STEP 1 — Pick ONE variable
From the catalog (campaign-level: bidding strategy, tROAS level, brand-exclusion on/off, new-customer mode,
split structure A vs B from `${CLAUDE_PLUGIN_ROOT}/references/pmax-split-strategies.md`; ad-group/asset-group-level: copy theme,
audience signal, landing page). Change exactly one — never bundle variables (you won't know what moved).

## STEP 2 — Feasibility check (don't run a test that can't conclude)
Using `${CLAUDE_PLUGIN_ROOT}/references/forecasting-and-benchmarks.md`, estimate conversions per arm over the planned runtime.
If each arm won't accumulate enough conversions to detect a meaningful difference, say so and either:
extend the runtime, increase budget, pick a higher-volume variable, or skip the test. **A test too small
to reach significance is worse than no test** — it invites false conclusions.
Runnable check: `python ${CLAUDE_PLUGIN_ROOT}/skills/experiments/scripts/significance.py --conv-per-arm N [--mde 0.15]` →
smallest detectable lift + whether the run is powered for your target effect.

## STEP 3 — Design
- Control vs variant, **50/50** split, one variable.
- Primary success metric (e.g. ROAS, CPA, conversions) + guardrail metrics (don't win on CPA while
  tanking volume).
- Minimum runtime (cover learning + at least 2-4 weeks; avoid mid-experiment changes).
- Pre-state the decision rule: what result ships the variant, what reverts it.

## STEP 4 — Map to the platform
Prefer native **Google Ads Experiments / campaign drafts** where the campaign type supports them; otherwise
describe the manual A/B setup. Note PMax's experiment support and limits for the chosen variable.

## STEP 5 — Readout criteria
When to call it: enough volume + runtime elapsed. Judge against the pre-stated rule and significance, not a
gut read of early noise. Output: winner, confidence, and the next action (ship / revert / iterate). Respect
the change-event cooldown when applying the result via `pusher`.

## Guardrails
- One variable at a time. No mid-flight changes. No calling a winner before the runtime/volume threshold.
- Honor `margin_tiers` when the metric is ROAS (compare within a tier, not across).

## To build / refine later
- [x] Significance calculator (`scripts/significance.py`). Done.
