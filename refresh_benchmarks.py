"""Download the publisher's sector tables with provenance; no guessed benchmarks."""
import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
import urllib.request
from credit import write

SOURCES = {'margins': 'https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/margin.html',
           'working_capital': 'https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wcdata.html'}
SPECIALIZED = {'Bank (Money Center)', 'Banks (Regional)', 'Brokerage & Investment Banking',
               'Financial Svcs. (Non-bank & Insurance)', 'Insurance (General)', 'Insurance (Life)',
               'Insurance (Prop/Cas.)', 'Investments & Asset Management', 'Reinsurance',
               'R.E.I.T.', 'Retail (REITs)', 'Real Estate (Development)', 'Real Estate (General/Diversified)',
               'Real Estate (Operations & Services)'}


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.row = []
        if tag in ['td', 'th'] and self.row is not None: self.cell = []

    def handle_data(self, text):
        if self.cell is not None: self.cell.append(text)

    def handle_endtag(self, tag):
        if tag in ['td', 'th'] and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def extract(text, fields):
    parser = Tables()
    parser.feed(text)
    header = next(row for row in parser.rows if 'Industry Name' in row and all(label in row for label in fields.values()))
    index = {key: header.index(label) for key, label in fields.items()}
    result = {}
    for row in parser.rows:
        if len(row) != len(header) or row[0] == 'Industry Name': continue
        try: firms = int(row[header.index('Number of firms')].replace(',', ''))
        except ValueError: continue
        metrics = {}
        for key, position in index.items():
            raw = row[position].strip()
            if raw in ['NA', 'N/A', '', '-']: metrics[key] = None
            elif raw.endswith('%'): metrics[key] = float(raw[:-1].replace(',', '')) / 100
            else: raise ValueError('Unexpected benchmark unit: ' + raw)
        result[row[0]] = {'firms': firms, **metrics}
    if len(result) < 50: raise ValueError('Unexpectedly small table; inspect source schema')
    return result


def refresh(output, vintage):
    pages, hashes = {}, {}
    month = dt.date.fromisoformat(vintage + '-01').strftime('%B %Y')
    for key, url in SOURCES.items():
        with urllib.request.urlopen(url, timeout=30) as response: raw = response.read()
        text = raw.decode('utf-8', errors='replace')
        if month not in ' '.join(re.sub('<[^>]+>', ' ', text).split()):
            raise ValueError('Requested vintage does not match publisher page: ' + key)
        pages[key], hashes[key] = text, hashlib.sha256(raw).hexdigest()
    margins = extract(pages['margins'], {'gross_margin': 'Gross Margin', 'net_margin': 'Net Margin'})
    wc = extract(pages['working_capital'], {'receivables_sales': 'Acc Rec/ Sales', 'inventory_sales': 'Inventory/Sales'})
    if set(margins) != set(wc): raise ValueError('Industry coverage differs between source tables')
    industries = {}
    for name in margins:
        if margins[name]['firms'] != wc[name]['firms']: raise ValueError('Firm counts differ: ' + name)
        industries[name] = {**margins[name], **wc[name],
                            'treatment': 'aggregate_reference_only' if name.startswith('Total Market') else
                            'specialist_review' if name in SPECIALIZED else 'general_corporate'}
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    result = {'provider': 'Aswath Damodaran, NYU Stern', 'region': 'US listed companies', 'vintage': vintage,
              'verified_on': today, 'available_from': today,
              'statistic': 'Published sector ratios; not medians, percentiles, or default statistics',
              'sources': SOURCES, 'source_sha256': hashes, 'industries': industries}
    write(output, result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--vintage', required=True, help='YYYY-MM must match source pages')
    a = p.parse_args()
    if Path(a.output).exists(): raise FileExistsError('Write a new snapshot and review changes')
    result = refresh(a.output, a.vintage)
    print(len(result['industries']), 'industry/aggregate rows')
