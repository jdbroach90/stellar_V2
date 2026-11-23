"""Google tag regression: one public tag and no false lead conversions."""
import unittest
from unittest.mock import Mock, patch

import server


class GoogleTagTests(unittest.TestCase):
    def setUp(self):
        self.old = dict(server.app.config)
        server.app.config.update(TESTING=True, CJ_GOOGLE_TAG_ENABLED="1",
                                 CJ_GOOGLE_TAG_ID="GTM-TQ6SDXNL")
        self.client = server.app.test_client()
        self.old_creds = (server.RECAPTCHA_SECRET_KEY, server.SMTP_EMAIL, server.SMTP_PASS)
        server.RECAPTCHA_SECRET_KEY = 'test-recaptcha-secret'
        server.SMTP_EMAIL = 'test-sender@example.com'
        server.SMTP_PASS = 'test-password'
        self.form = {"g-recaptcha-response": "TEST_TOKEN", "email": "customer@example.com",
                     "first_name": "Test", "last_name": "Customer", "message": "Interested in CodeJet",
                     "source_page": "demo"}

    def tearDown(self):
        server.app.config.clear()
        server.app.config.update(self.old)
        server.RECAPTCHA_SECRET_KEY, server.SMTP_EMAIL, server.SMTP_PASS = self.old_creds

    @staticmethod
    def captcha_ok():
        response = Mock()
        response.json.return_value = {"success": True, "score": 0.9, "action": "submit"}
        return response

    def test_only_one_tag_on_public_pages_and_no_legacy_universal_analytics(self):
        for path in ('/', '/demo', '/retail-analytics-software',
                     '/retail-reporting-automation', '/retail-data-questions'):
            with self.subTest(path=path):
                content = self.client.get(path).get_data(as_text=True)
                self.assertEqual(content.count('gtm.js?id=GTM-TQ6SDXNL'), 1)
                self.assertEqual(content.count('function gtag()'), 1)
                self.assertNotIn('UA-226912949-1', content)
                self.assertNotIn('codejet_lead_success', content)
        for path in ('/health', '/elements', '/_cj/analytics'):
            self.assertNotIn('GTM-TQ6SDXNL', self.client.get(path).get_data(as_text=True))

    def test_good_post_marks_lead_only_after_smtp_acceptance(self):
        with patch.object(server.requests, 'post', return_value=self.captcha_ok()), \
             patch.object(server, 'SMTP'):
            content = self.client.post('/send_email', data=self.form).get_data(as_text=True)
        self.assertEqual(content.count('gtm.js?id=GTM-TQ6SDXNL'), 1)
        self.assertEqual(content.count("'event': 'codejet_lead_success'"), 1)
        self.assertIn('"demo"', content)
        self.assertNotIn('customer@example.com', content)
        self.assertNotIn('TEST_TOKEN', content)
        self.assertNotIn('Interested in CodeJet', content)
        self.assertNotIn('send_to', content)
        self.assertIn('noindex, nofollow', content)

    def test_no_conversion_on_rejected_inquiries(self):
        response = self.client.post('/send_email', data={**self.form, 'g-recaptcha-response': ''})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('codejet_lead_success', response.get_data(as_text=True))
        with patch.object(server.requests, 'post', return_value=self.captcha_ok()), \
             patch.object(server, 'SMTP') as smtp:
            smtp.return_value.__enter__.return_value.send_message.side_effect = RuntimeError('test failure')
            response = self.client.post('/send_email', data=self.form)
            self.assertEqual(response.status_code, 502)
            self.assertNotIn('codejet_lead_success', response.get_data(as_text=True))

    def test_tag_switch_is_respected_and_invalid_ids_not_rendered(self):
        server.app.config['CJ_GOOGLE_TAG_ENABLED'] = '0'
        self.assertNotIn('gtm.js?', self.client.get('/demo').get_data(as_text=True))
        server.app.config['CJ_GOOGLE_TAG_ENABLED'] = '1'
        server.app.config['CJ_GOOGLE_TAG_ID'] = '<img onerror=alert(1)>'
        self.assertNotIn('gtm.js?', self.client.get('/demo').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
