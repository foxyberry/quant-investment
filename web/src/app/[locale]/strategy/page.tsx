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
  type EdgeChange,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  Loader2, Zap, RotateCcw, Save, TestTube, FolderOpen, X,
  ChevronRight, ChevronDown, Home, Calendar, Search,
  AlignHorizontalSpaceAround, AlignVerticalSpaceAround,
  PanelLeftClose, PanelLeftOpen, ChevronUp,
} from 'lucide-react';
import UniverseNode from '@/components/strategy/nodes/UniverseNode';
import ConditionNode from '@/components/strategy/nodes/ConditionNode';
import GroupNode from '@/components/strategy/nodes/GroupNode';
import OutputNode from '@/components/strategy/nodes/OutputNode';
import SectorNode from '@/components/strategy/nodes/SectorNode';
import LabeledEdge from '@/components/strategy/edges/LabeledEdge';
import NodePalette from '@/components/strategy/NodePalette';
import IntermediateResultsPanel from '@/components/strategy/IntermediateResultsPanel';
import SideInspectionPanel from '@/components/strategy/SideInspectionPanel';
import ChatPanel, { type NodeMapping } from '@/components/strategy/ChatPanel';

import BacktestPanel from '@/components/backtest/BacktestPanel';
import { Toast, useToast, type ToastType } from '@/components/ui/Toast';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import { serializeGraph, getDownstreamNodeIds } from '@/lib/strategy/graphSerializer';
import { validateGraph } from '@/lib/strategy/graphValidator';
import { SAMPLE_STRATEGY_PRESETS, PRESET_CATEGORY_ORDER, type SampleStrategyPreset, type PresetCategory } from '@/lib/strategy/sampleStrategies';
import { ConditionsProvider, useConditions } from '@/contexts/ConditionsContext';
import { useSavedStrategies, useSaveStrategy, useUpdateStrategy } from '@/hooks/useStrategy';
import type { StrategyResultItem, SavedStrategy, NodeIntermediateResult } from '@/lib/api';
import { runStrategyStream, saveExecution } from '@/lib/api';

