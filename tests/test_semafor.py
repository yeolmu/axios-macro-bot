import json
import os
import smtplib
import unittest
from datetime import date, datetime, timezone
from email.message import EmailMessage
from unittest.mock import Mock, patch

import semafor as s

DAY = date(2026, 9, 11)


def raw(sender="flagship@semafor.com", body=None):
    msg = EmailMessage()
    msg["From"] = f"Semafor <{sender}>"
    msg["Subject"] = "🟡 Test edition"
    msg["Date"] = "Thu, 10 Sep 2026 09:00:00 +0000"
    msg.set_content("plain duplicate")
    msg.add_alternative(body or '<a href="https://www.semafor.com/newsletter/2026/09/11/test">Read <b>on the web</b></a><p>News 2.5%</p>', subtype="html")
    return msg.as_bytes()


def sources():
    return [{"id": "s1", "kind": "Flagship", "subject": "Title", "text": "Source",
             "links": ["https://www.semafor.com/newsletter/flagship"]},
            {"id": "s2", "kind": "Washington DC", "subject": "DC", "text": "Other",
             "links": ["https://www.semafor.com/newsletter/dc"]}]


def digest():
    return {"sections": [{"title": "AI 규제 논의", "bullets": [
        {"text": "초당적 규제 논의 진행", "details": ["법안은 검토 단계"], "sources": ["s1", "s2"]}]}]}


