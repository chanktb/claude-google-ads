---
name: google-ads-pusher
description: >
  Pushes a campaign-spec.json (from any builder-*) OR a change-set.json (from optimizer/routine) into Google
  Ads safely. Reads the JSON contract — never the spreadsheet. Validates, then either exports a Google Ads
  Editor import file + a guided UI build/change checklist (default, read-only MCP), or performs API mutations
  when account-context google_ads.api_write is true. Always behind a human approval gate and a spend-cap
  guard; creates campaigns PAUSED and never enables them. Use when the user says "push", "export to google
  ads", "upload campaign", "import to editor", "apply changes", "apply the optimizer plan", "go live".
---

# Google Ads — Pusher (safety-critical)

Get a change into the account without ever spending money unexpectedly. Two units of work, auto-detected by
the input's `kind`:
- **`campaign-spec.json`** (from `builder-*`, `kind` absent) — creates a NEW campaign. Schema:
  `${CLAUDE_PLUGIN_ROOT}/references/campaign-spec.md`.
- **`change-set.json`** (from `optimizer`/`routine`, `kind: "change-set"`) — EDITS to live campaigns
  (negatives, geo/product exclusions, budget/target moves, pauses, extensions, signals). Schema:
  `${CLAUDE_PLUGIN_ROOT}/references/change-set.md`.

**Read the JSON, never the .xlsx.** The safety invariants below apply to both paths.

## Operating rules / safety invariants (non-negotiable)
- **Validate before anything** (STEP 1). A spec that fails validation never reaches an export or mutation.
- **Campaigns are created PAUSED.** The human enables them in the UI after reviewing. Never create enabled.
- **Human approval gate** (STEP 3): print exactly what will happen and require an explicit "yes".
- **Spend-cap guard**: block if `daily_budget` exceeds the cap (from context or asked). 
- **Mode honesty**: if `api_write` is false, do NOT claim auto-create — emit an importable file + guided
  UI steps. State precisely what is automated vs manual.

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — STEP 1 `validate_spec.py` + `spec_to_paste.py`; STEP 2 generators (`spec_to_editor_csv.py`, `spec_to_pmax_checklist.py`); STEP 1c/2c `validate_changeset.py` + `changeset_to_actions.py`; per-URL 200 checks. These are deterministic script runs — push them all down.
- **Judge (main session)** — STEP 3 **the approval gate** (print the plan, require an explicit "yes"), the spend-cap call, Mode B mutation oversight, and any FAIL interpretation. **Never delegate the gate.** A safety decision is judgment by definition.
- (No Routine tier here — validation and generation are single-shot Scout runs; the only judgment is the gate.)

## STEP 0 — Load + detect kind
Read the input JSON and `account-context.yaml` (for `google_ads.api_write` and any spend cap). Confirm the
target `customer_id` matches. **Branch on `kind`:** `"change-set"` → the change path (STEP 1c/2c below);
otherwise treat it as a `campaign-spec.json` → the build path (STEP 1/2).

## STEP 1c — Validate a change-set (dry-run gate)
```
python ${CLAUDE_PLUGIN_ROOT}/skills/pusher/scripts/validate_changeset.py <change-set.json> \
       --context ./account-context.yaml --max-budget <cap>
```
It enforces the Scaling Ladder + account guardrails: **cooldown gate** (BLOCKS a budget/target move on a
within-cooldown campaign), budget step ≤ +10% + spend cap, tROAS step ≤ 0.3x + ≥15 conv/wk floor, no
direction reversal inside the cooldown, PMax-scales-down-by-pausing (not budget cut), no broad negatives,
**never block a brand term** (word-boundary, from context `brand_terms`), and a `reason` on every action.
**FAIL → stop and report** (e.g. "3 scale moves blocked by cooldown — defer them"). On PASS, set
`provenance.verified = true`, then go to **STEP 2c**.

## STEP 2c — Render the change into operator actions
```
python ${CLAUDE_PLUGIN_ROOT}/skills/pusher/scripts/changeset_to_actions.py <change-set.json> --output-dir .
```
Emits `CHANGE-PLAN.md` (ordered, checkboxed, each step with its data reason + UI path + discipline note +
$/mo), `negatives-editor.csv` (Search/Branded campaign negatives → Editor import), and `negatives-paste.txt`
(wrapped negatives for shared lists / PMax campaign negatives). Then the approval gate (STEP 3) and report
(STEP 5). With `api_write: true`, apply the actions via the API instead (still gated; negatives/exclusions/
budget/target/pause are mutations on existing entities — nothing is created enabled).

