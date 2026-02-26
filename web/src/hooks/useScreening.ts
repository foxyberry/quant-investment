'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import {
  getPresets,
  getUniverses,
  runScreening,
  listSavedScreeningResults,
  saveScreeningResult,
  deleteSavedScreeningResult,
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

export function useSavedScreeningResults() {
  return useQuery({
    queryKey: queryKeys.screening.saved(),
    queryFn: listSavedScreeningResults,
  });
}

export function useSaveScreeningResult() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: saveScreeningResult,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.screening.saved() });
    },
  });
}

export function useDeleteScreeningResult() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteSavedScreeningResult,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.screening.saved() });
    },
  });
}
