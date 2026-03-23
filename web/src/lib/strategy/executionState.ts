import type { Edge, Node } from '@xyflow/react';
import type { StrategyNodeData } from './graphSerializer';

export type ExecutionState = 'idle' | 'pending' | 'executing' | 'completed';

/**
 * Compute the execution order of top-level nodes via topological sort.
 * Group nodes are treated as a single execution unit (children excluded).
 * Returns an array of node IDs in execution order.
 */
export function computeExecutionOrder(
  nodes: Node<StrategyNodeData>[],
  edges: Edge[]
): string[] {
  // Only consider top-level nodes (exclude group children)
  const topLevel = nodes.filter((n) => !n.parentId);
  const nodeIds = new Set(topLevel.map((n) => n.id));

  // Build adjacency list and in-degree map
  const adj = new Map<string, string[]>();
  const inDegree = new Map<string, number>();
  for (const id of nodeIds) {
    adj.set(id, []);
    inDegree.set(id, 0);
  }

  for (const edge of edges) {
    if (nodeIds.has(edge.source) && nodeIds.has(edge.target)) {
      adj.get(edge.source)!.push(edge.target);
      inDegree.set(edge.target, (inDegree.get(edge.target) ?? 0) + 1);
    }
  }

  // Kahn's algorithm
  const queue: string[] = [];
  for (const [id, deg] of inDegree) {
    if (deg === 0) queue.push(id);
  }

  const order: string[] = [];
  while (queue.length > 0) {
    const current = queue.shift()!;
    order.push(current);
    for (const neighbor of adj.get(current) ?? []) {
      const newDeg = (inDegree.get(neighbor) ?? 1) - 1;
      inDegree.set(neighbor, newDeg);
      if (newDeg === 0) queue.push(neighbor);
    }
  }

  return order;
}

/**
 * Given current progress (0-100) and execution order,
 * derive the execution state for each node.
 */
export function deriveNodeStates(
  executionOrder: string[],
  progressPct: number
): Map<string, ExecutionState> {
  const states = new Map<string, ExecutionState>();
  const count = executionOrder.length;
  if (count === 0) return states;

  const segmentSize = 100 / count;

  for (let i = 0; i < count; i++) {
    const nodeId = executionOrder[i];
    const nodeStart = i * segmentSize;

    if (progressPct >= nodeStart + segmentSize) {
      states.set(nodeId, 'completed');
    } else if (progressPct >= nodeStart) {
      states.set(nodeId, 'executing');
    } else {
      states.set(nodeId, 'pending');
    }
  }

  return states;
}

/**
 * CSS class helper for node execution state styling.
 */
export function getExecutionStateClasses(state: ExecutionState | undefined): string {
  switch (state) {
    case 'pending':
      return 'opacity-50 border-dashed border-gray-300 dark:border-gray-600';
    case 'executing':
      return 'border-2 border-[#1313ec] animate-execution-pulse';
    case 'completed':
      return 'border border-emerald-400/60 dark:border-emerald-500/40';
    default:
      return '';
  }
}
