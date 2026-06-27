# campaign-spec.json — the builder → pusher contract

Reusable, business-agnostic reference. Every `builder-*` emits a `campaign-spec.json` (the machine view)
alongside its human `.xlsx` blueprint. The `pusher` reads the JSON, never the spreadsheet. Template:
`templates/campaign-spec.json`.

## Why a JSON contract
A spreadsheet is for humans; parsing it is brittle. A typed JSON spec lets the pusher validate, dry-run,
and (when API write is available) mutate deterministically. It also makes the builder/pusher boundary
clean and lets every campaign type share one push path.

## Top-level fields
- `spec_version` — bump on schema changes.
- `campaign_type` — `performance_max | search | branded_search | demand_gen`. Drives the push path.
- `account` — `customer_id`, `login_customer_id`, `currency` (from context).
- `campaign` — name, `status` (**always `paused` on create** — enable after human review), `daily_budget`,
  `bidding` (strategy + optional `target_roas`), `conversion_goals` (**scope: campaign**), `brand_exclusion`,
  `final_url_expansion` (default false), `auto_created_assets` (default false), geo/language.
- `split_strategy` — the chosen campaign + asset-group axes + rationale (provenance, not pushed).
- `asset_groups[]` (PMax/Demand Gen) — the **AG-level** unit: name, `final_url`, display_paths, headlines/
  long_headlines/descriptions/search_themes, `listing_group` tree, `audience_signal`, `business_name`,
  `call_to_action`, and `image_assets`/`video_assets` (each with a specific `brief` shot description, not a
  generic spec). **Sitelinks are NOT here** — in PMax they attach at the campaign level (see `extensions`).
- `extensions` — **campaign-level** in PMax (sitelinks/callouts/structured snippets attach to the campaign,
  not an asset group): `sitelinks[]` ({text ≤25, description1/2 ≤35, final_url}), `callouts[]` (strings ≤25),
  `structured_snippets[]` ({header from Google's fixed list, values[] ≤25}), plus `promotions[]` and
  `prices[]` left as **placeholders** (empty arrays + a `_*_placeholder` note) so the operator remembers to
  add a promotion during a sale and optional price assets.
- `ad_groups[]` (Search/Branded — instead of asset_groups). Each:
  - `name`, `theme`, optional `default_bid`.
  - `keywords[]`: `{ "text", "match_type": "exact|phrase|broad", "source"? }`. `source` (optional, recommended
    for non-brand Search) records WHERE the keyword came from — `PMax insight (...)`, `search_term_view`,
    `expansion`, `catalog` — so the harvest is transparent. Proven converters harvested from PMax go in as
    **exact** (the control lever); the workbook renders a Source column.
  - `negatives[]`: `{ "text", "match_type": "exact|phrase" }`.
  - `rsa`: `{ "final_url", "headlines": [{"text","pinned":null}], "descriptions": [{"text","pinned":null}],
    "paths": ["",""] }` — ≤15 headlines (≤30 chars), ≤4 descriptions (≤90), paths ≤15 chars.
  - optional `sitelinks[]`, `callouts[]`.
- `campaign_negatives[]`, `shared_negative_lists[]`.
- `trademark_avoid[]` (branded/search) — competitor trademarks that must NEVER appear in ad TEXT
  (headlines/descriptions/paths); fine as keywords. `validate_spec.py` BLOCKS any ad text containing one
  (word-boundary), enforcing the no-competitor-TM-in-copy rule.
- `provenance` — built_by, context_source, `verified` (pusher flips to true only after validation passes).

**Workbook renderer:** `spec_to_xlsx.py` handles BOTH `asset_groups` (PMax/Demand Gen → AG sheets with
audience signals + listing groups + creative briefs) and `ad_groups` (Search/Branded → AG sheets with
keywords + RSA + negatives + paths), plus the shared Overview/Extensions/Negatives/Checklist sheets.

## listing_group tree
Recursive: a `subdivision` node has a `dimension` + `value` and `children`; `unit` nodes carry an
`action` of `include` or `exclude`. Every subdivision MUST contain an `other`/Everything-Else child set to
`exclude`. A product may appear in exactly one asset group across the whole spec (no overlap).

## Validation rules (enforced by pusher's validate_spec.py)
- Per asset group: ≤15 headlines (≤30 chars), ≤5 long headlines (≤90), ≤5 descriptions (≤90; #1 ≤60),
  ≤50 search themes; sitelink text ≤25, descriptions ≤35. Counting is Google-accurate (see
  `google-ads-formatting.md`), not naive `len()`.
- Listing groups: every subdivision has an Everything-Else=exclude node; no product in two asset groups.
- `campaign.status` must be `paused`. `conversion_goals.scope` must be `campaign`.
- `brand_exclusion.enabled` true for PMax unless an explicit override (guardrail).
- `daily_budget` ≤ the spend cap passed to the pusher (spend-cap guard).
- Negatives: match_type in {exact, phrase} (no broad-match negatives by default).

## Pushability matrix — be honest per campaign type and element
| Element | API (api_write) | Editor CSV | UI only |
|---------|-----------------|------------|---------|
| Search campaign + ad groups + keywords + RSAs | ✅ | ✅ (good) | — |
| Campaign settings, budget, bidding | ✅ | partial | — |
| PMax campaign + budget + bidding | ✅ | limited | — |
| PMax asset groups (text) | ✅ | limited | often |
| PMax listing group filters | ✅ | ✗ | ✅ |
| PMax audience signals (AG-level) | ✅ | ✗ | ✅ |
| Extensions: sitelinks/callouts/snippets (campaign-level) | ✅ | ✗ | ✅ |
| Image/video/asset uploads (AG-level) | ✅ (upload first) | ✗ | ✅ |
| Brand exclusion lists | ✅ | ✗ | ✅ |

**Implication:** Search pushes cleanly via Editor CSV. **PMax is mostly API-or-UI** — so the pusher's
default (no API write) mode for PMax is a *guided UI build* with paste-ready values, not a one-click import.
The pusher should confirm current Editor capability rather than assume; capabilities change over time.
