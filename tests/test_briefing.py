import email
import json
import unittest
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import Mock, patch
import briefing as b


def fixture():
    source = {'id': 's1', 'kind': 'Axios Macro', 'subject': '검증 원문', 'text': '생산성 2.5% 증가. 원문 근거.',
              'article_links': ['https://www.federalreserve.gov/monetarypolicy.htm'],
              'original': 'https://mail.google.com/mail/u/0/#all/123',
              'received_at': '2026-11-27T09:00:00+09:00', 'fingerprint': 'fp1'}
    d = {'title': '성장과 정책의 향방', 'summary': [{'text': '주요 사실 요약', 'sources': ['s1']} for _ in range(3)],
         'signals': [{'label': '생산성', 'value': '2.5%', 'context': '원문 기준 증가율', 'as_of': '원문 보도 시점',
                      'source': 's1', 'evidence': '생산성 2.5% 증가.'}],
         'sections': [{'name': name, 'stories': []} for name in b.SECTIONS],
         'watchlist': [{'text': '정책 시행 여부', 'sources': ['s1']}],
         'short_reason': '검증용 작은 원문으로 구성한 짧은 호입니다.'}
    d['sections'][0]['stories'] = [{'title': '성장의 배경', 'bullets': [
        {'text': '생산성이 **2.5% 증가**했다고 원문이 보도함.', 'details': ['증가율의 비교 기준은 원문을 확인해야 함.']}],
        'sources': ['s1'], 'links': source['article_links'], 'concepts': ['통화정책'],
        'implication': '측정 시점에 따라 해석이 달라질 수 있음.'}]
    return d, [source]


