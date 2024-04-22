# I am importing all the data file that we actually need
import pandas as pd
import yfinance as yf
import numpy as np
from bs4 import BeautifulSoup
import requests
import re
import time
import difflib
import datetime



def identity(name,surname,email):
    headers = {'User-Agent':f'{name} {surname} {email}'}
    return headers

def company_ticker(head):
    ticker = requests.get('https://www.sec.gov/files/company_tickers.json',headers=head.json())
    ticker_df = pd.DataFrame.from_dict(ticker,orient='index')
    ticker_df.rename(columns={'cik_str':'cik','title':'name'},inplace=True)
    #Filing in the cik code and adding the leading zeros
    ticker_df['cik'] = ticker_df['cik'].astype(str).str.zfill(10)
    return ticker_df

def company_facts(head):
    facts = requests.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',headers = head).json()
    return facts


def cik_finder(ticker):
    cik = ticker.loc[ticker['ticker'] == ticker.upper(), 'cik'].iloc[0]
    return cik

def find_best_match(items, search):
    matches = difflib.get_close_matches(search, items, n=1, cutoff=0.0)
    return matches[0] if matches else None

def matchmaker(facts):
    accounts = list(facts['facts']['us-gaap'].keys())
    names = {'Assets':['Assets'],
            'Current Assets':['assets current'],
            'Cash':['Cash and cash equivalents'],
            'Current Liability':['Liability current'],
            'Total Stockholders equity':['Stockholders Equity'],
            'Liability and Stockholder equity':['Liabilities and Stockholders equity'],
            'Revenues':['Sales'],
            'COGS':['Cost of Goods Sold'],
            'Operating Expense':['Total Operating Expense'],
            'Net Income':['Net Income'],
            'EPS':['Earnings Per Share basic'],
            }
    # Normalize everything down
    normalized_account = [re.sub(r'\W+', '',s).lower() for s in accounts]
    for key, value in names.items():
        value = [re.sub(r'\W+', '',s).lower() for s in value]
        best_match = [find_best_match(normalized_account, j) for j in value]
        
        accounts_match = [find_best_match(accounts, best_match[0])]
        names[key] = accounts_match[0]
    return names


def finance(head,cik,names):

    financials = pd.DataFrame(columns=['Year','val'])
    ix = 0
    for key,value in names.items():
        # To comply with SEC we need to set a timer so the program doesn't request too many items at once
        time.sleep(0.12)
        name = key
        company_concept = requests.get(f'https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{value}.json',headers=head).json()
        # the unit for Earning per share is USD/Share and not USD which means I need to adapt the code for that
        if key == 'EPS':
            name = pd.DataFrame(company_concept['units']['USD/shares'])
        else:
            name = pd.DataFrame(company_concept['units']['USD'])
        name = name[name['form'] == '10-K']
        name = name.drop_duplicates(subset='fy',keep='last')
        name = name.tail(60)
        name = name[['fy','val']]
        name = name.rename(columns={'fy':'Year','val':key})
        # I want to initialize the balance sheet that is why I need to merge on name, then after I will merge on Balance Sheet dataframe
        if ix == 0:
            financials = financials.merge(name,left_on='Year',right_on='Year',how='right')
            ix +=1
        else:
            financials = financials.merge(name,left_on='Year',right_on='Year',how='left')

    financials = financials.drop('val',axis = 1)
    financials = financials.sort_values(by='Year',ascending=False)
    financials = financials.set_index('Year')
    financials = financials.T
    return financials

def income(financials):
    income = financials.iloc[6:].transpose()
    income.reset_index(inplace=True)
    return income

def balance(financials):
    balance = financials.iloc[:6].transpose()
    balance.reset_index(inplace=True)
    return balance




def price(tic,financial):

    first = financial.columns[0].astype(int)
    last = financial.columns[-1].astype(int)

    start=datetime.datetime(last,1,1)
    end=datetime.datetime(first,12,31)

    price = yf.download(tic,start,end)
    market = yf.download('^GSPC',start,end)

    price.reset_index(inplace=True)
    market.reset_index(inplace=True)

    price['Average'] = (price['High'] + price['Low']) / 2
    price = price[['Date','Average','Volume']]

    market['Average'] = (market['High'] + market['Low']) / 2
    market = market[['Date','Average','Volume']]

    # Convert 'date' to datetime
    price['Date'] = pd.to_datetime(price['Date'])
    price = price.rename(columns={'Average':f'{tic} Price','Volume':f'{tic} Volume'})
    market = market.rename(columns={'Average':'S&P500','Volume':'S&P500 Volume'})
    main = pd.merge(price,market,right_on='Date',left_on='Date',how='inner')
    return main


