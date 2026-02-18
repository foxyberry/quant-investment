'use client';

import { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import {
  ReactFlow,
  addEdge,
  reconnectEdge,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  ConnectionMode,
  type Connection,
  type Edge,
  type Node,
  type NodeTypes,
  type ReactFlowInstance,
  type NodeChange,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { Loader2, Zap, RotateCcw, Save, TestTube, Download, FolderOpen, X } from 'lucide-react';
import UniverseNode from '@/components/strategy/nodes/UniverseNode';
import ConditionNode from '@/components/strategy/nodes/ConditionNode';
import GroupNode from '@/components/strategy/nodes/GroupNode';
import OutputNode from '@/components/strategy/nodes/OutputNode';
import LabeledEdge from '@/components/strategy/edges/LabeledEdge';
import NodePalette from '@/components/strategy/NodePalette';
import PropertiesPanel from '@/components/strategy/PropertiesPanel';
import BacktestPanel from '@/components/backtest/BacktestPanel';
import { Toast, useToast, type ToastType } from '@/components/ui/Toast';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import { serializeGraph } from '@/lib/strategy/graphSerializer';
import { validateGraph } from '@/lib/strategy/graphValidator';
import { ConditionsProvider, useConditions } from '@/contexts/ConditionsContext';
import { useRunStrategy, useSavedStrategies, useSaveStrategy, useUpdateStrategy } from '@/hooks/useStrategy';
import type { StrategyResultItem, SavedStrategy } from '@/lib/api';

const nodeTypes: NodeTypes = {
  universeNode: UniverseNode,
  conditionNode: ConditionNode,
  groupNode: GroupNode,
  outputNode: OutputNode,
};

const edgeTypes = {
  labeled: LabeledEdge,
};

const GROUP_PADDING_TOP = 60;
const GROUP_PADDING_BOTTOM = 28;
const GROUP_PADDING_X = 24;
const CHILD_SPACING = 16;
const CHILD_HEIGHT = 80;
const GROUP_MIN_WIDTH = 380;
const GROUP_MIN_HEIGHT = 220;

function getNodeId() {
  return `node_${crypto.randomUUID().slice(0, 8)}`;
}

const initialNodes: Node[] = [
  {
    id: 'universe_1',
    type: 'universeNode',
    position: { x: 50, y: 200 },
    data: { node_type: 'universe', universe: 'KOSPI' } satisfies StrategyNodeData,
  },
  {
    id: 'output_1',
    type: 'outputNode',
    position: { x: 800, y: 200 },
    data: { node_type: 'output' } satisfies StrategyNodeData,
  },
];

const initialEdges: Edge[] = [];

function getNodeData(node: Node): StrategyNodeData {
  return node.data as unknown as StrategyNodeData;
}

// --- sessionStorage helpers for locale-switch persistence (#80) ---
const STORAGE_KEY = 'strategy-canvas-state';

interface CanvasSnapshot {
  nodes: Node[];
  edges: Edge[];
  strategyName: string;
  strategyDescription: string;
  currentStrategyId: string | null;
}

function saveCanvasToSession(snapshot: CanvasSnapshot) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  } catch { /* quota exceeded — ignore */ }
}

function loadCanvasFromSession(): CanvasSnapshot | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(STORAGE_KEY); // one-time restore
    return JSON.parse(raw) as CanvasSnapshot;
  } catch {
    return null;
  }
}

