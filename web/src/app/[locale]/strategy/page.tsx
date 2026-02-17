'use client';

import { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import {
  ReactFlow,
  addEdge,
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

import { Loader2, Zap, RotateCcw, Save, TestTube, Download } from 'lucide-react';
import UniverseNode from '@/components/strategy/nodes/UniverseNode';
import ConditionNode from '@/components/strategy/nodes/ConditionNode';
import GroupNode from '@/components/strategy/nodes/GroupNode';
import OutputNode from '@/components/strategy/nodes/OutputNode';
import LabeledEdge from '@/components/strategy/edges/LabeledEdge';
import NodePalette from '@/components/strategy/NodePalette';
import PropertiesPanel from '@/components/strategy/PropertiesPanel';
import BacktestPanel from '@/components/backtest/BacktestPanel';
import { Toast, useToast } from '@/components/ui/Toast';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import { serializeGraph } from '@/lib/strategy/graphSerializer';
import { validateGraph } from '@/lib/strategy/graphValidator';
import { getDefaultParams } from '@/lib/strategy/conditionRegistry';
import { useRunStrategy } from '@/hooks/useStrategy';
import type { StrategyResultItem } from '@/lib/api';

const nodeTypes: NodeTypes = {
  universeNode: UniverseNode,
  conditionNode: ConditionNode,
  groupNode: GroupNode,
  outputNode: OutputNode,
};

const edgeTypes = {
  labeled: LabeledEdge,
};

const GROUP_PADDING_TOP = 56;
const GROUP_PADDING_BOTTOM = 20;
const GROUP_PADDING_X = 16;
const CHILD_SPACING = 8;
const CHILD_HEIGHT = 80;
const GROUP_MIN_WIDTH = 280;
const GROUP_MIN_HEIGHT = 200;

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

export default function StrategyPage() {
  const t = useTranslations('strategy');
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [results, setResults] = useState<StrategyResultItem[] | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [showBacktest, setShowBacktest] = useState(false);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  const runStrategy = useRunStrategy();
  const { toast, showToast, hideToast } = useToast();

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge(connection, eds));
    },
    [setEdges]
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

  // Auto-resize group nodes when children change (supports nested groups)
  useEffect(() => {
    setNodes((nds) => {
      let changed = false;
      const updatedNodes = nds.map((n) => {
        if (n.type !== 'groupNode') return n;
        const children = nds.filter((c) => c.parentId === n.id);
        // Calculate total height based on actual child sizes
        const totalChildrenHeight = children.reduce((acc, child) => {
          const h = child.type === 'groupNode'
            ? ((child.style?.height as number) || GROUP_MIN_HEIGHT)
            : CHILD_HEIGHT;
          return acc + h + CHILD_SPACING;
        }, 0);
        const neededHeight = Math.max(
          GROUP_MIN_HEIGHT,
          GROUP_PADDING_TOP + totalChildrenHeight + GROUP_PADDING_BOTTOM
        );
        // Nested groups are narrower; top-level groups use full width
        const isNested = !!n.parentId;
        const neededWidth = isNested
          ? GROUP_MIN_WIDTH - GROUP_PADDING_X * 2
          : GROUP_MIN_WIDTH;
        const currentWidth = (n.style?.width as number) || GROUP_MIN_WIDTH;
        const currentHeight = (n.style?.height as number) || GROUP_MIN_HEIGHT;
        if (
          Math.abs(currentHeight - neededHeight) > 1 ||
          Math.abs(currentWidth - neededWidth) > 1
        ) {
          changed = true;
          return {
            ...n,
            style: { ...n.style, width: neededWidth, height: neededHeight },
          };
        }
        return n;
      });
      return changed ? updatedNodes : nds;
    });
  }, [nodes, setNodes]);

  // Handle removing condition from group when dragged outside
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);

      // Check position changes to detect drag-out from group
      for (const change of changes) {
        if (change.type === 'position' && change.dragging === false && change.id) {
          setNodes((nds) => {
            const node = nds.find((n) => n.id === change.id);
            if (!node || !node.parentId) return nds;

            const parent = nds.find((n) => n.id === node.parentId);
            if (!parent) return nds;

            // Check if node was dragged outside parent bounds
            const pw = (parent.style?.width as number) || GROUP_MIN_WIDTH;
            const ph = (parent.style?.height as number) || GROUP_MIN_HEIGHT;
            const nx = node.position.x;
            const ny = node.position.y;

            if (nx < -50 || ny < -50 || nx > pw + 50 || ny > ph + 50) {
              // Remove from group - convert to absolute position
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
        },
        onError: (error) => {
          setErrors([error instanceof Error ? error.message : t('executionFailed')]);
        },
      }
    );
  }, [nodes, edges, runStrategy, setNodes, t]);

  const handleClear = useCallback(() => {
    setNodes(initialNodes);
    setEdges([]);
    setSelectedNodeId(null);
    setResults(null);
    setErrors([]);
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
          {t('untitled')}
        </span>

        <div className="flex-1" />

        {/* Error/status display */}
        {errors.length > 0 && (
          <div className="text-sm text-red-500">
            {errors[0]}
            {errors.length > 1 && ` (${t('moreErrors', { count: errors.length - 1 })})`}
          </div>
        )}
        {results && (
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
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
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
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onInit={setReactFlowInstance}
            onDragOver={onDragOver}
            onDrop={onDrop}
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
      {results && results.length > 0 && (
        <div className="border-t border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c] max-h-64 overflow-y-auto">
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
                  className="border-b border-[#e1e3e5] dark:border-[#2e2e30] hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                >
                  <td className="px-4 py-1.5 font-mono text-[#1313ec] font-medium">
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
          type={toast.type as 'error' | 'warning' | 'info'}
          onClose={hideToast}
        />
      )}
    </div>
  );
}
