"use client";

import * as React from "react";
import { Cpu, HardDrive, MemoryStick } from "lucide-react";

import { ErrorState, LoadingBlock } from "@/components/api-states";
import { ProgressBar } from "@/components/progress-bar";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useApiGet } from "@/lib/use-api-get";
import type { MonitorResponse, SystemInfoResponse } from "@/types";

/** Ambang peringatan pemakaian resource (bar berubah merah). */
const WARN_AT = 80;

/** Satu baris label-nilai. */
function InfoRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <div className="flex items-center justify-between gap-4 py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{children}</span>
    </div>
  );
}

/** Baris resource: ikon, label, bar, dan angka pemakaian. */
function ResourceRow({
  icon: Icon,
  label,
  percent,
  detail,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  percent: number;
  detail: string;
}): React.ReactElement {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-2">
          <Icon className="size-4 text-muted-foreground" />
          {label}
        </span>
        <span className="font-medium tabular-nums">{percent}%</span>
      </div>
      <ProgressBar value={percent} warnAt={WARN_AT} />
      <p className="text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

/** Badge status layanan (online/connected/loaded = hijau). */
function StatusBadge({
  ok,
  okLabel,
  failLabel,
}: {
  ok: boolean;
  okLabel: string;
  failLabel: string;
}): React.ReactElement {
  return (
    <Badge variant={ok ? "secondary" : "destructive"}>
      {ok ? okLabel : failLabel}
    </Badge>
  );
}

/** Format uptime detik -> "Xh Ym Zs". */
function formatUptime(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}j ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}d`;
  return `${seconds}d`;
}

export default function SystemPage(): React.ReactElement {
  // Monitor di-refresh otomatis tiap 30 detik (senyap).
  const monitor = useApiGet<MonitorResponse>("/monitor", {
    refreshMs: 30_000,
  });
  const info = useApiGet<SystemInfoResponse>("/system/info");

  const isLoading = monitor.isLoading || info.isLoading;
  const hasError =
    Boolean(monitor.error) || Boolean(info.error) || !monitor.data || !info.data;

  const retryAll = (): void => {
    monitor.retry();
    info.retry();
  };

  return (
    <section className="mx-auto w-full max-w-6xl space-y-6">
      <div>
        <h2 className="font-display text-2xl font-semibold tracking-tight">
          System Status
        </h2>
        <p className="text-sm text-muted-foreground">
          Kondisi server, resource, dan model AI — diperbarui otomatis
          setiap 30 detik.
        </p>
      </div>

      {isLoading ? (
        <LoadingBlock />
      ) : hasError || !monitor.data || !info.data ? (
        <ErrorState onRetry={retryAll} />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {/* Resource server */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Server Resources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <ResourceRow
                icon={Cpu}
                label="CPU"
                percent={monitor.data.cpu.percent}
                detail="Pemakaian prosesor saat ini"
              />
              <ResourceRow
                icon={MemoryStick}
                label="RAM"
                percent={monitor.data.memory.percent}
                detail={`${monitor.data.memory.used_mb.toLocaleString(
                  "id-ID"
                )} MB dari ${monitor.data.memory.total_mb.toLocaleString(
                  "id-ID"
                )} MB`}
              />
              <ResourceRow
                icon={HardDrive}
                label="Disk"
                percent={monitor.data.disk.percent}
                detail={`${monitor.data.disk.used_gb} GB dari ${monitor.data.disk.total_gb} GB`}
              />
            </CardContent>
          </Card>

          {/* Status layanan */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Service Status</CardTitle>
            </CardHeader>
            <CardContent>
              <InfoRow label="Backend">
                <StatusBadge
                  ok={monitor.data.backend === "online"}
                  okLabel="Online"
                  failLabel="Offline"
                />
              </InfoRow>
              <InfoRow label="Database">
                <StatusBadge
                  ok={monitor.data.database === "connected"}
                  okLabel="Connected"
                  failLabel="Disconnected"
                />
              </InfoRow>
              <InfoRow label="AI Model">
                <StatusBadge
                  ok={monitor.data.model === "loaded"}
                  okLabel="Loaded"
                  failLabel="Not loaded"
                />
              </InfoRow>
              <InfoRow label="API Latency">
                {monitor.data.latency_ms} ms
              </InfoRow>
              <InfoRow label="Uptime">
                {formatUptime(monitor.data.uptime_seconds)}
              </InfoRow>
              <InfoRow label="Last Update">
                {new Date(monitor.data.last_update).toLocaleString("id-ID", {
                  dateStyle: "medium",
                  timeStyle: "medium",
                })}
              </InfoRow>
            </CardContent>
          </Card>

          {/* Info model & runtime (endpoint lama, tetap dipakai) */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Model & Runtime</CardTitle>
            </CardHeader>
            <CardContent>
              <InfoRow label="App Version">{info.data.app_version}</InfoRow>
              <InfoRow label="TensorFlow">
                {info.data.tensorflow_version}
              </InfoRow>
              <InfoRow label="Input Size">
                {Array.isArray(info.data.model_input_size)
                  ? info.data.model_input_size.join(" × ")
                  : info.data.model_input_size}
              </InfoRow>
              <InfoRow label="Total Labels">{info.data.total_labels}</InfoRow>
            </CardContent>
          </Card>
        </div>
      )}
    </section>
  );
}