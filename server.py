
from flask import Flask, render_template, request
from smtplib import SMTP, SMTPResponseException, SMTPAuthenticationError
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


# @app.route('/generic')
# def generic():
#     return render_template('generic.html')


@app.route('/elements')
def elements():
    return render_template('elements.html')


@app.route('/send_email', methods=["POST"])
def send_email():
    # Gather info from form
    from_email = request.form["email"]
    email_message = request.form["message"]
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]

    # test_email
    # smtp_email = os.getenv("email")
    # smtp_pass = os.getenv("password")

    # Prod email
    smtp_email = os.getenv("cj_email")
    smtp_pass = os.getenv("cj_password")

    if from_email == "" or first_name == "" or first_name == "" or email_message == "":
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
                    # test
                    # to_addrs=smtp_email,
                    # prod
                    to_addrs="jbroach@codejet.app",
                    msg=f"Subject: New Inquiry from {first_name} {last_name} at {from_email}!\n\n"                        
                        f"{email_message}")
        except SMTPResponseException as e:
            error_message = f"Sorry we could not complete the request due to {e.smtp_error}"
            return error_message
        else:
            message = "We will be in touch with you soon, " \
                      "please allow 3 business days for us to respond"
            return render_template("email_success.html", result=message)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True)