const nodeTypes: NodeTypes = {
  universeNode: UniverseNode,
  conditionNode: ConditionNode,
  groupNode: GroupNode,
  outputNode: OutputNode,
  sectorNode: SectorNode,
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

type LayoutNodeData = {
  node_type: string;
  condition_type?: string;
  params?: Record<string, unknown>;
};

function estimateNodeSize(node: { data: LayoutNodeData }): { width: number; height: number } {
  const data = node.data;
  if (data.node_type === 'universe') {
    return { width: 340, height: 92 };
  }
  if (data.node_type === 'sector') {
    return { width: 300, height: 92 };
  }
  if (data.node_type === 'logic') {
    return { width: GROUP_MIN_WIDTH, height: GROUP_MIN_HEIGHT };
  }
  if (data.node_type === 'output') {
    return { width: 220, height: 84 };
  }

  // condition node
  const conditionKey = data.condition_type ?? '';
  const paramCount = Object.keys(data.params ?? {}).length;
  const width = Math.min(460, Math.max(280, 280 + conditionKey.length * 4 + paramCount * 10));
  const height = Math.min(180, Math.max(96, 96 + Math.min(paramCount, 4) * 16));
  return { width, height };
}

/**
 * Compute a clean layout for strategy nodes using topological sort.
 * Supports both horizontal (left-to-right) and vertical (top-to-bottom) directions.
 * Uses estimated node sizes so long condition cards do not overlap after loading.
 */
function computeAutoLayout(
  nodes: Array<{ id: string; data: LayoutNodeData }>,
  edges: Array<{ source: string; target: string }>,
  direction: 'horizontal' | 'vertical' = 'horizontal'
): Map<string, { x: number; y: number }> {
  const GAP_PRIMARY = direction === 'horizontal' ? 140 : 72;
  const GAP_SECONDARY = direction === 'horizontal' ? 72 : 140;
  const START_X = 80;
  const START_Y = 120;

  // Build adjacency + in-degree
  const inDegree = new Map<string, number>();
  const adj = new Map<string, string[]>();
  for (const n of nodes) {
    inDegree.set(n.id, 0);
    adj.set(n.id, []);
  }
  for (const e of edges) {
    adj.get(e.source)?.push(e.target);
    inDegree.set(e.target, (inDegree.get(e.target) ?? 0) + 1);
  }

  // Kahn's topological sort → assigns each node a "column" (depth)
  const depth = new Map<string, number>();
  const queue: string[] = [];
  for (const [id, deg] of inDegree) {
    if (deg === 0) {
      queue.push(id);
      depth.set(id, 0);
    }
  }

  while (queue.length > 0) {
    const curr = queue.shift()!;
    const currDepth = depth.get(curr) ?? 0;
    for (const next of adj.get(curr) ?? []) {
      const newDepth = currDepth + 1;
      depth.set(next, Math.max(depth.get(next) ?? 0, newDepth));
      const remaining = (inDegree.get(next) ?? 1) - 1;
      inDegree.set(next, remaining);
      if (remaining === 0) queue.push(next);
    }
  }

  // Assign unvisited nodes (disconnected) to column 0
  for (const n of nodes) {
    if (!depth.has(n.id)) depth.set(n.id, 0);
  }

  // Group nodes by depth level
  const columns = new Map<number, string[]>();
  for (const [id, col] of depth) {
    if (!columns.has(col)) columns.set(col, []);
    columns.get(col)!.push(id);
  }

  const nodeIndex = new Map(nodes.map((n, idx) => [n.id, idx]));
  const sizeById = new Map(nodes.map((n) => [n.id, estimateNodeSize(n)]));

  const positions = new Map<string, { x: number; y: number }>();
  const sortedCols = Array.from(columns.keys()).sort((a, b) => a - b);

  if (direction === 'horizontal') {
    // Left-to-right: depth → x, siblings → y
    const columnMaxWidth = new Map<number, number>();
    for (const col of sortedCols) {
      const ids = columns.get(col)!;
      columnMaxWidth.set(col, Math.max(...ids.map((id) => sizeById.get(id)?.width ?? 260), 260));
    }
    let runningX = START_X;
    const colX = new Map<number, number>();
    for (const col of sortedCols) {
      colX.set(col, runningX);
      runningX += (columnMaxWidth.get(col) ?? 260) + GAP_PRIMARY;
    }
    for (const col of sortedCols) {
      const ids = [...columns.get(col)!].sort((a, b) => (nodeIndex.get(a) ?? 0) - (nodeIndex.get(b) ?? 0));
      const x = colX.get(col) ?? START_X;
      let runningY = START_Y;
      for (const id of ids) {
        positions.set(id, { x, y: runningY });
        runningY += (sizeById.get(id)?.height ?? 100) + GAP_SECONDARY;
      }
    }
  } else {
    // Top-to-bottom: depth → y, siblings → x
    const rowMaxHeight = new Map<number, number>();
    for (const col of sortedCols) {
      const ids = columns.get(col)!;
      rowMaxHeight.set(col, Math.max(...ids.map((id) => sizeById.get(id)?.height ?? 100), 100));
    }
    let runningY = START_Y;
    const rowY = new Map<number, number>();
    for (const col of sortedCols) {
      rowY.set(col, runningY);
      runningY += (rowMaxHeight.get(col) ?? 100) + GAP_PRIMARY;
    }
    for (const col of sortedCols) {
      const ids = [...columns.get(col)!].sort((a, b) => (nodeIndex.get(a) ?? 0) - (nodeIndex.get(b) ?? 0));
      const y = rowY.get(col) ?? START_Y;
      let runningX = START_X;
      for (const id of ids) {
        positions.set(id, { x: runningX, y });
        runningX += (sizeById.get(id)?.width ?? 260) + GAP_SECONDARY;
      }
    }
  }

  return positions;
}

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

// --- sessionStorage helpers for locale-switch persistence (#80, #183) ---
const CANVAS_KEY = 'strategy-canvas-state';
const RESULTS_KEY = 'strategy-results-state';

interface CanvasSnapshot {
  nodes: Node[];
  edges: Edge[];
  strategyName: string;
  strategyDescription: string;
  currentStrategyId: string | null;
}

interface ResultsSnapshot {
  results: StrategyResultItem[] | null;
  nodeResults: Record<string, NodeIntermediateResult> | null;
  streamStatus: 'idle' | 'running' | 'done' | 'error';
  lastRunTime: string | null; // ISO string for serialization
}

function saveCanvasToSession(snapshot: CanvasSnapshot) {
  try {
    sessionStorage.setItem(CANVAS_KEY, JSON.stringify(snapshot));
  } catch { /* quota exceeded — ignore */ }
}

function saveResultsToSession(snapshot: ResultsSnapshot) {
  try {
    sessionStorage.setItem(RESULTS_KEY, JSON.stringify(snapshot));
  } catch { /* quota exceeded — ignore */ }
}

function loadCanvasFromSession(): CanvasSnapshot | null {
  try {
    const raw = sessionStorage.getItem(CANVAS_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as CanvasSnapshot;
  } catch {
    return null;
  }
}

function loadResultsFromSession(): ResultsSnapshot | null {
  try {
    const raw = sessionStorage.getItem(RESULTS_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as ResultsSnapshot;
  } catch {
    return null;
  }
}

function StrategyPageInner() {
  const t = useTranslations('strategy');
  const tScreening = useTranslations('screening');
  useLocale(); // force re-render on locale switch for sessionStorage persistence
  const { getDefaultParams } = useConditions();

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [results, setResults] = useState<StrategyResultItem[] | null>(null);
  const [nodeResults, setNodeResults] = useState<Record<string, NodeIntermediateResult> | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [showBacktest, setShowBacktest] = useState(false);
  const [showInspection, setShowInspection] = useState(false);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const reconnectingEdgeId = useRef<string | null>(null);
  const readyToSaveRef = useRef(false);

  // Prevent ReactFlow SSR hydration mismatch
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  // Save/Load state
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [showLoadDialog, setShowLoadDialog] = useState(false);
  const [presetSearch, setPresetSearch] = useState('');
  const [collapsedCategories, setCollapsedCategories] = useState<Set<PresetCategory>>(new Set());
  const [strategyName, setStrategyName] = useState('');
  const [strategyDescription, setStrategyDescription] = useState('');
  const [currentStrategyId, setCurrentStrategyId] = useState<string | null>(null);
  const [isSampleStrategy, setIsSampleStrategy] = useState(false);
  const [lastRunTime, setLastRunTime] = useState<Date | null>(null);
  const [deployProgress, setDeployProgress] = useState(0);
  const [progressDetail, setProgressDetail] = useState<{ processed: number; total: number; matched: number } | null>(null);
  const [streamStatus, setStreamStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [showMiniMap, setShowMiniMap] = useState(true);
  const [showPalette, setShowPalette] = useState(true);
  const streamAbortRef = useRef<{ abort: () => void } | null>(null);

  // Restore from sessionStorage after mount (locale-switch persistence)
  // Uses setTimeout guard so the save effect doesn't overwrite sessionStorage
  // with initial state before the restored state is applied (StrictMode safe).
  useEffect(() => {
    const restored = loadCanvasFromSession();
    if (restored) {
      setNodes(restored.nodes);
      setEdges(restored.edges);
      setStrategyName(restored.strategyName);
      setStrategyDescription(restored.strategyDescription);
      setCurrentStrategyId(restored.currentStrategyId);
    }
    // Restore execution results (#183)
    const restoredResults = loadResultsFromSession();
    if (restoredResults) {
      if (restoredResults.results !== undefined) setResults(restoredResults.results);
      if (restoredResults.nodeResults !== undefined) setNodeResults(restoredResults.nodeResults);
      if (restoredResults.streamStatus && restoredResults.streamStatus !== 'running') {
        setStreamStatus(restoredResults.streamStatus);
      }
      if (restoredResults.lastRunTime) {
        setLastRunTime(new Date(restoredResults.lastRunTime));
      }
    }
    const timer = setTimeout(() => { readyToSaveRef.current = true; }, 0);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist canvas state to sessionStorage on every change (for locale-switch survival)
  useEffect(() => {
    if (!readyToSaveRef.current) return;
    saveCanvasToSession({ nodes, edges, strategyName, strategyDescription, currentStrategyId });
  }, [nodes, edges, strategyName, strategyDescription, currentStrategyId]);

  // Persist execution results separately (avoids re-serializing large results on canvas drag)
  useEffect(() => {
    if (!readyToSaveRef.current) return;
    saveResultsToSession({
      results, nodeResults, streamStatus,
      lastRunTime: lastRunTime?.toISOString() ?? null,
    });
  }, [results, nodeResults, streamStatus, lastRunTime]);

  const savedStrategies = useSavedStrategies();
  const isRunning = streamStatus === 'running';
  const saveStrategy = useSaveStrategy();
  const updateStrategy = useUpdateStrategy();
  const { toast, showToast, hideToast } = useToast();

  // Abort stream on unmount
  useEffect(() => {
    return () => { streamAbortRef.current?.abort(); };
  }, []);

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

      // Exclude the edge being reconnected from checks
      const activeEdges = reconnectingEdgeId.current
        ? edges.filter((e) => e.id !== reconnectingEdgeId.current)
        : edges;

      // Each handle can only have one connection (both source and target)
      const sourceAlreadyConnected = activeEdges.some(
        (e) => e.source === source && (e.sourceHandle ?? null) === (sourceHandle ?? null)
      );
      const targetAlreadyConnected = activeEdges.some(
        (e) => e.target === target && (e.targetHandle ?? null) === (targetHandle ?? null)
      );
      if (sourceAlreadyConnected || targetAlreadyConnected) return false;

      // Allowed target types per source type
      const allowedTargets: Record<string, string[]> = {
        universeNode: ['conditionNode', 'groupNode', 'sectorNode'],
        sectorNode: ['conditionNode', 'groupNode'],
        conditionNode: ['conditionNode', 'groupNode', 'outputNode'],
        groupNode: ['conditionNode', 'groupNode', 'outputNode'],
      };

      const allowed = allowedTargets[sourceType!];
      if (!allowed || !allowed.includes(targetType!)) return false;

      // Prevent cycles: check if target can already reach source via existing edges
      const visited = new Set<string>();
      const queue = [target];
      while (queue.length > 0) {
        const current = queue.pop()!;
        if (current === source) return false; // cycle detected
        if (visited.has(current)) continue;
        visited.add(current);
        for (const edge of activeEdges) {
          if (edge.source === current) {
            queue.push(edge.target);
          }
        }
      }
      return true;
    },
    [nodes, edges]
  );


  const onConnect = useCallback(
    (connection: Connection) => {
      if (!isValidConnection(connection)) return;
      setEdges((eds) => addEdge(connection, eds));
    },
    [isValidConnection, setEdges]
  );

  const onReconnectStart = useCallback((_: unknown, edge: Edge) => {
    reconnectingEdgeId.current = edge.id;
  }, []);

  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      reconnectingEdgeId.current = null;
      setEdges((eds) => reconnectEdge(oldEdge, newConnection, eds));
    },
    [setEdges]
  );

  const onReconnectEnd = useCallback(
    (_: unknown, edge: Edge) => {
      if (reconnectingEdgeId.current) {
        // Reconnect failed — remove the dangling edge
        setEdges((eds) => eds.filter((e) => e.id !== edge.id));
      }
      reconnectingEdgeId.current = null;
    },
    [setEdges]
  );

  // Clear intermediate results for downstream nodes when edges are removed
  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const removedIds = changes
        .filter((c): c is EdgeChange & { type: 'remove' } => c.type === 'remove')
        .map((c) => c.id);

      if (removedIds.length > 0) {
        // Find target nodes of removed edges
        const targetNodeIds = edges
          .filter((e) => removedIds.includes(e.id))
          .map((e) => e.target);

        if (targetNodeIds.length > 0) {
          const downstream = getDownstreamNodeIds(targetNodeIds, edges);
          targetNodeIds.forEach((id) => downstream.add(id));

          setNodes((nds) =>
            nds.map((n) => {
              if (!downstream.has(n.id)) return n;
              const nd = n.data as Record<string, unknown>;
              if (nd.intermediateResult === undefined && nd.resultCount === undefined)
                return n;
              const { intermediateResult: _ir, resultCount: _rc, ...rest } = nd;
              return { ...n, data: rest as StrategyNodeData };
            })
          );
        }
      }

      onEdgesChange(changes);
    },
    [edges, onEdgesChange, setNodes]
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      setSelectedNodeId(node.id);
    },
    []
  );

  const onNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      setSelectedNodeId(node.id);
      if (nodeResults && nodeResults[node.id]) {
        setShowInspection(true);
      }
    },
    [nodeResults]
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
      } else if (type === 'sector') {
        nodeType = 'sectorNode';
        data = { node_type: 'sector', sector: '' };
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
        // Block invalid drops: universe, sector, and output cannot go in groups
        if (nodeType === 'universeNode' || nodeType === 'sectorNode' || nodeType === 'outputNode') {
          showToast(t('cannotDropInGroup'), 'warning');
          // Still place on canvas as standalone (fall through)
        } else if (nodeType === 'conditionNode' || nodeType === 'groupNode') {
          // Valid drop: condition or nested group into a group
          const childrenInGroup = nodes.filter(
            (n) => n.parentId === targetGroup.id
          );
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
    [reactFlowInstance, setNodes, setEdges, findGroupAtPosition, nodes, getDefaultParams, showToast, t]
  );

  // Add condition nodes from chat assistant suggestions
  const handleAddNodesFromChat = useCallback(
    (mappings: NodeMapping[]) => {
      const newNodes: Node[] = mappings.map((m, i) => ({
        id: getNodeId(),
        type: 'conditionNode',
        position: { x: 100 + i * 50, y: 200 + i * 80 },
        data: {
          node_type: 'condition' as const,
          condition_type: m.condition_type,
          params: m.params,
        } as unknown as Record<string, unknown>,
      }));
      setNodes((nds) => [...nds, ...newNodes]);
    },
    [setNodes],
  );

  // Existing condition nodes for chat update-in-place feature
  const existingConditionNodes = useMemo(
    () =>
      nodes
        .filter((n) => (n.data as Record<string, unknown>)?.node_type === 'condition' && (n.data as Record<string, unknown>)?.condition_type)
        .map((n) => ({
          id: n.id,
          condition_type: (n.data as Record<string, unknown>).condition_type as string,
        })),
    [nodes],
  );

  // Update existing node params from chat suggestion
  const handleUpdateNodeFromChat = useCallback(
    (nodeId: string, params: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId
            ? { ...n, data: { ...n.data, params: { ...((n.data as Record<string, unknown>).params as Record<string, unknown> || {}), ...params } } as Record<string, unknown> }
            : n,
        ),
      );
    },
    [setNodes],
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
                const parentId = node.parentId!;
                const remainingSiblings = nds.filter(
                  (n) => n.parentId === parentId && n.id !== change.id
                );

                // Rewire edges: group-level edges → direct to the extracted node
                // if no siblings remain, or keep group edges if siblings stay
                setEdges((eds) => {
                  let updated = eds.map((e) => {
                    // If group has no remaining children, redirect group edges to the extracted node
                    if (remainingSiblings.length === 0) {
                      if (e.target === parentId) {
                        return { ...e, target: change.id, targetHandle: null };
                      }
                      if (e.source === parentId) {
                        return { ...e, source: change.id, sourceHandle: null };
                      }
                    }
                    return e;
                  });

                  // Deduplicate
                  const seen = new Set<string>();
                  updated = updated.filter((e) => {
                    const key = `${e.source}:${e.sourceHandle ?? ''}→${e.target}:${e.targetHandle ?? ''}`;
                    if (seen.has(key)) return false;
                    seen.add(key);
                    return true;
                  });

                  return updated;
                });

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

                // --- Auto-rewire edges (#127) ---
                // Collect all node ids inside this group (including newly added)
                const siblingIds = new Set(
                  rest
                    .filter((n) => n.parentId === group.id)
                    .map((n) => n.id)
                );
                siblingIds.add(change.id);

                setEdges((eds) => {
                  let rewired = eds.map((e) => {
                    const srcInGroup = siblingIds.has(e.source);
                    const tgtInGroup = siblingIds.has(e.target);

                    // Rule 3: edges between siblings inside the same group → remove
                    if (srcInGroup && tgtInGroup) return null;

                    // Rule 1: incoming edge to a node entering the group → redirect to group
                    if (!srcInGroup && tgtInGroup) {
                      return { ...e, target: group.id, targetHandle: null };
                    }

                    // Rule 2: outgoing edge from a node entering the group → redirect from group
                    if (srcInGroup && !tgtInGroup) {
                      return { ...e, source: group.id, sourceHandle: null };
                    }

                    return e;
                  }).filter((e): e is Edge => e !== null);

                  // Rule 4: deduplicate (same source+target after rewiring)
                  const seen = new Set<string>();
                  rewired = rewired.filter((e) => {
                    const key = `${e.source}:${e.sourceHandle ?? ''}→${e.target}:${e.targetHandle ?? ''}`;
                    if (seen.has(key)) return false;
                    seen.add(key);
                    return true;
                  });

                  return rewired;
                });

                return rest;
              }
            }
            return nds;
          });
        }
      }
    },
    [onNodesChange, setNodes, setEdges]
  );

  const handleRun = useCallback(() => {
    setErrors([]);
    setResults(null);
    setDeployProgress(0);
    setProgressDetail(null);
    setStreamStatus('running');

    const typedNodes = nodes as unknown as Node<StrategyNodeData>[];
    const validation = validateGraph(typedNodes, edges);
    if (!validation.valid) {
      setErrors(validation.errors);
      setStreamStatus('idle');
      return;
    }

    const graph = serializeGraph(typedNodes, edges);

    // Abort any previous stream
    streamAbortRef.current?.abort();

    const handleResult = (data: import('@/lib/api').StrategyExecuteResponse) => {
      setResults(data.results);
      setDeployProgress(100);
      setStreamStatus('done');
      setLastRunTime(new Date());
      const nr = data.node_results ?? null;
      setNodeResults(nr);
      setNodes((nds) =>
        nds.map((n) => {
          const nd = getNodeData(n);
          const updates: Record<string, unknown> = {};
          if (nd.node_type === 'output') {
            updates.resultCount = data.matched_count;
          }
          if (nr && nr[n.id]) {
            updates.intermediateResult = nr[n.id];
          }
          if (nd.node_type === 'universe' && !updates.intermediateResult) {
            updates.intermediateResult = {
              node_id: n.id,
              node_type: 'universe',
              label: nd.universe || 'Universe',
              stock_count: data.total_count,
              stocks: [],
            };
          }
          if (Object.keys(updates).length === 0) return n;
          return { ...n, data: { ...n.data, ...updates } };
        })
      );
      showToast(
        t('deploySuccess', { count: data.matched_count, total: data.total_count }),
        'success'
      );

      // Auto-save execution result (fire-and-forget)
      saveExecution({
        execution_type: 'strategy',
        preset: strategyName || 'Untitled Strategy',
        universes: [data.universe],
        graph: graph as unknown as Record<string, unknown>,
        total_count: data.total_count,
        matched_count: data.matched_count,
        results: data.results as unknown as Array<Record<string, unknown>>,
        strategy_id: currentStrategyId ?? undefined,
      }).catch((err) => {
        console.warn('Auto-save failed:', err);
      });
    };

    const stream = runStrategyStream(graph, undefined, {
      onProgress: (event) => {
        setDeployProgress(event.progress_pct);
        setProgressDetail({
          processed: event.processed_tickers,
          total: event.total_tickers,
          matched: event.matched_count,
        });
      },
      onResult: handleResult,
      onError: (errorMsg) => {
        setStreamStatus('error');
        setErrors([errorMsg]);
        showToast(t('deployError'), 'error');
      },
    });

    streamAbortRef.current = stream;
  }, [nodes, edges, setNodes, currentStrategyId, strategyName, showToast, t]);

  const handleClear = useCallback(() => {
    setNodes(initialNodes);
    setEdges([]);
    setSelectedNodeId(null);
    setResults(null);
    setNodeResults(null);
    setErrors([]);
    setStrategyName('');
    setStrategyDescription('');
    setCurrentStrategyId(null);
    setIsSampleStrategy(false);
  }, [setNodes, setEdges]);

  const handleAutoLayout = useCallback((direction: 'horizontal' | 'vertical') => {
    const topLevelNodes = nodes.filter((n) => !n.parentId);
    const layoutData = topLevelNodes.map((n) => ({
      id: n.id,
      data: n.data as LayoutNodeData,
    }));
    const autoPositions = computeAutoLayout(layoutData, edges, direction);
    setNodes((nds) =>
      nds.map((n) => {
        const pos = autoPositions.get(n.id);
        if (pos) return { ...n, position: pos };
        return n;
      })
    );
    setTimeout(() => {
      reactFlowInstance?.fitView({ duration: 300 });
    }, 50);
  }, [nodes, edges, setNodes, reactFlowInstance]);

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

  const handleExportCsv = useCallback(() => {
    if (!results || results.length === 0) return;
    const headers = ['Ticker', 'Name', 'Current Price'];
    const rows = results.map((s) =>
      [s.ticker, `"${(s.name || '').replace(/"/g, '""')}"`, s.current_price ?? ''].join(',')
    );
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `strategy-results-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [results]);

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
            setIsSampleStrategy(false);
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

  const loadGraphIntoCanvas = useCallback(
    ({
      graph,
      name,
      description,
      strategyId,
      sample,
    }: {
      graph: SavedStrategy['graph'];
      name: string;
      description: string | null;
      strategyId: string | null;
      sample: boolean;
    }) => {
      // Compute auto-layout positions for top-level (non-child) nodes
      const topLevelNodes = graph.nodes.filter((n) => {
        // A node is a child if any other node lists it in child_node_ids
        return !graph.nodes.some(
          (parent) =>
            parent.data.child_node_ids?.includes(n.id)
        );
      });
      const autoPositions = computeAutoLayout(topLevelNodes, graph.edges);

      // Reconstruct nodes and edges from saved graph
      const loadedNodes: Node[] = graph.nodes.map((n) => {
        const isGroup = n.data.node_type === 'logic';
        // Use auto-layout position for top-level nodes
        const autoPos = autoPositions.get(n.id);
        return {
          id: n.id,
          type:
            n.data.node_type === 'universe'
              ? 'universeNode'
              : n.data.node_type === 'sector'
                ? 'sectorNode'
                : n.data.node_type === 'condition'
                  ? 'conditionNode'
                  : n.data.node_type === 'logic'
                    ? 'groupNode'
                    : 'outputNode',
          position: autoPos || n.position || { x: 0, y: 0 },
          data: n.data as unknown as Record<string, unknown>,
          ...(isGroup ? { style: { width: GROUP_MIN_WIDTH, height: GROUP_MIN_HEIGHT } } : {}),
        };
      });

      // Restore parent-child relationships from child_node_ids
      for (const n of graph.nodes) {
        if (n.data.child_node_ids && n.data.child_node_ids.length > 0) {
          for (const childId of n.data.child_node_ids) {
            const childNode = loadedNodes.find((ln) => ln.id === childId);
            if (childNode) {
              childNode.parentId = n.id;
              childNode.extent = 'parent' as const;
              // Position children relative to parent group
              const childIndex = n.data.child_node_ids.indexOf(childId);
              childNode.position = {
                x: GROUP_PADDING_X,
                y: GROUP_PADDING_TOP + childIndex * (CHILD_HEIGHT + CHILD_SPACING),
              };
            }
          }
        }
      }

      const loadedEdges: Edge[] = graph.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'labeled',
        animated: true,
        style: { stroke: '#1313ec', strokeWidth: 2, opacity: 0.6 },
      }));

      setNodes(loadedNodes);
      setEdges(loadedEdges);
      setStrategyName(name);
      setStrategyDescription(description || '');
      setCurrentStrategyId(strategyId);
      setIsSampleStrategy(sample);
      setShowLoadDialog(false);
      setResults(null);
      setNodeResults(null);
      setStreamStatus('idle');
      setDeployProgress(0);
      setProgressDetail(null);
      setLastRunTime(null);
      setErrors([]);
      setSelectedNodeId(null);

      // Fit view after layout settles
      requestAnimationFrame(() => {
        reactFlowInstance?.fitView({ maxZoom: 0.72, padding: 0.38 });
      });
    },
    [setNodes, setEdges, reactFlowInstance]
  );

  const handleLoadStrategy = useCallback(
    (saved: SavedStrategy) => {
      loadGraphIntoCanvas({
        graph: saved.graph,
        name: saved.name,
        description: saved.description,
        strategyId: saved.id,
        sample: false,
      });
    },
    [loadGraphIntoCanvas]
  );

  const handleLoadSampleStrategy = useCallback(
    (sample: SampleStrategyPreset) => {
      loadGraphIntoCanvas({
        graph: sample.graph,
        name: sample.name,
        description: sample.description,
        strategyId: null,
        sample: true,
      });
      showToast(t('sampleStrategyLoaded'), 'info');
    },
    [loadGraphIntoCanvas, showToast, t]
  );

  // Count nodes by type
  const nodeCount = nodes.length;
  const conditionCount = nodes.filter(
    (n) => getNodeData(n).node_type === 'condition'
  ).length;

  if (!mounted) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-var(--header-height)-2rem)] lg:h-[calc(100vh-var(--header-height)-3rem)]">
        <Loader2 className="h-8 w-8 animate-spin text-[#1313ec]" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-var(--header-height)-2rem)] lg:h-[calc(100vh-var(--header-height)-3rem)] p-3 gap-3">
      <h1 className="sr-only">{t('title')}</h1>
      {/* Toolbar - Stitch-style */}
      <div className="flex flex-wrap items-center gap-3 px-4 py-2 border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c] rounded-xl">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm">
          <Home className="h-4 w-4 text-[#1313ec]" />
          <span className="font-bold text-gray-900 dark:text-white tracking-tight">
            {t('title')}
          </span>
          <ChevronRight className="h-3.5 w-3.5 text-gray-400 dark:text-gray-500" />
          <span className="text-gray-500 dark:text-gray-400">
            {t('myStrategies')}
          </span>
          <ChevronRight className="h-3.5 w-3.5 text-gray-400 dark:text-gray-500" />
          <span className="font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
            {strategyName || t('untitled')}
            {isSampleStrategy && (
              <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded border border-[#1313ec]/30 text-[#1313ec] bg-[#1313ec]/5">
                {t('builtInSample')}
              </span>
            )}
          </span>
        </div>

        <div className="flex-1" />

        {/* Error/status display */}
        {isRunning && (
          <div className="text-sm text-[#1313ec] font-medium">
            {t('runningStatus')}
          </div>
        )}
        {!isRunning && errors.length > 0 && (
          <div className="text-sm text-red-500">
            {errors[0]}
            {errors.length > 1 && ` (${t('moreErrors', { count: errors.length - 1 })})`}
          </div>
        )}
        {!isRunning && results && (
          <div className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
            {t('stocksMatched', { count: results.length })}
          </div>
        )}

        {/* Primary actions */}
        <button
          type="button"
          onClick={handleClear}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium border border-[#e1e3e5] dark:border-[#2e2e30] rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          {t('reset')}
        </button>
        <button
          type="button"
          onClick={() => handleAutoLayout('horizontal')}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium border border-[#e1e3e5] dark:border-[#2e2e30] rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          title={t('autoLayoutHorizontal')}
        >
          <AlignHorizontalSpaceAround className="h-3.5 w-3.5" />
          {t('autoLayout')}
        </button>
        <button
          type="button"
          onClick={() => handleAutoLayout('vertical')}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium border border-[#e1e3e5] dark:border-[#2e2e30] rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          title={t('autoLayoutVertical')}
        >
          <AlignVerticalSpaceAround className="h-3.5 w-3.5" />
          {t('autoLayoutVertical')}
        </button>
        <button
          type="button"
          onClick={() => setShowLoadDialog(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium border border-[#e1e3e5] dark:border-[#2e2e30] rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          <FolderOpen className="h-3.5 w-3.5" />
          {t('loadStrategy')}
        </button>
        <div className="h-6 w-px bg-[#e1e3e5] dark:bg-[#2e2e30] mx-1" />
        <button
          type="button"
          onClick={handleSave}
          disabled={saveStrategy.isPending || updateStrategy.isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium border border-[#e1e3e5] dark:border-[#2e2e30] rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
        >
          <Save className="h-3.5 w-3.5" />
          {t('saveStrategy')}
        </button>
        <button
          type="button"
          onClick={() => setShowBacktest(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium border border-[#e1e3e5] dark:border-[#2e2e30] rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          <TestTube className="h-3.5 w-3.5" />
          {t('backtest')}
        </button>
        <button
          type="button"
          onClick={handleRun}
          disabled={isRunning}
          className="flex items-center gap-2 px-4 py-1.5 text-sm font-semibold bg-[#1313ec] text-white rounded hover:opacity-90 transition-opacity shadow-sm disabled:opacity-50"
        >
          {isRunning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          {t('executeStrategy')}
        </button>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden rounded-xl border border-[#e1e3e5] dark:border-[#2e2e30]">
        {/* Left palette */}
        {showPalette ? (
          <div className="relative">
            <NodePalette nodeCount={nodeCount} />
            <button
              type="button"
              onClick={() => setShowPalette(false)}
              className="absolute top-2 right-2 z-10 flex items-center justify-center w-6 h-6 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-gray-400 dark:text-gray-500"
              title={t('hidePalette')}
            >
              <PanelLeftClose className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowPalette(true)}
            className="flex items-center justify-center w-8 border-r border-[#e1e3e5] dark:border-[#2e2e30] hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-gray-400 dark:text-gray-500"
            title={t('showPalette')}
          >
            <PanelLeftOpen className="h-4 w-4" />
          </button>
        )}

        {/* Canvas */}
        <div className="relative flex-1" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={onConnect}
            onReconnectStart={onReconnectStart}
            onReconnect={onReconnect}
            onReconnectEnd={onReconnectEnd}
            edgesReconnectable
            onNodeClick={onNodeClick}
            onNodeDoubleClick={onNodeDoubleClick}
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
            {showMiniMap && (
              <MiniMap
                className="!bg-white dark:!bg-[#1e1e1f] !border-[#e1e3e5] dark:!border-[#2e2e30] !rounded-lg !shadow-sm"
                nodeColor={() => '#1313ec'}
                maskColor="rgba(0, 0, 0, 0.08)"
              />
            )}
            <button
              type="button"
              onClick={() => setShowMiniMap((v) => !v)}
              className="absolute bottom-2 right-2 z-10 flex items-center justify-center w-7 h-7 rounded-md bg-white dark:bg-[#1e1e1f] border border-[#e1e3e5] dark:border-[#2e2e30] shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-gray-500 dark:text-gray-400"
              title={showMiniMap ? t('hideMiniMap') : t('showMiniMap')}
            >
              {showMiniMap ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
            </button>
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1}
              color="#d1d5db"
              className="dark:!opacity-20"
            />
          </ReactFlow>
          <ChatPanel
            graph={serializeGraph(nodes as Node<StrategyNodeData>[], edges)}
            onAddNodes={handleAddNodesFromChat}
            existingConditionNodes={existingConditionNodes}
            onUpdateNode={handleUpdateNodeFromChat}
          />
        </div>
      </div>

      {/* Bottom status bar */}
      <div className="flex items-center justify-between px-4 py-1.5 border-t border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c] text-[10px] font-medium text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-4">
          {/* Node limit with progress bar */}
          <div className="flex items-center gap-2">
            <span>{t('nodeLimit', { count: nodeCount, max: 20 })}</span>
            <div className="w-16 h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#1313ec] rounded-full transition-all"
                style={{ width: `${Math.min((nodeCount / 20) * 100, 100)}%` }}
              />
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            <span>{t('kospiData')}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Calendar className="h-3 w-3" />
            <span>
              {lastRunTime
                ? t('lastRunAt', { time: lastRunTime.toLocaleString() })
                : t('lastRunNever')}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={!results || results.length === 0}
            className="text-[10px] font-bold uppercase tracking-wider text-[#1313ec] hover:underline disabled:opacity-40 disabled:cursor-default"
          >
            {t('exportCsv')}
          </button>
          <button
            type="button"
            onClick={handleExportJson}
            disabled={!results || results.length === 0}
            className="text-[10px] font-bold uppercase tracking-wider text-[#1313ec] hover:underline disabled:opacity-40 disabled:cursor-default"
          >
            {t('exportJson')}
          </button>
        </div>
      </div>

      {/* Tabbed results panel */}
      <IntermediateResultsPanel
        nodeResults={nodeResults}
        finalResults={results}
        selectedNodeId={selectedNodeId}
        isPending={isRunning}
        deployProgress={deployProgress}
        conditionCount={conditionCount}
        progressDetail={progressDetail}
        edges={edges}
      />

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
      {showLoadDialog && (() => {
        const searchLower = presetSearch.toLowerCase();
        const filteredPresets = presetSearch
          ? SAMPLE_STRATEGY_PRESETS.filter((s) => {
              const name = tScreening.has(`samplePresetNames.${s.key}`) ? tScreening(`samplePresetNames.${s.key}` as never) : s.name;
              const desc = tScreening.has(`samplePresetDescriptions.${s.key}`) ? tScreening(`samplePresetDescriptions.${s.key}` as never) : s.description;
              return name.toLowerCase().includes(searchLower) || desc.toLowerCase().includes(searchLower);
            })
          : SAMPLE_STRATEGY_PRESETS;
        const grouped = PRESET_CATEGORY_ORDER.reduce<Record<PresetCategory, SampleStrategyPreset[]>>((acc, cat) => {
          const items = filteredPresets.filter((p) => p.category === cat);
          if (items.length > 0) acc[cat] = items;
          return acc;
        }, {} as Record<PresetCategory, SampleStrategyPreset[]>);
        return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-[#1e1e1f] rounded-xl shadow-2xl border border-[#e1e3e5] dark:border-[#2e2e30] w-full max-w-lg mx-4">
            <div className="flex items-center justify-between px-5 py-3 border-b border-[#e1e3e5] dark:border-[#2e2e30]">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {t('loadStrategy')}
              </h3>
              <button type="button" onClick={() => { setShowLoadDialog(false); setPresetSearch(''); }} className="text-gray-400 hover:text-gray-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="px-5 py-3 border-b border-[#e1e3e5] dark:border-[#2e2e30]">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                <input
                  type="text"
                  value={presetSearch}
                  onChange={(e) => setPresetSearch(e.target.value)}
                  placeholder={t('searchPresets')}
                  className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-gray-50 dark:bg-white/5 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-[#1313ec]/40"
                />
              </div>
            </div>
            <div className="px-5 py-4 max-h-[60vh] overflow-y-auto">
              <div className="mb-4">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">
                  {t('sampleStrategies')}
                </h4>
                {(Object.keys(grouped) as PresetCategory[]).map((cat) => {
                  const items = grouped[cat];
                  const isCollapsed = collapsedCategories.has(cat);
                  return (
                    <div key={cat} className="mb-2">
                      <button
                        type="button"
                        onClick={() => setCollapsedCategories((prev) => {
                          const next = new Set(prev);
                          if (next.has(cat)) next.delete(cat); else next.add(cat);
                          return next;
                        })}
                        className="flex items-center gap-1.5 w-full text-left px-2 py-1.5 rounded-md hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                      >
                        {isCollapsed
                          ? <ChevronRight className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                          : <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" />}
                        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                          {t(`presetCategories.${cat}` as never)}
                        </span>
                        <span className="text-[10px] text-gray-400 ml-auto">{items.length}</span>
                      </button>
                      {!isCollapsed && items.map((sample) => (
                        <button
                          key={sample.key}
                          type="button"
                          onClick={() => handleLoadSampleStrategy(sample)}
                          className="w-full text-left pl-7 pr-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5 transition-colors mb-0.5"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {tScreening.has(`samplePresetNames.${sample.key}`) ? tScreening(`samplePresetNames.${sample.key}` as never) : sample.name}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded border border-[#1313ec]/30 text-[#1313ec] bg-[#1313ec]/5 shrink-0">
                              {t('builtInSample')}
                            </span>
                          </div>
                          <p className="text-xs text-gray-400 mt-0.5 truncate">
                            {tScreening.has(`samplePresetDescriptions.${sample.key}`) ? tScreening(`samplePresetDescriptions.${sample.key}` as never) : sample.description}
                          </p>
                        </button>
                      ))}
                    </div>
                  );
                })}
                {Object.keys(grouped).length === 0 && presetSearch && (
                  <p className="text-sm text-gray-400 text-center py-4">{t('noSavedStrategies')}</p>
                )}
              </div>
              <div className="h-px bg-[#e1e3e5] dark:bg-[#2e2e30] mb-3" />
              <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">
                {t('savedStrategies')}
              </h4>
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
        );
      })()}

      {/* Side inspection panel (double-click a node) */}
      <SideInspectionPanel
        nodeResult={
          selectedNodeId && nodeResults
            ? nodeResults[selectedNodeId] ?? null
            : null
        }
        totalStocks={
          nodeResults
            ? Math.max(
                ...Object.values(nodeResults).map((nr) => nr.stock_count),
                0
              )
            : null
        }
        isOpen={showInspection}
        onClose={() => setShowInspection(false)}
      />

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
