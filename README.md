# Corporate Credit Analyzer

**How much trade credit can we offer a corporate customer, and what would make us change that limit?**

This project turns annual financial statements and a proposed trading relationship into a credit memo. It scores financial performance against the selected industry, maps the score to configurable percentages, and lets the analyst choose **cash, working capital (WC), or tangible net worth (TNW)** as the credit-limit basis. The memo separates the total proposed limit from the amount still available for new orders.

The included example uses **real 2025 and 2024 Grainger financial figures**. Sales to the customer, payment terms, receivables, and policy caps are hypothetical. The result is a worked example of a policy, not a recommendation to extend credit to Grainger.

## What is implemented

- Annual financial statement validation, including currency, units, dates, missing data, and balance-sheet reconciliation.
- January 2026 US benchmarks for 94 industry groups, sourced from Aswath Damodaran at NYU Stern. Eighty groups use the general scorecard; 14 financial/real-estate groups route to specialist review. Small or incomplete benchmark groups also require review.
- A 0–100 industry-relative financial score with a visible contribution from every metric, plus analyst selection of cash, WC, or TNW.
- Liquidity, working capital, liabilities-to-assets, equity-to-assets, and operating cash-flow ratios, with annual comparisons.
- A transparent limit calculation constrained by trading need, financial capacity, group exposure, and portfolio concentration.
- Downside sensitivities for current assets, equity, cash flow, and collection delays.
- An HTML credit memo and JSON analysis with input hashes, sources, and a policy snapshot.
- An optional SEC Company Facts adapter that keeps the selected annual filing, currency, and reporting period together.
- Automated tests and GitHub Actions.

The core runs on Python 3.12 using only the standard library. No API subscription, machine-learning model, or external package installation is needed for the included example.

## Run the example

```powershell
python -m unittest -v
python analyze.py --statements example_statements.json --terms example_terms.json --as-of 2026-09-30 --output runs/grainger
```

Open `runs/grainger/credit_memo.html`. Use a new output directory for each run so previous decisions remain available.

Select a different basis with `--basis cash` or `--basis tangible_net_worth`; the example defaults to working capital. Change the industry with `--industry "Retail (Distributors)"`. Industry selection is an analyst classification, not an automatic assertion of peer equivalence.

The example's industry-relative score is **64.8/100**, corresponding to the illustrative Tier 2 schedule: 15% of cash, 7.5% of WC, or 3% of TNW. These give financial capacity caps of $87.75 million, $265.8 million, and $105.48 million respectively. Trading need and supplier policy constrain the final proposal below those amounts.

With the included assumptions, the calculation produces:

| Output | USD |
|---|---:|
| Estimated base trading need before rounding | 2,465,753 |
| Proposed total limit after policy, stress, and rounding | 2,465,000 |
| Existing receivables plus committed unbilled orders | 1,000,000 |
| Available for new orders | 1,465,000 |

The base case is constrained by trading need. Under the collection-delay sensitivity, the $2.5 million portfolio concentration cap becomes binding. The final proposal is the lower of the base and stressed limits, so a longer collection delay cannot automatically increase the proposed limit.

## How the limit works

Trading need is estimated as:

```text
Annual sales to this customer / 365
    × (payment terms + collection buffer)
    × peak exposure multiplier
```

This uses the supplier's sales to the customer, not the customer's reported revenue.

The financial cap is the percentage assigned by the score tier multiplied by the analyst's selected balance. Cash means reported cash and cash equivalents, subject to review of restrictions. WC is current assets less current liabilities. TNW is equity less goodwill and other net intangible assets. Missing intangible disclosures are not assumed to be zero. The tool shows all three alternatives but does not choose the smallest financial basis for the analyst.

The final total limit is the lowest of trading need, the selected financial cap, the single-customer cap, remaining group capacity, the concentration cap, and the available portfolio budget. It is rounded down.

Existing receivables and committed unbilled orders are then deducted to calculate remaining order capacity. Exposure belonging to other group companies reduces the group cap separately. The portfolio budget input must exclude the customer being assessed to avoid subtracting the same allocation twice.

All score weights and percentages live in `policy.json`. **The benchmarks are observed data; the scoring formula and credit percentages are illustrative policy choices, not empirically validated lending standards.** There is no universal standard percentage for every company and sector. The score is not a percentile, external rating, or probability of default. [METHODOLOGY.md](METHODOLOGY.md) describes the formulas and assumptions.

## Use another company

Start by copying the statement and commercial-input JSON files. Record a source for every financial figure and express all amounts in full currency units. Missing financials stay missing; do not enter zero unless the source actually reports zero.

The optional SEC adapter can fetch a US company's recent annual filing:

```powershell
$env:SEC_USER_AGENT = 'YourApp your-real-contact-address'
python fetch_sec.py --cik 277135 --as-of 2026-09-30 --output data/grainger_sec
python analyze.py --statements data/grainger_sec/statements.json --terms example_terms.json --as-of 2026-09-30 --output runs/grainger_sec
```

Use an actual application/contact identifier. The adapter stops if SEC blocks access; it does not circumvent the block. SEC live retrieval was blocked in the development environment, so its normalization logic has fixture tests but its live download path has not been verified here. The included real-data example comes directly from Grainger's investor-relations release instead.

See [WALKTHROUGH.md](WALKTHROUGH.md) for the analyst workflow and [DATA_SOURCES.md](DATA_SOURCES.md) for the exact financial source and normalization.

## What the output does not establish

A limit needs more than annual statements. Before approval, an analyst must confirm the contracting entity, current interim results, payment experience, disputes, existing commitments, and the supplier's actual risk appetite. Consolidated group financials do not establish that a subsidiary can use the parent's resources.

The general scorecard covers nonfinancial corporate industries and unsecured trade credit. Financial institutions and real-estate groups are visible in the benchmark catalog but require specialist scorecards; this version does not claim universal industry underwriting. Revolving loans, collateral valuation, guarantees, and credit insurance also require separate treatment. The sensitivities are independent haircuts, not a balanced forecast or a default-loss model.

Missing required figures, stale statements, nonpositive operating cash flow or equity, and material overdue balances route the case to manual review without an automatic numerical proposal. This is decision-support software; it does not approve customers or change account limits.

## Verification

The worked financial example has been executed locally. Tests cover limit arithmetic, exposure deductions, hard caps, stress behavior, data validation, source consistency, and output provenance. See [VALIDATION.md](VALIDATION.md) for the verification record.
