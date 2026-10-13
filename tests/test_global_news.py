import unittest
from datetime import date, datetime
from email.message import EmailMessage
from unittest.mock import Mock
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
        stamp = datetime.fromisoformat("2026-10-13T10:00:00+09:00")
        for sender, kind in [("flagship@semafor.com", "Flagship"),
                             ("washingtondc@semafor.com", "Washington DC"),
                             ("briefing@nature.com", "Nature Briefing"),
                             ("daily@newneek.co", "뉴닉")]:
            self.assertEqual(g.parse_source(raw(sender), stamp, DAY)["kind"], kind)
        for sender in ["macro@axios.com", "briefing@nature.com.evil.test", "x@newneek.co.evil.test"]:
            self.assertIsNone(g.parse_source(raw(sender), stamp, DAY))

    def test_confirmation_is_not_news(self):
        stamp = datetime.fromisoformat("2026-10-13T22:00:00+09:00")
        for subject in ["Nature Briefing Daily - Opt-in request", "Welcome to Nature", "뉴닉 구독 완료"]:
            self.assertIsNone(g.parse_source(raw("briefing@nature.com", subject), stamp, DAY))

    def test_newneek_onboarding_excluded(self):
        stamp = datetime.fromisoformat("2026-10-13T22:22:00+09:00")
        for subject in ["🦔뉴닉 사용법, 이건 꼭 알아야 해요! (feat. 뉴닉 활용 꿀팁.zip)",
                        "🦔[혜택 있음] 뉴니커, 만나서 반갑슴!"]:
            self.assertIsNone(g.parse_source(raw("whatsup@newneek.co", subject), stamp, DAY))
        self.assertIsNotNone(g.parse_source(raw("whatsup@newneek.co", "오늘의 주요 뉴스"), stamp, DAY))

    def test_exact_cutoff_and_next_day_carry(self):
        for stamp, included in [("2026-10-12T23:29:59+09:00", False),
                                ("2026-10-12T23:30:00+09:00", True),
                                ("2026-10-13T23:29:59+09:00", True),
                                ("2026-10-13T23:30:00+09:00", False)]:
            self.assertEqual(g.parse_source(raw("briefing@nature.com"), datetime.fromisoformat(stamp), DAY) is not None, included)

    def test_monday_includes_weekend(self):
        monday = date(2026, 10, 12)
        start, end = g.receipt_window(monday)
        self.assertEqual(start.isoformat(), "2026-10-09T23:30:00+09:00")
        self.assertEqual(end.isoformat(), "2026-10-12T23:30:00+09:00")
        self.assertIsNotNone(g.parse_source(raw("briefing@nature.com"), datetime.fromisoformat("2026-10-10T02:00:00+09:00"), monday))

    def test_mail_original_fallback_and_korean_web_link(self):
        stamp = datetime.fromisoformat("2026-10-13T10:00:00+09:00")
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

    def test_output_and_legacy_duplicate_guard(self):
        source = g.parse_source(raw("briefing@nature.com"), datetime.fromisoformat("2026-10-13T10:00:00+09:00"), DAY)
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
