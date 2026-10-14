import unittest
from datetime import date, datetime
from email.message import EmailMessage
from unittest.mock import Mock, patch
import os
import global_news as g

DAY = date(2026, 10, 13)

def raw(sender, subject="Daily news", link=True):
    msg = EmailMessage()
    msg["From"] = sender
    msg["Subject"] = subject
    msg["Message-ID"] = "<test-edition@example.com>"
    body = '<p>Research results and policy news</p>'
    if link:
        body += '<a href="https://example.com/edition">웹에서 보기</a>'
    msg.set_content(body, subtype="html")
    return msg.as_bytes()

class GlobalNewsTests(unittest.TestCase):
    def test_publishers_and_axios_exclusion(self):
        stamp = datetime.fromisoformat("2026-10-13T07:00:00+09:00")
        for sender, kind in [("flagship@semafor.com", "Flagship"),
                             ("washingtondc@semafor.com", "Washington DC"),
                             ("briefing@nature.com", "Nature Briefing"),
                             ("daily@newneek.co", "뉴닉")]:
            self.assertEqual(g.parse_source(raw(sender), stamp, DAY)["kind"], kind)
        for sender in ["macro@axios.com", "briefing@nature.com.evil.test", "x@newneek.co.evil.test"]:
            self.assertIsNone(g.parse_source(raw(sender), stamp, DAY))

    def test_confirmation_is_not_news(self):
        stamp = datetime.fromisoformat("2026-10-13T07:00:00+09:00")
        for subject in ["Nature Briefing Daily - Opt-in request", "Welcome to Nature", "뉴닉 구독 완료"]:
            self.assertIsNone(g.parse_source(raw("briefing@nature.com", subject), stamp, DAY))

    def test_newneek_onboarding_excluded(self):
        stamp = datetime.fromisoformat("2026-10-13T07:00:00+09:00")
        for subject in ["🦔뉴닉 사용법, 이건 꼭 알아야 해요! (feat. 뉴닉 활용 꿀팁.zip)",
                        "🦔[혜택 있음] 뉴니커, 만나서 반갑슴!"]:
            self.assertIsNone(g.parse_source(raw("whatsup@newneek.co", subject), stamp, DAY))
        self.assertIsNotNone(g.parse_source(raw("whatsup@newneek.co", "오늘의 주요 뉴스"), stamp, DAY))

    def test_exact_cutoff_and_next_day_carry(self):
        for stamp, included in [("2026-10-12T08:09:59+09:00", False),
                                ("2026-10-12T08:10:00+09:00", True),
                                ("2026-10-13T08:09:59+09:00", True),
                                ("2026-10-13T08:10:00+09:00", False)]:
            self.assertEqual(g.parse_source(raw("briefing@nature.com"), datetime.fromisoformat(stamp), DAY) is not None, included)

    def test_monday_includes_weekend(self):
        monday = date(2026, 10, 12)
        start, end = g.receipt_window(monday)
        self.assertEqual(start.isoformat(), "2026-10-09T08:10:00+09:00")
        self.assertEqual(end.isoformat(), "2026-10-12T08:10:00+09:00")
        self.assertIsNotNone(g.parse_source(raw("briefing@nature.com"), datetime.fromisoformat("2026-10-10T02:00:00+09:00"), monday))

    def test_mail_original_fallback_and_korean_web_link(self):
        stamp = datetime.fromisoformat("2026-10-13T07:00:00+09:00")
        source = g.parse_source(raw("briefing@nature.com", link=False), stamp, DAY)
        self.assertIn("#search/rfc822msgid", source["links"][0])
        self.assertEqual(g.parse_source(raw("daily@newneek.co"), stamp, DAY)["links"], ["https://example.com/edition"])

    def test_all_sources_search_and_read_only(self):
        mail = Mock()
        mail.list.return_value = ("OK", [b'(\\All) "/" "[Gmail]/All Mail"'])
        mail.select.return_value = ("OK", [])
        mail.uid.return_value = ("OK", [b""])
        self.assertEqual(g.collect_sources(mail, DAY), [])
        query = mail.uid.call_args.args[-1]
        for sender in ["briefing@nature.com", "@newneek.co", "flagship@semafor.com", "washingtondc@semafor.com"]:
            self.assertIn(sender, query)
        self.assertNotIn("axios", query)
        mail.select.assert_called_once_with('"[Gmail]/All Mail"', readonly=True)

    def test_partial_batch_sends_and_empty_batch_skips(self):
        source = g.parse_source(raw("flagship@semafor.com"),
                                datetime.fromisoformat("2026-10-13T07:00:00+09:00"), DAY)
        source["id"] = "s1"
        digest = {"sections": [{"title": "뉴스", "bullets": [
            {"text": "핵심 뉴스", "details": [], "sources": ["s1"]}]}]}
        mail = Mock()
        mail.login.return_value = ("OK", [])
        with patch.dict(os.environ, {"EMAIL_USER": g.SOURCE_ACCOUNT, "EMAIL_PASS": "test"}), \
             patch.object(g.imaplib, "IMAP4_SSL", return_value=mail), \
             patch.object(g, "already_reserved", return_value=False), \
             patch.object(g, "collect_sources", return_value=[source]) as collect, \
             patch.object(g, "analyze_sources", return_value=digest) as analyze, \
             patch.object(g, "deliver", return_value="sent") as deliver:
            self.assertEqual(g.run(DAY), "sent")
            analyze.assert_called_once_with([source])
            deliver.assert_called_once()
            message = deliver.call_args.args[2].get_body(preferencelist=("plain",)).get_content()
            self.assertIn("수신되지 않은 뉴스레터", message)
            self.assertIn("Nature Briefing", message)
            collect.return_value = []
            analyze.reset_mock()
            deliver.reset_mock()
            self.assertEqual(g.run(DAY), "no_sources")
            analyze.assert_not_called()
            deliver.assert_not_called()

    def test_schedule_and_transition(self):
        for stamp, expected in [("2026-10-16T08:09:59+09:00", "2026-10-15"),
                                ("2026-10-16T08:10:00+09:00", "2026-10-16"),
                                ("2026-10-17T13:00:00+09:00", "2026-10-16"),
                                ("2026-10-19T08:10:00+09:00", "2026-10-19")]:
            self.assertEqual(g.scheduled_date(datetime.fromisoformat(stamp)).isoformat(), expected)
        start, end = g.receipt_window(date(2026, 10, 15))
        self.assertEqual(start.isoformat(), "2026-10-13T23:30:00+09:00")
        self.assertEqual(end.isoformat(), "2026-10-15T08:10:00+09:00")

    def test_all_publishers_must_be_represented(self):
        sources = [{"id": f"s{i}", "kind": kind} for i, kind in enumerate(g.EXPECTED_SOURCES)]
        value = {"sections": [{"title": "뉴스", "bullets": [
            {"text": "핵심 뉴스", "details": [], "sources": ["s0"]}]}]}
        with self.assertRaisesRegex(ValueError, "omitted source"):
            g.validate_digest(value, sources)
        value["sections"][0]["bullets"][0]["sources"] = [s["id"] for s in sources]
        g.validate_digest(value, sources)

    def test_output_and_legacy_duplicate_guard(self):
        source = g.parse_source(raw("briefing@nature.com"), datetime.fromisoformat("2026-10-13T07:00:00+09:00"), DAY)
        source["id"] = "s1"
        digest = {"sections": [{"title": "과학", "bullets": [{"text": "연구 결과 발표", "details": [], "sources": ["s1"]}]}]}
        msg = g.build_message(digest, [source], DAY)
        self.assertEqual(str(msg["Subject"]), "🌐 통합 뉴스 요약 · 2026-10-13")
        text = msg.get_body(preferencelist=("plain",)).get_content()
        self.assertIn("[s1]", text)
        self.assertIn("뉴닉", text)
        self.assertIn("수집 구간", text)
        self.assertEqual(g.reservation_name(DAY), "SEMAFOR_DAILY_2026-10-13")

if __name__ == "__main__":
    unittest.main()
