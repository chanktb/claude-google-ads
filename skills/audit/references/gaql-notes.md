# GAQL compatibility & accuracy notes

Prevents false positives when auditing via the Google Ads MCP (`search` = GAQL). Business-agnostic.

## Principle: "can't fetch" = wrong METHOD, not an API limit
Google's API is comprehensive — the data is almost always reachable with the right query. Before you EVER
write "API can't see it / verify-in-UI", exhaust the method first: try a different **field name** (e.g.
`creative_quality_score` not `ad_relevance`), a different **resource** (`ad_group_ad_asset_view`,
`performance_max_placement_view`, `geographic_view`, `asset_group_asset`), **add `metrics.*`** (asset_group_asset
DOES return per-asset metrics — a text-only pull just looks empty), **drop the offending field and re-pull** (a
repeated-enum like `primary_status_reasons` failing to serialize ≠ the data is absent), or split the query. Only
mark verify-in-UI after several genuine attempts OR a confirmed older-MCP-version field gap (e.g.
`url_expansion_opt_out`). Treating a fetch failure as an API limit produces false "we can't know" findings.

**Confirmed exception (serializer, not method):** `ad_group_ad.ad.final_urls` is a protobuf
**RepeatedScalarContainer** the MCP JSON serializer cannot convert → the row errors regardless of query
shape. No field-name/resource workaround at the API layer. Treat campaign final URLs as verify-in-UI (PMax
uses URL expansion anyway). This is the rare genuine serializer limit — distinct from repeated-ENUM fields
(`primary_status_reasons`), which you fix by simply dropping that one field and re-pulling the rest.

## Date ranges
- Use **explicit `YYYY-MM-DD`** ranges with start AND end (the MCP rejects DURING literals like
  `LAST_90_DAYS`). Example: `segments.date >= '2026-05-27'` AND `segments.date <= '2026-06-26'`.
- `search_term_view` cannot use a 90-day window — keep search-term pulls to ≤30 days or explicit dates.

## Known field incompatibilities
| Resource | Field | Fix |
|----------|-------|-----|
| `search_term_view` | `campaign.status`, `ad_group.status` | Filter status in the application layer, not GAQL |
| `conversion_action` | `conversion_action.type` | Some MCPs reject it — omit if you get a field error |
| `campaign_criterion` | `campaign_criterion.type` | Same — omit; infer type from which sub-fields are populated |
| `custom_conversion_goal` | `custom_conversion_goal.conversion_actions` (repeated) | Fails to serialize via some MCPs — pull `id`/`name`/`status` only, resolve members separately |
| `campaign_search_term_insight` | (whole resource) | REQUIRES `campaign_search_term_insight.campaign_id = <one id>` in WHERE — can't query account-wide. Loop per active PMax/Search campaign. Returns category_label + conv/value, NOT per-term cost (so PMax "waste" = irrelevant categories with clicks but no conversions, not the >$10/0-conv rule). search_term_view does NOT contain PMax terms — use this insight for PMax/Demand Gen. |
| `asset_group_signal` | `audience_signal` | Use `resource_name` instead |
| `campaign` | `campaign.primary_status_reasons` (repeated enum) | Fails to serialize via some MCPs (RepeatedScalarContainer). `campaign.primary_status` (scalar: 2=ELIGIBLE, 8=LIMITED, 3=PAUSED…) works — but the REASON for LIMITED needs the UI or `bidding_strategy_system_status`. |
| `campaign` | `campaign.url_expansion_opt_out`, `campaign.asset_automation_settings` | UNRECOGNIZED on older MCP API versions → verify-in-UI (Final URL Expansion, text customization). `campaign.brand_guidelines_enabled` (bool) DOES read. |
| `campaign` | `asset_group_asset.performance_label` | UNRECOGNIZED on older MCP versions → fall back to per-asset metrics / structural analysis. |
| `asset_group_signal` | `asset_group_signal.type` | Enum rejected on some MCPs → drop it; infer: row with `asset_group_signal.search_theme.text` = a search theme, row with `asset_group_signal.audience.audience` = an audience signal. **Scope to ENABLED asset groups** (paused AGs still return signals). |
| `change_event` | start date >30 days | `START_DATE_TOO_OLD` — `change_event.change_date_time` can't be older than **today−30 days** (a date constraint, NOT absence). Use `>= today-30`, `LIMIT ≤ 10000`. Resource types: 2 AD · 3 AD_GROUP · 4 AD_GROUP_CRITERION · 5 CAMPAIGN · 6 CAMPAIGN_BUDGET · 7 CAMPAIGN_CRITERION. |
| `campaign` | `segments.conversion_lag_bucket` | **Works** — buckets 2=<1d · 3=1-2d · 4=2-3d · 5=3-4d · 6=4-5d · 7=5-6d · 8=6-7d · 9+=beyond 7d. Use for the "can I trust short-window ROAS?" gate. |
| `shopping_performance_view` | (product perf) | **Works** for product-level Shopping/PMax performance — `segments.product_item_id` + `segments.product_title` + metrics, scoped to active campaigns. This is the D14 "which product burns / converts" pull (no Merchant access needed). Merchant FEED health (OOS/disapproved/GTIN) needs a Google Merchant MCP — a Meta *catalog* MCP is NOT Google Merchant. |

