# I am importing all the data file that we actually need
import pandas as pd
import yfinance as yf
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import seaborn as sns
import time
import datetime
import difflib
from difflib import get_close_matches



def identity(name,surname,email):
    """
    Take in as parameter:

    - User name
    - User surname
    - User email and gives their headers

    Defines the headers as identification for SEC

    """
    headers = {'User-Agent':f'{name} {surname} {email}'}
    return headers



def company_ticker(head):
    """
    This will take in the header as a parameter, which is the identity

    The function creates a dataframe, rename the columns appropriatly and make fill the cik number with
    leading zeros so the ticker dataframe is well organised!

    Returns:
    a pandas dataframe containing Company Ticker and their name.
    """
    ticker = requests.get('https://www.sec.gov/files/company_tickers.json',headers=head).json()
    ticker_df = pd.DataFrame.from_dict(ticker,orient='index')
    ticker_df.rename(columns={'cik_str':'cik','title':'name'},inplace=True)
    #Filing in the cik code and adding the leading zeros
    ticker_df['cik'] = ticker_df['cik'].astype(str).str.zfill(10)
    return ticker_df




def cik_finder(ticker_df,tic):
    """
    Parameters
    - Pandas Dataframe containing Ticker information
    - The Ticker value the user has submitted

    Returns:
    - Company Cik number with leading Zeros
    """
    # Upper things up so even if user submits something wrong the code will make the ticker uppercase
    tic = tic.upper()
    #Now I will find the closest match so if the user put in something that is slightly wrong it won't crash the whole system up and still run the code fine.
    tic = get_close_matches(tic, ticker_df['ticker'], n=1, cutoff=0.65)[0]
    cik = ticker_df.loc[ticker_df['ticker'] == tic.upper(), 'cik'].iloc[0]
    return cik



def company_facts(head,cik):
    """
    Parameters:
    - head, which is the identity
    - cik, which is the cik number with leading zeros.

    Returns:
    Important information on the comapany like where the files like 10-K are.
    """

    facts = requests.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',headers = head).json()
    return facts

def find_best_match(items, search):
    matches = difflib.get_close_matches(search, items, n=1, cutoff=0.4)
    return matches[0] if matches else None

def matchmaker(facts):
    """
    Parameters
    - Pandas Dataframe containing all the information and facts 
    
    - The function will find the appropriate data in the US-GAAP
    - Names of the accounts needed are also created to have standard naming scheme
    - Normalize all the accounts.
    - Find the best match between accounts and names

    Returns:
    The best match
    """

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

    """
    Parameters:
    - Head as identifier
    - cik number with leading zeros
    - names as the perfect match

    The funtion creates a data frame with all the financial information
    After come computations the financial information is returned as a Pandas DataFrame
    """

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
    financials = financials.sort_values(by='Year',ascending=True)
    financials = financials.set_index('Year')
    try:
        financials['Liability'] = financials['Liability and Stockholder equity'] - financials['Total Stockholders equity']

    except Exception as e:
    # Code that runs if an exception occurs
        financials['Liability'] = financials['Liability and Stockholder equity'] * 0
    return financials

def income(financials):
    """
    Takes the financial dataframe and copy's only the income statement information
    """
    income = financials.iloc[6:].transpose()
    income.reset_index(inplace=True)
    return income

def balance(financials):
    """
    Takes the financial dataframe and copy's only the Balancesheet information
    """
    balance = financials.iloc[:6].transpose()
    balance.reset_index(inplace=True)
    return balance