class SourceTests(unittest.TestCase):
    def test_receipt_date_not_header_date_and_nested_browser_anchor(self):
        result = s.parse_source(raw(), datetime(2026, 9, 11, 10, tzinfo=timezone.utc), DAY)
        self.assertEqual(result["kind"], "Flagship")
        self.assertEqual(len(result["links"]), 1)
        self.assertIn("2.5%", result["text"])
        self.assertNotIn("plain duplicate", result["text"])

    def test_exact_kst_midnight_boundaries(self):
        for stamp, expected in [("2026-09-10T14:59:59+00:00", False),
                                ("2026-09-10T15:00:00+00:00", True),
                                ("2026-09-11T14:59:59+00:00", True),
                                ("2026-09-11T15:00:00+00:00", False)]:
            with self.subTest(stamp=stamp):
                self.assertEqual(s.parse_source(raw(), datetime.fromisoformat(stamp), DAY) is not None, expected)

    def test_other_senders_and_welcome_excluded(self):
        now = datetime(2026, 9, 11, tzinfo=timezone.utc)
        self.assertIsNone(s.parse_source(raw("flagship@semafor.com.evil.test"), now, DAY))
        self.assertIsNone(s.parse_source(raw().replace(b"Test edition", b"Welcome to Semafor"), now, DAY))

    def test_missing_or_unsafe_link_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Missing original"):
            s.parse_source(raw(body='<a href="javascript:alert(1)">Read on the web</a>'), datetime(2026, 9, 11, tzinfo=timezone.utc), DAY)

    def test_all_mail_uid_peek_and_duplicate_copy_deduplication(self):
        mail = Mock()
        mail.list.return_value = ("OK", [b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"'])
        mail.select.return_value = ("OK", [b"2"])
        fetched = ("OK", [(b'1 (INTERNALDATE "11-Sep-2026 10:00:00 +0000" BODY[] {12}', raw()), b")"])
        mail.uid.side_effect = [("OK", [b"1 2"]), fetched, fetched]
        result = s.collect_sources(mail, DAY)
        self.assertEqual(len(result), 1)
        mail.select.assert_called_once_with('"[Gmail]/All Mail"', readonly=True)
        self.assertEqual(mail.uid.call_args.args[-1], "(INTERNALDATE BODY.PEEK[])")

    def test_imap_search_failure_raises(self):
        mail = Mock()
        mail.list.return_value = ("NO", [b"failure"])
        with self.assertRaises(RuntimeError):
            s.collect_sources(mail, DAY)


class DigestTests(unittest.TestCase):
    def test_compact_validation(self):
        for mutate in [lambda d: d.update(sections=[]),
                       lambda d: d["sections"][0]["bullets"][0].update(text="x" * 121),
                       lambda d: d["sections"][0]["bullets"][0].update(sources=["s99"]),
                       lambda d: d["sections"][0]["bullets"][0].update(details=["초당적 규제 논의 진행"])]:
            candidate = digest()
            mutate(candidate)
            with self.assertRaises(ValueError):
                s.validate_digest(candidate, sources())

    def test_html_escapes_and_contains_both_original_links(self):
        candidate = digest()
        candidate["sections"][0]["title"] = "<script>x</script>"
        msg = s.build_message(candidate, sources(), DAY)
        self.assertEqual(msg["To"], s.RECIPIENT)
        markup = msg.get_body(preferencelist=("html",)).get_content()
        self.assertIn("&lt;script&gt;", markup)
        self.assertNotIn("<script>", markup)
        self.assertIn("<ul><li>", markup.replace("\n", ""))
        for source in sources():
            self.assertIn(source["links"][0], markup)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test"})
    @patch.object(s, "OpenAI")
    def test_model_gets_combined_sources_and_rejects_truncation(self, client):
        choice = client.return_value.chat.completions.create.return_value.choices.__getitem__.return_value
        choice.finish_reason = "stop"
        choice.message.content = json.dumps(digest())
        self.assertEqual(s.analyze_sources(sources()), digest())
        create = client.return_value.chat.completions.create
        self.assertEqual(create.call_count, 2)
        args = create.call_args_list[0].kwargs
        self.assertEqual(json.loads(args["messages"][1]["content"]), sources())
        self.assertEqual(create.call_args.kwargs["messages"][-2]["role"], "assistant")
        choice.finish_reason = "length"
        with self.assertRaises(ValueError):
            s.analyze_sources(sources())


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.mail = Mock()
        self.mail.list.return_value = ("OK", [None])
        self.mail.create.return_value = ("OK", [b"created"])
        self.smtp_patch = patch.object(s.smtplib, "SMTP_SSL")
        self.smtp = self.smtp_patch.start().return_value.__enter__.return_value
        self.addCleanup(self.smtp_patch.stop)

    def test_claim_before_send_and_second_run_skips(self):
        events = Mock()
        events.attach_mock(self.mail.create, "claim")
        events.attach_mock(self.smtp.send_message, "send")
        self.assertEqual(s.deliver(self.mail, "pw", "message", DAY), "sent")
        self.assertEqual([c[0] for c in events.mock_calls], ["claim", "send"])
        self.mail.list.return_value = ("OK", [b'() "/" "SEMAFOR_DAILY_2026-09-11"'])
        self.assertEqual(s.deliver(self.mail, "pw", "message", DAY), "already_reserved")
        self.smtp.send_message.assert_called_once()

    def test_concurrent_loser_never_sends(self):
        self.mail.create.return_value = ("NO", [b"already exists"])
        with self.assertRaises(RuntimeError):
            s.deliver(self.mail, "pw", "message", DAY)
        self.smtp.send_message.assert_not_called()

    def test_smtp_uncertainty_keeps_reservation(self):
        self.smtp.send_message.side_effect = smtplib.SMTPServerDisconnected("timeout")
        with self.assertRaises(smtplib.SMTPServerDisconnected):
            s.deliver(self.mail, "pw", "message", DAY)
        self.mail.delete.assert_not_called()
        self.mail.create.assert_called_once()

    def test_login_failure_does_not_reserve(self):
        self.smtp.login.side_effect = RuntimeError("credentials")
        with self.assertRaises(RuntimeError):
            s.deliver(self.mail, "pw", "message", DAY)
        self.mail.create.assert_not_called()

    def test_unknown_reservation_state_does_not_send(self):
        self.mail.list.return_value = ("NO", [])
        with self.assertRaises(RuntimeError):
            s.deliver(self.mail, "pw", "message", DAY)
        self.smtp.send_message.assert_not_called()


class RunTests(unittest.TestCase):
    @patch.dict(os.environ, {"EMAIL_USER": s.SOURCE_ACCOUNT, "EMAIL_PASS": "pw"}, clear=True)
    @patch.object(s, "imaplib")
    @patch.object(s, "collect_sources")
    @patch.object(s, "analyze_sources", return_value=digest())
    @patch.object(s, "deliver")
    def test_dry_run_and_missing_edition(self, deliver, analyze, collect, imap):
        mail = imap.IMAP4_SSL.return_value
        mail.login.return_value = ("OK", [])
        mail.list.return_value = ("OK", [None])
        collect.return_value = sources()
        self.assertEqual(s.run(DAY, dry_run=True), "dry_run_ready")
        deliver.assert_not_called()
        mail.create.assert_not_called()
        collect.return_value = sources()[:1]
        analyze.reset_mock()
        with self.assertRaisesRegex(RuntimeError, "Incomplete"):
            s.run(DAY)
        analyze.assert_not_called()
        deliver.assert_not_called()
        mail.logout.assert_called()

    @patch.object(s.imaplib, "IMAP4_SSL")
    def test_weekend_no_network(self, connect):
        self.assertEqual(s.run(date(2026, 9, 12)), "weekend")
        connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