## Channel, device & settings signals that DO work
`segments.ad_network_type` segments PMax by channel (2 Search · 3 SP · 4 Display · 8 YouTube · 11 Gmail · 12
Discover · 13 Maps; only ≥2026-06-01, else 7=MIXED). `segments.device` works (2 Mobile · 3 Tablet · 4 Desktop ·
5 Connected TV · 6 Other). `bidding_strategy_system_status` (2=ENABLED, 11=LIMITED_BY_DATA, 12=LIMITED_BY_BUDGET,
15=LIMITED_BY_INVENTORY…) and `campaign.brand_guidelines_enabled` read fine. `performance_max_placement_view`
returns impressions ONLY (no cost/conv).

## Asset & extension TEXT both pull — do NOT report them as "verify in UI"
- **PMax asset text + per-asset metrics:** `asset_group_asset` returns `asset.text_asset.text` AND
  `metrics.cost_micros`/`conversions`/`clicks` per asset — that's how "this headline spent $X at 0 conv"
  surfaces. A counts-only or text-only pull just *looks* empty. (Only `asset_group_asset.performance_label`
  is UNRECOGNIZED on some MCP versions.)
- **Search RSA text:** `ad_group_ad.ad.responsive_search_ad.headlines` is a RepeatedComposite the serializer
  can't return — but the RSA asset text + metrics ARE reachable via **`ad_group_ad_asset_view`** (per-asset
  rows). Use that; don't fall back to "verify in UI".
- **Extension text:** the sitelink/callout/snippet/price verbatim text reads from the `asset` resource
  (`asset.sitelink_asset.link_text`, `asset.callout_asset.callout_text`,
  `asset.structured_snippet_asset.values`, `asset.price_asset.*`) — join from `campaign_asset` by asset id.
  A `campaign_asset.field_type`-only pull gives counts; add the asset text for the real extensions.
| `campaign_shared_set` / `shared_set` | `shared_set.type` | Rejected by some MCPs — omit it; infer list purpose from `shared_set.name` |

## Settings & measurement fields — what READS vs what is genuinely UI/tag-side (empirically verified 2026-06-28)
These were once mislabeled "verify in UI" but DO read via GAQL — pull them, don't punt:
- **Location targeting type (Presence vs Interest)** — `campaign.geo_target_type_setting.positive_geo_target_type`
  (7 = PRESENCE_OR_INTEREST, 5 = PRESENCE) + `.negative_geo_target_type`. Positive = PRESENCE_OR_INTEREST is a
  real leak finding (serves users merely *interested* in the geo) → recommend Presence-only.