class BriefingTests(unittest.TestCase):
    def setUp(self):
        self.start = b.MIGRATION_START
        self.end = datetime(2026, 11, 28, 10, tzinfo=b.KST)

    def test_slots_and_delayed_runs(self):
        for timestamp, expected in [
            ('2026-11-28T09:59:59+09:00', '2026-11-25T10:00:00+09:00'),
            ('2026-11-28T10:00:00+09:00', '2026-11-28T10:00:00+09:00'),
            ('2026-11-29T01:00:00+09:00', '2026-11-28T10:00:00+09:00'),
            ('2026-12-02T10:01:00+09:00', '2026-12-02T10:00:00+09:00')]:
            self.assertEqual(b.scheduled_slot(datetime.fromisoformat(timestamp)).isoformat(), expected)

    def test_approved_template_and_safe_mime(self):
        d, sources = fixture()
        msg, _ = b.build_message(d, sources, self.start, self.end, 'reader@example.com')
        wire = email.message_from_bytes(msg.as_bytes())
        self.assertEqual(str(email.header.make_header(email.header.decode_header(wire['Subject']))), '🌐 ' + d['title'])
        self.assertEqual(wire['From'], 'Macro Gorilla <sub.seounyeol@gmail.com>')
        markup = msg.get_body(preferencelist=('html',)).get_content()
        for expected in ['max-width:600px', 'font-size:15px;line-height:1.8', 'font-size:22px',
                         'Sarasa Mono K', 'Courier New', '#080c10', '#10161c', '#192229', '#79e2b1',
                         '[ 00 ]', '[ 05 ]', 'WATCHLIST', 'REF /', 'IMPLICATION / 해석', '수집 /']:
            self.assertIn(expected, markup)
        for excluded in ['PILOT', 'TEST', '디자인 테스트', '{{']:
            self.assertNotIn(excluded, markup)
        self.assertIn('<strong style=', markup)
        self.assertIn('&lt;script&gt;', b.rich('<script>'))

    def test_no_fabricated_signals_or_links(self):
        d, sources = fixture()
        d['signals'][0]['value'] = '3.0%'
        with self.assertRaisesRegex(ValueError, 'verbatim'):
            b.validate_digest(d, sources)
        d, sources = fixture()
        d['sections'][0]['stories'][0]['links'] = ['https://invented.example/']
        with self.assertRaisesRegex(ValueError, 'URL'):
            b.validate_digest(d, sources)

    def test_shortfall_must_be_explicit_and_unknown_sources_fail(self):
        d, sources = fixture()
        d['short_reason'] = ''
        with self.assertRaisesRegex(ValueError, 'length'):
            b.validate_digest(d, sources)
        d['short_reason'] = '자료 부족'
        d['summary'][0]['sources'] = ['s2']
        with self.assertRaisesRegex(ValueError, 'source'):
            b.validate_digest(d, sources)

    def test_missing_publishers_do_not_block(self):
        d, sources = fixture()
        self.assertEqual(b.validate_digest(d, sources), d)
        self.assertIn('미수신:', b.render(d, sources, self.start, self.end))
        d['signals'] = []
        self.assertIn('확인 가능한 시장 수치 없음', b.render(d, sources, self.start, self.end))

    def test_receipt_boundaries_backlog_and_content_dedup(self):
        mail = Mock()
        mail.select.return_value = ('OK', [])
        mail.uid.return_value = ('OK', [b'1 2 3 4 5'])
        original = EmailMessage()
        original['From'] = 'Axios Macro <macro@axios.com>'
        original['Subject'] = 'News'
        original.set_content('원문 내용')
        fetched = [(original, t, str(n), '') for n, t in enumerate([
            self.start - timedelta(seconds=1), self.start, self.end - timedelta(seconds=1), self.end, self.start])]
        with patch.object(b, 'mailbox_for', return_value='All'), patch.object(b, 'fetch_message', side_effect=fetched):
            result = b.collect_sources(mail, self.start, self.end)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['received_at'], self.start.isoformat())
        mail.uid.return_value = ('OK', [b'1'])
        with patch.object(b, 'mailbox_for', return_value='All'), patch.object(b, 'fetch_message',
                return_value=(original, self.start - timedelta(days=10), '1', 'AXIOS_FAILED')):
            self.assertEqual(len(b.collect_sources(mail, self.start, self.end, bootstrap=True)), 1)

    def test_legacy_processed_skipped_and_uncertain_delivery_blocks(self):
        mail = Mock()
        mail.select.return_value = ('OK', [])
        mail.uid.return_value = ('OK', [b'1'])
        msg = EmailMessage()
        msg['From'] = 'macro@axios.com'
        for label, expected in [('AXIOS_PROCESSED', 0), ('AXIOS_PROCESSING', None)]:
            with patch.object(b, 'mailbox_for', return_value='All'), patch.object(b, 'fetch_message', return_value=(msg, self.start, '1', label)):
                if expected is None:
                    with self.assertRaisesRegex(RuntimeError, 'ambiguous'):
                        b.collect_sources(mail, self.start, self.end, bootstrap=True)
                else:
                    self.assertEqual(len(b.collect_sources(mail, self.start, self.end, bootstrap=True)), expected)

    def test_cursor_success_recovery_and_read_only_preview(self):
        intent = {'status': 'intent', 'claim': 'claim', 'end': self.end.isoformat(), 'fingerprints': ['fp1']}
        with patch.object(b, 'read_records', return_value=[intent]), patch.object(b, 'claims', return_value=['claim']), \
             patch.object(b, 'sent_copy_exists', return_value=False), patch.object(b, 'write_record') as write:
            with self.assertRaisesRegex(RuntimeError, 'resend blocked'):
                b.load_state(Mock(), False)
            write.assert_not_called()
        with patch.object(b, 'read_records', return_value=[intent]), patch.object(b, 'claims', return_value=['claim']), \
             patch.object(b, 'sent_copy_exists', return_value=True), patch.object(b, 'write_record') as write:
            cursor, seen, bootstrap = b.load_state(Mock(), True)
            self.assertEqual(cursor, self.end)
            self.assertEqual(seen, {'fp1'})
            self.assertFalse(bootstrap)
            write.assert_not_called()

    def test_smtp_failure_preserves_intent_no_success(self):
        d, sources = fixture()
        msg, token = b.build_message(d, sources, self.start, self.end, 'reader@example.com')
        mail = Mock()
        mail.create.return_value = ('OK', [])
        smtp = Mock()
        smtp.send_message.side_effect = TimeoutError('uncertain')
        with patch.object(b.smtplib, 'SMTP_SSL') as factory, patch.object(b, 'write_record') as write:
            factory.return_value.__enter__.return_value = smtp
            with self.assertRaises(TimeoutError):
                b.deliver(mail, 'secret', msg, token, self.start, self.end, sources)
            self.assertEqual(write.call_count, 1)
            self.assertEqual(write.call_args.args[1]['status'], 'intent')
            mail.delete.assert_not_called()

    def test_atomic_claim_precedes_smtp_and_success_checkpoint_follows(self):
        d, sources = fixture()
        msg, token = b.build_message(d, sources, self.start, self.end, 'reader@example.com')
        mail, smtp = Mock(), Mock()
        mail.create.return_value = ('OK', [])
        smtp.send_message.return_value = {}
        events = []
        mail.create.side_effect = lambda name: (events.append('claim') or ('OK', []))
        smtp.send_message.side_effect = lambda message: (events.append('send') or {})
        with patch.object(b.smtplib, 'SMTP_SSL') as factory, patch.object(b, 'write_record') as write:
            factory.return_value.__enter__.return_value = smtp
            write.side_effect = lambda mail, record: events.append(record['status'])
            self.assertEqual(b.deliver(mail, 'secret', msg, token, self.start, self.end, sources), 'sent')
        self.assertEqual(events, ['claim', 'intent', 'send', 'success'])
        mail.create.side_effect = None
        mail.create.return_value = ('NO', [b'already exists'])
        with patch.object(b.smtplib, 'SMTP_SSL') as factory, patch.object(b, 'write_record') as write:
            factory.return_value.__enter__.return_value = smtp
            smtp.reset_mock()
            with self.assertRaises(RuntimeError):
                b.deliver(mail, 'secret', msg, token, self.start, self.end, sources)
            smtp.send_message.assert_not_called()
            write.assert_not_called()

    def test_dry_run_never_reserves_or_sends(self):
        d, sources = fixture()
        with patch.dict(b.os.environ, {'EMAIL_USER': b.SOURCE_ACCOUNT, 'EMAIL_PASS': 'secret', 'RECEIVER_EMAIL': 'reader@example.com'}), \
             patch.object(b.imaplib, 'IMAP4_SSL') as factory, \
             patch.object(b, 'load_state', return_value=(self.start, set(), False)), \
             patch.object(b, 'collect_sources', return_value=sources), \
             patch.object(b, 'analyze_sources', return_value=d), patch.object(b, 'deliver') as deliver, \
             patch.object(Path, 'mkdir'), patch.object(Path, 'write_text'), patch.object(Path, 'write_bytes'):
            factory.return_value.login.return_value = ('OK', [])
            with patch.object(b, 'datetime', wraps=datetime) as clock:
                clock.now.return_value = self.end + timedelta(days=1)
                self.assertEqual(b.run(self.end, dry_run=True), 'dry_run_ready')
            deliver.assert_not_called()
            factory.return_value.create.assert_not_called()
            factory.return_value.append.assert_not_called()

    def test_only_new_workflow_can_send(self):
        root = Path(__file__).resolve().parents[1] / '.github/workflows'
        for old in ('macro.yml', 'semafor.yml'):
            content = (root / old).read_text(encoding='utf-8')
            self.assertNotIn('schedule:', content)
            self.assertNotIn('secrets.', content)
        content = (root / 'briefing.yml').read_text(encoding='utf-8')
        self.assertIn("cron: '0 1 * * 3,6'", content)
        self.assertIn('cancel-in-progress: false', content)
        self.assertIn("if: github.event_name != 'push'", content)

    def test_generation_repairs_then_reviews_before_delivery(self):
        d, sources = fixture()
        client = Mock()
        def response(content, reason='stop'):
            return Mock(choices=[Mock(finish_reason=reason, message=Mock(content=content))])
        client.chat.completions.create.side_effect = [response('{}'), response(json.dumps(d)), response(json.dumps(d))]
        with patch.dict(b.os.environ, {'OPENAI_API_KEY': 'test-only'}), patch.object(b, 'OpenAI') as factory:
            factory.return_value.__enter__.return_value = client
            self.assertEqual(b.analyze_sources(sources), d)
        self.assertEqual(client.chat.completions.create.call_count, 3)
        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual(request['model'], 'gpt-6.1-sol')
        self.assertEqual(request['response_format'], {'type': 'json_object'})
        self.assertIn('원문과 대조', request['messages'][-1]['content'])
        client.chat.completions.create.side_effect = [response('{}', 'length')]
        with patch.dict(b.os.environ, {'OPENAI_API_KEY': 'test-only'}), patch.object(b, 'OpenAI') as factory:
            factory.return_value.__enter__.return_value = client
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                b.analyze_sources(sources)


if __name__ == '__main__':
    unittest.main()
