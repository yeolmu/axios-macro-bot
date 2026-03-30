import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze(text):
    prompt = f"""
You are a macro hedge fund strategist.

Summarize the following Axios Macro newsletter in Korean.

Output format:

1. 핵심 요약 (한 줄)
2. 주요 내용 (3~5 bullet points)
3. 시장 영향 (금리 / 주식 / 환율)

4. 핵심 영어 표현 5개
- 단어
- 뜻
- 기사 내 뉘앙스

5. 좋은 문장 2개
- 원문
- 해석

6. 투자 인사이트 (포지션 관점)
- 지금 시장이 risk-on / risk-off인지
- 어떤 자산이 유리한지

{text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content