"use client";

import * as React from "react";
import { History, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { API_BASE_URL } from "@/services/api";
import { useApiGet } from "@/lib/use-api-get";
import type { RecentHistoryResponse } from "@/types";

interface RecentHistoryProps {
  /** Naikkan nilai ini agar daftar di-refresh (mis. setelah deteksi
   *  sukses dari panel Live Camera). */
  refreshToken?: number;
}

/** Panel daftar deteksi terbaru pada dashboard. */
export function RecentHistory({
  refreshToken = 0,
}: RecentHistoryProps): React.ReactElement {
  // Polling mandiri: deteksi kini datang dari perangkat (push), bukan
  // aksi di halaman ini.
  const { data, isLoading, error, retry } = useApiGet<RecentHistoryResponse>(
    "/dashboard/recent",
    { refreshMs: 30_000 }
  );

  // Refresh saat token berubah (deteksi baru terjadi).
  const previousToken = React.useRef<number>(refreshToken);
  React.useEffect(() => {
    if (refreshToken !== previousToken.current) {
      previousToken.current = refreshToken;
      retry();
    }
  }, [refreshToken, retry]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recent History</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-12 rounded-lg" />
            ))}
          </div>
        ) : error || !data ? (
          <div className="py-4 text-center">
            <p className="mb-2 text-sm text-muted-foreground">
              Backend tidak dapat dihubungi.
            </p>
            <Button variant="outline" size="sm" onClick={retry}>
              <RefreshCw />
              Retry
            </Button>
          </div>
        ) : data.items.length === 0 ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            <History className="mx-auto mb-2 size-6" />
            Belum ada riwayat deteksi.
          </div>
        ) : (
          <ul className="space-y-3">
            {data.items.map((item) => (
              <li key={item.id} className="flex items-center gap-3">
                <div className="size-12 shrink-0 overflow-hidden rounded-md border bg-muted">
                  {item.annotated_image_path ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={`${API_BASE_URL}/${item.annotated_image_path}`}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : null}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{item.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(item.detected_at).toLocaleString("id-ID", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}