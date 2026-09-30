# Scoring and limit methodology

## Industry-relative financial score

The benchmark snapshot contains NYU Stern's January 2026 sector ratios for US-listed companies. The analyst selects the relevant industry. The score compares four measures:

| Metric | Formula | Direction in this policy | Weight |
|---|---|---|---:|
| Gross margin | Gross profit / revenue | Higher | 25% |
| Net margin | Net income attributable to parent / revenue | Higher | 35% |
| Receivables / sales | Year-end net receivables / annual revenue | Lower | 25% |
| Inventory / sales | Year-end inventory / annual revenue | Lower | 15% |

For each metric:

```text
scale = max(abs(industry benchmark), 0.01)
metric score = clip(50 + direction * 50 * (company ratio - benchmark) / scale, 0, 100)
financial score = sum(metric score * metric weight)
```

Direction is +1 for higher-better and -1 for lower-better. Ratios are decimals, so 0.01 means one percentage point. The scale floor makes zero and negative benchmark margins usable without dividing by zero or reversing the direction. A company matching each benchmark scores 50. This is a policy transformation, not an observed percentile or a probability of default.

The weighting gives 60% to profitability and 40% to working-capital efficiency. Gross and net margin overlap. Inventory and receivables can reflect business-model differences, seasonality, or deliberate investment. The formula requires analyst review and is not a validated universal credit model.

## Score-to-percentage schedule

| Score | Tier | Cash | Working capital | Tangible net worth |
|---|---|---:|---:|---:|
| 80-100 | 1 | 20% | 10% | 5% |
| 60 to below 80 | 2 | 15% | 7.5% | 3% |
| 40 to below 60 | 3 | 10% | 5% | 2% |
| Below 40 | 4 | 5% | 2.5% | 1% |

These percentages are an explicit example policy. They are not published industry standards, bank approval thresholds, or estimates fitted to defaults. The analyst chooses the basis; the tool does not automatically take the lowest of cash, WC, and TNW.

```text
Cash basis = reported cash and cash equivalents
WC basis = current assets - current liabilities
TNW basis = total equity - goodwill - other net intangible assets
Selected financial cap = max(selected basis, 0) * tier percentage for that basis
```

Cash restrictions and accessibility require review. TNW requires reconciled goodwill and all other net intangible assets; absent disclosures are not zero. Consolidated equity includes the consolidated ownership basis and does not establish a subsidiary guarantee. Negative WC or TNW produces zero capacity for that selected basis, not an automatic switch to another.

## Other financial checks

The memo reports current ratio, liabilities/assets, equity/assets, annual CFO/current liabilities, annual CFO/revenue, and working capital. These are absolute financial diagnostics, not fabricated industry benchmarks. Liabilities are not described as interest-bearing debt, CFO/current liabilities is not DSCR, and equity is not called TNW before intangible deductions.

Required data must be finite, sourced, currency-consistent, annual, and available by the analysis date. Balance sheets must reconcile within 0.5% of assets. Nonpositive equity or operating cash flow, stale statements, and overdue balances beyond the configured trigger request manual underwriting without an automatic proposal.

## Commercial and portfolio constraints

```text
Trading need = annual supplier sales to this customer / 365
             * (payment terms + collection buffer) * peak multiplier
Total scenario limit = round down(min(trading need, selected financial cap,
  single-customer cap, group cap less other group exposure,
  portfolio budget * concentration share, remaining portfolio allocation), increment)
Final proposal = min(base scenario limit, stress scenario limit)
Available for new orders = max(final proposal - receivables - committed unbilled orders, 0)
```

Supplier sales are distinct from the customer's own revenue. Other group exposure excludes this customer. Remaining portfolio allocation also excludes this customer's allocation to avoid double counting. The tool does not cancel orders or change customer accounts.

## Stress sensitivity

Default haircuts are 20% of cash, 15% of current assets, and 20% of equity, with 15 additional collection days. Goodwill and other intangibles remain unchanged for the stressed TNW deduction. The base industry score and percentages remain fixed: the stress tests balance capacity, not a complete forecast income statement. The separate 30% CFO sensitivity is reported in diagnostic ratios; it is not a replacement for the analyst's selected basis.

These are independent sensitivities, not accounting entries or a balanced forecast. Longer collection time may increase trading need, but the final proposal cannot exceed the base limit.

## Coverage and professional context

The catalog contains 94 industry groups plus two aggregate rows. Eighty industries use the general scorecard; fourteen financial and real-estate groups require specialist treatment. A minimum of ten firms and complete metrics are needed. Coverage is not a claim that one formula is appropriate for every company in those industries.

[OCC commercial credit guidance](https://www.occ.treas.gov/topics/supervision-and-examination/credit/commercial-credit/index-commercial-credit.html) and [S&P's corporate methodology](https://spratings.prod.ratings.spglobal.com/ratings/en/regulatory/article/-/view/type/HTML/id/3415681) provide broader professional context. This project does not implement or claim certification under either framework. In particular, it does not replace analysis of adjusted debt, debt service, liquidity access, business risk, or management. Industry metrics alone cannot establish an approved credit limit.
