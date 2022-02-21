
from flask import Flask, render_template, request
from smtplib import SMTP, SMTPResponseException, SMTPAuthenticationError
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/generic')
def generic():
    return render_template('generic.html')


@app.route('/elements')
def elements():
    return render_template('elements.html')


if __name__ == "__main__":
    app.run(debug=True)

