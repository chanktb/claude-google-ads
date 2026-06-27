# Forecasting & benchmarks

Reusable, business-agnostic reference for `plan`. Derive from real account data whenever it exists;
fall back to benchmark bands only for new accounts, and label them as estimates.

## Forecast math
```
clicks       = budget / CPC
conversions  = clicks × CVR
revenue      = conversions × AOV
ROAS         = revenue / spend
CPA          = spend / conversions
```
Always present a **band**, not a point estimate, and show the inputs (CPC, CVR, AOV, budget) so the user
can sanity-check. For expansion, pull CPC and CVR from the account's own last-30-90-day data. For a new
account, use the bands below and widen the range.

## Learning-volume minimums
- A campaign / asset group / ad group needs roughly **15-30 conversions/month** to exit the learning
  phase and let Smart Bidding work.
- Max campaigns/AGs a budget can feed ≈ (expected monthly conversions) / 20. With limited budget, run
  fewer well rather than starving many.
- Min spend rule of thumb: a campaign wants enough daily budget to produce a few conversions/day at its
  expected CPA. Below that, consolidate.

## Benchmark bands (NEW-account fallback only — wide, illustrative, confirm per vertical)
| Vertical | CVR (search) | Notes |
|----------|--------------|-------|
| ecommerce | 1.5-4% | AOV-driven; ROAS is the headline metric |
| leadgen | 3-8% | CPA-driven; lead quality matters more than volume |
| saas | 1-3% | trial/signup; long downstream conversion |
| local | 3-10% | calls/directions; high intent |
These are starting points, not facts. Prefer the account's own data, GA4, or industry data for the
specific niche/geo. Never present a benchmark forecast as a promise.

## Campaign-type roles (for the mix)
- **Branded Search** — cheap, high-IS defense of your own name; near-certain ROAS but limited volume.
- **Search (non-brand)** — intent capture; scales with budget but needs negatives + Smart Bidding.
- **PMax / Shopping** — ecommerce workhorse; broad reach across channels; needs feed + brand exclusion.
- **Demand Gen** — upper/mid funnel; reach and consideration; view-through caveats, no frequency cap.
Sequencing: defend (branded) and capture (PMax/search) before you scale demand (Demand Gen).
