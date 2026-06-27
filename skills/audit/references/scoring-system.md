# Google Ads audit scoring

Weighted, severity-based scoring. Business-agnostic.

## Formula
```
Score = Σ(C_pass × W_sev × W_cat) / Σ(C_total × W_sev × W_cat) × 100
```
- `C_pass`: PASS = 1, WARNING = 0.5, FAIL = 0, N/A = excluded from the denominator.
- `W_sev`: severity multiplier. `W_cat`: category weight.

## Severity multipliers
| Severity | Multiplier | Meaning |
|----------|-----------|---------|
| Critical | 5.0 | Immediate revenue/data-loss risk. Fix now. |
| High | 3.0 | Significant performance drag. Fix within 7 days. |
| Medium | 1.5 | Optimization opportunity. Fix within 30 days. |
| Low | 0.5 | Best practice, minor impact. |

## Category weights (Google Ads)
| Category | Weight | Rationale |
|----------|--------|-----------|
| Conversion Tracking | 25% | Foundation; broken tracking invalidates everything downstream |
| Wasted Spend / Negatives | 20% | Direct money leak |
| Account Structure | 15% | Campaign organization, brand/non-brand separation |
| Keywords & Quality Score | 15% | QS as diagnostic; keyword-ad alignment |
| Ads & Assets | 15% | RSA strength, PMax/AI Max/Demand Gen assets |
| Settings & Targeting | 10% | Bidding, location, network, pacing |

## Grading
| Grade | Score | Label |
|-------|-------|-------|
| A | 90-100 | Excellent — minor optimizations only |
| B | 75-89 | Good — some opportunities |
| C | 60-74 | Needs improvement |
| D | 40-59 | Poor |
| F | <40 | Critical — urgent intervention |

(Bands are intentionally wide; ad-account health skews low, so 75+ is genuinely well-managed.)

## Quick Wins
Flag as a Quick Win if severity is Critical/High AND estimated remediation < 15 min. Sort by
severity × estimated impact, descending. Examples: enable Enhanced Conversions; add a shared negative
list; fix location targeting to "Presence".

## Unverified ≠ FAIL
Items the API/MCP cannot observe (Enhanced Conversions recording state, Consent Mode mode, gtag on-page
firing) are NOT scored as FAIL. Exclude them and mark "verify in UI", then state the ceiling if confirmed.
A score depressed by unverifiable items is not breakage — say so in the ledger.
