import programming
from flask import Flask, render_template, request, redirect, url_for
import threading

app = Flask(__name__)

# This could be your existing Python code adapted into a function
def process_financial_data(name, surname, email, ticker):
    header = programming.identity(name,surname,email)
    ticker = programming.company_ticker(header)
    facts = programming.company_facts(header)
    cik = programming.cik_finder(ticker)
    names = programming.matchmaker(facts)
    financial = programming.finance(header,cik,names)
    price = programming.price(ticker,financial)
    return price


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        ticker = request.form['ticker']

        # Run the financial data processing in a background thread
        thread = threading.Thread(target=results, args=(name, surname, email, ticker))
        thread.start()

        return redirect(url_for('results'))
    return render_template('home.html')

@app.route('/results')
def results():
    return 'This thing sucks'

if __name__ == '__main__':
    app.run(debug=True)
