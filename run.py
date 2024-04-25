import programming
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask import Markup
from flask_session import Session  # Session management
from difflib import get_close_matches
import pandas as pd
import threading

import plotly.graph_objects as go
import plotly.io as pio

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def process_financial_data(name, surname, email, ticker):
    header = programming.identity(name, surname, email)
    ticker_df = programming.company_ticker(header)
    ticker = ticker.upper()
    ticker = get_close_matches(ticker, ticker_df['ticker'], n=1, cutoff=0.65)[0]
    cik = programming.cik_finder(ticker_df, ticker)
    facts = programming.company_facts(header, cik)
    names = programming.matchmaker(facts)
    financial = programming.finance(header, cik, names)
    price = programming.price(ticker, financial)
    rf_plot = programming.rf_interactive(price)
    price_plot = programming.price_interactive(price,ticker)
    return_plot = programming.return_interactive(price,ticker)
    df_html = price.to_html(index=False, classes='dataframe')
    financial_df = financial.to_html(index=False, classes='dataframe')
    return ticker, rf_plot,price_plot,return_plot,df_html,financial_df,df_html

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        ticker = request.form['company']

        # Save user input to session to use across requests
        thread = threading.Thread(target=process_financial_data, args=(name, surname, email, ticker))
        thread.start()
        thread.join()  # Ensure the thread has completed before redirecting

        return redirect(url_for('options'))
    return render_template('home.html')

@app.route('/options')
def options():
    return render_template('options.html')

@app.route('/action1')
def action1():
    #name, surname, email, ticker = session.get('user_data', (None, None, None, None))
    #ticker, rf_plot,price_plot,return_plot,df_html,financial_df,df_html = process_financial_data(name, surname, email, ticker)
    return send_from_directory('static', 'plot_rf.html')


@app.route('/action2')
def action2():
    return "Action 2 executed!"

if __name__ == '__main__':
    app.run(debug=True)
