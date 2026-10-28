# Macro Gorilla

Gmail로 받은 뉴스레터를 OpenAI로 한국어 요약하고, HTML과 일반 텍스트 이메일로 전달하는 Python 자동화입니다. GitHub 저장소 이름은 `axios-macro-bot`이며, 두 브리핑을 독립적으로 운영합니다.

## 브리핑과 예약 실행

| 구분 | Axios Macro | Global News Brief |
| --- | --- | --- |
| 원문 | Axios Macro | Semafor Flagship·Washington DC, 뉴닉, Nature Briefing Daily |
| 결과 | 거시경제 초보자용 해설 | 정치·사회·지정학·과학·기술 통합 요약 |
| 이메일 제목 | `📈 요약 · 원문 제목` | `🌐 통합 뉴스 요약 · YYYY-MM-DD` |
| 실행 파일 | [main.py](main.py) | [global_news.py](global_news.py) |
| 모델 | `gpt-6-luna` | `gpt-6.1-sol` |
| 추론 수준 | `none` | 초안·검토 모두 `low` |
| 예약 시각(KST) | 매일 08:30 | 월~금 08:10 |
| GitHub Actions cron(UTC) | `30 23 * * *` | `10 23 * * 0-4` |
| 워크플로 | [macro.yml](.github/workflows/macro.yml) | [semafor.yml](.github/workflows/semafor.yml) |

예약 시각은 실행 목표이며 GitHub Actions 부하로 지연될 수 있습니다. 통합 뉴스의 `--scheduled`는 실행 시각을 기준으로 가장 최근 평일 08:10 회차를 선택합니다. 누락된 여러 회차를 자동으로 소급 실행하지는 않습니다.

`semafor.yml`은 현재 통합 뉴스를 실행합니다. [semafor.py](semafor.py)는 기존 Semafor 전용 구현으로, 회귀 테스트를 위해 남아 있으며 예약 작업에서 실행하지 않습니다.

## 브리핑 내용과 수집 방식

### Axios Macro

- 받은편지함에서 처리 가능한 최신 Axios Macro 메일을 찾아 기본 실행당 한 통을 처리합니다. 처리·진행·실패 라벨이 있는 메일은 건너뜁니다.
- 주요 항목 2~4개를 선정하고 **핵심 내용 → 쉽게 풀면 → 왜 중요한가** 순서로 설명합니다.
- 금리·물가·환율·채권 용어를 풀어 쓰고, 해석·배경 설명·비유를 구분하도록 지시합니다. 영어 학습과 일반적인 투자 조언 섹션은 넣지 않습니다.
- 읽기 시간 5~10분, 공백 포함 약 3,000~5,000자를 목표로 하되 원문 근거가 부족하면 정확성을 우선합니다. 분량과 사실 정확성은 모델 작성 지침이며 코드로 보장되지 않습니다.

### Global News Brief