def price(tic,financial):
    """
    Parameters:
    - Ticker value
    - Financial dataframe

    The function downloads company price and market prices for the same timeframe
    as in Financial dataframe from Yahoo Finance. 
    It drops the data that is not used
    The riskfree rates are imported and initializes
    The funtion also computes the returns and cumulative returns for all the accounts
    The function merges all the data frame 
    Returns
    - main as the merged DataFrame.
    """
    first = financial.transpose().columns[0].astype(int)
    last = financial.transpose().columns[-1].astype(int)

    start=datetime.datetime(first,1,1)
    end=datetime.datetime(last,12,31)

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
    main = main.merge(rate,right_on='Date',left_on='Date',how='inner')
    main = main.drop_duplicates(subset='Date')
    main = main.dropna()
    main[f'{tic}_return'] = main[f'{tic} Price'].pct_change()*100
    main['S&P500_return'] = main['S&P500'].pct_change()*100
    beta = get_company_beta(tic)
    main['CAPM'] = (main['Risk Free Rate']) + beta * (main['S&P500_return'] - main['Risk Free Rate'])
    main[f'{tic}_cum_return'] = main[f'{tic}_return'].cumsum()
    main['S&P500_cum_return'] = main['S&P500_return'].cumsum()
    main['CAPM_cum'] = main['CAPM'].cumsum()
    main['cum_rf_rate'] = main['Risk Free Rate'].cumsum()

    
    
    main = main.drop_duplicates(subset='Date')
    main = main.dropna()
    return main


def get_company_beta(ticker):
    """
    Parameter:
    - Ticker
    Get the company data there are times where yahoo doesn't have the beta data for newly listed companies including TSLA.
    For those company I will give beta balue of 1 so it doesn't change anything in further analysis
    
    Returns
    - Beta Value
    """
    # Get the company data there are times where yahoo doesn't have the beta data for newly listed companies including TSLA.
    #For those company I will give beta balue of 1 so it doesn't change anything in further analysis
    company = yf.Ticker(ticker)
    try:
        # Fetch the beta value
        beta_val = company.info['beta']
    except KeyError:
        beta_val = 1
    return beta_val



def return_plot(dataframe, ticker):
    fig, axs = plt.subplots(figsize=(12, 6))

    sns.lineplot(data=dataframe, x='Date', y=f'{ticker}_cum_return',label=f'{ticker} Cumulative returns', ax=axs,color='red')
    sns.lineplot(data=dataframe, x='Date', y='S&P500_cum_return',label='S&P500 Cumulative returns', ax=axs, color='blue')
    sns.lineplot(data=dataframe, x='Date', y='CAPM_cum',label='CAPM', ax=axs, color='blue')
    sns.lineplot(data=dataframe, x='Date', y='cum_rf_rate',label='Risk Free Returns', ax=axs, color='black')

    axs.spines['top'].set_visible(False)
    axs.spines['right'].set_visible(False)

    # Adjust layout
    plt.title('Cumulative returns')
    plt.tight_layout()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.fill_between(dataframe['Date'], dataframe[f'{ticker}_cum_return'].values, dataframe['S&P500_cum_return'].values, color='green', alpha=0.2)
    return plt


def riskfree():
    """
    Imports Riskfree rate
    Drops all the un necessary columns
    Returns the riskfree rate
    """
    # Emptry dataframe
    rate = pd.DataFrame()
    #empty rates
    rates = []
    # loop through all the csv files
    for i in range(11):
        #names are from 1 to 7
        i +=1

        name = str(i)
        name = pd.read_csv(f'./data/daily-treasury-rates-{i}.csv')
        # fill the list with dataframes
        rates.append(name)
    #concate everything row wise
    rate = pd.concat(rates,ignore_index=True)
    rate['Date'] = pd.to_datetime(rate['Date'])
    rate = rate.sort_values(by='Date')
    # I only want to consider the 13 weeks discount rate as the true riskfree rate
    rate = rate[['Date','13 WEEKS BANK DISCOUNT']]
    rate = rate.rename(columns={'13 WEEKS BANK DISCOUNT':'Risk Free Rate'})
    rate['Risk Free Rate'] = rate['Risk Free Rate']/100
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
    return plt

