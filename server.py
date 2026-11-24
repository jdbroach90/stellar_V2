"""Public CodeJet site and contact-form delivery."""

import os
import re
import ssl
import secrets
from email.message import EmailMessage
from smtplib import SMTP, SMTPResponseException

import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request
from codejet_analytics import init_analytics
from codejet_seo import init_seo, public_context
from codejet_demo_qualification import (
    COOKIE_NAME, START_TTL, derive_secret, issue_start, qualify, validate_qualified,
)

# Local development uses .env; Render uses its service environment variables.
load_dotenv(dotenv_path=".env")
app = Flask(__name__)
init_analytics(app)
init_seo(app)

RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "6LehmW0rAAAAANOuTO8pxfN_WL28pYoIggjREAnT")
SMTP_EMAIL = os.getenv("cj_email")
SMTP_PASS = os.getenv("cj_password")
CONTACT_RECIPIENT = (os.getenv("CJ_CONTACT_RECIPIENT") or "jbroach@codejet.app").strip()
DEMO_ENGAGEMENT_SECRET = derive_secret(os.getenv("CJ_DEMO_ENGAGEMENT_SECRET", ""),
                                      os.getenv("CJ_ANALYTICS_ORIGIN_KEY", ""))

# The supplied Google tag ID is public (not an authentication secret). Keep it
# centralized so it is loaded once on each public HTML page, not on private
# analytics endpoints. Disable instantly with CJ_GOOGLE_TAG_ENABLED=0 in Render.
app.config["CJ_GOOGLE_TAG_ENABLED"] = os.getenv("CJ_GOOGLE_TAG_ENABLED", "1")
app.config["CJ_GOOGLE_TAG_ID"] = os.getenv("CJ_GOOGLE_TAG_ID", "GTM-TQ6SDXNL")
_GOOGLE_TAG_PATTERN = re.compile(r"(?:GTM-[A-Z0-9]+|GT-[A-Z0-9]+|AW-[0-9]+|G-[A-Z0-9]+)\Z")


@app.context_processor
def google_marketing_context():
    enabled = str(app.config.get("CJ_GOOGLE_TAG_ENABLED", "1")).strip().lower() in {"1", "true", "yes"}
    tag_id = str(app.config.get("CJ_GOOGLE_TAG_ID", "")).strip()
    return {"cj_google_tag_id": tag_id if enabled and _GOOGLE_TAG_PATTERN.fullmatch(tag_id) else ""}

