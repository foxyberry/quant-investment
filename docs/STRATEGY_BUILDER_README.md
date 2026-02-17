# Strategy Builder (QuantCanvas)

Visual node-based strategy builder for creating stock screening strategies with drag-and-drop.

## Quick Start

1. Navigate to `/strategy` in the web app
2. Drag an **AND Group** from the palette onto the canvas
3. Drag conditions (e.g., "Min Price", "RSI Oversold") **into** the group
4. Connect: `Universe → AND Group → Output`
5. Click **Deploy Strategy** to execute

## Architecture

### Node Types

| Node | Type | Description |
|------|------|-------------|
| Universe | `universeNode` | Stock market selection (KOSPI, KOSDAQ, SP500, NASDAQ100) |
| Condition | `conditionNode` | Single screening condition (27 types across 6 categories) |
| Group | `groupNode` | AND/OR/NOT container that wraps conditions |
| Output | `outputNode` | Final result collection point |

### Group Container Pattern

Groups are container nodes that visually wrap child conditions:

```
┌─────────────────────────────────────┐
│ ● target handle (top)               │
│ ┌─[AND Group]─────────────────────┐ │
│ │  (dashed border container)      │ │
│ │                                 │ │
│ │  ┌──────────────────────┐       │ │
│ │  │ Min Price >= 5000    │       │ │
│ │  └──────────────────────┘       │ │
│ │  ┌──────────────────────┐       │ │
│ │  │ RSI Oversold < 30    │       │ │
│ │  └──────────────────────┘       │ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
│ ● source handle (bottom)            │
└─────────────────────────────────────┘
```

- **AND Group**: All conditions must match (blue)
- **OR Group**: Any condition must match (purple)
- **NOT Group**: Inverts the single condition (red, max 1 child)

### Data Flow

```
Universe ──edge──> [ AND Group: Cond1 + Cond2 ] ──edge──> Output
```

Conditions inside a group connect via `parentId` (React Flow's native grouping), not via edges. Only the group itself has edge connections.

## Condition Categories

| Category | Conditions |
|----------|-----------|
| Price | Min Price, Max Price, Price Range, Price Change % |
| Volume | Min Volume, Volume Above Avg, Volume Spike |
| Moving Average | MA Touch, Above MA, Below MA, MA Cross Up/Down |
| RSI | RSI Oversold, RSI Overbought, RSI Range |
| Accumulation | Bollinger Width, Volume Below Avg, Price Flat, OBV/Stochastic/VPCI Trend/Divergence |
| Breakout | Bottom Breakout, Fresh Breakout, Breakout + Volume, Resistance Breakout |

## Serialization

### Graph Format (API)

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

Key: Group nodes use `child_node_ids` instead of edges to reference their children.

### Backward Compatibility

Edge-based logic nodes (old format without `child_node_ids`) are still supported. The backend resolves children from edges as a fallback.

## File Structure

```
web/src/
├── app/[locale]/strategy/
│   └── page.tsx                    # Main canvas page
├── components/strategy/
│   ├── nodes/
│   │   ├── UniverseNode.tsx        # Market selection node
│   │   ├── ConditionNode.tsx       # Screening condition node
│   │   ├── GroupNode.tsx           # AND/OR/NOT group container
│   │   └── OutputNode.tsx          # Result output node
│   ├── NodePalette.tsx             # Left sidebar draggable palette
│   └── PropertiesPanel.tsx         # Right sidebar node properties
├── lib/strategy/
│   ├── conditionRegistry.ts        # 27 condition definitions
│   ├── graphSerializer.ts          # React Flow <-> API conversion
│   └── graphValidator.ts           # Client-side graph validation
└── hooks/
    └── useStrategy.ts              # API mutation hook

api/
├── schemas/strategy.py             # Pydantic models (StrategyNodeData with child_node_ids)
├── services/strategy_service.py    # Graph resolution + screening execution
└── tests/
    ├── test_strategy_service.py    # Unit tests (24 tests)
    └── test_strategy.py            # Integration tests
```

## API Reference

### POST `/api/strategy/run`

Execute a strategy graph.

**Request**: `StrategyExecuteRequest` with `graph: StrategyGraph`

**Response**: `StrategyExecuteResponse` with matched stocks

### GET `/api/strategy/conditions`

List all available condition types with parameter schemas.

## Related

- [Screener Conditions](./SCREENER_CONDITIONS.md) - Detailed condition documentation
- [Screener README](./SCREENER_README.md) - Core screening library
