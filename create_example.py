"""Reproduce the small, manually transcribed public financial example."""
from pathlib import Path
from credit import write


SOURCE = 'https://invest.grainger.com/investor-news/news-details/2026/GRAINGER-REPORTS-RESULTS-FOR-THE-FOURTH-QUARTER-AND-FULL-YEAR-2025/default.aspx'
# Values in the company's release are USD millions; normalize once to USD.
FIGURES = {
    '2025': {'revenue': 17942, 'assets': 8962, 'liabilities': 4821, 'equity': 4141,
             'current_assets': 5484, 'current_liabilities': 1940, 'operating_cash_flow': 2015,
             'cash': 585, 'receivables': 2329, 'inventory': 2394, 'capital_expenditure': 684,
             'gross_profit': 7009, 'net_income': 1706, 'goodwill': 360, 'other_intangibles': 265},
    '2024': {'revenue': 17168, 'assets': 8829, 'liabilities': 5126, 'equity': 3703,
             'current_assets': 5737, 'current_liabilities': 2305, 'operating_cash_flow': 2111,
             'cash': 1036, 'receivables': 2232, 'inventory': 2306, 'capital_expenditure': 541,
             'gross_profit': 6758, 'net_income': 1909, 'goodwill': 355, 'other_intangibles': 243}
}


def example():
    periods = []
    for year, numbers in FIGURES.items():
        facts = {}
        for name, value in numbers.items():
            table = ('condensed consolidated statements of cash flows, twelve months ended December 31'
                     if name in ['operating_cash_flow', 'capital_expenditure'] else
                     'condensed consolidated statements of earnings, twelve months ended December 31'
                     if name in ['revenue', 'gross_profit', 'net_income'] else 'condensed consolidated balance sheets, December 31')
            derivation = ' | derived: total assets minus total shareholders equity' if name == 'liabilities' else ''
            facts[name] = {'value': value * 1000000, 'source': f'{SOURCE} | {table} {year}{derivation}',
                           'reported_value_millions': value, 'normalization': 'USD millions multiplied by 1000000'}
        periods.append({'start': year + '-01-01', 'end': year + '-12-31', 'facts': facts})
    return {'company': 'W.W. Grainger, Inc. and Subsidiaries', 'cik': 277135, 'currency': 'USD',
            'unit': 'currency_units', 'sector': 'nonfinancial', 'published': '2026-02-03',
            'assurance': 'unaudited earnings release', 'data_kind': 'real public financials, manually transcribed',
            'source_url': SOURCE, 'periods': periods}


if __name__ == '__main__':
    destination = Path(__file__).parent / 'example_statements.json'
    write(destination, example())
    print(destination)
