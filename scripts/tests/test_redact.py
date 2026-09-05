"""Tests for review_html.redact: secret patterns and message truncation."""
from __future__ import annotations

import unittest

from review_html.redact import MESSAGE_LIMIT, PATTERNS, clean_message, redact

GH_TOKEN = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"   # 36 characters after the prefix


class RedactTest(unittest.TestCase):
    def test_pattern_count_and_order(self) -> None:
        self.assertEqual(len(PATTERNS), 7)
        self.assertTrue(PATTERNS[0].pattern.startswith("Bearer"))
        self.assertTrue(PATTERNS[-1].pattern.startswith("-----BEGIN"))

    def test_bearer_token(self) -> None:
        self.assertEqual(redact("Authorization: Bearer abc.DEF-123_x~+/== rest"),
                         "Authorization: [redacted] rest")

    def test_aws_access_key(self) -> None:
        self.assertEqual(redact("key AKIAIOSFODNN7EXAMPLE used"), "key [redacted] used")

    def test_github_token(self) -> None:
        self.assertEqual(redact(f"token {GH_TOKEN} ok"), "token [redacted] ok")
        self.assertEqual(redact("ghp_short"), "ghp_short")

    def test_slack_token(self) -> None:
        self.assertEqual(redact("xoxb-123-456-abcDEF end"), "[redacted] end")

    def test_aws_secret_access_key_assignment(self) -> None:
        self.assertEqual(redact("AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCY x"),
                         "[redacted] x")

    def test_bare_key_assignment(self) -> None:
        self.assertEqual(redact("KEY=abc123 done"), "[redacted] done")

    def test_password_colon(self) -> None:
        self.assertEqual(redact("password: hunter2\nnext"), "[redacted]\nnext")

    def test_quoted_json_key(self) -> None:
        cleaned = redact('{"api_key": "sk-abc123"}')
        self.assertIn("[redacted]", cleaned)
        self.assertNotIn("sk-abc123", cleaned)

    def test_url_with_userinfo(self) -> None:
        self.assertEqual(redact("dial postgres://user:s3cret@db.internal:5432/app failed"),
                         "dial [redacted]db.internal:5432/app failed")

    def test_pem_private_key_block(self) -> None:
        text = ("before\n-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nAAA\n"
                "-----END RSA PRIVATE KEY-----\nafter")
        self.assertEqual(redact(text), "before\n[redacted]\nafter")

    def test_plain_text_is_unchanged(self) -> None:
        self.assertEqual(redact("assert 1 == 2 in test_add"), "assert 1 == 2 in test_add")

    def test_patterns_apply_sequentially(self) -> None:
        self.assertEqual(redact("Bearer abc and AKIAIOSFODNN7EXAMPLE"),
                         "[redacted] and [redacted]")


class CleanMessageTest(unittest.TestCase):
    def test_redaction_precedes_truncation(self) -> None:
        text = "x" * 480 + GH_TOKEN + " trailing text " + "y" * 100
        cleaned = clean_message(text)
        self.assertNotIn("ghp_", cleaned)
        self.assertIn("[redacted]", cleaned)
        self.assertLessEqual(len(cleaned), MESSAGE_LIMIT)
        # truncated first, the token would be cut to 16 characters and survive
        self.assertIn("ghp_", text[:MESSAGE_LIMIT])
        self.assertEqual(redact(text[:MESSAGE_LIMIT]), text[:MESSAGE_LIMIT])

    def test_short_message_is_not_truncated(self) -> None:
        self.assertEqual(clean_message("short"), "short")

    def test_long_message_is_capped(self) -> None:
        cleaned = clean_message("z" * 1000)
        self.assertEqual(len(cleaned), MESSAGE_LIMIT)
        self.assertTrue(cleaned.endswith("…"))


if __name__ == "__main__":
    unittest.main()
