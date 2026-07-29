import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
from config import get_required_env

IMAP_SERVER = "imap.gmail.com"

def clean_text(text):
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        if line.strip() == "":
            continue
        if "unsubscribe" in line.lower():
            continue
        cleaned.append(line.strip())

    return "\n".join(cleaned)

LABEL_PROCESSED = "AXIOS_PROCESSED"
LABEL_FAILED = "AXIOS_FAILED"
LABEL_PROCESSING = "AXIOS_PROCESSING"


def _store_label(mail, email_id, operation, label):
    status, _ = mail.store(email_id, operation, label)
    if status != "OK":
        raise RuntimeError(f"Could not update Gmail label {label} for message {email_id!r}")


def _decode_part(part):
    payload = part.get_payload(decode=True) or b""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")

def mark_as_processed(mail, email_id):
    _store_label(mail, email_id, "+X-GM-LABELS", LABEL_PROCESSED)
    _store_label(mail, email_id, "-X-GM-LABELS", LABEL_PROCESSING)
    _store_label(mail, email_id, "-X-GM-LABELS", LABEL_FAILED)

def mark_as_failed(mail, email_id):
    _store_label(mail, email_id, "+X-GM-LABELS", LABEL_FAILED)
    _store_label(mail, email_id, "-X-GM-LABELS", LABEL_PROCESSING)


def mark_as_processing(mail, email_id):
    _store_label(mail, email_id, "+X-GM-LABELS", LABEL_PROCESSING)


def close_mail(mail):
    try:
        mail.close()
    except imaplib.IMAP4.error:
        pass
    finally:
        try:
            mail.logout()
        except imaplib.IMAP4.error:
            pass

def get_latest_axios_email(user=None, password=None, include_failed=False, excluded_ids=None):
    user = user or get_required_env("EMAIL_USER")
    password = password or get_required_env("EMAIL_PASS")

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(user, password)

    mail.select("inbox")

    # Axios Macro 메일 검색
    status, messages = mail.search(None, '(FROM "Axios Macro")')
    email_ids = messages[0].split()

    if not email_ids:
        print("❌ Axios 메일 없음")
        close_mail(mail)
        return None

    latest_email_id = None

        # ✅ 최신 메일부터 역순으로 검사
    excluded_ids = excluded_ids or set()
    for email_id in reversed(email_ids):
        if email_id in excluded_ids:
            continue
        # 라벨 / 플래그 확인
        status, msg_data = mail.fetch(email_id, "(X-GM-LABELS)")

        if status != "OK":
            continue

        labels = str(msg_data[0])

        # ✅ 이미 처리된 메일이면 skip
        skip_labels = (LABEL_PROCESSED, LABEL_PROCESSING)
        if not include_failed:
            skip_labels += (LABEL_FAILED,)
        if any(label in labels for label in skip_labels):
            continue

        # 👉 처리할 메일 발견
        latest_email_id = email_id
        break

    if latest_email_id is None:
        print("⏭️ 처리할 새 메일 없음")
        close_mail(mail)
        return None

    # 📩 메일 내용 가져오기
    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    subject_parts = decode_header(msg.get("Subject", ""))
    subject = "".join(
        value.decode(encoding or "utf-8", errors="replace") if isinstance(value, bytes) else value
        for value, encoding in subject_parts
    )

    text_parts = []
    html_parts = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if part.get_content_disposition() == "attachment":
                continue
            if content_type == "text/plain":
                text_parts.append(_decode_part(part))
            elif content_type == "text/html":
                html_parts.append(_decode_part(part))
    else:
        if msg.get_content_type() == "text/html":
            html_parts.append(_decode_part(msg))
        else:
            text_parts.append(_decode_part(msg))

    link = None
    if html_parts:
        soup = BeautifulSoup(html_parts[0], "html.parser")
        body = soup.get_text("\n")
        view_link = soup.find(
            "a", string=lambda value: value and "view" in value.lower() and "browser" in value.lower()
        )
        if view_link and view_link.get("href", "").startswith(("https://", "http://")):
            link = view_link["href"]
    else:
        body = "\n".join(text_parts)

    body = clean_text(body)

    # ✅ mail 객체 + email_id도 같이 반환 (중요)
    return subject, body, link, mail, latest_email_id