- Gmail All Mail에서 읽음·보관 여부와 관계없이 수집합니다. All Mail이 IMAP에 표시되어야 하며 스팸·휴지통은 수집 대상에서 제외됩니다.
- 발신 필터는 `flagship@semafor.com`, `washingtondc@semafor.com`, `briefing@nature.com`, 정확한 `newneek.co` 도메인입니다. Axios는 별도로 처리합니다.
- 수집 구간은 **직전 평일 08:10 이상 ~ 해당 회차 08:10 미만(KST)**입니다. 메일의 Date 헤더가 아닌 Gmail 수신 시각을 사용합니다. 월요일에는 금요일 08:10부터 주말 수신분을 포함하고, 마감 이후 도착한 원문은 다음 회차에 포함됩니다.
- 순수 인증·환영·사용법 메일을 제외하고, 본문이 같은 복제 메일은 코드로 중복 제거합니다. 같은 사건의 중복 보도 병합은 모델에 지시합니다.
- 일부 매체가 미수신·휴간이어도 수신된 원문으로 발송하고 누락 매체를 표시합니다. 원문이 전혀 없으면 발송하지 않으며, 예약 실행에서는 실패로 보고합니다.
- 주제별 1~5개 섹션, 섹션당 1~3개 bullet과 필요한 하위 bullet로 구성합니다. 각 항목 아래 **왜 중요한가:**를 한 문장(120자 이하)으로 표시해 원문에 근거한 영향·의미·맥락을 설명합니다. 도입부·오늘의 3줄·결론은 넣지 않습니다.
- 중요성 설명은 사실의 반복이나 막연한 강조 대신 누가 어떤 영향을 받는지 다룹니다. 원문에 없는 사실·예측을 보태지 않고, 편집상 추론은 `해석:`으로 구분합니다. 근거가 부족하면 파급효과를 판단하기 어렵다고 명시하도록 지시합니다. 출처 표시는 중요성 설명에도 붙습니다.
- 초안 생성 후 원문 대조 검토를 수행합니다. JSON 구조, 각 항목의 필수 `why_it_matters` 문자열, 문장당 120자, 제목·bullet·하위 bullet·중요성 설명 합계 1,800자 제한과 수집된 각 매체의 최소 한 번 인용을 코드로 검증합니다. 검증 실패 시 각 생성 단계에서 최대 두 번 수정하며, 사실 정확성과 편집 균형은 모델 지침입니다.
- 각 bullet에 `[s1]` 등 원문 식별자를 붙이고 말미에 원문 링크를 제공합니다. 웹 버전 링크가 없으면 Message-ID 기반 Gmail 검색 링크를 사용합니다.

## 설정

Python 3.11과 [requirements.txt](requirements.txt)의 패키지를 사용합니다.

```bash
python -m pip install -r requirements.txt
```

[.env.example](.env.example)은 변수명 참고용입니다. **코드는 `.env` 파일을 자동으로 읽지 않으므로**, 로컬 실행 전 셸 환경 변수로 주입해야 합니다. GitHub Actions에서는 아래 표의 Secrets를 설정합니다.

| 변수 | Axios | 통합 뉴스 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 필수 | 필수 |
| `EMAIL_USER` | 수집·발송 Gmail 계정, 필수 | 로컬 계정 선택의 대체값. Actions는 `SEMAFOR_EMAIL_USER`를 직접 지정 |
| `EMAIL_PASS` | 해당 Gmail 앱 비밀번호, 필수 | `SEMAFOR_EMAIL_PASS`가 비어 있을 때 사용하는 대체값 |
| `RECEIVER_EMAIL` | 수신 주소, 필수 | 사용하지 않음 |
| `SEMAFOR_EMAIL_USER` | 사용하지 않음 | 로컬에서 수집 계정을 명시할 때 사용 |
| `SEMAFOR_EMAIL_PASS` | 사용하지 않음 | 통합 뉴스 계정의 Gmail 앱 비밀번호 |
| `RETRY_FAILED` | `true`이면 실패 메일도 포함해 처리 가능한 메일을 반복 처리. 기본 `false` | 사용하지 않음 |

Axios Actions의 Secrets는 `OPENAI_API_KEY`, `EMAIL_USER`, `EMAIL_PASS`, `RECEIVER_EMAIL`입니다. 통합 뉴스 Actions는 `OPENAI_API_KEY`, `EMAIL_USER`, `EMAIL_PASS`, `SEMAFOR_EMAIL_PASS`를 전달하며, 비밀번호는 `SEMAFOR_EMAIL_PASS`를 우선합니다. 대체 비밀번호를 쓸 경우에도 통합 뉴스 계정의 비밀번호여야 합니다.

