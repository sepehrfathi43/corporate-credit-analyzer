"""Optional SEC Company Facts adapter. Stops on access blocks; never substitutes data."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import time
import urllib.request
import urllib.error
from credit import write, sha


TAGS = {
    'revenue': ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet'],
    'assets': ['Assets'], 'liabilities': ['Liabilities'],
    'equity': ['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 'StockholdersEquity'],
    'current_assets': ['AssetsCurrent'], 'current_liabilities': ['LiabilitiesCurrent'],
    'operating_cash_flow': ['NetCashProvidedByUsedInOperatingActivities'],
    'cash': ['CashAndCashEquivalentsAtCarryingValue'],
    'receivables': ['AccountsReceivableNetCurrent'], 'inventory': ['InventoryNet'],
    'capital_expenditure': ['PaymentsToAcquirePropertyPlantAndEquipment']
}
TAGS.update(gross_profit=['GrossProfit'], net_income=['NetIncomeLoss'], goodwill=['Goodwill'],
            other_intangibles=['FiniteLivedIntangibleAssetsNet'])
# The finite-lived tag alone cannot establish all other intangibles. Leave TNW
# unavailable until an analyst reconciles indefinite-lived assets separately.
TAGS.pop('other_intangibles')
DURATION = {'revenue', 'operating_cash_flow', 'capital_expenditure', 'gross_profit', 'net_income'}


def get_json(url, user_agent):
    if not user_agent or len(user_agent) < 15:
        raise ValueError('Set SEC_USER_AGENT to your application name and a real contact address')
    for attempt in range(3):
        time.sleep(0.6)
        request = urllib.request.Request(url, headers={'User-Agent': user_agent, 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 403:
                raise RuntimeError('SEC blocked access. Stop and use a permitted company-published statement or local SEC snapshot.') from error
            if error.code != 429 or attempt == 2:
                raise
            time.sleep(min(max(int(error.headers.get('Retry-After', 2 ** (attempt + 1))), 1), 60))


def normalize(submissions, companyfacts, as_of):
    cutoff = dt.date.fromisoformat(as_of)
    if int(submissions['cik']) != int(companyfacts['cik']):
        raise ValueError('Company Facts and submissions CIK differ')
    recent = submissions['filings']['recent']
    records = [{key: recent[key][i] for key in ['form', 'filingDate', 'reportDate', 'accessionNumber', 'primaryDocument']}
               for i in range(len(recent['form']))]
    filings = [r for r in records if r['form'] == '10-K' and dt.date.fromisoformat(r['filingDate']) <= cutoff]
    if not filings:
        raise ValueError('No available 10-K in recent submissions for this date; archived submissions require separate review')
    anchor = max(filings, key=lambda r: (r['reportDate'], r['filingDate']))
    if any(r['form'] == '10-K/A' and r['reportDate'] == anchor['reportDate'] and
           anchor['filingDate'] <= r['filingDate'] <= as_of for r in records):
        raise ValueError('An amended annual filing exists; reconcile it manually before analysis')
    cik, accession = int(submissions['cik']), anchor['accessionNumber']
    source_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{anchor['primaryDocument']}"
    us_gaap = companyfacts.get('facts', {}).get('us-gaap', {})
    starts = []
    for tag in TAGS['revenue']:
        starts += [x['start'] for x in us_gaap.get(tag, {}).get('units', {}).get('USD', [])
                   if x.get('accn') == accession and x.get('end') == anchor['reportDate'] and x.get('start') and
                   330 <= (dt.date.fromisoformat(x['end']) - dt.date.fromisoformat(x['start'])).days <= 400]
    if len(set(starts)) != 1:
        raise ValueError('Cannot establish one unambiguous annual duration from the selected filing')
    start = starts[0]
    facts = {}
    for field, tags in TAGS.items():
        for tag in tags:
            matches = [x for x in us_gaap.get(tag, {}).get('units', {}).get('USD', [])
                       if x.get('accn') == accession and x.get('end') == anchor['reportDate'] and
                       ((x.get('start') == start) if field in DURATION else not x.get('start'))]
            if not matches:
                continue
            values = {x['val'] for x in matches}
            if len(values) != 1:
                raise ValueError('Conflicting facts for ' + field)
            facts[field] = {'value': values.pop(), 'source': f'{source_url} | us-gaap:{tag} | accession {accession}',
                            'tag': tag, 'accession': accession}
            break
    # Do not substitute a different period, unit, entity, or filing for a missing fact.
    sic = int(submissions.get('sic') or 0)
    return {'company': submissions['name'], 'cik': cik, 'currency': 'USD', 'unit': 'currency_units',
            'sector': 'nonfinancial' if sic and not 6000 <= sic <= 6999 else 'requires_sector_review',
            'data_kind': 'SEC reported financial facts', 'published': anchor['filingDate'],
            'assurance': '10-K; auditor opinion not reviewed by this adapter', 'source_url': source_url,
            'periods': [{'start': start, 'end': anchor['reportDate'], 'facts': facts}]}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cik', required=True, type=int)
    p.add_argument('--as-of', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    output = Path(a.output)
    if output.exists():
        raise FileExistsError('Use a new snapshot directory')
    ua = os.environ.get('SEC_USER_AGENT')
    submissions = get_json(f'https://data.sec.gov/submissions/CIK{a.cik:010d}.json', ua)
    facts = get_json(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{a.cik:010d}.json', ua)
    normalized = normalize(submissions, facts, a.as_of)
    output.mkdir(parents=True)
    write(output / 'submissions.json', submissions)
    write(output / 'companyfacts.json', facts)
    write(output / 'statements.json', normalized)
    write(output / 'manifest.json', {'as_of': a.as_of, 'fetched_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                                    'sha256': {name: sha(output / name) for name in ['submissions.json', 'companyfacts.json', 'statements.json']}})
