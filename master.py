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


def identity(name, surname, email):
    return {'User-Agent': f'{name} {surname} {email}'}



class DataManager:
    def __init__(self, headers):
        self.headers = headers

    def company_ticker(self):
        response = requests.get('https://www.sec.gov/files/company_tickers.json', headers=self.headers).json()
        ticker_df = pd.DataFrame.from_dict(response, orient='index')
        ticker_df.rename(columns={'cik_str': 'cik', 'title': 'name'}, inplace=True)
        ticker_df['cik'] = ticker_df['cik'].astype(str).str.zfill(10)
        return ticker_df

    def company_facts(self, cik):
        response = requests.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json', headers=self.headers).json()
        return response

    def risk_free_rate(self):
        # Method for retrieving and processing risk-free rate data
        pass

    def get_company_beta(self, ticker):
        company = yf.Ticker(ticker)
        try:
            beta_val = company.info['beta']
        except KeyError:
            beta_val = 1
        return beta_val


class FinancialAnalysis:
    def __init__(self, ticker_df):
        self.ticker_df = ticker_df

    def cik_finder(self, tic):
        tic = tic.upper()
        tic = get_close_matches(tic, self.ticker_df['ticker'], n=1, cutoff=0.65)[0]
        cik = self.ticker_df.loc[self.ticker_df['ticker'] == tic.upper(), 'cik'].iloc[0]
        return cik

    def matchmaker(self, facts):
        # Matching financial terms and categories
        pass

    def finance(self, head, cik, names):
        # Method to retrieve financial data and form financial statements
        pass

    def income(self, financials):
        # Process income statements
        pass

    def balance(self, financials):
        # Process balance sheets
        pass

class Visualizer:
    def return_plot(self, dataframe, ticker):
        # Method to plot returns
        pass

    def return_interactive(self, dataframe, ticker):
        # Method to generate interactive return plots
        pass

    def eps_plot_interactive(self, dataframe, ticker):
        # Interactive EPS and net income plots
        pass

    def ratio_plot_interactive(self, dataframe, ticker):
        # Interactive ratio plots
        pass

    def rf_plot(self, dataframe):
        # Plot for risk-free rates
        pass
