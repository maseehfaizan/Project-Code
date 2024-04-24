# I am importing all the data file that we actually need
import pandas as pd
import yfinance as yf
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import time
import datetime
import difflib



def identity(name,surname,email):
    headers = {'User-Agent':f'{name} {surname} {email}'}
    return headers

def company_ticker(head):
    ticker = requests.get('https://www.sec.gov/files/company_tickers.json',headers=head).json()
    ticker_df = pd.DataFrame.from_dict(ticker,orient='index')
    ticker_df.rename(columns={'cik_str':'cik','title':'name'},inplace=True)
    #Filing in the cik code and adding the leading zeros
    ticker_df['cik'] = ticker_df['cik'].astype(str).str.zfill(10)
    return ticker_df

def company_facts(head,cik):
    facts = requests.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',headers = head).json()
    return facts


def cik_finder(ticker_df,tic):
    cik = ticker_df.loc[ticker_df['ticker'] == tic.upper(), 'cik'].iloc[0]
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
    rate = riskfree()
    main = pd.merge(price,market,right_on='Date',left_on='Date',how='inner')
    main = pd.merge(rate,market,right_on='Date',left_on='Date',how='inner')

    main = main.drop_duplicates(subset='Date')
    return main


def get_company_beta(ticker):
    # Get the company data
    company = yf.Ticker(ticker)
    
    # Fetch the beta value
    beta = company.info['beta']
    return beta

def capm(dataframe,beta):
    dataframe['CAPM'] = (dataframe['Risk Free Rate']) + beta * (dataframe['S&P500_return'] - dataframe['Risk Free Rate'])
    

def cum_returns(dataframe, ticker):
    """
    dataframe: In our case this is the main data frame which is merged so we can compute 
    the returns and the cumulative returns starting from 2014 (10years)

    ticker: Which is the ticker of the company we are trying to comput the data for
    """
    dataframe[f'{ticker}_return'] = dataframe[f'{ticker} Price'].pct_change()*100
    dataframe['S&P500_return'] = dataframe['S&P500'].pct_change()*100

    dataframe[f'{ticker}_cum_return'] = dataframe[f'{ticker}_return'].cumsum()
    dataframe['S&P500_cum_return'] = dataframe['S&P500_return'].cumsum()
    dataframe['CAPM_cum'] = dataframe['CAPM'].cumsum()
    dataframe['cum_rf_rate'] = dataframe['Risk Free Rate'].cumsum()

    dataframe = dataframe.dropna()
    return dataframe

def return_plot(dataframe, ticker):
    fig, axs = plt.subplots(figsize=(12, 6))

    sns.lineplot(data=dataframe, x='Date', y=f'{ticker}_cum_return',label=f'{ticker} Cumulative returns', ax=axs,color='red')

    sns.lineplot(data=dataframe, x='Date', y='S&P500_cum_return',label='S&P500 Cumulative returns', ax=axs, color='blue')
    axs.spines['top'].set_visible(False)
    axs.spines['right'].set_visible(False)

    # Adjust layout
    plt.title('Cumulative returns')
    plt.tight_layout()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.fill_between(dataframe['Date'], dataframe[f'{ticker}_cum_return'].values, dataframe['S&P500_cum_return'].values, color='green', alpha=0.2)


def riskfree():
    # Emptry dataframe
    rate = pd.DataFrame()
    #empty rates
    rates = []
    # loop through all the csv files
    for i in range(11):
        #names are from 1 to 7
        i +=1

        name = str(i)
        name = pd.read_csv(f'./daily-treasury-rates-{i}.csv')
        # fill the list with dataframes
        rates.append(name)
    #concate everything row wise
    rate = pd.concat(rates,ignore_index=True)
    rate['Date'] = pd.to_datetime(rate['Date'])
    rate = rate.sort_values(by='Date')
    # I only want to consider the 13 weeks discount rate as the true riskfree rate
    rate = rate[['Date','13 WEEKS BANK DISCOUNT']]
    rate = rate.drop_duplicates(subset='Date')
    return rate

def rf_plot(dataframe):
    fig, axs = plt.subplots(figsize=(12, 6))

    sns.lineplot(data=dataframe, x='Date', y='13 WEEKS BANK DISCOUNT',label='13 WEEKS BANK DISCOUNT %', ax=axs,color='red')


    axs.spines['top'].set_visible(False)
    axs.spines['right'].set_visible(False)

    # Adjust layout
    plt.title('13 Weeks Treasury bills (Risk Free Rates)')
    plt.tight_layout()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
