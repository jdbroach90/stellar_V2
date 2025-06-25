from flask import Flask, render_template, request
from smtplib import SMTP, SMTPResponseException
from dotenv import load_dotenv
import os
import requests

load_dotenv(dotenv_path=".env")
app = Flask(__name__)

# Load reCAPTCHA secret key from .env
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/elements')
def elements():
    return render_template('elements.html')

@app.route('/send_email', methods=["POST"])
def send_email():
    # Step 1: reCAPTCHA verification
    token = request.form.get("g-recaptcha-response")
    if not token:
        return render_template("email_failure.html", error="Missing reCAPTCHA token")

    recaptcha_response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={
            "secret": RECAPTCHA_SECRET_KEY,
            "response": token
        }
    )
    result = recaptcha_response.json()
    if not result.get("success") or result.get("score", 0) < 0.5:
        return render_template("email_failure.html", error="reCAPTCHA failed or suspicious activity detected.")

    # Step 2: Gather info from form
    from_email = request.form["email"]
    email_message = request.form["message"]
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]

    smtp_email = os.getenv("cj_email")
    smtp_pass = os.getenv("cj_password")

    if from_email == "" or first_name == "" or last_name == "" or email_message == "":
        return render_template("email_failure.html",
                               email=from_email,
                               name=f"{first_name} {last_name}",
                               message=email_message
                               )
    else:
        try:
            with SMTP("smtp.gmail.com", 587) as connection:
                connection.starttls()
                connection.login(user=smtp_email, password=smtp_pass)
                connection.sendmail(
                    from_addr=smtp_email,
                    to_addrs="jbroach@codejet.app",
                    msg=f"Subject: New Inquiry from {first_name} {last_name} at {from_email}!\n\n"
                        f"{email_message}")
        except SMTPResponseException as e:
            return f"Sorry we could not complete the request due to {e.smtp_error.decode('utf-8')}"
        else:
            message = "We will be in touch with you soon. Please allow 3 business days for us to respond."
            return render_template("email_success.html", result=message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True)
