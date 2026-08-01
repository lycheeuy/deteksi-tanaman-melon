"use client";

import * as React from "react";

import api from "@/services/api";

interface UseApiGetOptions {
  /** Interval refresh otomatis dalam ms (refresh berjalan senyap,
   *  tanpa mengubah isLoading). */
  refreshMs?: number;
}

interface UseApiGetResult<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  /** Durasi request terakhir dalam milidetik (latency backend). */
  latencyMs: number | null;
  /** Mengulang request (untuk tombol Retry pada error state). */
  retry: () => void;
}

/**
 * Hook GET sederhana dengan tiga state: loading, error, data.
 * Seluruh request melewati Axios instance di services/api.ts,
 * sehingga base URL selalu berasal dari NEXT_PUBLIC_API_URL.
 */
export function useApiGet<T>(
  path: string,
  options?: UseApiGetOptions
): UseApiGetResult<T> {
  const [data, setData] = React.useState<T | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);
  const [latencyMs, setLatencyMs] = React.useState<number | null>(null);
  const refreshMs = options?.refreshMs;

  const fetchData = React.useCallback(
    async (silent: boolean): Promise<void> => {
      if (!silent) setIsLoading(true);
      const started = performance.now();
      try {
        const response = await api.get<T>(path);
        setData(response.data);
        setError(null);
      } catch {
        setData(null);
        setError("Backend tidak dapat dihubungi.");
      } finally {
        setLatencyMs(performance.now() - started);
        if (!silent) setIsLoading(false);
      }
    },
    [path]
  );

  React.useEffect(() => {
    void fetchData(false);
  }, [fetchData]);

  // Polling senyap opsional.
  React.useEffect(() => {
    if (!refreshMs) return;
    const id = setInterval(() => void fetchData(true), refreshMs);
    return () => clearInterval(id);
  }, [fetchData, refreshMs]);

  return {
    data,
    isLoading,
    error,
    latencyMs,
    retry: () => void fetchData(false),
  };
}