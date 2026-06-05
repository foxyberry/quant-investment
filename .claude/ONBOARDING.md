# Claude Code 온보딩 (새 머신 / clone 후 1회 설정)

이 저장소를 새 머신에서 받은 뒤 Claude Code를 처음 열 때 필요한 **1회성** 설정입니다.
설정값(MCP 서버 / 플러그인 / 마켓플레이스)은 모두 저장소에 커밋되어 있으므로 직접 입력할 필요는 없고, 아래 단계만 따라가면 됩니다.

## 사전 준비
- Node.js / `npx` — MCP 서버가 `npx`로 실행됩니다.
- Codex 인증 — `mcp__codex__codex` 위임 도구를 쓰려면: `npx @openai/codex login`

## 1. 폴더 신뢰
Claude Code 첫 실행 시 폴더 신뢰 프롬프트 → 신뢰. (보안상 자동화 불가, 1회 클릭)

## 2. MCP 서버 — 자동 연결 (작업 없음)
`.mcp.json` + `enabledMcpjsonServers`(`.claude/settings.json`, committed)로 아래가 **자동 연결**됩니다:
- `codex` → `mcp__codex__codex` (워크플로우 위임 도구, **핵심**)
- `context7`, `playwright`

확인: `/mcp`

> 🔒 `.mcp.json`에는 secret이 없습니다(전부 `npx` 실행). API key가 필요한 MCP 서버를 추가할 경우
> 이 커밋되는 파일이 아니라 `~/.claude.json`(user scope)에 넣으세요.

## 3. 플러그인 — 수동 설치 (1회)
> ⚠️ 플러그인 스킬은 Claude Code 한계로 committed 설정만으로는 **자동 활성화되지 않습니다**.
> 마켓플레이스는 이미 등록돼 있으니 아래 install만 1회 실행하면 됩니다.

```
/plugin install codex@openai-codex
/plugin install skill-creator@claude-plugins-official
/plugin install chrome-devtools-mcp@claude-plugins-official
/plugin install frontend-design@claude-plugins-official
```

확인: `/plugin` 또는 `/doctor`

---
플러그인 구성을 바꾸려면 `.claude/settings.json`의 `enabledPlugins`를 수정하세요. (개인 권한 설정은 `.claude/settings.local.json`)
