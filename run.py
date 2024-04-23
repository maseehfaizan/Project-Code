
import programming
from flask import Flask, render_template, request, redirect, url_for
import threading

"""app = Flask(__name__)

 This could be your existing Python code adapted into a function
"""


from flask import Flask, render_template, request

app = Flask(__name__)

def process_financial_data(name, surname, email, ticker):
    header = programming.identity(name,surname,email)
    ticker_df = programming.company_ticker(header)
    cik = programming.cik_finder(ticker_df,ticker)
    facts = programming.company_facts(header,cik)
    names = programming.matchmaker(facts)
    financial = programming.finance(header,cik,names)
    price = programming.price(ticker,financial)
    df_html = price.to_html(index=False, classes='dataframe')
    return df_html

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Extract the form data
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        company = request.form['company']


        # Display or use the processed data
        thread = threading.Thread(target=process_financial_data, args=(name, surname, email, company))
        thread.start()

        # Redirect to another page after form submission
        return redirect(url_for('options'))
    return render_template('home.html')


@app.route('/options')
def options():
    return render_template('options.html')

@app.route('/action1')
def action1():
    # Perform some action here
    return "Action 1 executed!"

@app.route('/action2')
def action2():
    # Perform another action here
    return "Action 2 executed!"



if __name__ == '__main__':
    app.run(debug=True)
