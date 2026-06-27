# change-set.json — the optimizer → pusher contract

Reusable, business-agnostic reference. `optimizer` (and `routine`) emit a `change-set.json` — a typed list of
**changes to an EXISTING account** (add negatives, exclude geos/products, adjust budget/target, pause, add
extensions/signals). The `pusher` reads it, validates the safety discipline, and renders operator actions.
Template: `templates/change-set.json`.

## change-set vs campaign-spec — two different contracts
| | `campaign-spec.json` | `change-set.json` |
|---|---|---|
| Produced by | `builder-*` | `optimizer` / `routine` |
| Unit of work | a **new** campaign | **edits** to live campaigns |
| Pusher entry | STEP 0 (build path) | STEP 0 (change path) |
| Validator | `validate_spec.py` | `validate_changeset.py` |
| Renderer | `spec_to_editor_csv` / `spec_to_pmax_checklist` | `changeset_to_actions.py` |

Both share the same non-negotiables: **validate before anything**, **human approval gate**, **spend-cap
guard**, **honest push path** (api vs Editor vs paste vs UI). A change-set never touches the account directly;
it produces an Editor file + a paste block + an ordered UI checklist, behind the gate.

## Top-level fields
- `spec_version` — bump on schema changes.
- `kind` — must be `"change-set"` (lets the pusher tell it apart from a campaign-spec).
- `account` — `customer_id`, `login_customer_id`, `currency` (from context).
- `guardrails` — echo of the context guardrails the optimizer honored (provenance; the validator re-checks
  the discipline regardless).
- `actions[]` — the ordered list (below).
- `provenance` — `built_by`, `context_source`, `source_report` (e.g. MONEY-LEAK-REPORT.md), `verified`
  (pusher flips to true only after `validate_changeset.py` passes).

## action object — common fields
Every action carries:
- `id` — stable short id (`a1`, `geo-lite`, …) for the checklist + approval log.
- `type` — one of the action types below.
- `target` — `{ "campaign": "<name>", "campaign_id": "<id>", "campaign_type": "performance_max|search|...",
  "asset_group"/"ad_group": "<name>" (when scoped below campaign) }`. Name + id both, so the operator can
  find it and the API path can resolve it.
- `reason` — the data backing (the numbers, the $ leak, the diagnostic). **Required** — an action with no
  evidence is rejected.
- `diagnostic` — the D-code from `diagnostic-playbook.md` (D2…D14) for traceability.
- `est_impact_per_mo` — recoverable/gained $/mo (number, optional). The renderer ranks + totals these.
- `push_path` — honest path: `api | editor_csv | paste | ui`. The renderer groups by this.
- `is_scale` — `true` for any action that moves budget or target UP (triggers the cooldown + ladder gates).

## action types
| `type` | extra fields | push_path | diagnostic |
|---|---|---|---|
| `add_negatives` | `scope: campaign\|shared_list`, `list_name` (shared), `negatives:[{text,match_type}]` | editor_csv (Search) / paste (PMax campaign neg) | D5 |
| `exclude_geo` | `locations:[{name, id?}]`, `bid_modifier?` | ui / editor_csv — exclude OR a location **bid adjustment** (both supported on Search AND PMax) | D3 |
| `exclude_products` | `asset_group`, `products:[{item_id?, title}]` | ui (listing-group exclude) | D14 |
| `adjust_budget` | `current_daily`, `new_daily`, `direction: up\|down` | api / ui | D2 |
| `adjust_target_roas` | `current`, `new`, `conv_per_week` (for the floor) | api / ui | D1 |
| `pause` | `entity: campaign\|asset_group\|ad_group` | api / ui | D2/D9 |
| `add_extensions` | `sitelinks[]`, `callouts[]`, `snippets[]` (from `assets`) | api / ui | D9 |
| `add_audience_signal` | `asset_group`, `signal:{kind, value}` | ui | D11 |
| `exclude_placements` | `placements:[...]` (account-level) | ui | D8 |
| `add_assets` / `replace_asset` | `asset_group`, asset fields | ui | D9 |

`reallocate_budget` is expressed as a PAIR: an `adjust_budget` DOWN on the source + an `adjust_budget` UP on
the receiver (so each leg is gated independently — the UP leg hits the cooldown/ladder check).

## Safety discipline the validator enforces (`validate_changeset.py`)
These encode `optimization-playbook.md` (Scaling Ladder + tROAS step-up) and the account guardrails.

1. **Cooldown gate (the big one).** Any `is_scale` action (or any `adjust_budget`/`adjust_target_roas`) whose
   target is marked `within_cooldown: true` is **BLOCKED**. Source: a recent `change_event` (D13) or the
   context `change-event-cooldown` guardrail. *Don't scale a campaign that just changed — let Smart Bidding
   stabilize.* (e.g. if every active campaign was changed <14d ago, every scale move is blocked until the cooldown clears.)
2. **Budget step ≤ +10%** per step (default; an account guardrail may override). `new_daily` over `current ×
   1.10` → ERROR. Also `new_daily` over the **spend cap** → ERROR.
3. **tROAS step ≤ 0.3x** absolute per step. `new − current > 0.3` → ERROR. **Conversion floor:**
   `conv_per_week < 15` on a tROAS raise → ERROR ("consolidate for volume before raising").
4. **No direction reversal inside the cooldown.** If `target.last_change_direction` opposes this action's
   `direction` and the target is within cooldown → ERROR (whipsaw guard).
5. **PMax scales DOWN by pausing asset groups, not cutting budget.** An `adjust_budget` `down` on a
   `performance_max` campaign → ERROR with the fix ("pause the low-ROAS asset group instead").
6. **Negatives:** `match_type ∈ {exact, phrase}` (no broad). **Never block a brand term** — a negative whose
   text contains a `brand_terms` token (WORD-BOUNDARY match, not substring) → ERROR. (Brand intent is not
   waste, even at 0 conv; see the never-block rule in the playbook + `google-audit-checks.md` G-PM3.)
7. **Every action needs a `reason`.** Missing → ERROR. A `pause` with no ROAS/spend evidence in the reason →
   WARNING (don't pause blind).
8. **Spend-cap guard** stays in force (same as campaign-spec): any `new_daily` > cap → ERROR.

A change-set that fails validation never reaches the renderer or an export.

## Pushability — honest per action
| Action | API (`api_write`) | Editor CSV | Paste | UI only |
|---|---|---|---|---|
| Add Search/Branded negatives | ✅ | ✅ (good) | ✅ wrapped | — |
| Add PMax campaign negatives | ✅ | ✗ | ✅ wrapped | ✅ |
| Geo exclusion (Search) | ✅ | ✅ | — | ✅ |
| Geo exclusion (PMax) | ✅ | ✗ | — | ✅ (exclusion only) |
| Product / listing-group exclusion | ✅ | ✗ | — | ✅ |
| Budget / target adjust | ✅ | partial | — | ✅ |
| Pause campaign / asset group | ✅ | partial | — | ✅ |
| Extensions, audience signals, placement exclusions | ✅ | ✗ | — | ✅ |

**Implication:** with no API write, negatives push cleanly (Editor CSV / paste); everything else is a
**guided UI checklist** with the exact path, the data reason, and the discipline note per step. The renderer
produces all three artifacts; the operator applies them behind the approval gate. Confirm current Editor
capability rather than assume.
