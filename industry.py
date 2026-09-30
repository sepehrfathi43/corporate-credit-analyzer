"""Explainable industry-relative score; weights and score-to-limit rates are policy."""
import datetime as dt

METRICS = {'gross_margin': ('gross_profit', 1), 'net_margin': ('net_income', 1),
           'receivables_sales': ('receivables', -1), 'inventory_sales': ('inventory', -1)}


def industry_score(values, industry, benchmarks, policy, as_of):
    from credit import number
    if industry not in benchmarks['industries']:
        raise ValueError('No benchmark for selected industry; do not silently substitute another sector')
    if as_of < dt.date.fromisoformat(benchmarks['available_from']):
        raise ValueError('Benchmark snapshot not established as available on this analysis date')
    vintage = dt.date.fromisoformat(benchmarks['vintage'] + '-01')
    if (as_of - vintage).days > policy['max_benchmark_age_days']:
        raise ValueError('Industry benchmark is stale; obtain a new documented snapshot')
    benchmark = benchmarks['industries'][industry]
    if benchmark.get('treatment', 'general_corporate') != 'general_corporate':
        raise ValueError('This sector requires a specialist scorecard; aggregate market rows are not industry peers')
    if number(benchmark['firms'], 'industry firms', 0) < policy['minimum_industry_firms']:
        raise ValueError('Insufficient firms in benchmark')
    weights = policy['industry_score_weights']
    if set(weights) != set(METRICS) or abs(sum(number(x, 'weight', 0) for x in weights.values()) - 1) > 1e-8:
        raise ValueError('All four metric weights are required and must sum to 1')
    contributions = []
    for metric, (field, direction) in METRICS.items():
        reference = number(benchmark[metric], 'industry ' + metric)
        value = number(values[field], field) / values['revenue']
        floor = number(policy['metric_scale_floors'][metric], 'metric_scale_floor', 0)
        if floor <= 0: raise ValueError('Metric scale floors must be positive')
        scale = max(abs(reference), floor)
        score = min(max(50 + direction * 50 * (value - reference) / scale, 0), 100)
        contributions.append({'metric': metric, 'company_value': value, 'industry_value': reference,
                              'direction': 'higher_better' if direction == 1 else 'lower_better',
                              'scale': scale, 'weight': weights[metric], 'score': score, 'weighted_points': score * weights[metric]})
    score = sum(row['weighted_points'] for row in contributions)
    bands = policy['score_limit_bands']
    thresholds = [number(b['minimum_score'], 'minimum_score', 0) for b in bands]
    if thresholds != sorted(set(thresholds), reverse=True) or thresholds[-1] != 0 or thresholds[0] > 100:
        raise ValueError('Score bands must be unique, descending, end at zero, and stay within [0,100]')
    for band in bands:
        for basis in ['cash', 'working_capital', 'tangible_net_worth']:
            if number(band['percentages'][basis], basis + ' percentage', 0) > 1:
                raise ValueError('Limit percentages must be within [0,1]')
    chosen = next(b for b in bands if score >= b['minimum_score'])
    return {'score': score, 'band': chosen['name'], 'percentages': chosen['percentages'], 'industry': industry,
            'firms': benchmark['firms'], 'provider': benchmarks['provider'], 'vintage': benchmarks['vintage'],
            'sources': benchmarks['sources'], 'components': contributions,
            'interpretation': '50 equals the published benchmark under this policy formula; not a percentile or default probability'}
