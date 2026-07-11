import html
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from analyzer import analyze
from config import get_required_env

from email_reader import (
    get_latest_axios_email,
    close_mail,
    mark_as_processing,
    mark_as_processed,
    mark_as_failed
)


def _markdown_bold_to_html(text: str) -> str:
    """Convert **bold** to <strong>; escape all other text for safe HTML."""
    parts: list[str] = []
    last_end = 0
    for match in re.finditer(r"\*\*(.+?)\*\*", text, flags=re.DOTALL):
        parts.append(html.escape(text[last_end : match.start()]))
        parts.append(f"<strong>{html.escape(match.group(1))}</strong>")
        last_end = match.end()
    parts.append(html.escape(text[last_end:]))
    return "".join(parts)


def _email_subject_line(original_subject: str | None) -> str:
    base = (original_subject or "Axios Macro").strip()
    if len(base) > 120:
        base = base[:117] + "..."
    return f"📈 요약 · {base}"


def _build_newsletter_html(body_text: str, original_subject: str | None, link: str) -> str:
    safe_body = _markdown_bold_to_html(body_text.strip())
    safe_subject = html.escape((original_subject or "제목 없음").strip())
    issued = datetime.now().strftime("%Y-%m-%d %H:%M")
    has_link = bool(link and link != "링크 없음")
    safe_href = html.escape(link, quote=True) if has_link else ""

    if has_link:
        cta = f"""
        <p style="margin:28px 0 0;font-size:14px;line-height:1.5;">
          <a href="{safe_href}" style="display:inline-block;padding:10px 18px;background:#111827;color:#ffffff;
            text-decoration:none;border-radius:6px;font-weight:600;">원문 보기</a>
        </p>"""
    else:
        cta = '<p style="margin:28px 0 0;font-size:13px;color:#6b7280;">원문 링크 없음</p>'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Macro 요약</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f4f6;">
    <tr>
      <td align="center" style="padding:28px 16px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
          style="max-width:640px;background:#ffffff;border-radius:10px;border:1px solid #e5e7eb;
          box-shadow:0 1px 2px rgba(0,0,0,0.04);">
          <tr>
            <td style="padding:28px 28px 8px;font-family:Georgia,'Times New Roman',serif;">
              <p style="margin:0;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:#6b7280;">
                Axios Macro
              </p>
              <h1 style="margin:8px 0 0;font-size:22px;line-height:1.25;color:#111827;font-weight:700;">
                매크로 뉴스레터
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding:0 28px 20px;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
              font-size:13px;color:#4b5563;line-height:1.5;border-bottom:1px solid #e5e7eb;">
              <p style="margin:0;"><strong>원문 제목</strong> · {safe_subject}</p>
              <p style="margin:6px 0 0;color:#6b7280;">발행 시각 · {html.escape(issued)}</p>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 28px 32px;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;">
              <div style="margin:0;font-family:inherit;font-size:15px;line-height:1.75;color:#111827;
                white-space:pre-wrap;word-wrap:break-word;letter-spacing:0.01em;">{safe_body}</div>
              {cta}
            </td>
          </tr>
          <tr>
            <td style="padding:0 28px 24px;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
              font-size:12px;color:#9ca3af;line-height:1.5;">
              Macro Gorilla · 자동 요약. 투자 권유가 아닙니다.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_email(content, link, original_subject, sender_email, sender_password, receiver_email):
    plain = content.strip() + "\n\n—\n원문 제목: " + (original_subject or "").strip()
    plain += f"\n원문 링크: {link}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = _email_subject_line(original_subject)
    msg["From"] = f"Macro Gorilla <{sender_email}>"
    msg["To"] = receiver_email

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(
        MIMEText(
            _build_newsletter_html(content, original_subject, link),
            "html",
            "utf-8",
        )
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)

def main():
    sender_email = get_required_env("EMAIL_USER")
    sender_password = get_required_env("EMAIL_PASS")
    receiver_email = get_required_env("RECEIVER_EMAIL")
    result = get_latest_axios_email(sender_email, sender_password)

    if result is None:
        print("No email to process")
        return

    subject, text, link, mail, email_id = result

    sent = False
    try:
        mark_as_processing(mail, email_id)
        analysis = analyze(text)
        send_email(
            analysis, link if link else "링크 없음", subject,
            sender_email, sender_password, receiver_email,
        )
        sent = True

        print("✅ 메일 발송 완료:", email_id)
        # ✅ 성공 → 처리 완료 라벨
        mark_as_processed(mail, email_id)

        print("✅ 라벨 적용 완료:", email_id)

    except Exception as e:
        print("❌ 처리 실패:", e)
        if not sent:
            mark_as_failed(mail, email_id)
        else:
            print("⚠️ 메일은 발송됐지만 완료 라벨 처리에 실패했습니다. 중복 발송 방지를 위해 AXIOS_PROCESSING 라벨을 유지합니다.")
    finally:
        close_mail(mail)

if __name__ == "__main__":
    main()
