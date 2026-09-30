# Analyst walkthrough

1. Confirm the contracting legal entity and sector. A parent's consolidated statements may not support a subsidiary's obligations.
2. Enter annual financials with source references and full currency units. Supply gross profit, parent-attributable net income, receivables, and inventory for the industry score, alongside the basic financial statements.
3. Select the industry. Review the benchmark vintage, region, firm count, and business mix. Specialist sectors and incomplete benchmarks are routed to review, not silently assigned a substitute industry.
4. Choose cash, working capital, or tangible net worth using `--basis cash`, `--basis working_capital`, or `--basis tangible_net_worth`. Check cash restrictions. Reconcile goodwill and all other net intangible assets before selecting TNW.
5. Enter forecast supplier sales, invoice terms, collection buffer, existing receivables, committed unbilled orders, group exposure, and portfolio caps. Do not count an invoiced order again as unbilled.
6. Run the memo using the README command. The output displays the industry score, each metric's contribution, the percentage schedule, all three financial basis calculations, and the selected basis.
7. Inspect the binding cap and stress sensitivity. Financial capacity may exceed the supplier's trading need or portfolio allocation. Review score weights and percentages as policy assumptions, not established lending standards.
8. Review current interim results, payment behavior, disputes, guarantees, restrictions, and policy exceptions before making an actual decision. Save the memo, sources, and approved rationale separately. This tool does not approve or update accounts.

The included case uses September 30, 2026 as its analysis date. It demonstrates the annual-statement workflow and does not claim to incorporate every item of information then available about the company.