현재 통합 뉴스는 `global_news.py`의 `SOURCE_ACCOUNT`(`sub.seounyeol@gmail.com`)와 `RECIPIENT`(`seounyeol@gmail.com`)로 계정과 수신자가 고정되어 있습니다. 계정 선택 순서는 `SEMAFOR_EMAIL_USER` → `EMAIL_USER` → `SOURCE_ACCOUNT`이며, 선택된 주소가 `SOURCE_ACCOUNT`와 다르면 실행을 거부합니다. Actions의 `SEMAFOR_EMAIL_USER`도 같은 주소로 고정되어 있습니다. 다른 계정으로 운영하려면 환경 변수 설정 외에 코드와 워크플로의 고정값도 검토해야 합니다.

## 실행과 미리보기

환경 변수를 설정한 뒤 프로젝트 루트에서 실행합니다.

```bash
# Axios: 최신 미처리 메일 한 통을 요약하고 실제 발송
python main.py

# 통합 뉴스: 가장 최근 평일 08:10 회차를 실제 발송
python global_news.py --scheduled

# 통합 뉴스: 지정 회차를 발송·예약 없이 생성해 EML로 저장
python global_news.py --date 2026-10-28 --dry-run --output preview.eml
```

통합 뉴스의 `--date`와 `--scheduled`는 함께 사용할 수 없습니다. 둘 다 생략하면 오늘 KST 날짜를 사용합니다. 주말 회차는 건너뛰고 미래 날짜는 거부합니다. `--output`은 `--dry-run`과 함께 사용해야 합니다. 미리보기도 실제 Gmail 원문과 OpenAI API를 사용하므로 API 비용이 발생하지만, 메일 발송이나 Gmail 예약 라벨 생성은 하지 않습니다.

GitHub Actions에서 **Global News Brief → Run workflow**를 선택하면 `digest_date`로 회차를 지정할 수 있습니다. 수동 실행의 `dry_run` 기본값은 `true`이며, 생성된 EML은 `semafor-preview` 아티팩트로 1일간 보관됩니다. 실제 발송 시에는 `dry_run=false`를 선택합니다.

코드 push 시에는 통합 뉴스 워크플로의 지정 경로(모델 호출 코드·API 확인 스크립트·의존성·테스트·워크플로)가 바뀔 때 테스트만 실행합니다. README만 변경하면 이 워크플로는 실행되지 않습니다. Axios 워크플로에는 push 트리거가 없습니다.

## 중복 방지와 실패 복구

### Axios 라벨

- `AXIOS_PROCESSING`: 분석·발송 전에 붙입니다. 발송 후 완료 기록에 실패하면 유지하여 중복 발송을 막습니다.
- `AXIOS_PROCESSED`: 정상 발송과 상태 기록을 마친 메일입니다.
- `AXIOS_FAILED`: 분석 또는 발송에 실패한 메일입니다. 기본 실행에서는 재시도하지 않습니다.

실패분 재처리는 **Axios Macro Bot → Run workflow → retry_failed=true**로 실행합니다. 이 모드는 실패 메일 외에도 처리 가능한 미처리 메일을 반복 처리하며, 이미 완료되었거나 진행 중인 메일은 제외합니다. 성공하면 실패 라벨을 제거합니다. `AXIOS_PROCESSING`이 남은 메일은 실제 발송 여부를 확인한 뒤 개별적으로 판단해야 합니다.

### 통합 뉴스 회차 예약

SMTP 인증 후 Gmail에 `SEMAFOR_DAILY_YYYY-MM-DD` 라벨을 먼저 생성하고 발송합니다. 기존 Semafor와 같은 예약 이름과 Actions concurrency 그룹(`semafor-daily`)을 사용합니다. 예약이 있으면 해당 회차는 다시 발송하지 않습니다.

예약 이후 중단·타임아웃이 발생해도 라벨을 자동 삭제하지 않습니다. 이는 중복 방지를 위한 최대 한 번의 발송 시도이며 수신 성공 보장은 아닙니다. 복구 시에는 다음을 확인합니다.

