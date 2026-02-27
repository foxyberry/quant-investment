'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import {
  getPresets,
  getUniverses,
  runScreening,
} from '@/lib/api';

export function usePresets() {
  return useQuery({
    queryKey: queryKeys.screening.presets(),
    queryFn: getPresets,
    staleTime: 5 * 60 * 1000, // 5 minutes - presets rarely change
  });
}

export function useUniverses() {
  return useQuery({
    queryKey: queryKeys.screening.universes(),
    queryFn: getUniverses,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRunScreening() {
  return useMutation({
    mutationFn: ({
      preset,
      universes,
      referenceDate,
      params,
    }: {
      preset: string;
      universes: string[];
      referenceDate?: string | null;
      params?: Record<string, unknown>;
    }) => runScreening(preset, universes, referenceDate, params),
  });
}