function StrategyPageInner() {
  const t = useTranslations('strategy');
  const locale = useLocale();
  const { getDefaultParams } = useConditions();

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [results, setResults] = useState<StrategyResultItem[] | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [showBacktest, setShowBacktest] = useState(false);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  // Save/Load state
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [showLoadDialog, setShowLoadDialog] = useState(false);
  const [strategyName, setStrategyName] = useState('');
  const [strategyDescription, setStrategyDescription] = useState('');
  const [currentStrategyId, setCurrentStrategyId] = useState<string | null>(null);
  const [isResultPanelVisible, setIsResultPanelVisible] = useState(false);

  // Restore from sessionStorage after mount (locale-switch persistence)
  useEffect(() => {
    const restored = loadCanvasFromSession();
    if (restored) {
      setNodes(restored.nodes);
      setEdges(restored.edges);
      setStrategyName(restored.strategyName);
      setStrategyDescription(restored.strategyDescription);
      setCurrentStrategyId(restored.currentStrategyId);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist canvas state to sessionStorage on every change (for locale-switch survival)
  useEffect(() => {
    saveCanvasToSession({ nodes, edges, strategyName, strategyDescription, currentStrategyId });
  }, [nodes, edges, strategyName, strategyDescription, currentStrategyId]);

  const runStrategy = useRunStrategy();
  const savedStrategies = useSavedStrategies();
  const saveStrategy = useSaveStrategy();
  const updateStrategy = useUpdateStrategy();
  const { toast, showToast, hideToast } = useToast();

  const isValidConnection = useCallback(
    (connection: Edge | Connection) => {
      const { source, target, sourceHandle, targetHandle } = connection;

      if (!source || !target) return false;
      if (source === target) return false;

      const sourceNode = nodes.find((node) => node.id === source);
      const targetNode = nodes.find((node) => node.id === target);
      if (!sourceNode || !targetNode) return false;

      // Guard explicit handle ids used inside groups.
      if (sourceHandle === 'top' || targetHandle === 'bottom') return false;

      const sourceType = sourceNode.type;
      const targetType = targetNode.type;

      // Each handle can only have one connection (both source and target)
      const sourceAlreadyConnected = edges.some(
        (e) => e.source === source && (e.sourceHandle ?? null) === (sourceHandle ?? null)
      );
      const targetAlreadyConnected = edges.some(
        (e) => e.target === target && (e.targetHandle ?? null) === (targetHandle ?? null)
      );
      if (sourceAlreadyConnected || targetAlreadyConnected) return false;

      if (sourceType === 'universeNode') {
        return targetType === 'conditionNode';
      }

      if (sourceType === 'conditionNode') {
        if (targetType !== 'conditionNode' && targetType !== 'outputNode') return false;

        // Prevent cycles: check if target can already reach source via existing edges
        const visited = new Set<string>();
        const queue = [target];
        while (queue.length > 0) {
          const current = queue.pop()!;
          if (current === source) return false; // cycle detected
          if (visited.has(current)) continue;
          visited.add(current);
          for (const edge of edges) {
            if (edge.source === current) {
              queue.push(edge.target);
            }
          }
        }
        return true;
      }

      return false;
    },
    [nodes, edges]
  );

  useEffect(() => {
    const shouldShowPanel = runStrategy.isPending || (!!results && results.length > 0);
    if (!shouldShowPanel) {
      setIsResultPanelVisible(false);
      return;
    }

    setIsResultPanelVisible(false);
    const rafId = window.requestAnimationFrame(() => {
      setIsResultPanelVisible(true);
    });

    return () => {
      window.cancelAnimationFrame(rafId);
    };
  }, [runStrategy.isPending, results]);

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!isValidConnection(connection)) return;
      setEdges((eds) => addEdge(connection, eds));
    },
    [isValidConnection, setEdges]
  );

  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      if (!isValidConnection(newConnection)) return;
      setEdges((eds) => reconnectEdge(oldEdge, newConnection, eds));
    },
    [isValidConnection, setEdges]
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      setSelectedNodeId(node.id);
    },
    []
  );

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Find group node at a given position
  const findGroupAtPosition = useCallback(
    (flowPosition: { x: number; y: number }): Node | null => {
      // Check all group nodes to see if position is inside
      const groupNodes = nodes.filter(
        (n) => n.type === 'groupNode'
      );
      for (const group of groupNodes) {
        const gx = group.position.x;
        const gy = group.position.y;
        const gw = (group.style?.width as number) || GROUP_MIN_WIDTH;
        const gh = (group.style?.height as number) || GROUP_MIN_HEIGHT;
        if (
          flowPosition.x >= gx &&
          flowPosition.x <= gx + gw &&
          flowPosition.y >= gy &&
          flowPosition.y <= gy + gh
        ) {
          return group;
        }
      }
      return null;
    },
    [nodes]
  );

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow-type');
      const conditionKey = event.dataTransfer.getData('application/reactflow-condition');

      if (!type || !reactFlowInstance) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      let data: StrategyNodeData;
      let nodeType: string;

      if (type === 'universe') {
        nodeType = 'universeNode';
        data = { node_type: 'universe', universe: 'KOSPI' };
      } else if (type === 'condition') {
        nodeType = 'conditionNode';
        const params = conditionKey ? getDefaultParams(conditionKey) : {};
        data = {
          node_type: 'condition',
          condition_type: conditionKey || undefined,
          params,
        };
      } else if (type.startsWith('logic_')) {
        nodeType = 'groupNode';
        const operator = type.replace('logic_', '');
        data = { node_type: 'logic', logic_operator: operator };
      } else if (type === 'output') {
        nodeType = 'outputNode';
        data = { node_type: 'output' };
      } else {
        return;
      }

      const newNodeId = getNodeId();

      // Check if dropping inside a group
      const targetGroup = findGroupAtPosition(position);
      if (targetGroup) {
        // Block invalid drops: universe and output cannot go in groups
        if (nodeType === 'universeNode' || nodeType === 'outputNode') {
          showToast(t('cannotDropInGroup'), 'warning');
          // Still place on canvas as standalone (fall through)
        } else if (nodeType === 'conditionNode' || nodeType === 'groupNode') {
          // Valid drop: condition or nested group into a group
          const childrenInGroup = nodes.filter(
            (n) => n.parentId === targetGroup.id
          );
          const childIndex = childrenInGroup.length;
          const childHeight = nodeType === 'groupNode' ? GROUP_MIN_HEIGHT : CHILD_HEIGHT;
          const relativePosition = {
            x: GROUP_PADDING_X,
            y: GROUP_PADDING_TOP + childrenInGroup.reduce((acc, child) => {
              const h = child.type === 'groupNode'
                ? ((child.style?.height as number) || GROUP_MIN_HEIGHT)
                : CHILD_HEIGHT;
              return acc + h + CHILD_SPACING;
            }, 0),
          };

          const newNode: Node = {
            id: newNodeId,
            type: nodeType,
            position: relativePosition,
            parentId: targetGroup.id,
            extent: 'parent' as const,
            data: data as unknown as Record<string, unknown>,
            ...(nodeType === 'groupNode'
              ? { style: { width: GROUP_MIN_WIDTH - GROUP_PADDING_X * 2, height: GROUP_MIN_HEIGHT } }
              : {}),
          };

          setNodes((nds) => [...nds, newNode]);

          // Auto-create internal "Then" edge from previous child
          if (childrenInGroup.length > 0) {
            const prevChild = childrenInGroup[childrenInGroup.length - 1];
            const isLast = true; // new node is always last
            setEdges((eds) => [
              ...eds,
              {
                id: `internal_${prevChild.id}_${newNodeId}`,
                source: prevChild.id,
                sourceHandle: 'bottom',
                target: newNodeId,
                targetHandle: 'top',
                type: 'labeled',
                animated: false,
                data: { label: 'Then' },
                style: { stroke: '#1313ec', strokeWidth: 1.5, opacity: 0.4, strokeDasharray: '4 4' },
              },
            ]);
          }
          return;
        }
      }

      // Normal drop (not inside a group, or invalid type for group)
      const newNode: Node = {
        id: newNodeId,
        type: nodeType,
        position,
        data: data as unknown as Record<string, unknown>,
        ...(nodeType === 'groupNode'
          ? {
              style: { width: GROUP_MIN_WIDTH, height: GROUP_MIN_HEIGHT },
            }
          : {}),
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [reactFlowInstance, setNodes, findGroupAtPosition, nodes, showToast, t]
  );

  // Auto-resize group nodes when children change (only expand, never shrink)
  const childNodeCount = useMemo(
    () => nodes.filter((n) => n.parentId).length,
    [nodes]
  );

  useEffect(() => {
    setNodes((currentNodes) => {
      let changed = false;
      const updated = currentNodes.map((node) => {
        if (node.type !== 'groupNode') return node;

        const children = currentNodes.filter((n) => n.parentId === node.id);
        if (children.length === 0) return node;

        const totalChildrenHeight = children.reduce((acc, child) => {
          const h = child.type === 'groupNode'
            ? ((child.style?.height as number) || GROUP_MIN_HEIGHT)
            : CHILD_HEIGHT;
          return acc + h + CHILD_SPACING;
        }, 0);

        const newHeight = Math.max(
          GROUP_MIN_HEIGHT,
          GROUP_PADDING_TOP + totalChildrenHeight + GROUP_PADDING_BOTTOM
        );
        const newWidth = Math.max(GROUP_MIN_WIDTH, GROUP_MIN_WIDTH);
        const curH = Number(node.style?.height || GROUP_MIN_HEIGHT);
        const curW = Number(node.style?.width || GROUP_MIN_WIDTH);

        if (curH < newHeight || curW < newWidth) {
          changed = true;
          return {
            ...node,
            style: {
              ...node.style,
              width: Math.max(curW, newWidth),
              height: Math.max(curH, newHeight),
            },
          };
        }
        return node;
      });
      return changed ? updated : currentNodes;
    });
  }, [childNodeCount, setNodes]);

  // Handle drag-in / drag-out between groups and canvas
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);

      for (const change of changes) {
        if (change.type === 'position' && change.dragging === false && change.id) {
          setNodes((nds) => {
            const node = nds.find((n) => n.id === change.id);
            if (!node) return nds;

            // --- Drag-out: node already in a group, check if dragged outside ---
            if (node.parentId) {
              const parent = nds.find((n) => n.id === node.parentId);
              if (!parent) return nds;

              const pw = (parent.style?.width as number) || GROUP_MIN_WIDTH;
              const ph = (parent.style?.height as number) || GROUP_MIN_HEIGHT;
              const nx = node.position.x;
              const ny = node.position.y;

              if (nx < -50 || ny < -50 || nx > pw + 50 || ny > ph + 50) {
                return nds.map((n) => {
                  if (n.id !== change.id) return n;
                  return {
                    ...n,
                    position: {
                      x: parent.position.x + nx,
                      y: parent.position.y + ny,
                    },
                    parentId: undefined,
                    extent: undefined,
                  };
                });
              }
              return nds;
            }

            // --- Drag-in: standalone node dropped inside a group ---
            // Only condition and group nodes can enter a group
            if (node.type !== 'conditionNode' && node.type !== 'groupNode') return nds;

            const groupNodes = nds.filter((n) => n.type === 'groupNode' && n.id !== change.id);
            for (const group of groupNodes) {
              const gx = group.position.x;
              const gy = group.position.y;
              const gw = (group.style?.width as number) || GROUP_MIN_WIDTH;
              const gh = (group.style?.height as number) || GROUP_MIN_HEIGHT;

              if (
                node.position.x >= gx &&
                node.position.x <= gx + gw &&
                node.position.y >= gy &&
                node.position.y <= gy + gh
              ) {
                // Calculate stacked position within group
                const childrenInGroup = nds.filter((n) => n.parentId === group.id);
                const relY = GROUP_PADDING_TOP + childrenInGroup.reduce((acc, child) => {
                  const h = child.type === 'groupNode'
                    ? ((child.style?.height as number) || GROUP_MIN_HEIGHT)
                    : CHILD_HEIGHT;
                  return acc + h + CHILD_SPACING;
                }, 0);

                // Update the node with parent relationship
                const updatedChild: Node = {
                  ...node,
                  position: { x: GROUP_PADDING_X, y: relY },
                  parentId: group.id,
                  extent: 'parent' as const,
                };

                // ReactFlow requires parent nodes to appear before their
                // children in the nodes array.  Rebuild the array so that
                // the parent (group) always precedes the newly-adopted child.
                const rest = nds.filter(
                  (n) => n.id !== change.id
                );
                const parentIdx = rest.findIndex(
                  (n) => n.id === group.id
                );
                // Insert the child right after its parent
                rest.splice(parentIdx + 1, 0, updatedChild);
                return rest;
              }
            }
            return nds;
          });
        }
      }
    },
    [onNodesChange, setNodes]
  );

  const handleUpdateNode = useCallback(
    (id: string, dataUpdate: Partial<StrategyNodeData>) => {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id !== id) return n;
          return {
            ...n,
            data: { ...n.data, ...dataUpdate },
          };
        })
      );
    },
    [setNodes]
  );

  const handleRun = useCallback(() => {
    setErrors([]);
    setResults(null);

    const typedNodes = nodes as unknown as Node<StrategyNodeData>[];
    const validation = validateGraph(typedNodes, edges);
    if (!validation.valid) {
      setErrors(validation.errors);
      return;
    }

    const graph = serializeGraph(typedNodes, edges);

    runStrategy.mutate(
      { graph },
      {
        onSuccess: (data) => {
          setResults(data.results);
          setNodes((nds) =>
            nds.map((n) => {
              const nd = getNodeData(n);
              if (nd.node_type === 'output') {
                return {
                  ...n,
                  data: { ...n.data, resultCount: data.matched_count },
                };
              }
              return n;
            })
          );
          showToast(
            t('deploySuccess', { count: data.matched_count, total: data.total_count }),
            'success'
          );
        },
        onError: (error) => {
          setErrors([error instanceof Error ? error.message : t('executionFailed')]);
          showToast(t('deployError'), 'error');
        },
      }
    );
  }, [nodes, edges, runStrategy, setNodes, showToast, t]);

  const handleClear = useCallback(() => {
    setNodes(initialNodes);
    setEdges([]);
    setSelectedNodeId(null);
    setResults(null);
    setErrors([]);
    setStrategyName('');
    setStrategyDescription('');
    setCurrentStrategyId(null);
  }, [setNodes, setEdges]);

  const handleExportJson = useCallback(() => {
    const typedNodes = nodes as unknown as Node<StrategyNodeData>[];
    const graph = serializeGraph(typedNodes, edges);
    const blob = new Blob([JSON.stringify(graph, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'strategy.json';
    a.click();
    URL.revokeObjectURL(url);
  }, [nodes, edges]);

  const handleSave = useCallback(() => {
    if (!strategyName.trim()) {
      setShowSaveDialog(true);
      return;
    }

    const typedNodes = nodes as unknown as Node<StrategyNodeData>[];
    const graph = serializeGraph(typedNodes, edges);

    if (currentStrategyId) {
      updateStrategy.mutate(
        { id: currentStrategyId, data: { name: strategyName, description: strategyDescription || undefined, graph } },
        {
          onSuccess: () => showToast(t('strategyUpdated'), 'info'),
          onError: () => showToast(t('saveFailed'), 'error'),
        }
      );
    } else {
      saveStrategy.mutate(
        { name: strategyName, description: strategyDescription || undefined, graph },
        {
          onSuccess: (saved) => {
            setCurrentStrategyId(saved.id);
            setShowSaveDialog(false);
            showToast(t('strategySaved'), 'info');
          },
          onError: () => showToast(t('saveFailed'), 'error'),
        }
      );
    }
  }, [strategyName, strategyDescription, currentStrategyId, nodes, edges, saveStrategy, updateStrategy, showToast, t]);

  const handleSaveDialogSubmit = useCallback(() => {
    if (!strategyName.trim()) {
      showToast(t('strategyNameRequired'), 'warning');
      return;
    }
    handleSave();
  }, [strategyName, handleSave, showToast, t]);

  const handleLoadStrategy = useCallback(
    (saved: SavedStrategy) => {
      // Reconstruct nodes and edges from saved graph
      const loadedNodes: Node[] = saved.graph.nodes.map((n) => {
        const isGroup = n.data.node_type === 'logic';
        return {
          id: n.id,
          type:
            n.data.node_type === 'universe'
              ? 'universeNode'
              : n.data.node_type === 'condition'
                ? 'conditionNode'
                : n.data.node_type === 'logic'
                  ? 'groupNode'
                  : 'outputNode',
          position: n.position || { x: 0, y: 0 },
          data: n.data as unknown as Record<string, unknown>,
          ...(isGroup ? { style: { width: GROUP_MIN_WIDTH, height: GROUP_MIN_HEIGHT } } : {}),
        };
      });

      // Restore parent-child relationships from child_node_ids
      for (const n of saved.graph.nodes) {
        if (n.data.child_node_ids && n.data.child_node_ids.length > 0) {
          for (const childId of n.data.child_node_ids) {
            const childNode = loadedNodes.find((ln) => ln.id === childId);
            if (childNode) {
              childNode.parentId = n.id;
              childNode.extent = 'parent' as const;
            }
          }
        }
      }

      const loadedEdges: Edge[] = saved.graph.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'labeled',
        animated: true,
        style: { stroke: '#1313ec', strokeWidth: 2, opacity: 0.6 },
      }));

      setNodes(loadedNodes);
      setEdges(loadedEdges);
      setStrategyName(saved.name);
      setStrategyDescription(saved.description || '');
      setCurrentStrategyId(saved.id);
      setShowLoadDialog(false);
      setResults(null);
      setErrors([]);
      setSelectedNodeId(null);
    },
    [setNodes, setEdges]
  );

  const currentSelectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    const found = nodes.find((n) => n.id === selectedNodeId);
    if (!found) return null;
    return found as unknown as Node<StrategyNodeData>;
  }, [nodes, selectedNodeId]);

  // Count nodes by type
  const nodeCount = nodes.length;
  const conditionCount = nodes.filter(
    (n) => getNodeData(n).node_type === 'condition'
  ).length;

  return (
    <div className="flex flex-col h-[calc(100vh-var(--header-height))]">
      {/* Toolbar - Stitch-style */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c]">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-[#1313ec]" />
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {t('title')}
          </span>
        </div>
        <span className="text-gray-300 dark:text-gray-600">|</span>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {t('myStrategies')}
        </span>
        <span className="text-gray-300 dark:text-gray-600">/</span>
        <span className="text-sm text-gray-700 dark:text-gray-200 font-medium">
          {strategyName || t('untitled')}
        </span>

        <div className="flex-1" />

        {/* Error/status display */}
        {runStrategy.isPending && (
          <div className="text-sm text-[#1313ec] font-medium">
            {t('runningStatus')}
          </div>
        )}
        {!runStrategy.isPending && errors.length > 0 && (
          <div className="text-sm text-red-500">
            {errors[0]}
            {errors.length > 1 && ` (${t('moreErrors', { count: errors.length - 1 })})`}
          </div>
        )}
        {!runStrategy.isPending && results && (
          <div className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
            {t('stocksMatched', { count: results.length })}
          </div>
        )}

        <button
          type="button"
          onClick={handleClear}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          {t('reset')}
        </button>
        <button
          type="button"
          onClick={() => setShowLoadDialog(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
        >
          <FolderOpen className="h-3.5 w-3.5" />
          {t('loadStrategy')}
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saveStrategy.isPending || updateStrategy.isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors disabled:opacity-50"
        >
          <Save className="h-3.5 w-3.5" />
          {t('saveStrategy')}
        </button>
        <button
          type="button"
          onClick={() => setShowBacktest(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
        >
          <TestTube className="h-3.5 w-3.5" />
          {t('backtest')}
        </button>
        <button
          type="button"
          onClick={handleRun}
          disabled={runStrategy.isPending}
          className="flex items-center gap-2 px-5 py-1.5 rounded-full bg-[#1313ec] text-white text-sm font-medium hover:bg-[#1010c0] transition-colors disabled:opacity-50"
        >
          {runStrategy.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          {t('deployStrategy')}
        </button>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left palette */}
        <NodePalette nodeCount={nodeCount} />

        {/* Canvas */}
        <div className="flex-1" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onReconnect={onReconnect}
            edgesReconnectable
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onInit={setReactFlowInstance}
            onDragOver={onDragOver}
            onDrop={onDrop}
            isValidConnection={isValidConnection}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            fitViewOptions={{ maxZoom: 0.75, padding: 0.3 }}
            connectionMode={ConnectionMode.Loose}
            className="!bg-[#f6f6f7] dark:!bg-[#141414]"
            defaultEdgeOptions={{
              type: 'labeled',
              animated: true,
              style: { stroke: '#1313ec', strokeWidth: 2, opacity: 0.6 },
            }}
          >
            <Controls className="!bg-white dark:!bg-[#1e1e1f] !border-[#e1e3e5] dark:!border-[#2e2e30] !shadow-sm !rounded-lg [&>button]:!bg-white dark:[&>button]:!bg-[#1e1e1f] [&>button]:!border-[#e1e3e5] dark:[&>button]:!border-[#2e2e30] [&>button]:!text-gray-600 dark:[&>button]:!text-gray-300 [&>button:hover]:!bg-gray-50 dark:[&>button:hover]:!bg-gray-800" />
            <MiniMap
              className="!bg-white dark:!bg-[#1e1e1f] !border-[#e1e3e5] dark:!border-[#2e2e30] !rounded-lg !shadow-sm"
              nodeColor={() => '#1313ec'}
              maskColor="rgba(0, 0, 0, 0.08)"
            />
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1}
              color="#d1d5db"
              className="dark:!opacity-20"
            />
          </ReactFlow>
        </div>

        {/* Right properties panel */}
        {currentSelectedNode && (
          <PropertiesPanel
            node={currentSelectedNode}
            onUpdate={handleUpdateNode}
            onClose={() => setSelectedNodeId(null)}
            onDeleteNode={(nodeId) => {
              setNodes((nds) => nds.filter((n) => n.id !== nodeId && n.parentId !== nodeId));
              setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
              setSelectedNodeId(null);
            }}
          />
        )}
      </div>

      {/* Bottom status bar */}
      <div className="flex items-center justify-between px-4 py-1.5 border-t border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c] text-[11px] text-gray-400 dark:text-gray-500">
        <div className="flex items-center gap-4">
          <span>{t('nodes')}: {nodeCount}</span>
          <span>{t('filters')}: {conditionCount}</span>
          {results && (
            <span className="text-emerald-600 dark:text-emerald-400 font-medium">
              {t('matched')}: {results.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span>{t('kospiData')}</span>
          <span>{results ? t('lastRunJustNow') : t('lastRunNever')}</span>
          <button
            type="button"
            onClick={handleExportJson}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <Download className="h-3 w-3" />
            {t('exportJson')}
          </button>
        </div>
      </div>

      {/* Results panel */}
      {(runStrategy.isPending || (results && results.length > 0)) && (
        <div
          className={`border-t border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c] transition-all duration-300 ease-out ${
            isResultPanelVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
          } ${runStrategy.isPending ? 'min-h-44' : 'max-h-64 overflow-y-auto'}`}
        >
          {runStrategy.isPending ? (
            <div className="flex flex-col items-center justify-center py-10 text-gray-400 dark:text-gray-500">
              <Loader2 className="h-8 w-8 animate-spin mb-3" />
              <span className="text-sm">{t('runningStrategy')}</span>
              <span className="text-xs mt-1">{t('runningStrategyNote')}</span>
            </div>
          ) : results ? (
            <>
              <div className="px-4 py-2 border-b border-[#e1e3e5] dark:border-[#2e2e30]">
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {t('results', { count: results.length })}
                </span>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider border-b border-[#e1e3e5] dark:border-[#2e2e30]">
                    <th className="px-4 py-2">{t('ticker')}</th>
                    <th className="px-4 py-2">{t('name')}</th>
                    <th className="px-4 py-2 text-right">{t('price')}</th>
                    <th className="px-4 py-2 text-center">{t('status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r) => (
                    <tr
                      key={r.ticker}
                      className="border-b border-[#e1e3e5] dark:border-[#2e2e30] hover:bg-gray-50 dark:hover:bg-white/5 transition-colors cursor-pointer"
                      onClick={() => {
                        const width = 1000;
                        const height = 700;
                        const left = (screen.width - width) / 2;
                        const top = (screen.height - height) / 2;
                        window.open(
                          `/${locale}/analysis/${r.ticker}`,
                          `analysis_${r.ticker}`,
                          `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`
                        );
                      }}
                    >
                      <td className="px-4 py-1.5 font-mono text-[#1313ec] font-medium underline decoration-[#1313ec]/30 hover:decoration-[#1313ec]">
                        {r.ticker}
                      </td>
                      <td className="px-4 py-1.5 text-gray-700 dark:text-gray-200">
                        {r.name}
                      </td>
                      <td className="px-4 py-1.5 text-right text-gray-700 dark:text-gray-200">
                        {r.current_price?.toLocaleString() ?? '-'}
                      </td>
                      <td className="px-4 py-1.5 text-center">
                        <span
                          className={`inline-block w-2 h-2 rounded-full ${
                            r.matched ? 'bg-emerald-500' : 'bg-red-500'
                          }`}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
        </div>
      )}

      {/* Save dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-[#1e1e1f] rounded-xl shadow-2xl border border-[#e1e3e5] dark:border-[#2e2e30] w-full max-w-md mx-4">
            <div className="flex items-center justify-between px-5 py-3 border-b border-[#e1e3e5] dark:border-[#2e2e30]">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {t('saveDialogTitle')}
              </h3>
              <button type="button" onClick={() => setShowSaveDialog(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="px-5 py-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  {t('strategyName')}
                </label>
                <input
                  type="text"
                  value={strategyName}
                  onChange={(e) => setStrategyName(e.target.value)}
                  placeholder={t('strategyNamePlaceholder')}
                  className="w-full px-3 py-2 text-sm border border-[#e1e3e5] dark:border-[#2e2e30] rounded-lg bg-white dark:bg-[#0b0b0c] text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-[#1313ec]/30 focus:border-[#1313ec]"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  {t('strategyDescription')}
                </label>
                <textarea
                  value={strategyDescription}
                  onChange={(e) => setStrategyDescription(e.target.value)}
                  placeholder={t('strategyDescPlaceholder')}
                  rows={2}
                  className="w-full px-3 py-2 text-sm border border-[#e1e3e5] dark:border-[#2e2e30] rounded-lg bg-white dark:bg-[#0b0b0c] text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-[#1313ec]/30 focus:border-[#1313ec] resize-none"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 px-5 py-3 border-t border-[#e1e3e5] dark:border-[#2e2e30]">
              <button
                type="button"
                onClick={() => setShowSaveDialog(false)}
                className="px-4 py-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveDialogSubmit}
                disabled={saveStrategy.isPending}
                className="px-4 py-1.5 text-sm font-medium text-white bg-[#1313ec] rounded-lg hover:bg-[#1010c0] transition-colors disabled:opacity-50"
              >
                {saveStrategy.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : t('saveStrategy')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Load dialog */}
      {showLoadDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-[#1e1e1f] rounded-xl shadow-2xl border border-[#e1e3e5] dark:border-[#2e2e30] w-full max-w-lg mx-4">
            <div className="flex items-center justify-between px-5 py-3 border-b border-[#e1e3e5] dark:border-[#2e2e30]">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {t('savedStrategies')}
              </h3>
              <button type="button" onClick={() => setShowLoadDialog(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="px-5 py-4 max-h-80 overflow-y-auto">
              {savedStrategies.isLoading && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
                </div>
              )}
              {savedStrategies.data && savedStrategies.data.strategies.length === 0 && (
                <p className="text-sm text-gray-400 text-center py-8">{t('noSavedStrategies')}</p>
              )}
              {savedStrategies.data?.strategies.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => handleLoadStrategy(s)}
                  className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5 transition-colors mb-1 group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{s.name}</span>
                    <span className="text-[10px] text-gray-400">
                      {new Date(s.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  {s.description && (
                    <p className="text-xs text-gray-400 mt-0.5 truncate">{s.description}</p>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Backtest slide-over panel */}
      <BacktestPanel
        isOpen={showBacktest}
        onClose={() => setShowBacktest(false)}
      />

      {/* Toast notifications */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type as ToastType}
          onClose={hideToast}
          autoCloseMs={null}
        />
      )}
    </div>
  );
}

export default function StrategyPage() {
  return (
    <ConditionsProvider>
      <StrategyPageInner />
    </ConditionsProvider>
  );
}
