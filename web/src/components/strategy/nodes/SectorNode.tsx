'use client';

import { memo, useCallback, useState, useEffect } from 'react';
import { Handle, Position, useNodeId, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Building2, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import { getSectors, type SectorInfo } from '@/lib/api';
import NodeEditPopup, { FieldLabel, SelectInput } from './NodeEditPopup';

function SectorNode({ data, selected }: NodeProps) {
  const t = useTranslations('strategy');
  const nodeData = data as unknown as StrategyNodeData;
  const nodeId = useNodeId()!;
  const { updateNodeData, deleteElements } = useReactFlow();

  const [sectors, setSectors] = useState<SectorInfo[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch sectors for the current market (KOSPI/KOSDAQ)
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getSectors('KOSPI')
      .then((res) => {
        if (!cancelled) setSectors(res.sectors);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

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
            {t('sectorInstruction')}
          </div>
        )}
      </div>

      <Handle
        type="target"
        position={Position.Left}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-left-[7px] hover:!scale-125 !transition-transform"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-right-[7px] hover:!scale-125 !transition-transform"
      />

      {/* Inline edit popup */}
      <NodeEditPopup selected={!!selected} onDelete={handleDelete}>
        <div>
          <FieldLabel>{t('sectorSelection')}</FieldLabel>
          {loading ? (
            <div className="flex items-center gap-2 py-2 text-xs text-gray-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {t('loadingSectors')}
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
