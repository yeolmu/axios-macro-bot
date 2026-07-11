import os
import unittest
from unittest.mock import patch

from config import ConfigurationError, get_required_env
from email_reader import clean_text
from main import _build_newsletter_html, _email_subject_line


class HelperTests(unittest.TestCase):
    def test_clean_text_removes_blank_and_unsubscribe_lines(self):
        text = "\n First useful line \nunsubscribe here\nSecond line\n"
        self.assertEqual(clean_text(text), "First useful line\nSecond line")

    def test_html_email_escapes_untrusted_content(self):
        result = _build_newsletter_html("**Bold** <script>x</script>", "<title>", "https://example.com")
        self.assertIn("<strong>Bold</strong>", result)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", result)
        self.assertIn("&lt;title&gt;", result)

    def test_subject_is_bounded(self):
        subject = _email_subject_line("x" * 130)
        self.assertTrue(subject.startswith("📈 요약 · "))
        self.assertTrue(subject.endswith("..."))

    def test_required_environment_variable_is_validated(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                get_required_env("EMAIL_PASS")


if __name__ == "__main__":
    unittest.main()
