import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze(text):

    # 문장 단위 분리
    sentences = text.split(". ")
    joined_text = "\n".join(sentences)

    prompt = f"""
You are a macro hedge fund strategist.

IMPORTANT:
- Preserve the original meaning exactly.
- Do NOT distort causal relationships.
- Analyze sentence by sentence.
- Do not merge meanings across sentences.
- If the sentence structure is:
  "A happened after B"
  you must clearly preserve:
    1. B happened first
    2. B caused A
    3. Then A happened

First, translate key sentences literally.
Then summarize.

Formatting (readability):
- Put one blank line between sections 1–6.
- Use a single "-" at the start of each bullet line (one idea per line).
- Keep section headings exactly as numbered below (1. … 6.).

Output format:

1. 핵심 요약 (한 줄)

2. 주요 내용 (3~5 bullet points)

3. 시장 영향 (금리 / 주식 / 환율 / 미국 채무 상황 등 기사에 맞게 선택)

4. 핵심 영어 표현 5개 (경제 맥락상 중요한 표현 우선)
- 단어
- 뜻
- 기사 내 뉘앙스

5. 문장 뜯어보기 2개
- 원문
- 직역
- 표현 설명

6. 투자 인사이트 (포지션 관점)
- risk-on / risk-off
- 유리한 자산군

Newsletter:

{joined_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content