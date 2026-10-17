"""Run from the repository root: python -m unittest discover -s tests -v"""

import unittest
from smtplib import SMTPResponseException
from unittest.mock import Mock, patch

import server


class ContactTests(unittest.TestCase):
    def setUp(self):
        server.app.config.update(TESTING=True)
        self.client = server.app.test_client()
        self.old_credentials = (server.RECAPTCHA_SECRET_KEY, server.SMTP_EMAIL, server.SMTP_PASS)
        server.RECAPTCHA_SECRET_KEY = "test-captcha-secret"
        server.SMTP_EMAIL = "test-sender@example.com"
        server.SMTP_PASS = "test-smtp-password"
        self.form = {
            "g-recaptcha-response": "PRIVATE_TEST_TOKEN",
            "email": "customer@example.com",
            "first_name": "Test",
            "last_name": "Customer",
            "message": "Interested in a demo.",
        }

    def tearDown(self):
        server.RECAPTCHA_SECRET_KEY, server.SMTP_EMAIL, server.SMTP_PASS = self.old_credentials

    def captcha_ok(self):
        response = Mock()
        response.json.return_value = {"success": True, "score": 0.9, "action": "submit"}
        response.raise_for_status.return_value = None
        return response

    def test_health_get_and_head(self):
        for method in ("GET", "HEAD"):
            with self.subTest(method=method):
                response = self.client.open("/health", method=method)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(self.client.get("/health").data, b"ok\n")

    @patch.object(server.requests, "post")
    def test_missing_token_displays_failure_page(self, post):
        response = self.client.post("/send_email", data={"first_name": "Test"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"We couldn't complete your request", response.data)
        post.assert_not_called()

    @patch.object(server.requests, "post")
    def test_captcha_denial(self, post):
        post.return_value = self.captcha_ok()
        post.return_value.json.return_value["score"] = 0.1
        response = self.client.post("/send_email", data=self.form)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"customer@example.com", response.data)

    @patch.object(server.requests, "post")
    def test_deliver_and_reply_to(self, post):
        post.return_value = self.captcha_ok()
        with patch.object(server, "SMTP") as smtp_class:
            response = self.client.post("/send_email", data=self.form)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Message Received", response.data)
            smtp_connection = smtp_class.return_value.__enter__.return_value
            smtp_connection.login.assert_called_once_with(
                user="test-sender@example.com", password="test-smtp-password"
            )
            msg = smtp_connection.send_message.call_args.args[0]
            self.assertEqual(msg["Reply-To"], "customer@example.com")
            self.assertEqual(msg["To"], "jbroach@codejet.app")
            self.assertIn("Interested in a demo.", msg.get_content())

    @patch.object(server.requests, "post")
    def test_smtp_errors_have_no_private_data(self, post):
        post.return_value = self.captcha_ok()
        with patch.object(server, "SMTP") as smtp_class:
            smtp_class.return_value.__enter__.return_value.login.side_effect = SMTPResponseException(
                535, b"SECRET_AUTH_RESPONSE"
            )
            with self.assertLogs(server.app.logger, level="ERROR") as capture:
                response = self.client.post("/send_email", data=self.form)
            self.assertEqual(response.status_code, 502)
            self.assertIn(b"We couldn&#39;t deliver your message", response.data)
            self.assertNotIn(b"SECRET_AUTH_RESPONSE", response.data)
            self.assertNotIn("SECRET_AUTH_RESPONSE", "\n".join(capture.output))
            self.assertNotIn("customer@example.com", "\n".join(capture.output))
            self.assertNotIn("PRIVATE_TEST_TOKEN", "\n".join(capture.output))

    @patch.object(server.requests, "post")
    def test_header_injection_rejected(self, post):
        post.return_value = self.captcha_ok()
        data = {**self.form, "first_name": "Test\r\nBcc: target@example.org"}
        response = self.client.post("/send_email", data=data)
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
