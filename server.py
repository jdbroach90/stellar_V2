from flask import Flask, render_template, request
from smtplib import SMTP, SMTPResponseException
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv(dotenv_path=".env")
app = Flask(__name__)

# Load reCAPTCHA secret key from .env
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")
SMTP_EMAIL = os.getenv("cj_email")
SMTP_PASS = os.getenv("cj_password")


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
    print(f"[DEBUG] Received reCAPTCHA token: {token}")

    if not token:
        return render_template("email_failure.html", error="Missing reCAPTCHA token")

    try:
        recaptcha_response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": token
            }
        )
        result = recaptcha_response.json()
        print("[DEBUG] reCAPTCHA verification result:", json.dumps(result, indent=2))
    except Exception as e:
        print(f"[ERROR] reCAPTCHA verification failed: {e}")
        return render_template("email_failure.html", error="Failed to verify reCAPTCHA")

    if not result.get("success") or result.get("score", 0) < 0.5:
        return render_template("email_failure.html", error="reCAPTCHA failed or suspicious activity detected.")

    # Step 2: Gather info from form
    from_email = request.form.get("email")
    email_message = request.form.get("message")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")

    print(f"[DEBUG] Form data - From: {from_email}, Name: {first_name} {last_name}")

    if not from_email or not first_name or not last_name or not email_message:
        return render_template("email_failure.html",
                               email=from_email,
                               name=f"{first_name} {last_name}",
                               message=email_message,
                               error="Missing required form fields."
                               )

    # Step 3: Send the email
    try:
        with SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()
            connection.login(user=SMTP_EMAIL, password=SMTP_PASS)
            connection.sendmail(
                from_addr=SMTP_EMAIL,
                to_addrs="jbroach@codejet.app",
                msg=f"Subject: New Inquiry from {first_name} {last_name} at {from_email}!\n\n"
                    f"{email_message}"
            )
    except SMTPResponseException as e:
        print(f"[ERROR] Email failed: {e.smtp_error.decode('utf-8')}")
        return f"Sorry we could not complete the request due to {e.smtp_error.decode('utf-8')}"
    except Exception as e:
        print(f"[ERROR] General email send failure: {e}")
        return "Something went wrong while sending your message."

    # Step 4: Show success
    message = "We will be in touch with you soon. Please allow 3 business days for us to respond."
    return render_template("email_success.html", result=message)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True)