## STEP 1 — Validate (dry-run gate)
Run the validator:
```
python ${CLAUDE_PLUGIN_ROOT}/skills/pusher/scripts/validate_spec.py <campaign-spec.json> --max-budget <cap>
```
It checks: char limits + counts per asset group (**Google-accurate counting** — NFC-normalized, CJK/full-
width = 2, trailing whitespace + hidden/non-breaking chars flagged; see `${CLAUDE_PLUGIN_ROOT}/references/google-ads-formatting.md`),
listing-group Everything-Else nodes + no cross-AG product overlap, `status = paused`,
`conversion_goals.scope = campaign`, `brand_exclusion` for PMax, negative match types, and
`daily_budget ≤ cap`. **FAIL → stop and report.** On PASS, set `provenance.verified = true`.

Also emit ready-to-copy keyword/negative/search-theme blocks (already wrapped `[exact]` / `"phrase"` / broad
so the operator pastes them straight in — no re-formatting):
`python ${CLAUDE_PLUGIN_ROOT}/skills/pusher/scripts/spec_to_paste.py <campaign-spec.json> --output paste.txt`

## STEP 2 — Choose the push path (honest, per `${CLAUDE_PLUGIN_ROOT}/references/campaign-spec.md` pushability matrix)
Decide by `api_write` AND `campaign_type`:

- **Mode A — Guided build (default; `api_write: false`)**
  - **Search / Branded Search** → generate a Google Ads **Editor import CSV** (campaigns, ad groups,
    keywords + match types, RSAs, negatives) with:
    `python ${CLAUDE_PLUGIN_ROOT}/skills/pusher/scripts/spec_to_editor_csv.py <campaign-spec.json> --output editor-import.csv`
    Then: Google Ads Editor → Account → Import → From file → REVIEW → post. Editor handles these well.
  - **Performance Max / Demand Gen** → PMax is mostly API-or-UI. Emit a **precise, ordered UI build
    checklist** with all copy/values/URLs **paste-ready** and Google-accurate char counts:
    `python ${CLAUDE_PLUGIN_ROOT}/skills/pusher/scripts/spec_to_pmax_checklist.py <campaign-spec.json> --output checklist.md`
    It renders campaign settings, per-asset-group listing-group include/exclude steps, paste blocks
    (headlines/long/descriptions/search themes), asset-upload list, sitelinks, audience signals, and
    wrapped campaign negatives — each as a checkbox. The operator follows it click-by-click in the UI.
- **Mode B — API mutate (`api_write: true`)**
  - Create via the Google Ads API: campaign + budget + bidding, asset groups, listing-group filters,
    asset-group signals, text assets; upload image/video assets first, then attach. Still PAUSED, still
    behind the approval gate. (Requires a write-capable connection — most MCPs are read-only.)

## STEP 3 — Approval gate
Print a concise plan and **wait for explicit "yes"** (no yes → stop):
- **Build path:** campaign name, type, daily budget (vs cap), bidding, # asset/ad groups, brand exclusion
  on/off, and — for Mode A — what's auto vs manual.
- **Change path:** the action count + total $/mo from `CHANGE-PLAN.md`, the campaigns touched, what mutates
  (negatives / exclusions / budget±/target±/pauses), and explicitly any moves **HELD by cooldown** (these are
  NOT applied). Confirm nothing enables a paused campaign and no budget move exceeds +10% or the cap.

## STEP 4 — Execute
Mode A: write the Editor file + the UI checklist to the working directory. Mode B: run the mutations
(create-paused), capturing returned resource names; on any error, stop and report what was/wasn't created.

## STEP 5 — Report
- What was created/exported, what remains manual, and the **exact next action** ("import this file", or
  "complete these UI steps", then "review and enable").
- Reminder: campaign is PAUSED — enable only after review. Hand off monitoring to `tracker`.

## To build / refine later
- [x] Editor CSV generator for Search/Branded (`scripts/spec_to_editor_csv.py`). Done.
- [x] Ready-to-copy keyword/negative/theme blocks (`scripts/spec_to_paste.py`). Done.
- [x] PMax guided-UI checklist generator (`scripts/spec_to_pmax_checklist.py`). Done.
- [x] Change-set path: `validate_changeset.py` (safety gates) + `changeset_to_actions.py` (CHANGE-PLAN.md +
  negatives CSV/paste). Contract: `references/change-set.md`, template: `templates/change-set.json`. Done.
- [ ] API mutate path (Mode B) — deferred (few accounts have write API access right now). Applies to both
  the build path AND the change path (negatives/exclusions/budget/target/pause mutations).
- [ ] Re-check current Google Ads Editor PMax import capability (it changes over time).
