import copy
import tempfile
import unittest
from pathlib import Path
from credit import analyze, read
from create_example import example
from analyze import run, render
from fetch_sec import normalize

ROOT = Path(__file__).parent


class CreditTests(unittest.TestCase):
    def setUp(self):
        self.statement = example()
        self.terms = read(ROOT / 'example_terms.json')
        self.policy = read(ROOT / 'policy.json')
        self.benchmarks = read(ROOT / 'industry_benchmarks.json')

    def evaluate(self):
        return analyze(self.statement, self.terms, self.policy, '2026-09-30', self.benchmarks)

    def test_real_financial_example_and_limit_arithmetic(self):
        result = self.evaluate()
        self.assertEqual(result['proposed_total_limit'], 2465000)
        self.assertEqual(result['available_for_new_orders'], 1465000)
        self.assertAlmostEqual(result['base']['ratios']['current_ratio'], 5484 / 1940)
        self.assertEqual(result['base']['binding_caps'], ['sales_and_terms_need'])
        self.assertEqual(result['stress']['binding_caps'], ['portfolio_concentration_cap'])

    def test_currency_mismatch(self):
        self.terms['currency'] = 'CAD'
        with self.assertRaises(ValueError): self.evaluate()

    def test_millions_not_silently_accepted(self):
        self.statement['unit'] = 'millions'
        with self.assertRaises(ValueError): self.evaluate()

    def test_missing_fact_is_not_zero(self):
        del self.statement['periods'][0]['facts']['operating_cash_flow']
        self.assertIsNone(self.evaluate()['proposed_total_limit'])

    def test_stale_statements(self):
        self.policy['max_statement_age_days'] = 90
        self.assertEqual(self.evaluate()['status'], 'manual_review_required')

    def test_negative_cash_flow(self):
        self.statement['periods'][0]['facts']['operating_cash_flow']['value'] = -1
        self.assertIsNone(self.evaluate()['proposed_total_limit'])

    def test_balance_sheet_mismatch(self):
        self.statement['periods'][0]['facts']['assets']['value'] *= 2
        self.assertIsNone(self.evaluate()['proposed_total_limit'])

    def test_exposure_above_limit_never_negative_availability(self):
        self.terms['current_receivables'] = 4000000
        result = self.evaluate()
        self.assertEqual(result['available_for_new_orders'], 0)
        self.assertGreater(result['exposure_above_proposal'], 0)

    def test_group_cap_includes_other_group_exposure(self):
        self.terms['other_group_exposure'] = 4800000
        self.assertEqual(self.evaluate()['proposed_total_limit'], 200000)

    def test_stress_cannot_increase_final_proposal(self):
        result = self.evaluate()
        self.assertLessEqual(result['proposed_total_limit'], result['base']['rounded_limit'])

    def test_more_severe_selected_basis_stress_reduces_capacity(self):
        self.policy['stress']['current_assets_haircut'] = 0.999
        self.assertLess(self.evaluate()['proposed_total_limit'], 2465000)

    def test_analyst_selects_cash_wc_or_tnw(self):
        for basis in ['cash', 'working_capital', 'tangible_net_worth']:
            self.terms['limit_basis'] = basis
            result = self.evaluate()
            self.assertEqual(result['base']['caps']['selected_financial_basis_cap'], result['base']['basis_limits'][basis])
        self.assertEqual(result['base']['basis_values']['tangible_net_worth'], 3516000000)

    def test_missing_intangibles_blocks_tnw_not_wc(self):
        del self.statement['periods'][0]['facts']['other_intangibles']
        self.assertIsNotNone(self.evaluate()['proposed_total_limit'])
        self.terms['limit_basis'] = 'tangible_net_worth'
        self.assertIsNone(self.evaluate()['proposed_total_limit'])

    def test_benchmark_equals_company_scores_fifty(self):
        from industry import industry_score, METRICS
        import datetime
        benchmark = self.benchmarks['industries'][self.terms['industry']]
        values = {'revenue': 100}
        values.update({field: benchmark[metric] * 100 for metric, (field, _) in METRICS.items()})
        result = industry_score(values, self.terms['industry'], self.benchmarks, self.policy, datetime.date(2026, 9, 30))
        self.assertAlmostEqual(result['score'], 50)

    def test_score_components_sum_to_total(self):
        result = self.evaluate()['industry_scorecard']
        self.assertAlmostEqual(result['score'], sum(c['weighted_points'] for c in result['components']))

    def test_specialist_industry_does_not_get_generic_score(self):
        self.terms['industry'] = 'Banks (Regional)'
        self.assertIsNone(self.evaluate()['proposed_total_limit'])

    def test_unknown_industry_has_no_fallback(self):
        self.terms['industry'] = 'Not an industry'
        self.assertIsNone(self.evaluate()['proposed_total_limit'])

    def test_low_sample_benchmark_routes_review(self):
        self.benchmarks['industries'][self.terms['industry']]['firms'] = 2
        self.assertIsNone(self.evaluate()['proposed_total_limit'])

    def test_negative_industry_margin_is_supported(self):
        self.benchmarks['industries'][self.terms['industry']]['net_margin'] = -0.02
        score = self.evaluate()['industry_scorecard']['score']
        self.assertTrue(0 <= score <= 100)

    def test_overdue_triggers_manual_review(self):
        self.terms['oldest_overdue_days'] = 31
        self.assertIsNone(self.evaluate()['proposed_total_limit'])

    def test_no_future_information(self):
        with self.assertRaises(ValueError):
            analyze(self.statement, self.terms, self.policy, '2026-01-01')

    def test_sector_exclusion(self):
        self.statement['sector'] = 'bank'
        self.assertIsNone(self.evaluate()['proposed_total_limit'])

    def test_nonfinite_input_rejected(self):
        self.terms['current_receivables'] = float('nan')
        with self.assertRaises(ValueError): self.evaluate()

    def test_report_escapes_company_name(self):
        self.statement['company'] = '<script>alert(1)</script>'
        self.assertNotIn('<script>', render(self.evaluate()))

    def test_artifact_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(ROOT / 'example_statements.json', ROOT / 'example_terms.json',
                         ROOT / 'policy.json', '2026-09-30', Path(tmp) / 'memo')
            self.assertEqual(len(result['input_sha256']['statements']), 64)
            self.assertTrue((Path(tmp) / 'memo/credit_memo.html').exists())

    def test_sec_adapter_does_not_mix_accessions_or_quarters(self):
        submissions = {'cik': 1, 'name': 'Test fixture', 'sic': '5000', 'filings': {'recent': {
            'form': ['10-K'], 'filingDate': ['2026-02-01'], 'reportDate': ['2025-12-31'],
            'accessionNumber': ['a'], 'primaryDocument': ['annual.htm']}}}
        annual = {'accn': 'a', 'start': '2025-01-01', 'end': '2025-12-31', 'val': 100}
        quarter = dict(annual, start='2025-10-01', val=25)
        wrong_filing = dict(annual, accn='b', val=999)
        facts = {'cik': 1, 'facts': {'us-gaap': {'Revenues': {'units': {'USD': [annual, quarter, wrong_filing]}}}}}
        normalized = normalize(submissions, facts, '2026-09-30')
        self.assertEqual(normalized['periods'][0]['facts']['revenue']['value'], 100)
        self.assertNotIn('current_assets', normalized['periods'][0]['facts'])


if __name__ == '__main__':
    unittest.main()
