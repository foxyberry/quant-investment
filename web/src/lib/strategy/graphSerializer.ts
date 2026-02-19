import type { Node, Edge } from '@xyflow/react';

export interface StrategyNodeData extends Record<string, unknown> {
  node_type: 'universe' | 'condition' | 'logic' | 'output' | 'sector';
  condition_type?: string;
  params?: Record<string, unknown>;
  logic_operator?: string;
  universe?: string;
  sector?: string;
  label?: string;
  resultCount?: number;
  child_node_ids?: string[];
  intermediateResult?: import('@/lib/api').NodeIntermediateResult;
}

export interface StrategyNode {
  id: string;
  data: {
    node_type: string;
    condition_type?: string;
    params?: Record<string, unknown>;
    logic_operator?: string;
    universe?: string;
    sector?: string;
    child_node_ids?: string[];
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

/**
 * BFS to find all node IDs reachable downstream from a set of starting nodes.
 */
export function getDownstreamNodeIds(
  startNodeIds: string[],
  edges: Array<{ source: string; target: string }>
): Set<string> {
  const downstream = new Set<string>();
  const queue = [...startNodeIds];
  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const edge of edges) {
      if (edge.source === current && !downstream.has(edge.target)) {
        downstream.add(edge.target);
        queue.push(edge.target);
      }
    }
  }
  return downstream;
}

export function serializeGraph(
  nodes: Node<StrategyNodeData>[],
  edges: Edge[]
): StrategyGraph {
  // Collect child_node_ids from React Flow parentId relationships
  const parentChildMap: Record<string, string[]> = {};
  for (const n of nodes) {
    if (n.parentId) {
      if (!parentChildMap[n.parentId]) {
        parentChildMap[n.parentId] = [];
      }
      parentChildMap[n.parentId].push(n.id);
    }
  }

  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      data: {
        node_type: n.data.node_type,
        condition_type: n.data.condition_type,
        params: n.data.params || {},
        logic_operator: n.data.logic_operator,
        universe: n.data.universe,
        sector: n.data.sector,
        ...(parentChildMap[n.id]
          ? { child_node_ids: parentChildMap[n.id] }
          : {}),
        // intermediateResult is runtime-only, excluded from serialization
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
  // Build parentId lookup from child_node_ids
  const childToParent: Record<string, string> = {};
  for (const n of graph.nodes) {
    if (n.data.child_node_ids) {
      for (const childId of n.data.child_node_ids) {
        childToParent[childId] = n.id;
      }
    }
  }

  const nodes: Node<StrategyNodeData>[] = graph.nodes.map((n) => {
    let nodeType = 'conditionNode';
    if (n.data.node_type === 'universe') nodeType = 'universeNode';
    else if (n.data.node_type === 'sector') nodeType = 'sectorNode';
    else if (n.data.node_type === 'logic') nodeType = 'groupNode';
    else if (n.data.node_type === 'output') nodeType = 'outputNode';

    const base: Node<StrategyNodeData> = {
      id: n.id,
      type: nodeType,
      position: n.position || { x: 0, y: 0 },
      data: {
        node_type: n.data.node_type as StrategyNodeData['node_type'],
        condition_type: n.data.condition_type,
        params: n.data.params || {},
        logic_operator: n.data.logic_operator,
        universe: n.data.universe,
        sector: n.data.sector,
      },
    };

    // Set parentId for child nodes
    if (childToParent[n.id]) {
      base.parentId = childToParent[n.id];
      base.extent = 'parent';
    }

    // Set group node dimensions
    if (nodeType === 'groupNode') {
      const isNested = !!childToParent[n.id];
      base.style = {
        width: isNested ? 280 - 32 : 280,
        height: 200,
      };
    }

    return base;
  });

  const edges: Edge[] = graph.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
  }));

  return { nodes, edges };
}
