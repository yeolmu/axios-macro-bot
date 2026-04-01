import feedparser
import smtplib
from email.mime.text import MIMEText
from analyzer import analyze
import requests
from bs4 import BeautifulSoup
import os

from email_reader import (
    get_latest_axios_email,
    mark_as_processed,
    mark_as_failed
)

SENDER_EMAIL = os.getenv("EMAIL_USER")
SENDER_PASSWORD = os.getenv("EMAIL_PASS").strip()

RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

def get_latest_article():
    feed = feedparser.parse(RSS_URL)


    print("entries:", feed.entries)

    if not feed.entries:
        print("No entries found")
        return None, None

    entry = feed.entries[0]
    return entry.link, entry.title

def get_article_text(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    paragraphs = soup.find_all("p")
    text = "\n".join([p.get_text() for p in paragraphs])
    return text

def send_email(content, link):
    msg = MIMEText(content + f"\n\n원문 링크: {link}")
    msg["Subject"] = "📈 Axios Macro 요약"
    msg["From"] = f"Macro Gorilla <{SENDER_EMAIL}>"
    msg["To"] = RECEIVER_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

def main():
    result = get_latest_axios_email()

    if result is None:
        print("No email to process")
        return

    subject, text, link, mail, email_id = result

    try:
        analysis = analyze(text)
        send_email(analysis, link if link else "링크 없음")

        print("✅ 메일 발송 완료:", email_id)
        # ✅ 성공 → 처리 완료 라벨
        mark_as_processed(mail, email_id)

        print("✅ 라벨 적용 완료:", email_id)

    except Exception as e:
        print("❌ 처리 실패:", e)

        # ❌ 실패 → 실패 라벨
        mark_as_failed(mail, email_id)

if __name__ == "__main__":
    main()