1. 해당 날짜의 Actions 로그와 보낸편지함·수신함에서 실제 발송 여부를 확인합니다.
2. 미발송이 확인된 경우에만 해당 회차의 예약 라벨을 수동 해제합니다.
3. `digest_date`와 `dry_run=true`로 결과를 검토한 뒤 `dry_run=false`로 발송합니다. 예약이 없던 누락 회차도 날짜를 지정해 복구합니다.

`already_reserved`는 기존 예약으로 인한 건너뜀, `no_sources`는 원문 없음, `weekend`는 주말 건너뜀, `dry_run_ready`는 미리보기 생성 완료, `sent`는 SMTP 발송 완료를 뜻합니다. 예약 실행의 `no_sources`는 오류로 종료됩니다.

## 검증

```bash
python -m unittest discover -s tests
python -m compileall -q analyzer.py config.py email_reader.py main.py global_news.py semafor.py check_models.py tests
```

테스트는 OpenAI·메일 처리를 모의 객체로 대체하므로 실제 API 호출이나 메일 발송이 없습니다. 분석 지침, HTML 출력, 매체 분류, 수집 시각·주말 경계, 누락 매체, 출처 인용, 발송 상태와 중복 방지를 확인합니다. 실제 뉴스레터 MIME 파싱이나 요약의 사실 정확성을 보장하는 운영 검증은 별도로 필요합니다.

## 모델 전환 (2026-10-29)

Axios는 GPT-6 Luna, 통합 뉴스의 초안·원문 대조 검토는 GPT-6.1 Sol을 사용합니다. 기존 Chat Completions와 원문 전달·출력 형식은 유지합니다. OpenAI SDK는 `3.40.0`으로 고정했습니다.

- Axios: `reasoning_effort="none"`, `temperature=0.2`, `max_completion_tokens=6000`. 잘리거나 비어 있는 결과는 발송하지 않고 기존 실패 처리로 넘깁니다.
- 통합 뉴스: `reasoning_effort="low"`, `max_completion_tokens=10000`. 추론 사용 시 지원되지 않는 `temperature`를 제거했습니다. 토큰 한도는 추론과 가시 출력을 합한 상한이며, 기존 1,800자 검증과 2단계 생성·수정 절차는 유지합니다.
- 모델명·추론 수준·토큰 상한은 각 실행 파일에 고정되어 있습니다. 실제 API 사용 권한과 비용은 연결된 OpenAI API 프로젝트 기준입니다.

실제 API 연결 확인은 `python check_models.py` 또는 **Global News Brief → Run workflow → check_models=true**로 실행합니다. 가상 원문으로 Luna 한 번과 Sol 초안·검토를 호출하고 결과를 출력합니다. 이 모드에서는 Gmail 접근·발송·예약을 하지 않으며 API 비용만 발생합니다. `check_models=true`는 `dry_run` 값과 관계없이 뉴스레터 생성·발송 단계를 건너뜁니다.

호환성 근거: [공식 전환 지침](https://developers.openai.com/api/docs/guides/latest-model), [Chat Completions 토큰·추론 옵션](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## 운영 참고

2026-10-28 통합 발송 메일에서 네 매체의 출처 링크와 요약을 확인했습니다. 기존의 뉴닉·Nature 첫 수신 대기 안내는 현재 상태에 맞지 않아 제거했습니다. 이 확인은 실제 정규 뉴스레터 MIME에 대한 자동 회귀 테스트를 대신하지 않습니다.

2026-10-13에 Semafor 전용 예약을 통합 뉴스로 전환했고, 10월 14일에 일부 매체만 도착해도 발송하도록 변경했습니다. 과거 회차 복구 시 참고하도록, `2026-10-15` 회차에만 적용되는 수집 시작 예외(`2026-10-13 23:30 KST`)는 코드에 남아 있습니다. 일반 회차는 평일 08:10 경계를 사용합니다.
