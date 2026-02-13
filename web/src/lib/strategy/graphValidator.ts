import type { Node, Edge } from '@xyflow/react';
import type { StrategyNodeData } from './graphSerializer';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export function validateGraph(
  nodes: Node<StrategyNodeData>[],
  edges: Edge[]
): ValidationResult {
  const errors: string[] = [];

  if (nodes.length === 0) {
    errors.push('Graph is empty. Add some nodes to get started.');
    return { valid: false, errors };
  }

  // Check for output node
  const outputNodes = nodes.filter((n) => n.data.node_type === 'output');
  if (outputNodes.length === 0) {
    errors.push('Graph must have an Output node.');
  } else if (outputNodes.length > 1) {
    errors.push('Graph should have only one Output node.');
  }

  // Check for universe node
  const universeNodes = nodes.filter((n) => n.data.node_type === 'universe');
  if (universeNodes.length === 0) {
    errors.push('Graph must have a Universe node (stock universe selection).');
  }

  // Check that at least one condition or logic node exists
  const conditionNodes = nodes.filter(
    (n) => n.data.node_type === 'condition' || n.data.node_type === 'logic'
  );
  if (conditionNodes.length === 0) {
    errors.push('Graph must have at least one Condition node.');
  }

  // Check that condition nodes have condition_type set
  for (const node of nodes) {
    if (node.data.node_type === 'condition' && !node.data.condition_type) {
      errors.push(`Condition node "${node.id}" has no condition type selected.`);
    }
  }

  // Check output node has incoming connections
  if (outputNodes.length > 0) {
    const outputId = outputNodes[0].id;
    const incomingToOutput = edges.filter((e) => e.target === outputId);
    if (incomingToOutput.length === 0) {
      errors.push('Output node must have at least one incoming connection.');
    }
  }

  // Check for disconnected condition/logic nodes (no outgoing edges)
  const nodeIds = new Set(nodes.map((n) => n.id));
  const nodesWithOutgoing = new Set(edges.map((e) => e.source));
  for (const node of nodes) {
    if (
      node.data.node_type !== 'output' &&
      !nodesWithOutgoing.has(node.id)
    ) {
      // Node has no outgoing edge - it's disconnected
      errors.push(
        `Node "${node.data.label || node.id}" is not connected to anything.`
      );
    }
  }

  // Simple cycle detection using DFS
  const adjacency: Record<string, string[]> = {};
  for (const node of nodes) {
    adjacency[node.id] = [];
  }
  for (const edge of edges) {
    if (adjacency[edge.source]) {
      adjacency[edge.source].push(edge.target);
    }
  }

  const visited = new Set<string>();
  const recursionStack = new Set<string>();

  function hasCycle(nodeId: string): boolean {
    visited.add(nodeId);
    recursionStack.add(nodeId);

    for (const neighbor of adjacency[nodeId] || []) {
      if (!visited.has(neighbor)) {
        if (hasCycle(neighbor)) return true;
      } else if (recursionStack.has(neighbor)) {
        return true;
      }
    }

    recursionStack.delete(nodeId);
    return false;
  }

  for (const nodeId of nodeIds) {
    if (!visited.has(nodeId)) {
      if (hasCycle(nodeId)) {
        errors.push('Graph contains a cycle. Remove circular connections.');
        break;
      }
    }
  }

  return { valid: errors.length === 0, errors };
}
