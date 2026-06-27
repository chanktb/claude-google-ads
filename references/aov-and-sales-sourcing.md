# AOV & sales sourcing — do it from the store, not from Google Ads

Reusable, business-agnostic reference for `setup` (and `plan`). AOV drives forecasting, so it must be
derived correctly. The common shortcut — computing AOV from Google Ads conversion value — is WRONG for
new or low-spend accounts and is biased even for mature ones. Use this priority order.

## Priority order for AOV
1. **Store sales (best, works for new accounts too).** Pull orders/sales from the store connector or API.
   This is the only reliable source when Google Ads has little history.
2. **Google Ads attributed (cross-check / fallback only).** `conversions_value / conversions` for the
   primary purchase action over 30-90 days. Only meaningful with enough conversion volume; it reflects
   *Google-attributed* purchases, a biased subset. Never the sole source for a new account.
3. **Ask the user** when neither is reliable (brand-new store, no orders yet).

If both #1 and #2 are available, compute both and report the gap — a large divergence is itself a signal
(attribution, tracking, or channel-mix issue) worth surfacing.

## Filter store sales correctly — channel matters
AOV must reflect the **Online Store** channel only. Other channels distort it and are not what Google Ads
drives:
- **Exclude** draft orders, abandoned/unpaid, cancelled, and test orders.
- **Exclude** non-web channels: POS / in-store, TikTok Shop, marketplace (Amazon/eBay), social shops,
  manual/phone orders. **Match the channel your ads actually drive** (read `business.model` from context):
  for a B2C/retail store exclude wholesale/draft orders; for a wholesale store whose ads drive wholesale
  inquiries, INCLUDE those orders — they're the conversions you're optimizing for.
- Use a representative window (30-90 days); prefer **net sales** (after discounts and refunds), not gross.

### Shopify specifics
- Filter orders by sales channel / `source_name` to the online store (web). Channel apps (TikTok, POS,
  draft orders) carry their own source and must be dropped.
- Easiest path: an analytics/ShopifyQL query for **sales by channel, Online Store only**, then
  `net_sales / orders`. Or pull paid, non-draft web orders and average `current_total_price` net of refunds.

### WooCommerce specifics
- Orders with status `completed`/`processing`; exclude `draft`, `pending`, `cancelled`, `refunded`.
- If other channels feed Woo, filter them out the same way.

## Pull COMPLETELY — paginate or the count is wrong (silent failure)
A truncated pull is the most dangerous failure here because it **hides**: AOV can still look right while order
count and total sales are massively undercounted. (Seen in practice: a REST pull that stopped after ~2 pages
reported 385 orders / $40k where the real figure was ~3,000 orders / $360k in the same window — AOV was
fine, volume was off by ~8×, which then broke the Ads-vs-store value cross-check.)
- **Paginate to exhaustion** — follow `pageInfo.hasNextPage`/cursors (GraphQL) or `Link: rel="next"` (REST)
  until there are no more pages. Never trust a single page.
- **Sanity-check the magnitude:** the store's 30d revenue should be the same order of magnitude as GA4
  purchase revenue and at/above Google Ads' attributed value. If store revenue comes out *below* what Ads
  claims it drove, suspect the pull (pagination/channel/status filter) before suspecting the account.
- Prefer an aggregate analytics/ShopifyQL query (returns server-side totals, no client pagination to get
  wrong) over hand-rolled order iteration when you only need totals + AOV.

## Output for the context
Write `business.aov` as the **store online-store AOV**, and note the source + window. If you also have a
Google-Ads-attributed figure, keep it in a note for cross-reference, not as the primary value.
