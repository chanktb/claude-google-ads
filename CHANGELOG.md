# Changelog

All notable changes to **claude-google-ads** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Clarified D14 product/feed into 3 sourced layers** (a CEO question: "products show in Google Ads via the
  Merchant link — why report no data?"). Verified live: `shopping_performance_view` returns FULL product data
  (item_id/title/brand/type/condition + cost/impr/conv) through the Ads↔Merchant link — products ARE in Ads and
  the D4/D14 performance leak already uses them. Out-of-stock is reachable from the STORE connector (cross-ref
  item_ids vs Shopify/Woo inventory) — no Merchant needed. ONLY the approval/disapproval/GTIN status layer needs
  the Merchant Content API. Skill + gaql-notes now say this explicitly so the report never claims "no product data".
- **Geo drains now surface ZERO-value spend, and PMax bid-adjust is stated correctly.** Drains previously
  hid states with spend but $0 conversion value (a `cost < $50` floor dropped them) and ranked only by raw
  cost — so pure-waste states could fall off the list; now 0-value states are included at a low floor, labeled
  "0 value (100% waste)", and the list ranks by dollars WASTED. Also corrected guidance across the geo + daypart
  findings and `change-set` / `diagnostic-playbook`: **location AND ad-schedule bid adjustments are supported on
  PMax** (the campaign criterion `bid_modifier` is settable) — it is NOT exclusion-only. (Per CEO correction on a live review.)
- **Geo card redesigned to be actionable.** Replaced the flat "Geo — top spend by ROAS" list with two
  decision-ready lists per campaign: **winners** (high conversion value + ROAS at/above the campaign's bar —
  keep / scale) and **drains** (high cost but ~0 value or ROAS well below bar — exclude / bid-down, with the
  $/mo total). An operator can now see at a glance which states to protect vs cut, instead of a flat spend list.
- Hardened the cold-start (no-data) path: every data-pulling skill — `measurement`, `plan`, `optimizer`,
  `tracker` — now explicitly routes to `setup` when `account-context.yaml` is missing, matching the guard
  `audit` and the router already had. Verified end-to-end that a brand-new user with nothing connected is
  stopped cleanly with connect-this guidance and never gets a fabricated number (`validate_context.py`
  emits `Next step: setup (connect Google Ads)`).
- `references/aov-and-sales-sourcing.md`: added a "pull COMPLETELY — paginate" section after a live onboarding
  hit a truncated store pull (385 vs ~3,000 orders) that left AOV looking right while undercounting volume ~8×
  and breaking the Ads-vs-store cross-check. Now mandates exhausting pagination + a magnitude sanity check.
- `audit` skill: added the campaign-extensions pull to the mandatory bundle with the correct `campaign_asset`
  GAQL (and the `asset.type` INVALID_ARGUMENT gotcha), plus the `EXPECTED_REFERENCED_FIELD_IN_SELECT_CLAUSE`
  rule — both surfaced by a live DTK audit. Reinforces flagging extensions `UNVERIFIED` over assuming.

### Fixed

- **Empirically eliminated false "verify in UI" labels.** Tested every blocked field against the live API:
  **location targeting type** (`campaign.geo_target_type_setting` — Presence vs Interest), **Enhanced
  Conversions** (`customer.conversion_tracking_setting.enhanced_conversions_for_leads_enabled`), **final URLs**
  (`landing_page_view` / `expanded_landing_page_view`), **RSA text + per-asset metrics** (`ad_group_ad_asset_view`),
  and **placement exclusions** (`campaign_criterion.placement.url`) ALL read via GAQL and were wrongly punted to
  the UI. Skill + gaql-notes now carry the exact queries; the report renders location type + Enhanced Conversions
  and drops the blanket "Location/FUE/... API can't read these" card. Only the truly-unreadable remain verify-in-UI:
  FUE toggle, asset-automation, content-suitability (UNRECOGNIZED on this API version) and Consent Mode v2 /
  server-side-CAPI (tag-side by design, not Ads entities). Merchant feed health needs the Content API connector.
- **Corrected a false "asset / extension text isn't pullable" claim** caught by diffing against a known-good
  prior report. The earlier prior run's bundle clearly carried PMax **asset text + per-asset cost**
  (`asset_group_asset` → `asset.text_asset.text` + `metrics.*`), **descriptions** text, and **extension text**
  (`ext_text`) — all of which a later "improved" pull had reduced to counts-only and the report then mislabeled
  "text not returned by this MCP — verify in UI". That was wrong-method, not an API limit. The `audit` skill +
  `gaql-notes` now specify pulling asset TEXT + metrics and extension TEXT explicitly, route Search-RSA text
  through `ad_group_ad_asset_view` (the one genuine serializer block), and the generator's fallback no longer
  blames the MCP. Lesson: diff every report against a prior known-good one before trusting "no data".
- Added a **`pulled` manifest** contract so a truncated one-shot pull can't fabricate findings. A cold one-shot
  audit revealed an agent may fetch a long per-campaign pull (e.g. `asset_group_signal`) for only some
  campaigns and the generator would then emit FALSE "0 audience signals" for the rest. Now `bundle.json`
  declares `pulled: [...]` (dimensions fully covered); the generator renders any un-declared dimension as
  VERIFY ("not pulled — re-run"), never a confident GOOD/FIX. The `audit` skill mandates looping every
  campaign and declaring `pulled` (honesty-by-construction).
  Further: if signals are declared pulled but ONE PMax campaign shows 0 while others have signals, that
  lone 0 renders **VERIFY "confirm (pull may be partial)"** — not a confident FIX — catching an under-covered
  per-campaign pull (the residual a whole-dimension `pulled` flag can't see).
- Stopped the generator from mislabeling **pullable** data as "verify in UI". The channel-mix fail-safe no
  longer claims "PMax channel not API-exposed" (it IS — `segments.ad_network_type`); headlines show the real
  count when only verbatim text is serializer-blocked; and the non-search-burn finding is suppressed when
  channel rows carry no conversions (a cost-only pull no longer fabricates "0-conv burn" on every network).
  The `audit` MANDATORY-pull manifest now explicitly lists channel / device / dayparting / ad-schedule /
  all-region geo + name resolution / asset text, and pins verify-in-UI to the few confirmed non-API fields.
- `money_leak_report.py` now **fails safe on un-pulled dimensions** instead of fabricating findings. A bundle
  missing `channel`/`assets`/`negatives` previously rendered a fake "Channel mix GOOD 0%", "Headlines WATCH",
  and "no negatives → attach lists" — confident verdicts on absent data. Now each renders **VERIFY / "not
  pulled"**. This enforces the suite's no-fabricate
  rule at the RENDER layer, not just the pull layer. Surfaced when a live DTK audit shipped an incomplete
  bundle and the report still showed (false) green/red findings.
- `money_leak_report.py` extension detection used a wrong `AssetFieldType` enum (snippet=12, price=17). The
  live API returns **STRUCTURED_SNIPPET=27, PRICE=26**, so real snippet/price assets were missed and the
  generator emitted false "snippets 0" findings. Corrected the enum + added `SNIPPET_FT`/`PRICE_FT` constants.
- `money_leak_report.py` crashed (`unsupported format string passed to NoneType`) when a connected Merchant
  Center had `active: null` (feed health not pulled). Made the merchant block null-safe and show a
  "feed health not pulled — verify in Merchant" note instead of fake zeros.
- `validate_context.py` "Next step" no longer points at `plan`/`builder-*` when those gates are blocked by a
  missing prerequisite. With Google Ads connected but no store (so no AOV), it now reads
  `Next step: setup — provide AOV or live data source` instead of sending the user into `plan` to hit the
  gap. Surfaced by a "Google-Ads-only, reduced-scope" test.

## [0.1.0] - 2026-06-27

First public release — a Claude Code **plugin** that operates Google Ads end-to-end for **ecommerce**
advertisers (retail B2C, wholesale, DTC). Runs on real account data, never guesses, and never touches your
account without approval.

### Added

- **15 skills** as independently-invokable slash commands, routed by `/google-ads`:
  - **Start:** `setup` (connection hub → `account-context.yaml`) and the `google-ads` router.
  - **Diagnose & fix:** `measurement` (conversion-tracking gate), `audit` (money-leak engine), `optimizer`
    (safe change-set with Scaling Ladder discipline).
  - **Plan & build:** `plan`, `builder-pmax`, `builder-search`, `builder-branded-search`,
    `builder-demand-gen`, `assets`.
  - **Push & operate:** `pusher` (paused-on-create + approval gate + spend cap), `tracker`, `experiments`,
    `routine`.
- **Money-leak engine (D1–D14)** — ranks budget leaks by $/month: bid/target health, geo & dayparting
  waste, 0-conversion products, PMax channel burn, weak assets/extensions, account structure, Quality Score,
  and Merchant feed health.
- **Two JSON contracts:** `campaign-spec.json` (builder → pusher, for new campaigns) and `change-set.json`
  (optimizer → pusher, for edits to live campaigns), each with a validator enforcing bidding cooldowns,
  ≤10% budget steps, ≤0.3× target-ROAS steps, brand-safe negatives, and trademark rules.
- **No-fabricate gate** — every number is grounded in connected account data or flagged `UNVERIFIED`;
  the suite never invents a figure to fill a gap.
- **Connection hub** — inventories and registers Google Ads (mandatory), Store
  (Shopify / WooCommerce / BigCommerce), Merchant Center, GA4, and GSC in `account-context.yaml`, and
  guides the user to connect what's missing before skills run.
- **Grounded builders** — Search harvests the proven converters PMax discovered into exact-match control
  (dual-source: `search_term_view` + `campaign_search_term_insight`); PMax themes, audiences, and price
  assets come from converting data and real store data, not from an example account.
- **Blueprint renderer** (`spec_to_xlsx.py`) — Overview / Extensions / per-asset-group / Negatives /
  Checklist, for both PMax/Demand-Gen asset groups and Search ad groups.
- Ecommerce knowledge base (benchmarks, policy, character limits, bidding playbooks), MIT license, and a
  full usage guide.

[Unreleased]: https://github.com/chanktb/claude-google-ads/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/chanktb/claude-google-ads/releases/tag/v0.1.0
