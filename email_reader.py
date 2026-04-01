import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import os

IMAP_SERVER = "imap.gmail.com"

def clean_text(text):
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        if len(line.strip()) < 30:
            continue
        if "unsubscribe" in line.lower():
            continue
        cleaned.append(line.strip())

    return "\n".join(cleaned)

LABEL_PROCESSED = "AXIOS_PROCESSED"
LABEL_FAILED = "AXIOS_FAILED"

def mark_as_processed(mail, email_id):
    mail.store(email_id, '+X-GM-LABELS', LABEL_PROCESSED)

def mark_as_failed(mail, email_id):
    mail.store(email_id, '+X-GM-LABELS', LABEL_FAILED)

def get_latest_axios_email():
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS").strip()

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(user, password)

    mail.select("inbox")

    # Axios Macro 메일 검색
    status, messages = mail.search(None, '(FROM "Axios Macro")')
    email_ids = messages[0].split()

    if not email_ids:
        print("❌ Axios 메일 없음")
        return None

    latest_email_id = None

        # ✅ 최신 메일부터 역순으로 검사
    for email_id in reversed(email_ids):
        # 라벨 / 플래그 확인
        status, msg_data = mail.fetch(email_id, "(X-GM-LABELS)")

        if status != "OK":
            continue

        labels = str(msg_data[0])

        # ✅ 이미 처리된 메일이면 skip
        if LABEL_PROCESSED in labels:
            continue

        # 👉 처리할 메일 발견
        latest_email_id = email_id
        break

    if latest_email_id is None:
        print("⏭️ 처리할 새 메일 없음")
        return None

    # 📩 메일 내용 가져오기
    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8")

    body = ""
    link = None
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                html = part.get_payload(decode=True).decode(errors="ignore")
                soup = BeautifulSoup(html, "html.parser")
                
                # 본문 텍스트
                body = soup.get_text()

                # 첫 번째 링크 추출
                link = None

                view_link = soup.find(
                    "a",
                    string=lambda text: text and "view" in text.lower() and "browser" in text.lower()
                )

                if view_link:
                    link = view_link.get("href")
                else:
                    a_tag = soup.find("a", href=True)
                    if a_tag:
                        link = a_tag["href"]
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    body = clean_text(body)

    # ✅ mail 객체 + email_id도 같이 반환 (중요)
    return subject, body, link, mail, latest_email_id