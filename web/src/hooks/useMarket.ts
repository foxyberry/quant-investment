'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import { searchTickers } from '@/lib/api';

export function useSearchTickers(query: string) {
  return useQuery({
    queryKey: queryKeys.market.search(query),
    queryFn: () => searchTickers(query),
    enabled: query.length >= 1,
    staleTime: 30 * 1000, // 30 seconds
  });
}
