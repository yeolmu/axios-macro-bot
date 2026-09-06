# Axios Macro Bot

Axios Macro 뉴스레터를 Gmail에서 가져와 한국어 시장 브리핑으로 요약하고, HTML 이메일로 전달하는 Python 자동화입니다.

## 실행 흐름

1. Gmail에서 `Axios Macro` 발신 메일 중 미처리 메일을 찾습니다.
2. 본문과 `View in browser` 원문 링크를 추출합니다.
3. OpenAI로 주요 항목 2~4개를 선정해 거시경제 초보자용 한국어 해설을 생성합니다.
4. 결과를 이메일로 보내고 Gmail 라벨로 처리 상태를 기록합니다.

## 브리핑 구성

기존 고정 섹션 대신 각 주요 항목을 다음 순서로 설명합니다.

- **핵심 내용**: 원문의 주요 사실과 수치, 발언 주체를 정리합니다.
- **쉽게 풀면**: 일상적인 말로 풀어 설명하고 필요한 배경을 덧붙입니다.
- **왜 중요한가**: 원문에 근거해 경제와 생활에 갖는 의미를 설명합니다.

금리·인플레이션·환율·채권 등 어려운 용어는 처음 등장할 때 짧게 설명합니다.
원문의 사실·수치·단위·비교 기준·인과관계와 불확실성을 보존하도록 지시하며,
편집자의 해석은 `해석:`, 일반 개념은 `배경 설명:`, 비유는 `이해를 위한 비유:`로 구분합니다.
원문 본문은 문장부호를 바꾸지 않고 편집 지시와 분리해 모델에 전달합니다.

전체 읽기 시간은 약 5~10분을 목표로 합니다(작성 참고: 공백 포함 약 3,000~5,000자).
원문이 짧거나 근거가 부족하면 항목 수와 분량보다 정확성을 우선합니다.
영어 표현, 문장 뜯어보기, 일반적인 투자 조언 섹션은 포함하지 않습니다.
이 구성과 분량은 모델에 전달하는 작성 지침이며, 실제 결과의 정확성과 읽기 시간을
코드로 보장하지는 않습니다.

기존 HTML 디자인, Gmail 수신·발송 및 중복 방지 로직은 그대로 사용합니다.
GitHub Actions의 기존 예약 실행은 매일 UTC 23:30(한국 시간 다음 날 오전 8:30)이며,
수동 실행 시 `retry_failed`로 실패 메일을 재시도할 수 있습니다.

## 설정

`.env.example`을 참고해 아래 환경 변수를 설정합니다. GitHub Actions에서는 같은 이름으로 repository secrets를 등록합니다.

- `OPENAI_API_KEY`
- `EMAIL_USER`
- `EMAIL_PASS` — Gmail 앱 비밀번호
- `RECEIVER_EMAIL`

로컬에서는 Python 3.11에서 다음을 실행합니다.

```bash
python -m pip install -r requirements.txt
python main.py
```

## Gmail 라벨

- `AXIOS_PROCESSING`: 발송을 시작한 메일입니다. 발송 후 상태 기록이 불완전할 때 중복 발송을 막기 위해 유지됩니다.
- `AXIOS_PROCESSED`: 정상 발송을 마친 메일입니다.
- `AXIOS_FAILED`: 발송 또는 분석에 실패한 메일입니다. 자동 재시도하지 않습니다. GitHub Actions의 수동 실행에서 `retry_failed`를 선택하면 실패분을 다시 처리하며, 성공한 메일의 라벨은 자동으로 제거됩니다.

## 테스트

```bash
python -m unittest discover -s tests
python -m compileall -q analyzer.py config.py email_reader.py main.py tests
```

테스트는 OpenAI와 메일 처리를 모의 객체로 대체하므로 API 호출이나 실제 이메일 발송이 없습니다.
분석 지침, 원문 보존, HTML 출력 호환성 및 발송 성공·실패 시 상태 처리를 확인합니다.
