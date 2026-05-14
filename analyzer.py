import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze(text):

    # 문장 단위 분리
    sentences = text.split(". ")
    joined_text = "\n".join(sentences)

    prompt = f"""
You are the editor of a premium macro / investing newsletter for a Korean audience.
Your job is to turn the source article into a tight, scannable briefing: human voice, insight-forward, useful for both markets context and English learning.
Do NOT write like a generic AI summary, a dry analyst report, or a textbook.

Faithfulness (non-negotiable):
- Preserve the original meaning exactly; do not invent facts, numbers, or quotes.
- Do NOT distort causal relationships.
- Analyze sentence by sentence when extracting facts; do not merge meanings across sentences.
- Work from the article text; when inferring market psychology or "what investors debate," ground it in what the article actually implies—no free-floating speculation.
- If the article says "A happened after B," keep order and causality clear: B first → link → A.
- Prefer short bullets over dense paragraphs everywhere.

Voice and style:
- Concise, intelligent, conversational but informed—like a macro-aware editor, not a lecturer.
- Prefer concrete market lines over abstract summaries (e.g. favor "시장은 다시 'higher for longer' 시나리오를 반영하기 시작했다" over vague "인플레이션 문제가 심화되고 있다" unless the article supports the latter tightly).
- Avoid dictionary tone and rigid grammar-lecture tone.
- Avoid repetitive, robotic Korean endings and hedges such as: "~가능성이 있다", "~일 수 있다", "~로 보인다" (rewrite with fresher, more direct phrasing).
- Vary sentence openings; no stacked filler commentary.

Formatting (readability):
- Use these six section titles verbatim (including numbering):
  1. 한눈에 보기
  2. 무슨 일이 있었나
  3. 시장은 어떻게 반응했나
  4. 핵심 영어 표현
  5. 문장 뜯어보기
  6. 투자자 시선
- One blank line between each numbered section.
- Use "-" at the start of each bullet line. One main idea per bullet; split long ideas into multiple bullets.
- Where a bullet uses a Fact → Meaning → Market impact chain, you may use sub-lines indented with two spaces then "→ " for each step (still scannable).

Section rules:

1. 한눈에 보기
- Exactly 2–3 short bullets only.
- Each bullet: what changed, why markets care, or a major narrative shift—concrete, not textbook abstraction.

2. 무슨 일이 있었나
- Clean bullets; ideally each bullet follows Fact → Meaning → Market impact (use "→ " sub-lines as above when helpful).
- Any numbers must include brief interpretation (why the magnitude or direction matters).
- No long paragraphs.

3. 시장은 어떻게 반응했나
- Organize with sub-headings as bullets only where the article gives relevant material, in this order when applicable:
  - 금리
  - 달러
  - 장기채
  - 성장주
  - 위험자산 심리
- Skip sub-headings that the article does not support.
- Emphasize market psychology, repricing, positioning, and investor expectations—not generic textbook commentary.

4. 핵심 영어 표현
- Section title must be exactly: 핵심 영어 표현 (as part of "4. 핵심 영어 표현").
- Exactly 5 expressions taken from or clearly tied to the article.
- Do NOT only pick formal economic jargon. Include idioms and phrases native speakers use in markets and news (e.g. priced in, sticky inflation, higher for longer, pivot, cooling demand)—especially where literal translation misleads Korean learners.
- For each expression, use bullets:
  - English expression
  - natural Korean meaning (not dictionary-only)
  - nuance explanation
  - why native speakers use it this way
  - real-world usage context (brief)
- Avoid dry dictionary definitions.

5. 문장 뜯어보기
- Section title must be exactly: 문장 뜯어보기 (as part of "5. 문장 뜯어보기").
- Exactly 2 examples from the article.
- For each example, bullets:
  - original sentence (English, as in article)
  - natural Korean translation
  - nuance explanation
  - why this wording is used / what it signals
  - useful sentence pattern (only if clearly relevant; otherwise omit this sub-bullet)
- Focus on native-style English thinking, not a grammar exam.

6. 투자자 시선
- What investors are debating, what markets are worried about, what positioning might shift—tied to the article.
- Prefer specific debate frames (e.g. "시장은 이번 물가 반등이 일시적인지 재가속의 시작인지 판단하려 하고 있다") over generic lines (e.g. vague "안전자산 선호 가능성 증가").
- No generic AI-style investment platitudes.

Source article (process this):

{joined_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content