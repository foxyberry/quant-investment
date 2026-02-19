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

  // Check sector node (max 1, must not be inside group, must have sector selected)
  const sectorNodes = nodes.filter((n) => n.data.node_type === 'sector');
  if (sectorNodes.length > 1) {
    errors.push('Only one Sector node is allowed per strategy graph.');
  }
  for (const sn of sectorNodes) {
    if (sn.parentId) {
      errors.push('Sector nodes cannot be placed inside groups.');
    }
    if (!sn.data.sector) {
      errors.push(`Sector node "${sn.id}" has no sector selected.`);
    }
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

  // Build set of nodes that are children of group nodes
  const childNodeIds = new Set<string>();
  for (const node of nodes) {
    if (node.parentId) {
      childNodeIds.add(node.id);
    }
  }

  // Group node validation
  for (const node of nodes) {
    if (node.data.node_type === 'logic') {
      // Count children (conditions or nested groups with parentId pointing to this group)
      const children = nodes.filter((n) => n.parentId === node.id);
      const hasChildNodeIds = children.length > 0;
      // Also check edge-based children (backward compatibility)
      const incomingEdges = edges.filter((e) => e.target === node.id);
      const hasEdgeInputs = incomingEdges.some((e) => {
        const srcNode = nodes.find((n) => n.id === e.source);
        return srcNode && srcNode.data.node_type !== 'universe';
      });

      if (!hasChildNodeIds && !hasEdgeInputs) {
        errors.push(
          `Group node "${node.id}" has no conditions. Add conditions to the group.`
        );
      }

      // NOT group: max 1 child
      const op = (node.data.logic_operator || 'and').toLowerCase();
      if (op === 'not' && children.length > 1) {
        errors.push(
          `NOT group "${node.id}" can only have one condition.`
        );
      }
    }
  }

  // Check maximum group nesting depth (max 3 levels)
  const nodeById = new Map(nodes.map((n) => [n.id, n] as const));

  function getGroupDepth(groupId: string): number {
    let depth = 1;
    let current = nodeById.get(groupId);

    while (current?.parentId) {
      const parent = nodeById.get(current.parentId);
      if (!parent || parent.data.node_type !== 'logic') {
        break;
      }

      depth += 1;
      if (depth > 3) {
        return depth;
      }
      current = parent;
    }

    return depth;
  }

  const hasTooDeepNesting = nodes.some(
    (node) => node.data.node_type === 'logic' && getGroupDepth(node.id) > 3
  );
  if (hasTooDeepNesting) {
    errors.push('Group nesting is too deep (max 3 levels).');
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
  // Skip condition nodes that are inside a group (they connect via parentId, not edges)
  const nodesWithOutgoing = new Set(edges.map((e) => e.source));
  for (const node of nodes) {
    if (
      node.data.node_type !== 'output' &&
      !nodesWithOutgoing.has(node.id) &&
      !childNodeIds.has(node.id)
    ) {
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
  const nodeIds = new Set(nodes.map((n) => n.id));

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
