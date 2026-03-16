'use client';

import { memo, useCallback, useEffect, useMemo, useState } from 'react';
import { Handle, Position, useNodeId, useReactFlow, useStore } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Building2, Eye } from 'lucide-react';
import { useTranslations } from 'next-intl';
import {
  parseUniverseSelection,
  resolveSectorMarket,
  type StrategyNodeData,
} from '@/lib/strategy/graphSerializer';
import { getSectors, type SectorInfo } from '@/lib/api';
import NodeEditPopup, { FieldLabel, SelectInput } from './NodeEditPopup';

function SectorNode({ data, selected }: NodeProps) {
  const t = useTranslations('strategy');
  const nodeData = data as unknown as StrategyNodeData;
  const nodeId = useNodeId()!;
  const { updateNodeData, deleteElements } = useReactFlow();
  const nodes = useStore((state) => state.nodes);

  const [sectors, setSectors] = useState<SectorInfo[]>([]);

  const selectedUniverses = useMemo(() => {
    const universeNode = nodes.find((n) => {
      const d = n.data as unknown as StrategyNodeData;
      return d.node_type === 'universe';
    });
    const universeData = (universeNode?.data as StrategyNodeData | undefined)?.universe;
    return parseUniverseSelection(universeData);
  }, [nodes]);

  const sectorMarket = useMemo(
    () => resolveSectorMarket(selectedUniverses),
    [selectedUniverses]
  );
  const isSectorSupported = sectorMarket !== null;

  // Fetch sectors based on current universe selection.
  useEffect(() => {
    let cancelled = false;
    if (!sectorMarket) return () => { cancelled = true; };
    getSectors(sectorMarket)
      .then((res) => {
        if (!cancelled) setSectors(res.sectors);
      })
      .catch(() => {
        if (!cancelled) setSectors([]);
      });
    return () => { cancelled = true; };
  }, [sectorMarket]);

  useEffect(() => {
    if (!sectorMarket && nodeData.sector) {
      updateNodeData(nodeId, { sector: '' });
    }
  }, [nodeData.sector, nodeId, sectorMarket, updateNodeData]);

  const handleSectorChange = useCallback(
    (value: string) => {
      updateNodeData(nodeId, { sector: value });
    },
    [nodeId, updateNodeData]
  );

  const handleDelete = useCallback(() => {
    deleteElements({ nodes: [{ id: nodeId }] });
  }, [nodeId, deleteElements]);

  const selectedSector = nodeData.sector || '';
  const sectorInfo = sectors.find((s) => s.name === selectedSector);

  return (
    <div
      className={`rounded-lg bg-white dark:bg-[#1e1e1f] border min-w-[200px] transition-shadow ${
        selected
          ? 'border-2 border-[#1313ec] shadow-xl'
          : 'border-[#e1e3e5] dark:border-[#2e2e30] shadow-sm hover:shadow-md'
      }`}
    >
      {/* Header bar */}
      <div className="px-3 py-2 border-b border-[#e1e3e5] dark:border-[#2e2e30] bg-amber-50 dark:bg-amber-900/10 rounded-t-[7px] flex items-center gap-2">
        <Building2 className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
        <span className="text-[11px] font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wider">
          {t('sectorBadge')}
        </span>
      </div>
      {/* Content */}
      <div className="p-3">
        <div className="text-[13px] font-bold text-gray-900 dark:text-gray-100">
          {selectedSector || t('selectSector')}
        </div>
        {sectorInfo && (
          <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {t('sectorStockCount', { count: sectorInfo.stock_count })}
          </div>
        )}
        {!selectedSector && (
          <div className="text-xs text-slate-400 dark:text-slate-500 mt-1">
            {sectorMarket
              ? t('sectorInstruction')
              : t('sectorUnavailableForUniverse', { universe: selectedUniverses.join(' + ') })}
          </div>
        )}
      </div>

      {/* Stock count funnel badge */}
      {nodeData.intermediateResult && nodeData.intermediateResult.stock_count != null && (
        <div className="px-3 pb-2 flex items-center gap-1.5 animate-in fade-in duration-300">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200/60 dark:border-emerald-500/20 text-[10px] font-bold text-emerald-700 dark:text-emerald-400">
            <Eye className="h-3 w-3" />
            {t('stocksRemaining', { count: nodeData.intermediateResult.stock_count.toLocaleString() })}
          </span>
        </div>
      )}

      <Handle
        type="target"
        position={Position.Left}
        className="!w-5 !h-5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-left-[10px] hover:!scale-125 !transition-transform"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-5 !h-5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-right-[10px] hover:!scale-125 !transition-transform"
      />

      {/* Inline edit popup */}
      <NodeEditPopup selected={!!selected} onDelete={handleDelete}>
        <div>
          <FieldLabel>{t('sectorSelection')}</FieldLabel>
          {!isSectorSupported ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/60 dark:bg-amber-900/20 dark:text-amber-200">
              {t('sectorUnavailableForUniverse', { universe: selectedUniverses.join(' + ') })}
            </div>
          ) : (
            <SelectInput
              value={selectedSector}
              onChange={handleSectorChange}
            >
              <option value="">{t('selectSector')}</option>
              {sectors.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name} ({s.stock_count})
                </option>
              ))}
            </SelectInput>
          )}
        </div>
      </NodeEditPopup>
    </div>
  );
}

export default memo(SectorNode);
