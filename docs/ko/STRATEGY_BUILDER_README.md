이 문서는 [영문 버전](../STRATEGY_BUILDER_README.md)의 번역입니다.

# 전략 빌더 (QuantCanvas)

드래그 앤 드롭으로 주식 스크리닝 전략을 만드는 비주얼 노드 기반 전략 빌더입니다.

## 빠른 시작

1. 웹 앱에서 `/strategy`로 이동
2. 팔레트에서 **AND 그룹**을 캔버스에 드래그
3. 조건(예: "최소 가격", "RSI 과매도")을 그룹 **안에** 드래그
4. 연결: `유니버스 → AND 그룹 → 출력`
5. **전략 배포** 클릭하여 실행

## 아키텍처

### 노드 타입

| 노드 | 타입 | 설명 |
|------|------|------|
| 유니버스 | `universeNode` | 주식 시장 선택 (KOSPI, KOSDAQ, SP500, NASDAQ100) |
| 조건 | `conditionNode` | 단일 스크리닝 조건 (6개 카테고리, 27가지 타입) |
| 그룹 | `groupNode` | 조건을 감싸는 AND/OR/NOT 컨테이너 |
| 출력 | `outputNode` | 최종 결과 수집 포인트 |

### 그룹 컨테이너 패턴

그룹은 자식 조건을 시각적으로 감싸는 컨테이너 노드입니다:

```
┌─────────────────────────────────────┐
│ ● 타겟 핸들 (상단)                    │
│ ┌─[AND 그룹]──────────────────────┐ │
│ │  (점선 테두리 컨테이너)            │ │
│ │                                 │ │
│ │  ┌──────────────────────┐       │ │
│ │  │ 최소 가격 >= 5000     │       │ │
│ │  └──────────────────────┘       │ │
│ │  ┌──────────────────────┐       │ │
│ │  │ RSI 과매도 < 30       │       │ │
│ │  └──────────────────────┘       │ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
│ ● 소스 핸들 (하단)                    │
└─────────────────────────────────────┘
```

- **AND 그룹**: 모든 조건 충족 필요 (파란색)
- **OR 그룹**: 하나 이상 조건 충족 (보라색)
- **NOT 그룹**: 단일 조건 반전 (빨간색, 자식 1개 제한)

### 데이터 흐름

```
유니버스 ──엣지──> [ AND 그룹: 조건1 + 조건2 ] ──엣지──> 출력
```

그룹 내부의 조건은 엣지가 아닌 `parentId`(React Flow 네이티브 그룹핑)로 연결됩니다. 그룹 자체만 엣지 연결이 필요합니다.

## 조건 카테고리

| 카테고리 | 조건 |
|----------|------|
| 가격 | 최소 가격, 최대 가격, 가격 범위, 가격 변동률 |
| 거래량 | 최소 거래량, 평균 이상 거래량, 거래량 급증 |
| 이동평균 | MA 터치, MA 위, MA 아래, 골든크로스/데드크로스 |
| RSI | RSI 과매도, RSI 과매수, RSI 범위 |
| 매집 | 볼린저 밴드 폭, 평균 이하 거래량, 가격 횡보, OBV/스토캐스틱/VPCI 추세/다이버전스 |
| 돌파 | 저점 돌파, 신규 돌파, 돌파 + 거래량, 저항선 돌파 |

## 직렬화

### 그래프 포맷 (API)

```json
{
  "nodes": [
    { "id": "u1", "data": { "node_type": "universe", "universe": "KOSPI" } },
    { "id": "g1", "data": {
        "node_type": "logic",
        "logic_operator": "and",
        "child_node_ids": ["c1", "c2"]
    }},
    { "id": "c1", "data": { "node_type": "condition", "condition_type": "min_price", "params": { "min_price": 5000 } } },
    { "id": "c2", "data": { "node_type": "condition", "condition_type": "rsi_oversold", "params": { "threshold": 30 } } },
    { "id": "o1", "data": { "node_type": "output" } }
  ],
  "edges": [
    { "id": "e1", "source": "u1", "target": "g1" },
    { "id": "e2", "source": "g1", "target": "o1" }
  ]
}
```

핵심: 그룹 노드는 엣지 대신 `child_node_ids`로 자식 노드를 참조합니다.

### 하위 호환성

엣지 기반 로직 노드(`child_node_ids` 없는 기존 포맷)도 여전히 지원됩니다. 백엔드는 폴백으로 엣지에서 자식을 해석합니다.

## 파일 구조

```
web/src/
├── app/[locale]/strategy/
│   └── page.tsx                    # 메인 캔버스 페이지
├── components/strategy/
│   ├── nodes/
│   │   ├── UniverseNode.tsx        # 시장 선택 노드
│   │   ├── ConditionNode.tsx       # 스크리닝 조건 노드
│   │   ├── GroupNode.tsx           # AND/OR/NOT 그룹 컨테이너
│   │   └── OutputNode.tsx          # 결과 출력 노드
│   ├── NodePalette.tsx             # 좌측 사이드바 드래그 팔레트
│   └── PropertiesPanel.tsx         # 우측 사이드바 노드 속성
├── lib/strategy/
│   ├── conditionRegistry.ts        # 27개 조건 정의
│   ├── graphSerializer.ts          # React Flow <-> API 변환
│   └── graphValidator.ts           # 클라이언트 그래프 검증
└── hooks/
    └── useStrategy.ts              # API 뮤테이션 훅

api/
├── schemas/strategy.py             # Pydantic 모델 (child_node_ids 포함 StrategyNodeData)
├── services/strategy_service.py    # 그래프 해석 + 스크리닝 실행
└── tests/
    ├── test_strategy_service.py    # 단위 테스트 (24개)
    └── test_strategy.py            # 통합 테스트
```

## API 레퍼런스

### POST `/api/strategy/run`

전략 그래프를 실행합니다.

**요청**: `StrategyExecuteRequest` (`graph: StrategyGraph` 포함)

**응답**: `StrategyExecuteResponse` (매치된 종목 목록)

### GET `/api/strategy/conditions`

사용 가능한 모든 조건 타입과 파라미터 스키마를 반환합니다.

## 관련 문서

- [스크리너 조건](./SCREENER_CONDITIONS.md) - 상세 조건 문서
- [스크리너 README](./SCREENER_README.md) - 핵심 스크리닝 라이브러리
