import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze(text):
    sentences = text.split(". ")
    joined_text = "\n".join(sentences)
    prompt = f"""
You are a macro hedge fund strategist.

IMPORTANT:
- Do NOT distort causal relationships.
- Preserve the original meaning exactly.
- If the sentence structure is "A happened after B",
  you must clearly reflect that B caused A.

First, translate key sentences literally.
Then summarize.

Output format:

1. 핵심 요약 (한 줄)
2. 주요 내용 (3~5 bullet points)
3. 시장 영향 (금리 / 주식 / 환율 / 미국 채무 상황 / 시장 영향 / 투자 인사이트 등 기사 내용에 맞는 항목을 선정해서 1~3개 작성성)

4. 핵심 영어 표현 5개 (원어민에게는 익숙하지만 외국인에게 배경설명이 필요한 단어 / 경제 맥락에서 다른 의미로 사용되는 단어를 먼저 선정)
- 단어
- 뜻
- 기사 내 뉘앙스

5. 문장 뜯어보기 2개
- 원문
- 해석

6. 투자 인사이트 (포지션 관점)
- 지금 시장이 risk-on / risk-off인지
- 어떤 자산이 유리한지

{joined_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content