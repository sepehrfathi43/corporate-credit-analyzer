"""Build a reproducible credit memo from statements and commercial inputs."""
import argparse
import html
from pathlib import Path
from credit import analyze, read, write, sha


def render(result):
    def esc(value):
        return html.escape(str(value))
    def amount(value):
        return 'Not available; review required for this calculation' if value is None else f"{result['currency']} {value:,.0f}"
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>Corporate credit memo</title><body>',
             '<h1>' + esc(result['company']) + ' — trade credit memo</h1>',
             '<p>Analysis date: ' + esc(result['as_of']) + '; annual period end: ' + esc(result['period_end']) + '</p>',
             '<p><strong>' + esc(result['note']) + '</strong></p>',
             '<p>Financials: ' + esc(result['financial_data_kind']) + '. Commercial inputs: ' + esc(result['commercial_input_kind']) + '.</p>',
             '<h2>Proposed total limit: ' + esc(amount(result['proposed_total_limit'])) + '</h2>',
             '<p>Available for new orders: ' + esc(amount(result['available_for_new_orders'])) + '</p>',
             '<h2>Review notes</h2><ul>']
    parts += ['<li>' + esc(reason) + '</li>' for reason in result['review_reasons']]
    parts.append('</ul>')
    score = result.get('industry_scorecard')
    if score:
        parts.append('<h2>Industry-relative financial score: ' + esc(f"{score['score']:.1f}/100") + '</h2><p>' +
                     esc(score['industry']) + ' | ' + esc(score['provider']) + ' | ' + esc(score['vintage']) +
                     ' | ' + esc(score['firms']) + ' firms</p><p>' + esc(score['interpretation']) +
                     '</p><table border="1"><tr><th>Metric</th><th>Company</th><th>Industry</th><th>Weight</th><th>Score</th><th>Weighted points</th></tr>')
        for row in score['components']:
            parts.append('<tr><td>' + esc(row['metric']) + '</td><td>' + esc(f"{row['company_value']:.2%}") +
                         '</td><td>' + esc(f"{row['industry_value']:.2%}") + '</td><td>' + esc(f"{row['weight']:.0%}") +
                         '</td><td>' + esc(f"{row['score']:.1f}") + '</td><td>' + esc(f"{row['weighted_points']:.1f}") + '</td></tr>')
        parts.append('</table>')
    for scenario in ['base', 'stress']:
        item = result[scenario]
        if not item:
            continue
        parts.append('<h2>' + scenario.title() + ' financial limit bases</h2><p>Analyst selection: ' + esc(item['selected_basis']) +
                     '</p><table border="1"><tr><th>Basis</th><th>Balance</th><th>Policy percentage</th><th>Calculated limit</th></tr>')
        for basis, value in item['basis_values'].items():
            parts.append('<tr><td>' + esc(basis) + '</td><td>' + esc(amount(value)) + '</td><td>' +
                         esc(f"{item['percentages'][basis]:.2%}") + '</td><td>' + esc(amount(item['basis_limits'][basis])) + '</td></tr>')
        parts.append('</table>')
        parts.append('<h2>' + scenario.title() + ' case</h2><p>Policy band: ' + esc(item['band']) +
                     '; binding cap: ' + esc(', '.join(item['binding_caps'])) + '</p><table border="1"><tr><th>Cap</th><th>Amount</th></tr>')
        parts += ['<tr><td>' + esc(k) + '</td><td>' + esc(amount(v)) + '</td></tr>' for k, v in item['caps'].items()]
        parts.append('</table><h3>Ratios and balances</h3><ul>')
        parts += ['<li>' + esc(k) + ': ' + esc(f'{v:,.4f}') + '</li>' for k, v in item['ratios'].items()]
        parts.append('</ul>')
    parts.append('<h2>Annual comparison</h2><ul>')
    for historical in result.get('historical_ratios', []):
        parts.append('<li>' + esc(historical['period_end']) + ': ' + esc(historical['ratios'] or historical['review_reasons']) + '</li>')
    parts.append('</ul><h2>Financial source trail</h2><table border="1"><tr><th>Field</th><th>Value</th><th>Source</th></tr>')
    for key, fact in result['financials']['facts'].items():
        parts.append('<tr><td>' + esc(key) + '</td><td>' + esc(amount(fact.get('value'))) + '</td><td>' + esc(fact.get('source')) + '</td></tr>')
    parts.append('</table><p>Stress values are independent sensitivity haircuts, not a balanced forecast or an economic loss model.</p></body></html>')
    return '\n'.join(parts)


def run(statement_path, terms_path, policy_path, as_of, output, benchmark_path=None, basis=None, industry=None):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Use a new output directory to preserve the earlier memo')
    statement, terms, policy = read(statement_path), read(terms_path), read(policy_path)
    benchmark_path = benchmark_path or Path(__file__).with_name('industry_benchmarks.json')
    benchmarks = read(benchmark_path)
    if basis: terms['limit_basis'] = basis
    if industry: terms['industry'] = industry
    result = analyze(statement, terms, policy, as_of, benchmarks)
    result['input_sha256'] = {k: sha(p) for k, p in [('statements', statement_path), ('terms', terms_path), ('policy', policy_path)]}
    result['input_sha256']['benchmarks'] = sha(benchmark_path)
    result['analyst_overrides'] = {'basis': basis, 'industry': industry}
    output.mkdir(parents=True)
    write(output / 'analysis.json', result)
    write(output / 'policy_snapshot.json', policy)
    write(output / 'statements_snapshot.json', statement)
    write(output / 'terms_snapshot.json', terms)
    write(output / 'benchmarks_snapshot.json', benchmarks)
    (output / 'credit_memo.html').write_text(render(result), encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--statements', required=True)
    p.add_argument('--terms', required=True)
    p.add_argument('--policy', default='policy.json')
    p.add_argument('--as-of', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--benchmarks', default='industry_benchmarks.json')
    p.add_argument('--basis', choices=['cash', 'working_capital', 'tangible_net_worth'])
    p.add_argument('--industry', help='Exact industry name from the benchmark snapshot')
    a = p.parse_args()
    result = run(a.statements, a.terms, a.policy, a.as_of, a.output, a.benchmarks, a.basis, a.industry)
    print(result['status'], result['proposed_total_limit'])
