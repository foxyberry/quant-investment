'use client';

import { memo } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type EdgeProps,
} from '@xyflow/react';

function LabeledEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  data,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const label = (data as Record<string, unknown>)?.label as string | undefined;

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        <div
          className="nodrag nopan pointer-events-none absolute"
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
          }}
        >
          <span className="bg-white dark:bg-[#1e1e1f] text-[10px] font-medium text-gray-400 dark:text-gray-500 px-2 py-0.5 rounded-full border border-[#e1e3e5] dark:border-[#2e2e30] shadow-sm">
            {label ?? 'Then'}
          </span>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export default memo(LabeledEdge);
