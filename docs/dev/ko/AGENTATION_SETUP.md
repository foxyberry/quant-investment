# Agentation 설정 가이드

AI 에이전트를 위한 시각 피드백 도구. 페이지에서 요소를 클릭하면 CSS 셀렉터, React 컴포넌트 계층, 위치 정보를 캡처하여 구조화된 출력을 코딩 에이전트에게 전달한다.

- **GitHub**: https://github.com/benjitaylor/agentation
- **문서**: https://agentation.dev/faq
- **npm**: https://www.npmjs.com/package/agentation

## 요구사항

- React 18+
- 데스크톱 브라우저 (모바일 미지원)
- Node.js (MCP 서버용)

## 설정 (3단계)

### 1. 패키지 설치

```bash
cd web
npm install agentation -D
```

### 2. React 컴포넌트 추가

`web/src/components/dev/AgentationProvider.tsx` 생성:

```tsx
'use client';

import dynamic from 'next/dynamic';

const AgentationLazy = dynamic(
  () => import('agentation').then((m) => ({ default: m.Agentation })),
  { ssr: false },
);

export default function AgentationProvider() {
  if (process.env.NODE_ENV !== 'development') return null;
  return <AgentationLazy />;
}
```

레이아웃에 추가 (`web/src/app/[locale]/layout.tsx`):

```tsx
import AgentationProvider from '@/components/dev/AgentationProvider';

// 레이아웃 JSX 내부, MainLayout 다음에:
<MainLayout>{children}</MainLayout>
<AgentationProvider />
```

> **참고**: Next.js Server Component에서는 `next/dynamic`의 `ssr: false`를 사용할 수 없으므로 반드시 별도 Client Component로 분리해야 한다.

### 3. MCP 서버 등록 (Claude Code)

**글로벌** (권장 — 모든 프로젝트에서 사용 가능):

```bash
claude mcp add --scope user agentation -- npx agentation-mcp server
```

**프로젝트별** (대안):

```bash
cd <프로젝트 루트>
npx agentation-mcp init
```

## 사용법

1. 개발 서버 실행: `cd web && npm run dev`
2. 브라우저 열기 — 우측 하단에 Agentation 툴바 표시
3. 툴바 클릭하여 활성화 → 원하는 요소 클릭
4. 구조화된 출력 복사 (CSS 셀렉터 + 컴포넌트 경로 + 메모)
5. AI 에이전트 프롬프트에 붙여넣기

### 출력 모드

| 모드 | 상세 수준 | 용도 |
|------|----------|------|
| Compact | 셀렉터 + 메모 | 빠른 수정 |
| Standard | + 바운딩 박스 | 일반 용도 |
| Detailed | + 전체 컨텍스트 | 레이아웃 작업 |
| Forensic | + 계산된 스타일 | CSS 디버깅 |

### Agent Sync (MCP)

툴바 설정에서 "Agent Sync"를 활성화하면 어노테이션이 MCP를 통해 실시간으로 Claude Code에 전달된다.

## 프로덕션 안전성

- `AgentationProvider`는 `process.env.NODE_ENV !== 'development'` 체크 — 프로덕션에서 `null` 반환
- `agentation`은 `devDependency`로 설치 — 프로덕션 번들에 포함 안 됨
- 프로덕션 빌드에서 런타임 오버헤드 없음

## 문제 해결

| 문제 | 해결 |
|------|------|
| 툴바가 안 보임 | 개발 서버 실행 중인지 확인 (`npm run dev`, `npm run build` 아님) |
| MCP 연결 안 됨 | `claude mcp list`로 등록 확인 |
| SSR 에러 | `AgentationProvider`가 Client Component (`'use client'`)이고 `ssr: false`인지 확인 |
