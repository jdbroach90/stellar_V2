"""Contract tests for paid-search conversion instrumentation (Flask integration tests also included)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ConversionContractTests(unittest.TestCase):
    def test_demo_requires_company_and_authored_message(self):
        html = (ROOT / "templates/demo.html").read_text()
        self.assertRegex(html, r'name="company"[^>]*\brequired\b')
        self.assertRegex(html, r'<textarea name="message"[^>]*\brequired\b')
        self.assertRegex(html, r'<textarea name="message"[^>]*minlength="10"')
        self.assertNotIn("<textarea name=\"message\" rows=\"3\" required maxlength=\"4000\">I'd like", html)

    def test_conversion_event_is_only_in_success_template(self):
        matches = []
        for file in (ROOT / 'templates').rglob('*.html'):
            if "'event': 'codejet_form_submitted'" in file.read_text():
                matches.append(file.relative_to(ROOT).as_posix())
        self.assertEqual(matches, ['templates/email_success.html'])
        success = (ROOT / 'templates/email_success.html').read_text()
        self.assertIn('lead_accepted | default(false)', success)
        self.assertIn('lead_transaction_id | default(none)', success)
        self.assertIn('lead_transaction_id | tojson', success)
        self.assertNotIn('customer@example.com', success)

    def test_server_requires_server_side_acceptance(self):
        server = (ROOT / 'server.py').read_text()
        self.assertIn('connection.send_message', server)
        self.assertLess(server.index('connection.send_message'), server.index('lead_transaction_id ='))
        self.assertIn('source_page == "demo" and (not company or len(message_body) < 10)', server)
        self.assertIn('secrets.token_hex(16)', server)

if __name__ == '__main__':
    unittest.main()
