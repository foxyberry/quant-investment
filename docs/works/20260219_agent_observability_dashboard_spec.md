# Agent Observability Dashboard Spec (v1)

## 1. 목적

터미널을 계속 보지 않아도 다음을 한 화면에서 파악한다.

1. 각 Sub Agent가 **실제로 지금 일하고 있는지**
2. 각 Agent(또는 관측 가능한 대리 지표)가 **얼마나 토큰을 쓰고 있는지**
3. `quant-investment` / `quant-investment2` 두 레포에서 **무슨 작업이 진행 중인지**

핵심은 "보기 좋은 대시보드"가 아니라 "운영 관측 정확도"다.

---

## 2. 사용자 핵심 질문 (Primary Questions)

1. 지금 어느 레포가 실제로 동작 중인가?
2. 지금 누가(어떤 agent) 작업 중이며, 대기 중인가?
3. 토큰 사용량이 실제 활동과 일치하는가?
4. 두 레포가 동시에 반짝이는 것이 실제 상황인가, 오탐인가?

---

## 3. 범위

## In Scope (v1)

1. 레포 2개 동시 모니터링
   - `/Users/miyoungjang/Repository/quant/quant-investment`
   - `/Users/miyoungjang/Repository/quant/quant-investment2`
2. 실시간 상태 API (`/api/agent-office/status`) 확장
3. 웹 대시보드 표시
   - Runtime Telemetry
   - Recent Commands
   - 최근 커밋/작업 말풍선
4. 반짝임 규칙 개선
   - 실제 런타임 활성 레포만 애니메이션

## Out of Scope (v1)

1. Claude 내부 모든 subagent를 100% 정확한 팀명 단위로 역매핑
2. Anthropic Usage API 연동을 통한 과금 기준 완전 정합 토큰 리포트
3. 사용자/팀 권한 관리

---

## 4. 기능 요구사항

## FR-1. 레포별 실제 실행 상태

시스템은 각 레포(`qi1`, `qi2`)에 대해 아래를 표시해야 한다.

1. 최근 10분 Active Command 수
2. 마지막 실행 명령
3. 마지막 감지 시각

## FR-2. Agent 상태 가시화

시스템은 각 agent의 상태(`active`, `working`, `waiting_input`, `idle`, `sleeping`)를 표시해야 한다.

1. 상태 칩
2. 작업 말풍선
3. 클릭 시 상세(프로필 카드)

## FR-3. 토큰 관측

시스템은 관측 가능한 토큰 지표를 제공해야 한다.

1. Forked agent usage 합계(input/output)
2. 이벤트 수
3. 마지막 관측 시각

## FR-4. 오탐 줄이기

시스템은 "활동 중 애니메이션"을 실제 런타임 신호와 연결해야 한다.

1. 런타임 활성 레포만 반짝임
2. waiting_input은 기본적으로 반짝이지 않음

---

## 5. 데이터 소스 / 신뢰도

## Source A: Git Activity (레포 내부)

1. 장점: 팀별 디렉토리 기준 상태 계산 가능
2. 한계: "지금 이 순간 실행 중"을 직접 보장하지 않음

## Source B: `~/.claude/debug/*.txt`

1. 장점: 실제 Bash 실행 흔적, Forked agent usage 관측 가능
2. 한계: 로그 형식 의존, agent 이름이 `prompt_suggestion` 등으로 보일 수 있음

## Source C: Runtime Heuristic

1. 최근 명령 timestamp, 최근 N분 명령 수로 "실행 중" 추정
2. 한계: 완전한 프로세스 추적이 아니라 추정 기반

---

## 6. API 스펙 (v1)

기존 payload에 다음 필드를 포함한다.

```json
{
  "generated_at": "...",
  "projects": [...],
  "claude_limit": {...},
  "claude_code": {...},
  "recent_commands": [
    {
      "cmd": "....",
      "status": "running|done|failed",
      "label": "Running|Done|Failed",
      "time": "...",
      "source": "....txt"
    }
  ],
  "runtime": {
    "projects": {
      "qi1": {"active_commands": 0, "last_command": "", "last_seen": null},
      "qi2": {"active_commands": 0, "last_command": "", "last_seen": null}
    },
    "forked_agents": [
      {
        "repo": "qi1|qi2|unknown",
        "agent": "prompt_suggestion|...",
        "events": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "last_time": null
      }
    ]
  }
}
```

---

## 7. UI 스펙 (v1)

## 레이아웃

1. 상단: Claude Code 상태 + 현재 작업
2. 중단: 프로젝트 오피스맵
3. 하단: Runtime Telemetry, Recent Commands, Recent Commits

## 시각 규칙

1. 반짝임은 `runtime.projects[repo].active_commands > 0` 인 레포에만 적용
2. waiting_input은 반짝임 제거
3. active/working만 강한 하이라이트

---

## 8. 내가 지금 할 수 있는 것 (Codex Implementation Capability)

아래는 즉시 구현/수정 가능한 항목이다.

1. `live_server.py` 파서 로직 확장
   - debug 로그에서 명령/토큰/상태 추출
2. API 계약 확장
   - `recent_commands`, `runtime` 제공
3. 대시보드 UI/상태 연결
   - 레포별 런타임 카드, 명령 패널, 애니메이션 조건 변경
4. 민감정보 마스킹
   - token/key/secret/password 패턴 마스킹
5. 반응형/가독성 튜닝
   - 모바일 요약 모드, 데스크톱 상세 모드

---

## 9. 내가 당장은 100% 보장할 수 없는 것

1. 모든 subagent를 팀명(`designer`, `quant`, `server`...)으로 완전 정확 매핑
2. Anthropic 과금 리포트와 1:1 일치하는 정산 토큰
3. 로그 포맷 변경 시 파서 무수정 동작

해결 방향:

1. Claude 실행 훅에서 세션/agent 태그 명시 저장
2. 필요 시 외부 Usage API 연동(정식 집계)

---

## 10. 수용 기준 (Acceptance Criteria)

1. 두 레포 중 실제 실행 중인 쪽만 애니메이션이 눈에 띄어야 한다.
2. 하단 Runtime Telemetry에 레포별 Active Command 수가 표시되어야 한다.
3. Recent Commands에 최근 Bash 명령과 상태가 보여야 한다.
4. Forked Agent Token(Observed)이 비어 있지 않거나, 비었을 때 명확히 "없음"으로 표시되어야 한다.
5. API 실패 시 UI가 깨지지 않고 fallback 상태를 표시해야 한다.

---

## 11. 다음 단계 (v2 제안)

1. 팀별 확정 토큰 맵핑
   - 로그 태그 표준화
2. PID/프로세스 기반 실행 감지
   - 추정(heuristic)에서 실측(process)으로 고도화
3. Alerting
   - "10분 이상 활동 없음", "명령 실패 연속" 알림