- **Enhanced Conversions** — `customer.conversion_tracking_setting.enhanced_conversions_for_leads_enabled` +
  `.accepted_customer_data_terms` (customer-level is authoritative; conversion_action-level EC fails as a
  RepeatedComposite — don't use it).
- **Final URLs / landing pages** — `landing_page_view.unexpanded_final_url` and
  `expanded_landing_page_view.expanded_final_url` (+ `metrics.*`, explicit date range). Use these — NOT
  `ad_group_ad.ad.final_urls` (RepeatedScalar serializer block).
- **RSA headline/description text + per-asset metrics** — `ad_group_ad_asset_view` (`.field_type` 2=headline /
  3=description, `asset.text_asset.text`, `metrics.*`, `.performance_label` reads for SEARCH).
- **Placement exclusions** — `campaign_criterion.placement.url` + `campaign_criterion.negative=true` (drop `.type`).

**Genuinely NOT readable on this MCP/API version (confirmed, every variant tried — record as verify-in-UI):**
`campaign.url_expansion_opt_out` / `final_url_expansion_opt_out` (FUE toggle) → UNRECOGNIZED;
`campaign.asset_automation_settings` → RepeatedComposite/PROHIBITED, `automatically_created_assets_setting` →
UNRECOGNIZED; `customer.content_label_exclusions` (content suitability) → UNRECOGNIZED;
`asset_group_asset.performance_label` (PMax) → UNRECOGNIZED (substitute: `asset_group.ad_strength` + per-asset
cost/conv from `asset_group_asset`).

**Tag-side by DESIGN — never in the Ads API (don't keep retrying; verify in GTM / Google Tag Diagnostics):**
Consent Mode v2 and server-side/CAPI are website tag configuration, not Ads entities. `accepted_customer_data_terms=true`
is a prerequisite signal but not proof CAPI is live. State this as "tag-side, verify in GTM" — it is NOT a pull failure.

## Negatives live in TWO places — pull BOTH (GUARD-2)
`campaign_criterion (negative=true)` is only campaign-level negatives. Shared negative LISTS (brand block,
cross-brand block, location block, account-level) are separate: `campaign_shared_set` (which list attaches to
which campaign; `campaign_shared_set.status` 2=ENABLED, 3=REMOVED) → `shared_criterion`
(`shared_criterion.keyword.text` + `.match_type`, filter `shared_set.id = <one>`). A PMax/Search **brand
exclusion is most often a shared negative list**, so a `campaign_criterion`-only pull reports "no brand
exclusion / no negatives" when coverage is actually extensive. Never decide G07/G14/G-PM5/G-PM6 without
`shared_criterion`.

## PMax Brand exclusions = a THIRD place, separate from both negatives above
The PMax "Brand exclusions" setting is stored as `campaign_criterion` with `negative=true` and a populated
`campaign_criterion.brand_list.shared_set` — and its **`keyword.text` is EMPTY**. A pull that only selects
`campaign_criterion.keyword.text` returns these rows blank and drops them, so you'll wrongly report "no brand
exclusion" even when it's set. To read them: select `campaign_criterion.brand_list.shared_set` +
`campaign_criterion.negative` (filter `campaign_criterion.brand_list.shared_set IS NOT NULL`), then resolve
`shared_set.name` (the brand list's name, e.g. the own brand). Brand exclusions match by brand ENTITY (Google's brand
DB), more robust than keyword negatives — accounts often run BOTH. So brand coverage = THREE sources:
campaign-level negatives + shared negative lists + brand-list exclusions. Merge all three before flagging.

## Keyword deduplication
`keyword_view` + `segments.date` returns one row per keyword per day (× match types). Deduplicate by
`(ad_group_id + keyword_text + match_type)` and aggregate metrics, or drop `segments.date` to dedup at
source. All keyword-dependent checks depend on correct unique counts.

## Filter scope — ENABLED **and live in the window**
Audit ENABLED resources: `campaign.status = 'ENABLED'` (not `!= 'REMOVED'`, which keeps PAUSED). But ENABLED
status alone is NOT enough — build the **active campaign set = ENABLED + impressions > 0 in the audit
window** (pull campaign metrics over the window, keep impressions>0 app-side), and scope everything to it.

**Entity `status = ENABLED` ≠ campaign is live.** A campaign turned off years ago can still contain ENABLED
asset groups / ad groups, so `asset_group.status = 'ENABLED'` returns assets from long-dead campaigns. Always
gate child resources on the parent being in the active set: filter `campaign.id IN (...active ids...)`, or
pull the child WITH `segments.date` + metrics over the window and drop zero-impression rows (metrics can't go
in a GAQL WHERE). Never let a dormant campaign's stale assets into the audit. This is GUARD-4 + scope in
practice.

## Legacy BMM heuristic
Google kept `match_type = 'BROAD'` after stripping '+' in 2021. True intentional broad is ALWAYS paired
with Smart Bidding (tCPA/tROAS/Maximize). BROAD + Manual CPC = legacy BMM (behaves like phrase) — don't
flag it as risky broad match.

## Error handling = G-SYS1 diagnostic
Track which fetches failed and why. Report failed sources + which checks were skipped. Never silently
skip a check, and never read "no rows" as "absent" without a completeness proof (GUARD-6).
