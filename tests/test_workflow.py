import os
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, call, patch

import main


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.dict(os.environ, {
            "EMAIL_USER": "sender@example.com",
            "EMAIL_PASS": "test-password",
            "RECEIVER_EMAIL": "reader@example.com",
            "RETRY_FAILED": "false",
        }))
        stack.enter_context(patch("builtins.print"))
        self.events = Mock()
        for name in (
            "get_latest_axios_email", "analyze", "send_email",
            "mark_as_processing", "mark_as_processed", "mark_as_failed", "close_mail",
        ):
            mock = stack.enter_context(patch.object(main, name))
            setattr(self, name, mock)
            self.events.attach_mock(mock, name)
        self.mail = Mock()
        self.get_latest_axios_email.return_value = (
            "Axios Macro", "source", "https://example.com", self.mail, b"42",
        )
        self.analyze.return_value = "briefing"

    def test_success_marks_processing_before_analysis_and_processed_after_send(self):
        main.main()
        self.events.assert_has_calls([
            call.mark_as_processing(self.mail, b"42"),
            call.analyze("source"),
            call.send_email("briefing", "https://example.com", "Axios Macro",
                            "sender@example.com", "test-password", "reader@example.com"),
            call.mark_as_processed(self.mail, b"42"),
            call.close_mail(self.mail),
        ])
        self.mark_as_failed.assert_not_called()
        self.get_latest_axios_email.assert_called_once()

    def test_analysis_failure_marks_failed_without_sending(self):
        self.analyze.side_effect = RuntimeError("analysis failed")
        main.main()
        self.send_email.assert_not_called()
        self.mark_as_processed.assert_not_called()
        self.mark_as_failed.assert_called_once_with(self.mail, b"42")
        self.close_mail.assert_called_once_with(self.mail)

    def test_post_send_label_failure_does_not_mark_failed_for_retry(self):
        self.mark_as_processed.side_effect = RuntimeError("label failed")
        main.main()
        self.send_email.assert_called_once()
        self.mark_as_processing.assert_called_once_with(self.mail, b"42")
        self.mark_as_failed.assert_not_called()
        self.close_mail.assert_called_once_with(self.mail)


if __name__ == "__main__":
    unittest.main()
