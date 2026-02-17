# Google Stitch MCP 설정 가이드

AI 기반 UI/UX 디자인을 위해 Google Stitch MCP를 Claude Code에 연결하는 설정 가이드입니다.

## 개요

Google Stitch는 AI를 활용해 UI/UX 디자인을 즉시 생성할 수 있는 도구입니다. MCP(Model Context Protocol)를 통해 Claude Code와 연동하면 디자인에서 코드로의 워크플로우를 자동화할 수 있습니다.

### 주요 기능
- AI 기반 UI 디자인 생성
- 디자인 시스템 문서 자동 생성
- React 컴포넌트 코드 생성
- Figma/디자인 파일과의 연동

## 사전 요구사항

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| Node.js v18+ | 필수 | npx 실행에 필요 |
| Google Cloud CLI (gcloud) | 필수 | `~/google-cloud-sdk/bin/gcloud` |
| Google 계정 로그인 | 필수 | Cloud 접근 권한이 있는 Google 계정 |
| Google Cloud 프로젝트 | 필수 | Stitch API가 활성화된 프로젝트 |
| Application Default Credentials | 필수 | `~/.config/gcloud/application_default_credentials.json` |

## 설정 방법

### 1. `.mcp.json` 설정

프로젝트 루트의 `.mcp.json`에 stitch 서버 추가:

```json
{
  "mcpServers": {
    "stitch": {
      "command": "npx",
      "args": ["-y", "@_davideast/stitch-mcp", "proxy"],
      "env": {
        "STITCH_PROJECT_ID": "your-google-cloud-project-id",
        "GOOGLE_APPLICATION_CREDENTIALS": "~/.config/gcloud/application_default_credentials.json"
      }
    }
  }
}
```

### 2. Claude Code 설정에서 활성화

`.claude/settings.local.json`의 `enabledMcpjsonServers`에 `"stitch"` 추가:

```json
{
  "enabledMcpjsonServers": ["stitch"]
}
```

### 3. stitch-mcp 초기화

```bash
npx -y @_davideast/stitch-mcp init
# → Claude Code 선택
# → Google Cloud 프로젝트 선택
```

### 4. Application Default Credentials (ADC) 설정

```bash
gcloud auth application-default login
```

실행 시:
1. 브라우저가 열립니다
2. Google 계정으로 로그인
3. 권한 승인
4. `~/.config/gcloud/application_default_credentials.json` 파일 생성됨

### 5. Claude Code 재시작

ADC 설정 완료 후 Claude Code를 재시작합니다. `/mcp` 명령어로 `stitch` 서버가 목록에 표시되면 성공입니다.

## 진단 방법

```bash
npx -y @_davideast/stitch-mcp doctor
```

정상 출력:
```
✔ Google Cloud CLI: Installed (bundled): v555.0.0
✔ User Authentication: Authenticated: <이메일>
✔ Application Credentials: Present
✔ Active Project: your-google-cloud-project-id
```

## 사용 예시

연결 완료 후 Claude Code에서 다음과 같이 사용:

```
# 디자인 생성 요청
"로그인 페이지 UI를 디자인해줘"

# 컴포넌트 생성
"이 디자인을 React 컴포넌트로 변환해줘"

# 디자인 시스템
"버튼 컴포넌트의 디자인 시스템을 만들어줘"
```

## 문제 해결

### "Failed to reconnect to stitch" 오류

원인 우선순위:
1. **Active Project 미설정** — 가장 흔한 원인
2. `enabledMcpjsonServers`에 `"stitch"` 미포함
3. ADC 인증 파일 누락

해결:
```bash
npx -y @_davideast/stitch-mcp init
# → Claude Code 선택 → 프로젝트 선택 → Claude Code 재시작
```

### ADC 인증 실패 시

```bash
gcloud auth application-default revoke
gcloud auth application-default login
```

### gcloud 설치 위치

| 경로 | 용도 |
|------|------|
| `~/google-cloud-sdk/bin/gcloud` | PATH에 등록된 기본 gcloud |
| `~/.stitch-mcp/google-cloud-sdk/bin/gcloud` | stitch-mcp 번들 버전 |

## 참고 자료

- [@_davideast/stitch-mcp (npm)](https://www.npmjs.com/package/@_davideast/stitch-mcp)
- [Google Stitch 공식 사이트](https://stitch.withgoogle.com/)
- [Claude Code MCP 문서](https://code.claude.com/docs/en/mcp)

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-02-03 | 초기 설정 문서 작성 |
| 2026-02-05 | 실제 연동 완료, `@_davideast/stitch-mcp` 패키지로 변경 |
| 2026-02-08 | 문서를 실제 설정에 맞게 전면 업데이트 |
| 2026-02-12 | quant-investment 프로젝트에 추가 |