def return_interactive(dataframe,ticker):
        # Sample DataFrame - replace this with your actual DataFrame
    # main = pd.read_csv('your_data.csv')
    # tic = 'your_ticker'

    # Assuming 'Date' is already a datetime type; if not, convert it:
    # main['Date'] = pd.to_datetime(main['Date'])

    # Create traces
    trace1 = go.Scatter(x=dataframe['Date'], y=dataframe[f'{ticker}_cum_return'], mode='lines', name=f'{ticker} Cumulative returns', line=dict(color='red'))

    trace2 = go.Scatter(x=dataframe['Date'], y=dataframe['CAPM_cum'], mode='lines', name='CAPM', line=dict(color='blue'))
    trace3 = go.Scatter(x=dataframe['Date'], y=dataframe['S&P500_cum_return'], mode='lines', name='S&P500 Cumulative returns', line=dict(color='green'))
    trace4 = go.Scatter(x=dataframe['Date'], y=dataframe['cum_rf_rate'], mode='lines', name='Risk Free Returns', line=dict(color='black'))

    # Create the figure
    fig = go.Figure(data=[trace1, trace2, trace3, trace4])

    # Fill between trace1 and trace3
    fig.add_trace(go.Scatter(x=dataframe['Date'], y=dataframe[f'{ticker}_cum_return'],
                            mode='lines', fill=None, showlegend=False,
                            line=dict(color='rgba(255,255,255,0)')))

    fig.add_trace(go.Scatter(x=dataframe['Date'], y=dataframe['S&P500_cum_return'],
                            mode='lines', fill='tonexty', showlegend=False,
                            line=dict(color='green', width=0), fillcolor='rgba(0,255,0,0.2)'))



    # Update layout
    fig.update_layout(title='Cumulative Returns Comparison',
                    xaxis_title='Date',
                    yaxis_title='Cumulative Return',
                    hovermode='x unified')
    div = fig.write_html("./static/plot_returns.html")

    return div

def rf_interactive(dataframe):
    # Sample DataFrame - replace 'rate' with your actual DataFrame variable name
    # rate = pd.read_csv('your_data.csv')

    # Assuming 'Date' is already in datetime format; if not, convert it:
    # rate['Date'] = pd.to_datetime(rate['Date'])

    # Create trace
    dataframe = dataframe.reset_index()
    trace = go.Scatter(x=dataframe['Date'], y=dataframe['Risk Free Rate'], mode='lines', name='13 WEEKS BANK DISCOUNT %', line=dict(color='red'))

    # Create the figure
    fig = go.Figure(data=[trace])

    # Update layout
    fig.update_layout(
        title='13 Weeks Treasury Bills (Risk Free Rates)',
        xaxis_title='Date',
        yaxis_title='Risk Free Rate',
        hovermode='x unified',
        template='plotly_white'  # This adds a clean white background similar to your Matplotlib style
    )

    # Add grid lines
    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='lightgrey')
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='lightgrey')

    # Remove right and top lines
    fig.update_layout(showlegend=True, plot_bgcolor='white', xaxis_showspikes=True, yaxis_showspikes=True)
    div = fig.write_html("./static/plot_rf.html")
    return div


def price_interactive(dataframe,ticker):
    trace = go.Scatter(x=dataframe['Date'], y=dataframe[f'{ticker} Price'], mode='lines', name=f'{ticker} Price', line=dict(color='green'))

    # Create the figure
    fig = go.Figure(data=[trace])

    # Update layout
    fig.update_layout(
        title=(f'{ticker} Price '),
        xaxis_title='Date',
        yaxis_title='Price $',
        hovermode='x unified',
        template='plotly_white'  # This adds a clean white background similar to your Matplotlib style
    )

    # Add grid lines
    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='lightgrey')
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='lightgrey')

    # Remove right and top lines
    fig.update_layout(showlegend=True, plot_bgcolor='white', xaxis_showspikes=True, yaxis_showspikes=True)
    
    div = fig.write_html("./static/plot_price.html")
    return div



