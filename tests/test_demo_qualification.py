"""Pure qualification logic tests; no SMTP, Flask or internet required."""
import time
import unittest
from codejet_demo_qualification import (
    derive_secret, issue_start, qualify, serializer, validate_qualified,
)


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.secret = derive_secret('separate-product-secret-' + 's'*45)
        self.start, self.nonce = issue_start(self.secret, now=time.time()-50)

    def test_requires_strong_secret(self):
        self.assertIsNone(derive_secret('short', ''))
        self.assertIsNotNone(derive_secret('', 'a'*48))

    def test_correct_coverage_and_elapsed_yields_qualified_token(self):
        qualified = qualify(self.secret, self.start, self.nonce, 43, 81)
        self.assertIsNotNone(qualified)
        self.assertEqual(validate_qualified(self.secret, qualified, self.nonce), self.nonce)

    def test_short_watch_and_seek_are_not_qualified(self):
        for played in (0, 1, 10, 39, 40):
            self.assertIsNone(qualify(self.secret, self.start, self.nonce, played, 81))

    def test_forged_cookie_or_token_rejected(self):
        self.assertIsNone(qualify(self.secret, self.start, 'other-browser', 50, 81))
        self.assertIsNone(qualify(self.secret, self.start + 'bad', self.nonce, 50, 81))
        token = qualify(self.secret, self.start, self.nonce, 50, 81)
        self.assertIsNone(validate_qualified(self.secret, token, 'other-browser'))

    def test_elapsed_wall_time_is_required(self):
        start, nonce = issue_start(self.secret)
        self.assertIsNone(qualify(self.secret, start, nonce, 50, 81))

    def test_rejects_invalid_numeric_data(self):
        values = ((float('nan'), 81), (float('inf'), 81), (50, 0),
                  (-2, 81), (100, 81), (50, float('inf')),
                  ('abc', 81), (True, 81), (50, 1000000))
        for played, duration in values:
            with self.subTest(values=(played, duration)):
                self.assertIsNone(qualify(self.secret, self.start, self.nonce, played, duration))

    def test_replay_keeps_same_transaction_id(self):
        qualified = qualify(self.secret, self.start, self.nonce, 45, 81)
        self.assertEqual(validate_qualified(self.secret, qualified, self.nonce), self.nonce)
        self.assertEqual(validate_qualified(self.secret, qualified, self.nonce), self.nonce)

if __name__ == '__main__':
    unittest.main()
