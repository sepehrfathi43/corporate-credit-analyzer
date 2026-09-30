"""Deterministic trade-credit policy calculations; no automatic approvals."""
import copy
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from industry import industry_score


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value, name, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if minimum is not None and value < minimum:
        raise ValueError(f'{name} must be >= {minimum}')
    return value


REQUIRED = ['revenue', 'assets', 'liabilities', 'equity', 'current_assets',
            'current_liabilities', 'operating_cash_flow', 'gross_profit', 'net_income', 'receivables', 'inventory']
NONNEGATIVE = ['revenue', 'assets', 'liabilities', 'current_assets', 'current_liabilities', 'receivables', 'inventory']
TERM_FIELDS = ['annual_sales_to_customer', 'payment_terms_days', 'collection_buffer_days',
               'peak_exposure_multiplier', 'current_receivables', 'committed_unbilled_orders',
               'other_group_exposure', 'oldest_overdue_days', 'single_customer_cap', 'group_cap',
               'portfolio_limit_budget', 'max_customer_share', 'remaining_portfolio_budget_excluding_customer']


def validate_policy(policy):
    for k in ['rounding_increment', 'max_statement_age_days', 'max_overdue_days', 'max_benchmark_age_days', 'minimum_industry_firms']:
        if number(policy[k], k, 0) == 0:
            raise ValueError(f'{k} must be positive')
    for key in ['current_assets_haircut', 'equity_haircut', 'operating_cash_flow_haircut', 'cash_haircut']:
        if number(policy['stress'][key], key, 0) > 1:
            raise ValueError('Haircuts must be within [0,1]')
    number(policy['stress']['extra_collection_days'], 'extra_collection_days', 0)


def validate_statement(statement, as_of, policy):
    if statement['currency'] != policy['currency'] or statement['unit'] != 'currency_units':
        raise ValueError('Currency must match policy; financial values must be in full currency units')
    periods = statement['periods']
    if not periods:
        raise ValueError('No financial periods')
    ends = [p['end'] for p in periods]
    if len(set(ends)) != len(ends):
        raise ValueError('Duplicate period ends')
    current = max(periods, key=lambda p: p['end'])
    end, start = dt.date.fromisoformat(current['end']), dt.date.fromisoformat(current['start'])
    published = dt.date.fromisoformat(statement['published'])
    if not 330 <= (end - start).days <= 400:
        raise ValueError('Supply annual financials; quarterly or mixed-duration inputs are unsupported')
    if end > as_of or published > as_of or published < end:
        raise ValueError('Statement was not available on the requested analysis date')
    values, errors = {}, []
    for field in REQUIRED:
        entry = current['facts'].get(field)
        if not entry or entry.get('value') is None:
            errors.append('Missing required financial: ' + field)
            continue
        value = number(entry['value'], field, 0 if field in NONNEGATIVE else None)
        if not entry.get('source'):
            errors.append('Missing source for ' + field)
        values[field] = value
    for field in ['cash', 'goodwill', 'other_intangibles']:
        entry = current['facts'].get(field)
        if entry and entry.get('value') is not None:
            values[field] = number(entry['value'], field, 0)
            if not entry.get('source'):
                errors.append('Missing source for ' + field)
    if (as_of - end).days > policy['max_statement_age_days']:
        errors.append('Annual statement exceeds policy age limit')
    if statement.get('sector') != 'nonfinancial':
        errors.append('Financial institutions and unclassified sectors need a separate policy')
    if set(REQUIRED).issubset(values):
        tolerance = max(values['assets'] * 0.005, 1)
        if abs(values['assets'] - values['liabilities'] - values['equity']) > tolerance:
            errors.append('Balance sheet does not reconcile within 0.5% of assets')
        if values['current_assets'] > values['assets'] or values['current_liabilities'] > values['liabilities']:
            errors.append('Current balances exceed total balances')
        if values['assets'] <= 0 or values['current_liabilities'] <= 0 or values['revenue'] <= 0:
            errors.append('Positive assets, revenue and current liabilities are required for this policy')
        if values['equity'] <= 0 or values['operating_cash_flow'] <= 0:
            errors.append('Nonpositive equity or operating cash flow requires manual underwriting')
    return current, values, errors


def ratios(v):
    return {'current_ratio': v['current_assets'] / v['current_liabilities'],
            'liabilities_assets': v['liabilities'] / v['assets'],
            'cfo_current_liabilities': v['operating_cash_flow'] / v['current_liabilities'],
            'operating_cash_flow_margin': v['operating_cash_flow'] / v['revenue'],
            'working_capital': v['current_assets'] - v['current_liabilities'],
            'equity_assets': v['equity'] / v['assets']}


