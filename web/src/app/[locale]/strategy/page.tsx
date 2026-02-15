'use client';

import { useState, useCallback, useRef, useMemo } from 'react';
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
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { Loader2, Zap, RotateCcw, Save, TestTube } from 'lucide-react';
import UniverseNode from '@/components/strategy/nodes/UniverseNode';
import ConditionNode from '@/components/strategy/nodes/ConditionNode';
import LogicNode from '@/components/strategy/nodes/LogicNode';
import OutputNode from '@/components/strategy/nodes/OutputNode';
import NodePalette from '@/components/strategy/NodePalette';
import PropertiesPanel from '@/components/strategy/PropertiesPanel';
import BacktestPanel from '@/components/backtest/BacktestPanel';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import { serializeGraph } from '@/lib/strategy/graphSerializer';
import { validateGraph } from '@/lib/strategy/graphValidator';
import { getDefaultParams } from '@/lib/strategy/conditionRegistry';
import { useRunStrategy } from '@/hooks/useStrategy';
import type { StrategyResultItem } from '@/lib/api';

const nodeTypes: NodeTypes = {
  universeNode: UniverseNode,
  conditionNode: ConditionNode,
  logicNode: LogicNode,
  outputNode: OutputNode,
};

let nodeId = 0;
function getNodeId() {
  return `node_${++nodeId}`;
}

const initialNodes: Node[] = [
  {
    id: 'universe_1',
    type: 'universeNode',
    position: { x: 250, y: 50 },
    data: { node_type: 'universe', universe: 'KOSPI' } satisfies StrategyNodeData,
  },
  {
    id: 'output_1',
    type: 'outputNode',
    position: { x: 250, y: 400 },
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

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow-type');
      const conditionKey = event.dataTransfer.getData('application/reactflow-condition');

      if (!type || !reactFlowInstance || !reactFlowWrapper.current) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
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
        nodeType = 'logicNode';
        const operator = type.replace('logic_', '');
        data = { node_type: 'logic', logic_operator: operator };
      } else if (type === 'output') {
        nodeType = 'outputNode';
        data = { node_type: 'output' };
      } else {
        return;
      }

      const newNode: Node = {
        id: getNodeId(),
        type: nodeType,
        position,
        data: data as unknown as Record<string, unknown>,
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [reactFlowInstance, setNodes]
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
    nodeId = 0;
  }, [setNodes, setEdges]);

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
        <NodePalette />

        {/* Canvas */}
        <div className="flex-1" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onInit={setReactFlowInstance}
            onDragOver={onDragOver}
            onDrop={onDrop}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ maxZoom: 0.75, padding: 0.3 }}
            connectionMode={ConnectionMode.Loose}
            className="!bg-[#f6f6f7] dark:!bg-[#141414]"
            defaultEdgeOptions={{
              type: 'smoothstep',
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
    </div>
  );
}
