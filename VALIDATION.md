# Verification

The included Grainger example uses selected figures from the company's February 3, 2026 earnings release. The end-to-end analysis has been run against those figures with hypothetical commercial inputs.

Local environment: Windows, Python 3.12. No third-party packages required.

The test suite covers arithmetic, current and committed exposure, group caps, stress monotonicity of the final proposal, missing financials, currency and unit mismatches, stale and future information, negative cash flow, balance-sheet reconciliation, non-finite inputs, unsupported sectors, overdue review triggers, HTML escaping, artifact hashes, and SEC period/accession isolation.

Verification command: `python -m unittest -v`.

September 30, 2026 result: **26 tests passed**. Industry-specific checks cover benchmark equality producing a score of 50, weighted contribution reconciliation, negative benchmark margins, low sample counts, unsupported industries, selection of cash/WC/TNW, and missing intangible disclosures. The real-financial example produces a score of 64.8272 and a proposed USD 2,465,000 total limit under the hypothetical trading scenario.

The benchmark import was also executed against both live NYU Stern source tables. It found 94 industry groups and two aggregate market rows, with matched names and firm counts across sources. Eighty groups use the general scorecard; fourteen route to specialist review. Minimum-sample and missing-data rules can further restrict automated scoring. This does not establish suitability for every industry or country.

The live SEC download was blocked by SEC's access controls and is not claimed as verified. Normalization is tested with artificial API-shaped records. The published-financial example and hypothetical trading terms are kept distinct throughout the memo.

This verification establishes software behavior and reproducibility of the worked example. It does not establish predictive accuracy, default probability calibration, recoverability, policy suitability, or the appropriate credit limit for a real trading relationship.
