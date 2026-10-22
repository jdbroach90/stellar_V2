"""Public CodeJet site and contact-form delivery."""

import os
import re
import ssl
from email.message import EmailMessage
from smtplib import SMTP, SMTPResponseException

import requests
from dotenv import load_dotenv
from flask import Flask, Response, render_template, request

# Local development uses .env; Render uses its service environment variables.
load_dotenv(dotenv_path=".env")
app = Flask(__name__)

from origin_guard import OriginGuard
app.wsgi_app = OriginGuard(app.wsgi_app)

RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")
SMTP_EMAIL = os.getenv("cj_email")
SMTP_PASS = os.getenv("cj_password")
CONTACT_RECIPIENT = "jbroach@codejet.app"

# Input validation also prevents untrusted strings being inserted into mail headers.
EMAIL_PATTERN = re.compile(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+\Z")


def failure(message, status):
    """Show a branded failure page; never echo form data or provider details."""
    return render_template("email_failure.html", error=message), status


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/demo")
def demo():
    return render_template("demo.html")


@app.get("/elements")
def elements():
    return render_template("elements.html")


@app.get("/health")
def health():
    """Simple readiness endpoint for Render and Azure Front Door GET/HEAD probes."""
    return Response("ok\n", status=200, mimetype="text/plain", headers={"Cache-Control": "no-store"})


@app.errorhandler(404)
def not_found(_error):
    return failure("That page could not be found.", 404)


@app.errorhandler(500)
def internal_error(_error):
    return failure("Something went wrong. Please try again in a moment.", 500)


@app.post("/send_email")
def send_email():
    # Don't log the reCAPTCHA token, user-submitted fields, or raw vendor responses.
    token = request.form.get("g-recaptcha-response")
    if not token:
        return failure("Verification could not be completed. Please return and try again.", 400)

    if not RECAPTCHA_SECRET_KEY:
        app.logger.error("Contact form verification is not configured")
        return failure("The contact form is temporarily unavailable. Please try again later.", 503)

    try:
        response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": token},
            timeout=10,
        )
        response.raise_for_status()
        verdict = response.json()
        if not isinstance(verdict, dict):
            raise ValueError("Invalid verification response")
    except (requests.RequestException, ValueError):
        app.logger.warning("reCAPTCHA verification service unavailable")
        return failure("Verification is temporarily unavailable. Please try again later.", 503)

    # The current index.html calls grecaptcha.execute with action='submit'.
    if (
        not verdict.get("success")
        or verdict.get("score", 0) < 0.5
        or verdict.get("action") != "submit"
    ):
        app.logger.info("reCAPTCHA verification rejected a contact submission")
        return failure("Verification was unsuccessful. Please return and try again.", 403)

    from_email = (request.form.get("email") or "").strip()
    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    message_body = (request.form.get("message") or "").strip()

    if not all((from_email, first_name, last_name, message_body)):
        return failure("Please complete every field before submitting the form.", 400)

    # Reject headers with control characters rather than silently modifying input.
    header_parts = (from_email, first_name, last_name)
    if (
        not EMAIL_PATTERN.fullmatch(from_email)
        or len(from_email) > 254
        or len(first_name) > 100
        or len(last_name) > 100
        or any(ord(char) < 32 or ord(char) == 127 for part in header_parts for char in part)
    ):
        return failure("Please enter a valid name and business email.", 400)

    if not SMTP_EMAIL or not SMTP_PASS:
        app.logger.error("SMTP configuration is missing")
        return failure("Message delivery is temporarily unavailable. Please try again later.", 503)

    try:
        email = EmailMessage()
        email["From"] = SMTP_EMAIL
        email["To"] = CONTACT_RECIPIENT
        email["Reply-To"] = from_email
        email["Subject"] = f"New Inquiry from {first_name} {last_name} at {from_email}!"
        email.set_content(message_body)

        # Preserve the current Gmail SMTP host, port, STARTTLS, login and recipient.
        with SMTP("smtp.gmail.com", 587, timeout=20) as connection:
            connection.starttls(context=ssl.create_default_context())
            connection.login(user=SMTP_EMAIL, password=SMTP_PASS)
            connection.send_message(email, from_addr=SMTP_EMAIL, to_addrs=[CONTACT_RECIPIENT])
    except SMTPResponseException as exc:
        # The SMTP response text may contain sensitive context; only log its code.
        app.logger.error("Contact email rejected by SMTP (code=%s)", exc.smtp_code)
        return failure("We couldn't deliver your message. Please try again later.", 502)
    except Exception as exc:
        # Never emit exception details that could contain credentials or user data.
        app.logger.error("Contact email delivery failed (type=%s)", type(exc).__name__)
        return failure("We couldn't deliver your message. Please try again later.", 502)

    message = "We will be in touch with you soon. Please allow 3 business days for us to respond."
    return render_template("email_success.html", result=message)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
