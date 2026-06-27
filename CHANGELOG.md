# Changelog

All notable changes to **claude-google-ads** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Hardened the cold-start (no-data) path: every data-pulling skill — `measurement`, `plan`, `optimizer`,
  `tracker` — now explicitly routes to `setup` when `account-context.yaml` is missing, matching the guard
  `audit` and the router already had. Verified end-to-end that a brand-new user with nothing connected is
  stopped cleanly with connect-this guidance and never gets a fabricated number (`validate_context.py`
  emits `Next step: setup (connect Google Ads)`).

### Fixed

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
