# Financial data and assumptions

## Included real example

Source: [W.W. Grainger, Inc. — fourth-quarter and full-year 2025 results, published February 3, 2026](https://invest.grainger.com/investor-news/news-details/2026/GRAINGER-REPORTS-RESULTS-FOR-THE-FOURTH-QUARTER-AND-FULL-YEAR-2025/default.aspx).

The example transcribes selected numerical facts from the release's condensed consolidated statements of earnings, balance sheets, and cash flows for 2025 and 2024. The release labels the financial tables unaudited. It is not presented here as an audited annual report.

Every selected amount is reported in USD millions and multiplied by 1,000,000 exactly once. Annual revenue and operating cash flow use the twelve-month columns, not fourth-quarter columns. Balance-sheet figures use December 31. Capital expenditure is stored as a positive outflow magnitude; the release presents it as a negative investing cash flow. It is included for traceability but not used in the current limit formula.

Total liabilities are derived as total assets less total shareholders' equity, including the consolidated equity basis reported in the source. Each derived field identifies that calculation. Reported customer revenue is not used as the supplier's forecast sales to that customer.

`create_example.py` records the small transcription explicitly and regenerates `example_statements.json`. The JSON retains a source reference, original million-unit value, and normalization note per field. Review the source rather than treating a checksum as proof of financial correctness.

## Industry benchmark data

`industry_benchmarks.json` contains numerical sector ratios retrieved from NYU Stern's [margin table](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/margin.html) and [working-capital table](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wcdata.html). Both identify January 2026 as their analysis vintage. The import records source hashes and retrieval date, checks matching sectors and firm counts, and retains reported ratios rather than inventing missing values.

The snapshot includes 94 industries and two aggregate market rows. Aggregate rows cannot serve as industry peers. Fourteen financial and real-estate groups need specialist treatment. The general formula also requires at least ten firms and complete benchmark metrics. US-listed-company benchmarks are not automatically appropriate for private companies, other countries, or narrower subsectors.

These are published sector ratios, not a peer-level distribution. A score of 80 is not the 80th percentile. The snapshot's conservative available-from date is its verification date, September 30, 2026; the January vintage does not establish a precise historical publication date.

Refresh to a new file with `python refresh_benchmarks.py --vintage 2026-01 --output benchmarks_new.json`, review changes, then select it with `--benchmarks`. When the publisher updates the tables, supply the new matching vintage. Do not silently relabel old data as current.

The example uses reported gross profit and net earnings attributable to Grainger for gross/net margin. Retail (Distributors) is a demonstration analyst classification. Business mix and accounting differences require review. Gross and net margins overlap, and lower inventory or receivables relative to sales is not always evidence of lower default risk.

## Hypothetical inputs

`example_terms.json` describes an invented trading relationship used only to demonstrate the calculation: forecast annual sales, terms, collection buffer, receivables, committed orders, group exposure, and portfolio limits. Those values are not facts about Grainger's actual customers, suppliers, borrowing capacity, or payment performance.

`policy.json` is an illustrative policy, not an empirical estimate, agency methodology, or approved credit policy.

## Optional SEC data

The [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) describes Company Facts and submissions data. The [developer guidelines](https://www.sec.gov/about/developer-resources) describe fair access. The client requests sequentially, with a pause between requests, bounded retry for rate limiting, and immediate stop on access denial.

The adapter selects one recent 10-K available by the analysis date. Facts must share that accession, annual start/end dates where relevant, and USD units. It never joins arbitrary latest facts from different filings. Missing concepts remain absent; custom company tags and IFRS are not mapped. An amended annual filing triggers manual reconciliation. Archived filing history is not downloaded automatically.

Live SEC access was blocked in the development environment. The checked-in financial example is obtained from the company-published release, not from a bypass or an unofficial dataset mirror. The SEC normalization tests use explicitly artificial records.
