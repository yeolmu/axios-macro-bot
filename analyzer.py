from openai import OpenAI

from config import get_required_env


def analyze(text):
    if not text or not text.strip():
        raise ValueError("Newsletter body is empty")

    client = OpenAI(api_key=get_required_env("OPENAI_API_KEY"))

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
- Work from the article text. When inferring market psychology or investor debate, ground it in what the article actually implies—no free-floating speculation.
- If the article says "A happened after B," keep order and causality clear: B first → link → A.
- Prefer short bullets over dense paragraphs everywhere.

Voice and style:
- Concise, intelligent, conversational but informed—like a macro-aware editor, not a lecturer.
- Prefer concrete market lines over abstract summaries (e.g. favor "시장은 다시 'higher for longer' 시나리오를 반영하기 시작했다" over vague "인플레이션 문제가 심화되고 있다" unless the article supports the latter tightly).
- Avoid dictionary tone and rigid grammar-lecture tone.
- Avoid repetitive, robotic Korean endings and hedges such as: "~가능성이 있다", "~일 수 있다", "~로 보인다". Rewrite with fresher, more direct phrasing.
- Vary sentence openings; no stacked filler commentary.

Formatting (readability):
- Use these seven section titles verbatim (including numbering):
  1. 한눈에 보기
  2. 무슨 일이 있었나
  3. 왜 중요한가
  4. 한 단계 더 생각해보기
  5. 앞으로 볼 것
  6. 핵심 영어 표현
  7. 문장 뜯어보기
- One blank line between each numbered section.
- Use "-" at the start of each bullet line. One main idea per bullet; split long ideas into multiple bullets.
- Where useful, use sub-lines indented with two spaces then "→ " for Fact → Meaning → Market impact.
- Do not omit a section. If the article does not contain enough relevant information, write "- 기사에서 명시적으로 확인되지 않음."

Section rules:

1. 한눈에 보기
- Exactly 2–3 short bullets only.
- Each bullet should capture what changed, why it matters, or the major narrative shift.
- Keep it concrete and scannable.

2. 무슨 일이 있었나
- Explain the article's key facts in logical or chronological order.
- Keep causality and timing exactly as stated in the source.
- Any numbers must include a brief explanation of why the magnitude or direction matters.
- No long paragraphs.

3. 왜 중요한가
- Explain why this development matters for the economy, markets, companies, consumers, or policy—only where supported by the article.
- Focus on the practical implication and the market narrative that may be changing.
- Prefer specific explanations over generic phrases such as "market uncertainty increased."
- Use Fact → Meaning → Market impact when helpful.

4. 한 단계 더 생각해보기
- Add 2–3 insight-forward bullets that help readers interpret the news beyond the headline.
- Clearly distinguish fact from interpretation. Begin inference-based bullets with "고려할 점:" or "기사의 흐름상 주목할 점:".
- Discuss possible debate frames, investor psychology, or second-order effects only when grounded in the article.
- Do not make unsupported forecasts or free-floating speculation.

5. 앞으로 볼 것
- List the next data points, decisions, comments, deadlines, or market signals readers should watch.
- Include a date or timing only if stated in the article.
- For each item, briefly explain what would matter and why.
- If no future event is mentioned, identify the most relevant confirmation signal implied by the article, without inventing a specific date.

6. 핵심 영어 표현
- Exactly 5 expressions taken from or clearly tied to the article.
- Include useful market/news idioms as well as economic vocabulary; prioritize expressions whose literal Korean translation can mislead.
- For each expression, use bullets:
  - English expression
  - natural Korean meaning
  - nuance explanation
  - why native speakers use it this way
  - brief real-world usage context
- Avoid dry dictionary definitions.

7. 문장 뜯어보기
- Exactly 2 examples from the article.
- For each example, use bullets:
  - original sentence (English, exactly as in article)
  - natural Korean translation
  - nuance explanation
  - why this wording is used / what it signals
  - useful sentence pattern (only if clearly relevant; otherwise omit)
- Focus on native-style English thinking, not a grammar exam.

Source article (process this):

{joined_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content
