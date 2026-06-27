# Vertical defaults — smart presets for setup

Generic starting points the `setup` interview offers per vertical. Always confirm with the user;
these are defaults, not facts. Business-agnostic and safe to publish.

## ecommerce
- Primary conversion: `purchase` (value tracking ON, count = one).
- Bidding ramp: `maxconv-value-then-troas` (no target during learning, then Target ROAS).
- Conversion window: 30-day click, 1-day view.
- Campaign mix priority: PMax/Shopping -> Branded Search -> Search -> Demand Gen.
- Watch: feed quality, AOV for forecasting, margin tiers (house brand vs distributed).

## leadgen
- Primary conversion: `lead` / `contact` (count = one to avoid form-spam inflation).
- Bidding ramp: `maxconv-then-tcpa`.
- Campaign mix priority: Search -> Branded Search -> Demand Gen.
- Watch: lead quality (offline conversion import), not just lead volume.

## local
- Primary conversion: calls, direction requests, form leads.
- Add location assets + radius targeting; Local/PMax for store visits where eligible.
- Watch: NAP consistency, store-visit conversions, call tracking.

## saas
- Primary conversion: `signup` / trial-start (value via predicted LTV if available).
- Bidding ramp: `maxconv-then-tcpa`, move to tROAS once value signals mature.
- Campaign mix priority: Branded Search (defend) -> Search (non-brand) -> Demand Gen.
- Watch: trial-to-paid downstream conversion; enhanced/offline conversions.

## b2b-services
- Primary conversion: qualified lead / consultation request.
- Longer consideration window; offline conversion import strongly recommended.
- Watch: small conversion volume -> consolidate campaigns; avoid over-segmenting.

## Common minimum-budget guidance (for `plan`)
- Each campaign needs enough conversions to exit the learning phase (~15-30/month per asset group/ad group).
- With a small budget, run fewer campaigns/asset groups rather than starving many.
