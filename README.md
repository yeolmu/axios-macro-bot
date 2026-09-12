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

## Semafor Daily Brief

`semafor.py`와 별도 `Semafor Daily Brief` Actions 작업을 추가했습니다.
기존 Axios 코드·예약 시간·라벨·수신자 설정은 변경하지 않습니다.

- 수신 계정: `sub.seounyeol@gmail.com`
- 대상 발신자: `flagship@semafor.com`, `washingtondc@semafor.com`
- 받는 사람: `seounyeol@gmail.com`
- 예약: 한국 시간 월~금 23:30(UTC 14:30). Actions 예약은 지연될 수 있습니다.
- 날짜: **Gmail 수신 시각의 한국 날짜**가 같은 메일만 통합합니다. 읽음/보관 여부와
  무관하게 Gmail 전체보관함을 검색합니다. 스팸·휴지통은 포함하지 않습니다.
- 실행 시점까지 도착한 당일분을 한 통으로 발송합니다. 발송 이후 도착한 메일은
  추가 발송하지 않습니다. 두 종류 중 하나가 없으면 작업을 실패로 표시하고 보류합니다.
  두 종류 모두 없거나 토·일이면 발송하지 않습니다. 이전 날짜를 자동 소급하지 않습니다.

합의한 형식대로 `오늘의 3줄`·도입부·결론 없이 주제별 1~5번 섹션으로 작성합니다.
충분한 뉴스가 있으면 5개, 부족하면 더 적게 작성하며 제목은 매일 내용에 맞게 바뀝니다.
짧은 bullet과 한 단계 하위 bullet만 사용하며 광고·협찬·문화/오락 단신·반복 부록을
제외하고 두 원문의 중복 주제를 병합합니다. 본문 최대 1,800자, bullet별 최대 120자,
섹션별 최대 3개 bullet을 검증합니다. 원문 링크는 모델이 생성하지 않고 메일의
`Read on the web` 링크를 추출하여 붙입니다. 링크 누락·형식 오류·생성 중단은 발송을 막습니다.
사실 충실성·의미상 중복/광고 제거는 모델 지침이며 기계 검증만으로 보장하지 않습니다.

### 인증과 실행

기존 `OPENAI_API_KEY`를 사용합니다. `EMAIL_PASS`가 부계정 앱 비밀번호라면 그대로
재사용하고, 다른 계정이면 `SEMAFOR_EMAIL_PASS` repository secret을 별도로 설정합니다.
계정은 `SEMAFOR_EMAIL_USER`로 지정하며 Actions에는 위 부계정이 고정되어 있습니다.
Gmail의 전체보관함이 IMAP에 표시되어 있어야 합니다.

```bash
# 당일 실제 발송
python semafor.py
# 특정 평일을 실제 원문/API로 검증: SMTP 발송·Gmail 상태 변경 없음
python semafor.py --date 2026-09-11 --dry-run --output artifacts/semafor-preview.eml
# 보류된 날짜 재실행: 예약 기록이 없는 날짜만 발송
python semafor.py --date 2026-09-11
```

Actions 수동 실행의 `digest_date`에 날짜를 입력합니다. `dry_run` 기본값은 `true`이며
미리보기 EML은 `semafor-preview` artifact에 1일간 저장됩니다. 실제 발송은 `dry_run=false`입니다.
수동 날짜는 셸 코드에 직접 삽입하지 않고 환경 변수로 전달합니다.

### 날짜별 중복 발송 방지

분석·검증 및 SMTP 로그인 성공 후 Gmail에 `SEMAFOR_DAILY_YYYY-MM-DD` 라벨(IMAP mailbox)을
**CREATE로 먼저 예약**합니다. 같은 이름이 이미 있으면 발송하지 않습니다. 라벨은 비어 있어도
계속 보존하며 모든 재실행에서 확인합니다. Actions 동시 실행 제한과 CREATE 충돌 검사로
동일 날짜의 두 실행이 동시에 발송하지 못하게 합니다. 원본 메일의 Axios 라벨은 건드리지 않습니다.

SMTP 발송 이후 프로세스 종료나 연결 끊김이 발생해도 예약을 삭제하지 않습니다.
SMTP는 정확히 한 번 전달을 보장하지 않으므로, 이 구현은 **중복 방지를 우선하는 최대 한 번의
발송 시도**입니다. 발송 직전 장애이면 메일이 누락될 수 있으며 자동 재시도하지 않습니다.
해당 날짜가 예약 상태라면 부계정 보낸메일함과 수신 계정에서 제목 `Semafor 요약 · YYYY-MM-DD`를
확인합니다. 실제로 발송되지 않았음을 확인한 경우에만 해당 날짜 예약 라벨을 수동 삭제하고
날짜를 지정해 재실행합니다. 예약 생성 전의 분석/인증 실패와 누락 메일은 안전하게 재실행할 수 있습니다.

### 검증

`python -m unittest discover -s tests`는 기존 Axios 회귀 테스트와 Semafor의 날짜 경계,
발신자 필터, MIME/원문 링크, 중복 원본 제거, compact 출력, 누락된 원문, dry-run,
예약 충돌, 재실행 및 SMTP 불확실성을 테스트합니다. 실제 이메일 원문과 미리보기는
`artifacts/`에만 저장하여 Git에서 제외합니다.
