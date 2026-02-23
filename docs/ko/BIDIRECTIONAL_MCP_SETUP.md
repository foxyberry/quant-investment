# 양방향 MCP 설정: Claude Code <-> Codex CLI

이 문서는 [영문 버전](../BIDIRECTIONAL_MCP_SETUP.md)의 번역입니다.

Claude Code와 OpenAI Codex CLI 간의 양방향 MCP (Model Context Protocol) 설정 과정을 기록합니다. 각 도구가 상대방을 MCP 서버로 호출할 수 있습니다.

## 개요

| 방향 | 호출자 (클라이언트) | 피호출자 (서버) | 상태 |
|------|-------------------|----------------|------|
| 정방향 | Claude Code | Codex CLI | 설정 완료 |
| 역방향 | Codex CLI | Claude Code | 설정 완료 |

### 왜 양방향인가?

- **Claude Code -> Codex**: 코드 구현, 리뷰, 파일 수정을 Codex에 위임하고 Claude Code가 오케스트레이션
- **Codex -> Claude Code**: Codex 세션에서 Claude의 파일 편집, 코드 분석, 도구 활용
- **토큰 최적화**: 한쪽 모델의 컨텍스트가 부족할 때 다른 쪽으로 핸드오프

## 사전 요구 사항

| 도구 | 버전 | 경로 |
|------|------|------|
| Claude Code | 2.1.50+ | `/Users/miyoungjang/.local/bin/claude` |
| Codex CLI | 0.104.0+ | `/opt/homebrew/bin/codex` |

```bash
# 설치 확인
claude --version   # 예상: 2.x.x (Claude Code)
codex --version    # 예상: codex-cli 0.x.x
```

## 설정 과정

### 방향 1: Claude Code -> Codex (정방향)

Claude Code가 Codex를 MCP 서버로 호출합니다. `npx @openai/codex mcp-server`를 사용합니다.

**설정 파일**: `~/.claude/settings.json`

```json
{
  "mcpServers": {
    "codex": {
      "command": "npx",
      "args": ["-y", "@openai/codex", "mcp-server"]
    }
  }
}
```

**CLI로 추가하는 방법**:
```bash
claude mcp add codex -- npx -y @openai/codex mcp-server
```

**확인**:
```bash
claude mcp list
# codex (stdio) 가 표시되어야 함
```

**Claude Code 내에서 사용**:
Claude Code가 자동으로 `mcp__codex__codex`와 `mcp__codex__codex-reply` 도구를 인식합니다:

```
# Codex 세션 시작
mcp__codex__codex(prompt="auth.py의 버그를 수정해", cwd="/path/to/project")

# 대화 이어가기
mcp__codex__codex-reply(threadId="...", prompt="테스트도 추가해")
```

### 방향 2: Codex -> Claude Code (역방향)

Codex가 Claude Code를 MCP 서버로 호출합니다. `claude mcp serve`를 사용합니다.

**설정 파일**: `~/.codex/config.toml`

```toml
[mcp_servers.claude-code]
command = "/Users/miyoungjang/.local/bin/claude"
args = ["mcp", "serve"]
```

**CLI로 추가하는 방법**:
```bash
codex mcp add claude-code -- /Users/miyoungjang/.local/bin/claude mcp serve
```

> **참고**: `claude` 바이너리의 절대 경로를 사용해야 합니다. stdio 서버 시작 시 Codex의 PATH에 `claude`가 없을 수 있습니다.

**확인**:
```bash
codex mcp list
# 예상 출력:
# Name         Command                               Args       Status
# claude-code  /Users/miyoungjang/.local/bin/claude  mcp serve  enabled

codex mcp get claude-code
# transport: stdio 등 상세 정보 표시
```

**Claude Code MCP 서버가 제공하는 도구**:

Codex가 Claude Code에 MCP로 연결하면 다음 도구를 사용할 수 있습니다:

| 도구 | 설명 |
|------|------|
| `View` | 파일 읽기 |
| `Edit` | 정확한 문자열 치환으로 파일 편집 |
| `Write` | 파일 생성 또는 덮어쓰기 |
| `LS` | 디렉토리 목록 조회 |
| `Grep` | 정규식으로 파일 내용 검색 |
| `Glob` | 패턴으로 파일 찾기 |
| `Bash` | 셸 명령어 실행 |

## 설정 파일 요약

### Claude Code (`~/.claude/settings.json`)

```json
{
  "mcpServers": {
    "codex": {
      "command": "npx",
      "args": ["-y", "@openai/codex", "mcp-server"]
    }
  }
}
```

### Codex CLI (`~/.codex/config.toml`)

```toml
[mcp_servers.claude-code]
command = "/Users/miyoungjang/.local/bin/claude"
args = ["mcp", "serve"]
```

## 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│                   개발자 워크플로우                         │
│                                                          │
│  ┌─────────────┐   MCP (stdio)    ┌─────────────┐      │
│  │             │ ───────────────> │             │      │
│  │ Claude Code │                  │  Codex CLI  │      │
│  │  (Opus 4)   │ <─────────────── │ (GPT-5.3)   │      │
│  │             │   MCP (stdio)    │             │      │
│  └─────────────┘                  └─────────────┘      │
│        │                                │                │
│        │  도구: Edit, Bash,             │  도구: codex,  │
│        │  Grep, Read, Write             │  codex-reply   │
│        │                                │                │
│        └────────────┬───────────────────┘                │
│                     │                                    │
│              공유 작업 공간                                │
│           (quant-investment/)                            │
└──────────────────────────────────────────────────────────┘
```

## 문제 해결

### Codex에서 Claude Code MCP 서버가 시작되지 않는 경우

**증상**: `codex mcp list`에 `claude-code`가 표시되지만 도구를 사용할 수 없음.

**해결**: Claude Code가 최소 한 번은 권한을 수락한 상태로 실행되어야 합니다. MCP serve 모드는 headless이므로 대화형 권한 요청이 불가능합니다.

```bash
# 한 번 실행하여 권한 수락
claude --dangerously-skip-permissions
# 시작 후 Ctrl+C로 종료
```

### Claude Code에서 Codex MCP 서버에 연결되지 않는 경우

**증상**: `mcp__codex__codex` 도구를 사용할 수 없음.

**해결**: `npx`가 사용 가능하고 `@openai/codex`를 다운로드할 수 있는지 확인합니다.

```bash
npx -y @openai/codex --version
```

### PATH 문제

**증상**: `spawn claude ENOENT` 또는 유사한 오류.

**해결**: 설정 파일에서 항상 절대 경로를 사용합니다:

```bash
which claude    # /Users/miyoungjang/.local/bin/claude
which codex     # /opt/homebrew/bin/codex
```

### 타임아웃 문제

장시간 작업의 경우 타임아웃을 늘립니다:

**Codex 측** (`config.toml`):
```toml
[mcp_servers.claude-code]
command = "/Users/miyoungjang/.local/bin/claude"
args = ["mcp", "serve"]
tool_timeout_sec = 120
startup_timeout_sec = 30
```

**Claude Code 측**: `MCP_TIMEOUT` 환경 변수 설정:
```bash
MCP_TIMEOUT=30000 claude  # 30초 시작 타임아웃
```

## 관련 문서

- [Claude Code MCP 공식 문서](https://code.claude.com/docs/en/mcp)
- [Codex MCP 설정 가이드](https://developers.openai.com/codex/mcp)
- [Model Context Protocol 스펙](https://modelcontextprotocol.io)
