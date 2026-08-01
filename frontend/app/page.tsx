"use client";

import * as React from "react";
import {
  BrainCircuit,
  CalendarClock,
  Database,
  Gauge,
  RefreshCw,
  ScanSearch,
  Server,
} from "lucide-react";

import { ErrorState, LoadingCards } from "@/components/api-states";
import { LabelStats } from "@/components/dashboard/label-stats";
import { LastDetection } from "@/components/dashboard/last-detection";
import { RecentHistory } from "@/components/dashboard/recent-history";
import { StatCard } from "@/components/dashboard/stat-card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { API_BASE_URL } from "@/services/api";
import { useApiGet } from "@/lib/use-api-get";
import { cn } from "@/lib/utils";
import type { DashboardSummaryResponse } from "@/types";

const API_HOST = API_BASE_URL.replace(/^https?:\/\//, "");

export default function DashboardPage(): React.ReactElement {
  // Statistik + status di-refresh otomatis setiap 30 detik.
  const { data, isLoading, error, latencyMs, retry } =
    useApiGet<DashboardSummaryResponse>("/dashboard/summary", {
      refreshMs: 30_000,
    });

  return (
    <section className="mx-auto w-full max-w-6xl space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-semibold tracking-tight">
            Overview
          </h2>
          <p className="text-sm text-muted-foreground">
            Ringkasan aktivitas deteksi tanaman melon dari perangkat
            ESP32-CAM.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={retry}
          disabled={isLoading}
          aria-label="Refresh statistik"
        >
          <RefreshCw className={cn(isLoading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      <Separator />

      {isLoading ? (
        <LoadingCards count={6} />
      ) : error || !data ? (
        <ErrorState onRetry={retry} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            title="Total Detection"
            value={data.total_detection}
            hint="Seluruh riwayat deteksi"
            icon={ScanSearch}
          />
          <StatCard
            title="Today's Detection"
            value={data.today_detection}
            hint="Berdasarkan tanggal server"
            icon={CalendarClock}
            tone="melon"
          />
          <StatCard
            title="Backend Latency"
            value={latencyMs !== null ? `${Math.round(latencyMs)} ms` : "-"}
            hint="Durasi request terakhir"
            icon={Gauge}
            tone="melon"
          />
          <StatCard
            title="Backend Status"
            value={data.backend === "online" ? "Online" : "Offline"}
            hint={`FastAPI · ${API_HOST}`}
            icon={Server}
          />
          <StatCard
            title="Database Status"
            value={data.database === "connected" ? "Connected" : "Down"}
            hint="PostgreSQL 17"
            icon={Database}
          />
          <StatCard
            title="Model Status"
            value={data.model === "loaded" ? "Loaded" : "Not loaded"}
            hint="MobileNetV2 FOMO · int8"
            icon={BrainCircuit}
          />
        </div>
      )}

      {/* Panel Last Detection + statistik label + riwayat terbaru.
          Semua panel polling mandiri (arsitektur push: deteksi datang
          dari perangkat, bukan dari aksi di halaman ini). */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <LastDetection backendOnline={!error && data?.backend === "online"} />
        </div>
        <div className="space-y-4">
          {data ? (
            <LabelStats labels={data.labels} noDetection={data.no_detection} />
          ) : null}
          <RecentHistory />
        </div>
      </div>
    </section>
  );
}