def eps_plot_interactive(dataframe,ticker):
    """
    - Dataframe is the income statement so it can look up for the EPS and NetIncome in there
    - The Ticker is used to change the title of the company.
    """
    fig = make_subplots(rows=1, cols=2, subplot_titles=('Earnings per Share', 'Net Income'))

    # Generate the colors based on the sign of the 'EPS' and 'Net Income' values
    colors_eps = ['red' if x < 0 else 'green' for x in dataframe['EPS']]
    colors_net_income = ['red' if x < 0 else 'green' for x in dataframe['Net Income']]

    # Add bar plots for 'EPS'
    fig.add_trace(
        go.Bar(x=dataframe.reset_index()['Year'], y=dataframe['EPS'], marker_color=colors_eps, name='EPS'),
        row=1, col=1
    )

    # Add bar plots for 'Net Income'
    fig.add_trace(
        go.Bar(x=dataframe.reset_index()['Year'], y=dataframe['Net Income'], marker_color=colors_net_income, name='Net Income'),
        row=1, col=2
    )

    # Update the layout for a cleaner look
    fig.update_layout(
        title_text=f'Earning Per Share and Net Income for {ticker}',
        showlegend=False,
        plot_bgcolor='white',
        height=600, width=1200
        
    )

    # Update yaxis properties
    fig.update_yaxes(title_text='Dollars', showline=True, linewidth=2, linecolor='black', mirror=True)

    # Update xaxis properties
    fig.update_xaxes(title_text='Years', showline=True, linewidth=2, linecolor='black', mirror=True)

    # Add a horizontal line at y=0 for both subplots
    fig.add_hline(y=0, line_color='black', line_width=2, row=1, col=1)
    fig.add_hline(y=0, line_color='black', line_width=2, row=1, col=2)

    # Remove the 'spines' (In plotly, they are called 'lines')
    fig.update_xaxes(showspikes=False)
    fig.update_yaxes(showspikes=False)
    div = fig.write_html("./static/plot_eps.html")
    # Show the plot
    return div




def ratio_plot_interactive(dataframe,ticker):
    """
    The dataframe here is the Balancesheet dataframe
    The Ticker is about the name of the company.
    """
    # Create subplots
    fig = make_subplots(rows=1, cols=2, subplot_titles=('Liability to Equity Ratio', 'Liability to Current Asset Ratio'))

    # First subplot for 'Liability to Equity ratio'
    fig.add_trace(
        go.Bar(name='Liability', x=dataframe.reset_index()['Year'], y=dataframe['Liability'], marker_color='blue'),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(name='Total Stockholders Equity', x=dataframe.reset_index()['Year'], y=dataframe['Total Stockholders equity'], marker_color='green'),
        row=1, col=1
    )

    # Second subplot for 'Liability to Current Asset Ratio'
    fig.add_trace(
        go.Bar(name='Liability', x=dataframe.reset_index()['Year'], y=dataframe['Liability'], marker_color='blue'),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(name='Current Assets', x=dataframe.reset_index()['Year'], y=dataframe['Current Assets'], marker_color='green'),
        row=1, col=2
    )

    # Update the layout for a cleaner look
    fig.update_layout(
        title_text=f'Balance Sheet Ratios for {ticker}',
        showlegend=False,
        plot_bgcolor='white',
        height=600, width=1200
    )

    # Update xaxes and yaxes titles
    fig.update_xaxes(title_text='Years', row=1, col=1)
    fig.update_xaxes(title_text='Years', row=1, col=2)
    fig.update_yaxes(title_text='Dollars', row=1, col=1)
    fig.update_yaxes(title_text='Dollars', row=1, col=2)

    # Make the bar charts stacked
    fig.update_layout(barmode='stack')

    # Remove the 'spines' (In plotly, they are called 'lines')
    fig.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=True)
    fig.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=True)
    div = fig.write_html("./static/plot_ratio.html")
# Show the plot
    return div