def scenario(values, terms, policy, score, stressed=False):
    v = copy.deepcopy(values)
    extra = 0
    if stressed:
        for field in ['current_assets', 'equity', 'operating_cash_flow']:
            v[field] *= 1 - policy['stress'][field + '_haircut']
        if 'cash' in v:
            v['cash'] *= 1 - policy['stress']['cash_haircut']
        # Partial sensitivity inputs are NOT presented as a balanced forecast balance sheet.
        extra = policy['stress']['extra_collection_days']
    r = ratios(v)
    bases = {'cash': v.get('cash'), 'working_capital': v['current_assets'] - v['current_liabilities'],
             'tangible_net_worth': v['equity'] - v['goodwill'] - v['other_intangibles']
             if 'goodwill' in v and 'other_intangibles' in v else None}
    candidates = {basis: None if value is None else max(value, 0) * score['percentages'][basis]
                  for basis, value in bases.items()}
    selected = terms['limit_basis']
    if selected in candidates and candidates[selected] is not None:
        financial_cap = candidates[selected]
    else:
        raise ValueError('Selected limit basis is unsupported or lacks required disclosures')
    demand = terms['annual_sales_to_customer'] / 365 * (
        terms['payment_terms_days'] + terms['collection_buffer_days'] + extra) * terms['peak_exposure_multiplier']
    caps = {
        'sales_and_terms_need': demand,
        'selected_financial_basis_cap': financial_cap,
        'single_customer_policy_cap': terms['single_customer_cap'],
        'group_capacity_after_other_exposure': max(terms['group_cap'] - terms['other_group_exposure'], 0),
        'portfolio_concentration_cap': terms['portfolio_limit_budget'] * terms['max_customer_share'],
        'remaining_portfolio_budget': terms['remaining_portfolio_budget_excluding_customer']
    }
    lowest = min(caps.values())
    increment = policy['rounding_increment']
    return {'ratios': r, 'industry_score': score['score'], 'band': score['band'], 'percentages': score['percentages'],
            'basis_values': bases, 'basis_limits': candidates, 'selected_basis': selected, 'caps': caps,
            'binding_caps': [k for k, v in caps.items() if abs(v - lowest) < 0.01],
            'unrounded_limit': lowest, 'rounded_limit': math.floor(lowest / increment) * increment}


def analyze(statement, terms, policy, as_of, benchmarks=None):
    as_of = dt.date.fromisoformat(as_of)
    validate_policy(policy)
    for key in TERM_FIELDS:
        number(terms[key], key, 0)
    if terms['max_customer_share'] > 1 or terms['peak_exposure_multiplier'] < 1:
        raise ValueError('Customer share must be <=1; peak multiplier must be >=1')
    if terms['currency'] != policy['currency']:
        raise ValueError('Customer terms and policy currencies differ')
    current, v, reasons = validate_statement(statement, as_of, policy)
    if terms['oldest_overdue_days'] > policy['max_overdue_days']:
        reasons.append('Overdue exposure exceeds policy review trigger')
    result = {'company': statement['company'], 'as_of': str(as_of), 'period_end': current['end'],
              'currency': policy['currency'], 'policy': policy['name'],
              'financial_data_kind': statement['data_kind'], 'commercial_input_kind': terms['input_kind'],
              'status': 'manual_review_required' if reasons else 'proposal_for_analyst_review',
              'review_reasons': reasons, 'proposed_total_limit': None, 'available_for_new_orders': None,
              'note': 'Illustrative policy output, not an approval, credit rating, or probability of default.',
              'financials': current, 'terms': terms, 'base': None, 'stress': None}
    score = None
    if not reasons:
        try:
            if benchmarks is None:
                raise ValueError('Industry benchmark snapshot is required')
            score = industry_score(v, terms['industry'], benchmarks, policy, as_of)
            selected = terms['limit_basis']
            if selected not in ['cash', 'working_capital', 'tangible_net_worth']:
                raise ValueError('Unsupported limit basis')
            for field in (['cash'] if selected == 'cash' else ['goodwill', 'other_intangibles'] if selected == 'tangible_net_worth' else []):
                if field not in v:
                    raise ValueError('Missing disclosure for selected basis: ' + field)
        except (ValueError, KeyError) as error:
            reasons.append(str(error))
            result['status'] = 'manual_review_required'
    result['industry_scorecard'] = score
    if reasons:
        return result
    result['base'] = scenario(v, terms, policy, score)
    result['stress'] = scenario(v, terms, policy, score, stressed=True)
    result['historical_ratios'] = []
    for period in sorted(statement['periods'], key=lambda p: p['end']):
        historical = dict(statement, periods=[period])
        historical_policy = dict(policy, max_statement_age_days=100000)
        _, historical_values, historical_errors = validate_statement(historical, as_of, historical_policy)
        result['historical_ratios'].append({'period_end': period['end'],
                                           'ratios': None if historical_errors else ratios(historical_values),
                                           'review_reasons': historical_errors})
    total = min(result['base']['rounded_limit'], result['stress']['rounded_limit'])
    used = terms['current_receivables'] + terms['committed_unbilled_orders']
    result.update(proposed_total_limit=total, existing_and_committed_exposure=used,
                  available_for_new_orders=max(total - used, 0), exposure_above_proposal=max(used - total, 0))
    result['review_reasons'].append('Confirm contracting legal entity, recent interim results, payment history, disputes, and supplier policy before approval')
    if statement.get('assurance') != 'audited':
        result['review_reasons'].append('Source financial statements are not identified as audited')
    if used > total:
        result['review_reasons'].append('Existing and committed exposure exceeds the proposal; review rather than automatically cancelling orders')
    return result
