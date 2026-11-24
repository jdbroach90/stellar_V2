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
        self.old_demo_secret = server.DEMO_ENGAGEMENT_SECRET
        server.DEMO_ENGAGEMENT_SECRET = 'x' * 64
        self.form = {"g-recaptcha-response": "TEST_TOKEN", "email": "customer@example.com",
                     "first_name": "Test", "last_name": "Customer", "company": "Sample Store Group",
                     "message": "Interested in understanding gross profit by store",
                     "source_page": "demo"}

    def tearDown(self):
        server.app.config.clear()
        server.app.config.update(self.old)
        server.RECAPTCHA_SECRET_KEY, server.SMTP_EMAIL, server.SMTP_PASS = self.old_creds
        server.DEMO_ENGAGEMENT_SECRET = self.old_demo_secret

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
                self.assertNotIn('codejet_demo_engaged_lead', content)
        for path in ('/health', '/elements', '/_cj/analytics'):
            self.assertNotIn('GTM-TQ6SDXNL', self.client.get(path).get_data(as_text=True))

    def test_good_post_marks_lead_only_after_smtp_acceptance(self):
        with patch.object(server.requests, 'post', return_value=self.captcha_ok()), \
             patch.object(server, 'SMTP'):
            content = self.client.post('/send_email', data=self.form).get_data(as_text=True)
        self.assertEqual(content.count('gtm.js?id=GTM-TQ6SDXNL'), 1)
        self.assertEqual(content.count("'event': 'codejet_inquiry_accepted'"), 1)
        self.assertEqual(content.count("'event': 'codejet_form_submitted'"), 1)
        self.assertRegex(content, r'cjlead_[0-9a-f]{32}')
        self.assertNotIn("'event': 'codejet_demo_engaged_lead'", content)
        self.assertIn('"demo"', content)
        self.assertNotIn('customer@example.com', content)
        self.assertNotIn('TEST_TOKEN', content)
        self.assertNotIn('Interested in understanding gross profit by store', content)
        self.assertNotIn('send_to', content)
        self.assertIn('noindex, nofollow', content)

    def test_no_conversion_on_rejected_inquiries(self):
        response = self.client.post('/send_email', data={**self.form, 'g-recaptcha-response': ''})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('codejet_demo_engaged_lead', response.get_data(as_text=True))
        self.assertNotIn('codejet_form_submitted', response.get_data(as_text=True))
        with patch.object(server.requests, 'post', return_value=self.captcha_ok()), \
             patch.object(server, 'SMTP') as smtp:
            smtp.return_value.__enter__.return_value.send_message.side_effect = RuntimeError('test failure')
            response = self.client.post('/send_email', data=self.form)
            self.assertEqual(response.status_code, 502)
            self.assertNotIn('codejet_demo_engaged_lead', response.get_data(as_text=True))
            self.assertNotIn('codejet_form_submitted', response.get_data(as_text=True))

    def test_only_a_valid_watched_demo_form_emits_qualified_lead(self):
        import time
        from codejet_demo_qualification import serializer
        start = self.client.post('/demo/watch/start', json={})
        self.assertEqual(start.status_code, 200)
        token = start.get_json()['watch_token']
        payload = serializer(server.DEMO_ENGAGEMENT_SECRET).loads(token)
        payload['started'] = int(time.time()) - 55
        watched_token = serializer(server.DEMO_ENGAGEMENT_SECRET).dumps(payload)
        short = self.client.post('/demo/watch/qualify', json={
            'watch_token': watched_token, 'played_seconds': 12, 'duration_seconds': 81})
        self.assertEqual(short.status_code, 403)
        full = self.client.post('/demo/watch/qualify', json={
            'watch_token': watched_token, 'played_seconds': 45, 'duration_seconds': 81})
        self.assertEqual(full.status_code, 200)
        qualified = full.get_json()['qualified_token']
        with patch.object(server.requests, 'post', return_value=self.captcha_ok()), \
             patch.object(server, 'SMTP'):
            content = self.client.post('/send_email', data={**self.form,
                'demo_qualified_token': qualified}).get_data(as_text=True)
        self.assertEqual(content.count("'event': 'codejet_demo_engaged_lead'"), 1)
        self.assertEqual(content.count("'event': 'codejet_inquiry_accepted'"), 1)
        self.assertEqual(content.count("'event': 'codejet_form_submitted'"), 1)
        self.assertRegex(content, r'cjlead_[0-9a-f]{32}')
        self.assertIn(payload['nonce'], content)
        self.assertNotIn('customer@example.com', content)
        self.assertNotIn('TEST_TOKEN', content)
        # A different browser without the matching flow cookie cannot claim the same token.
        other = server.app.test_client()
        with patch.object(server.requests, 'post', return_value=self.captcha_ok()), \
             patch.object(server, 'SMTP'):
            other_content = other.post('/send_email', data={**self.form,
                'demo_qualified_token': qualified}).get_data(as_text=True)
        self.assertNotIn("'event': 'codejet_demo_engaged_lead'", other_content)

    def test_demo_form_requires_company_and_customer_written_message(self):
        for override in ({"company": ""}, {"message": ""}, {"message": "too short"}):
            with self.subTest(override=override), \
                 patch.object(server.requests, 'post', return_value=self.captcha_ok()), \
                 patch.object(server, 'SMTP') as smtp:
                data = {**self.form, **override}
                response = self.client.post('/send_email', data=data)
                self.assertEqual(response.status_code, 400)
                self.assertNotIn('codejet_form_submitted', response.get_data(as_text=True))
                smtp.assert_not_called()

    def test_each_accepted_inquiry_gets_a_unique_non_pii_transaction_id(self):
        import re
        ids = []
        for _ in range(2):
            with patch.object(server.requests, 'post', return_value=self.captcha_ok()), \
                 patch.object(server, 'SMTP'):
                response = self.client.post('/send_email', data=self.form)
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertEqual(html.count("'event': 'codejet_form_submitted'"), 1)
            ids.extend(re.findall(r'cjlead_[0-9a-f]{32}', html))
            self.assertNotIn('customer@example.com', html)
            self.assertNotIn('Sample Store Group', html)
        self.assertEqual(len(ids), 2)
        self.assertNotEqual(ids[0], ids[1])

    def test_homepage_remains_eligible_without_company(self):
        data = {k:v for k,v in self.form.items() if k not in ('company', 'source_page')}
        with patch.object(server.requests, 'post', return_value=self.captcha_ok()), \
             patch.object(server, 'SMTP'):
            response = self.client.post('/send_email', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("'event': 'codejet_form_submitted'", response.get_data(as_text=True))

    def test_tag_switch_is_respected_and_invalid_ids_not_rendered(self):
        server.app.config['CJ_GOOGLE_TAG_ENABLED'] = '0'
        self.assertNotIn('gtm.js?', self.client.get('/demo').get_data(as_text=True))
        server.app.config['CJ_GOOGLE_TAG_ENABLED'] = '1'
        server.app.config['CJ_GOOGLE_TAG_ID'] = '<img onerror=alert(1)>'
        self.assertNotIn('gtm.js?', self.client.get('/demo').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
