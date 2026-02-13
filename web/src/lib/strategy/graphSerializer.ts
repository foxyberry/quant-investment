import type { Node, Edge } from '@xyflow/react';

export interface StrategyNodeData extends Record<string, unknown> {
  node_type: 'universe' | 'condition' | 'logic' | 'output';
  condition_type?: string;
  params?: Record<string, unknown>;
  logic_operator?: string;
  universe?: string;
  label?: string;
  resultCount?: number;
}

export interface StrategyNode {
  id: string;
  data: {
    node_type: string;
    condition_type?: string;
    params?: Record<string, unknown>;
    logic_operator?: string;
    universe?: string;
  };
  position?: { x: number; y: number };
}

export interface StrategyEdge {
  id: string;
  source: string;
  target: string;
}

export interface StrategyGraph {
  nodes: StrategyNode[];
  edges: StrategyEdge[];
}

export function serializeGraph(
  nodes: Node<StrategyNodeData>[],
  edges: Edge[]
): StrategyGraph {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      data: {
        node_type: n.data.node_type,
        condition_type: n.data.condition_type,
        params: n.data.params || {},
        logic_operator: n.data.logic_operator,
        universe: n.data.universe,
      },
      position: n.position,
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
    })),
  };
}

export function deserializeGraph(
  graph: StrategyGraph
): { nodes: Node<StrategyNodeData>[]; edges: Edge[] } {
  const nodes: Node<StrategyNodeData>[] = graph.nodes.map((n) => {
    let nodeType = 'conditionNode';
    if (n.data.node_type === 'universe') nodeType = 'universeNode';
    else if (n.data.node_type === 'logic') nodeType = 'logicNode';
    else if (n.data.node_type === 'output') nodeType = 'outputNode';

    return {
      id: n.id,
      type: nodeType,
      position: n.position || { x: 0, y: 0 },
      data: {
        node_type: n.data.node_type as StrategyNodeData['node_type'],
        condition_type: n.data.condition_type,
        params: n.data.params || {},
        logic_operator: n.data.logic_operator,
        universe: n.data.universe,
      },
    };
  });

  const edges: Edge[] = graph.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
  }));

  return { nodes, edges };
}
