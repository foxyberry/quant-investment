# Slack Notification Integration

Issue: #1353

## Decision Log

### Round 1 — Planning Proposal
- Slack Incoming Webhook으로 알림 채널 추가
- 기존 `portfolio/notifiers/slack.py`의 SlackNotifier 활용
- 텔레그램 패턴 복제

### Round 2 — Dev Team Review
- **수용**: 공통 dispatcher 레이어 필요 (텔레그램 코드 중복 해소)
- **수용**: Webhook URL 암호화 + SSRF 방지 필수
- **수용**: SlackNotifier rate limit 추가
- **타협**: BrokerCredential 테이블 Phase 1 재사용, Phase 2 분리
- **반론 수용**: portfolio.yaml vs DB 분리는 의도적 — 문서화로 충분

### Round 3 — Final Agreement
- notification_dispatcher.py 신설 (통합 발송 레이어)
- 기존 텔레그램 코드도 dispatcher 경유로 리팩토링
- 일정은 개발팀이 판단

---

## Execution Units

### Unit 1: notification_dispatcher.py + telegram refactor
- `api/services/notification_dispatcher.py` 신설
- `portfolio/notifiers/MultiNotifier` 패턴 활용
- `portfolio_alert_service._send_telegram()` → dispatcher 경유
- `strategy_alert_service.fire_alert()` 내 telegram 블록 → dispatcher 경유
- 기존 텔레그램 기능 회귀 없음 확인

### Unit 2: SlackNotifier 보강
- `portfolio/notifiers/slack.py`에 rate_limit 추가
- HTTP 403/410 응답 → webhook 만료 로그
- TelegramNotifier 패턴 참고

### Unit 3: Slack settings API
- `BrokerSettingsService`에 slack 메서드 추가
- `GET/PUT /api/settings/slack`, `POST /api/settings/slack/test`
- Webhook URL Fernet 암호화
- SSRF: `https://hooks.slack.com/services/` 화이트리스트
- `VALID_CHANNELS`에 `"slack"` 추가

### Unit 4: Frontend — Slack 설정 UI
- 설정 페이지에 Slack 탭 추가
- Webhook URL 입력 (password type), 채널명, 활성화 토글, 테스트 버튼
- i18n (en/ko/zh)
