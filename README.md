# Axios Macro Bot

Axios Macro 뉴스레터를 Gmail에서 가져와 한국어 시장 브리핑으로 요약하고, HTML 이메일로 전달하는 Python 자동화입니다.

## 실행 흐름

1. Gmail에서 `Axios Macro` 발신 메일 중 미처리 메일을 찾습니다.
2. 본문과 `View in browser` 원문 링크를 추출합니다.
3. OpenAI로 한국어 요약, 영어 표현, 문장 해설, 투자자 관점을 생성합니다.
4. 결과를 이메일로 보내고 Gmail 라벨로 처리 상태를 기록합니다.

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
- `AXIOS_FAILED`: 발송 또는 분석에 실패한 메일입니다. 자동 재시도하지 않으며, 원인을 확인한 뒤 라벨을 제거해 재처리합니다.

## 테스트

```bash
python -m unittest discover -s tests
```