# Input validation also prevents untrusted strings being inserted into mail headers.
EMAIL_PATTERN = re.compile(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+\Z")


def failure(message, status):
    """Show a branded failure page; never echo form data or provider details."""
    return render_template("email_failure.html", error=message), status


@app.get("/")
def home():
    return render_template("index.html", **public_context("/"))


@app.get("/demo")
def demo():
    return render_template("demo.html", recaptcha_site_key=RECAPTCHA_SITE_KEY, **public_context("/demo"))


@app.post("/demo/watch/start")
def demo_watch_start():
    """Mint a short-lived token only after the visitor clicks the demo Play button."""
    if not DEMO_ENGAGEMENT_SECRET:
        app.logger.warning("Demo qualification is not configured; regular inquiries remain available")
        return jsonify({"error": "unavailable"}), 503
    if not request.is_json:
        return jsonify({"error": "invalid_request"}), 415
    issued = issue_start(DEMO_ENGAGEMENT_SECRET)
    if not issued:
        return jsonify({"error": "unavailable"}), 503
    token, nonce = issued
    response = jsonify({"watch_token": token})
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(COOKIE_NAME, nonce, max_age=START_TTL + 1800, httponly=True,
                        secure=request.is_secure or request.host.split(":")[0] in {"codejet.app", "www.codejet.app"},
                        samesite="Lax", path="/")
    return response


@app.post("/demo/watch/qualify")
def demo_watch_qualify():
    """Check reported played ranges and elapsed time; never include visitor PII."""
    if not DEMO_ENGAGEMENT_SECRET:
        return jsonify({"error": "unavailable"}), 503
    if not request.is_json:
        return jsonify({"error": "invalid_request"}), 415
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "invalid_request"}), 400
    token = qualify(DEMO_ENGAGEMENT_SECRET, data.get("watch_token", ""),
                    request.cookies.get(COOKIE_NAME, ""),
                    data.get("played_seconds"), data.get("duration_seconds"))
    if token is None:
        return jsonify({"error": "not_qualified"}), 403
    result = jsonify({"qualified_token": token})
    result.headers["Cache-Control"] = "no-store"
    return result


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
    company = (request.form.get("company") or "").strip()
    source_page = (request.form.get("source_page") or "").strip()

    if not all((from_email, first_name, last_name, message_body)):
        return failure("Please complete every field before submitting the form.", 400)

    # The paid-search demo form intentionally requires a company and a genuine,
    # visitor-entered reporting question; the legacy homepage form is unchanged.
    if source_page == "demo" and (not company or len(message_body) < 10):
        return failure("Please provide your company and a short message about your reporting needs.", 400)

    # Reject headers with control characters rather than silently modifying input.
    header_parts = (from_email, first_name, last_name)
    if (
        not EMAIL_PATTERN.fullmatch(from_email)
        or len(from_email) > 254
        or len(first_name) > 100
        or len(last_name) > 100
        or len(company) > 120
        or len(message_body) > 4000
        or any(ord(char) < 32 or ord(char) == 127 for char in company)
        or any(ord(char) < 32 or ord(char) == 127 for part in header_parts for char in part)
    ):
        return failure("Please enter a valid name and business email.", 400)

    # This is independent of whether someone may contact us. Only an inquiry
    # following a deliberate player click and >=50% reported viewing qualifies
    # for the Google Ads conversion; no video watch is required to contact us.
    qualified_demo_id = (validate_qualified(
        DEMO_ENGAGEMENT_SECRET,
        request.form.get("demo_qualified_token", ""),
        request.cookies.get(COOKIE_NAME, ""),
    ) if source_page == "demo" else None)

    if not SMTP_EMAIL or not SMTP_PASS:
        app.logger.error("SMTP configuration is missing")
        return failure("Message delivery is temporarily unavailable. Please try again later.", 503)

    try:
        email = EmailMessage()
        email["From"] = SMTP_EMAIL
        email["To"] = CONTACT_RECIPIENT
        email["Reply-To"] = from_email
        email["Subject"] = (f"CodeJet demo inquiry from {first_name} {last_name}" if source_page == "demo"
                            else f"New Inquiry from {first_name} {last_name} at {from_email}!")
        # Only a known page label can be attached; no arbitrary form data in headers.
        context = []
        if company:
            context.append(f"Company: {company}")
        if source_page == "demo":
            context.append("Source: CodeJet demo form")
            if qualified_demo_id:
                context.append("Demo engagement: click-to-play and >=50% browser-reported playback")
            for key in ("utm_source", "utm_medium", "utm_campaign", "utm_content"):
                value = (request.form.get(key) or "").strip()
                if 0 < len(value) <= 100 and not any(ord(c) < 32 or ord(c) == 127 for c in value):
                    context.append(f"{key}: {value}")
        email.set_content(message_body + ("\n\n" + "\n".join(context) if context else ""))

        # Preserve SMTP login as configured; deliver website inquiries to the sales inbox.
        with SMTP("smtp.gmail.com", 587, timeout=20) as connection:
            connection.starttls(context=ssl.create_default_context())
            connection.login(user=SMTP_EMAIL, password=SMTP_PASS)
            connection.send_message(email, from_addr=SMTP_EMAIL, to_addrs=[CONTACT_RECIPIENT])
        # Records SMTP acceptance only, not end-to-end mailbox delivery. No visitor PII logged.
        app.logger.info("Contact inquiry accepted by Gmail SMTP (source=%s; destination=%s)",
                        "demo" if source_page == "demo" else "website", CONTACT_RECIPIENT)
    except SMTPResponseException as exc:
        # The SMTP response text may contain sensitive context; only log its code.
        app.logger.error("Contact email rejected by SMTP (code=%s)", exc.smtp_code)
        return failure("We couldn't deliver your message. Please try again later.", 502)
    except Exception as exc:
        # Never emit exception details that could contain credentials or user data.
        app.logger.error("Contact email delivery failed (type=%s)", type(exc).__name__)
        return failure("We couldn't deliver your message. Please try again later.", 502)

    message = "We will be in touch with you soon. Please allow 3 business days for us to respond."
    # Only a verified, server-validated, SMTP-accepted inquiry receives this
    # unique, non-PII transaction ID. GTM uses it to deduplicate ad conversions.
    # This is an acceptance signal, not proof of final inbox delivery.
    lead_transaction_id = "cjlead_" + secrets.token_hex(16)
    return render_template("email_success.html", result=message, lead_accepted=True,
                           lead_source="demo" if source_page == "demo" else "homepage",
                           lead_transaction_id=lead_transaction_id,
                           qualified_demo_id=qualified_demo_id), 200, {"Cache-Control": "no-store"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
