"use client";

import * as React from "react";
import { isAxiosError } from "axios";
import { ImageOff, Loader2, ScanSearch } from "lucide-react";

import { useToast } from "@/components/toast";
import { Button } from "@/components/ui/button";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import api, { API_BASE_URL } from "@/services/api";
import { useApiGet } from "@/lib/use-api-get";
import { cn } from "@/lib/utils";
import type { RecentHistoryResponse } from "@/types";

/** Format selisih waktu menjadi "x detik/menit/jam lalu". */
function relativeTime(fromIso: string, nowMs: number): string {
  const seconds = Math.max(
    0,
    Math.floor((nowMs - new Date(fromIso).getTime()) / 1000)
  );
  if (seconds < 60) return `${seconds} detik lalu`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} menit lalu`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} jam lalu`;
  return `${Math.floor(hours / 24)} hari lalu`;
}

/** Memetakan error Axios menjadi pesan pengguna. */
function mapCommandError(err: unknown): string {
  if (isAxiosError(err) && err.response) {
    return "Terjadi kesalahan pada server.";
  }
  return "Backend tidak dapat dihubungi.";
}

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

interface LastDetectionProps {
  /** Status backend dari /dashboard/summary halaman induk. */
  backendOnline: boolean;
}

/**
 * Panel Last Detection: deteksi terbaru dari database — sumber apa pun
 * (ESP32 push, halaman Detect, simulator). Menggantikan panel Live
 * Camera pada arsitektur push (tanpa CameraWebServer/stream MJPEG).
 */
export function LastDetection({
  backendOnline,
}: LastDetectionProps): React.ReactElement {
  // Deteksi terbaru: cukup satu record, di-refresh senyap tiap 15 dtk.
  const { data, isLoading, error, retry } =
    useApiGet<RecentHistoryResponse>("/dashboard/recent?limit=1", {
      refreshMs: 15_000,
    });

  // Jam berjalan agar "x detik lalu" hidup tanpa menunggu polling.
  const [nowMs, setNowMs] = React.useState<number>(() => Date.now());
  React.useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), 1_000);
    return () => clearInterval(id);
  }, []);

  const { toast } = useToast();
  const [isWaiting, setIsWaiting] = React.useState<boolean>(false);

  const latest = data?.items[0] ?? null;
  const latestId: string | null = latest?.id ?? null;

  // Menunggu record baru muncul: begitu id teratas berubah, deteksi
  // hasil perintah sudah masuk.
  const waitingRef = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (isWaiting && latestId !== null && latestId !== waitingRef.current) {
      setIsWaiting(false);
      toast({ title: "Deteksi selesai", variant: "success" });
    }
  }, [isWaiting, latestId, toast]);

  /** Menitipkan perintah detect; ESP32 menjemputnya (polling 3 dtk). */
  const handleDetect = async (): Promise<void> => {
    if (isWaiting) return;
    waitingRef.current = latestId;
    setIsWaiting(true);
    try {
      await api.post("/api/esp32/command/detect");
      toast({
        title: "Perintah dikirim",
        description: "Menunggu ESP32 menjemput perintah…",
        variant: "success",
      });
      // Percepat deteksi perubahan: refresh beberapa kali.
      const timers = [3000, 6000, 10000, 15000].map((delay) =>
        setTimeout(retry, delay)
      );
      setTimeout(() => {
        timers.forEach(clearTimeout);
        setIsWaiting(false);
      }, 20000);
    } catch (err: unknown) {
      setIsWaiting(false);
      toast({
        title: "Gagal mengirim perintah",
        description: mapCommandError(err),
        variant: "error",
      });
    }
  };

  // total_detection & device tidak dipersist di tabel riwayat
  // (kontrak backend tidak boleh diubah) — tampilkan apa adanya:
  // "No Detection" pasti 0, selain itu tidak diketahui dari DB.
  const totalDetectionText: string =
    latest === null ? "-" : latest.label === "No Detection" ? "0" : "—";
  const deviceText = "—";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">Last Detection</CardTitle>
        <Badge
          variant={backendOnline ? "secondary" : "destructive"}
          className="px-3 py-1"
        >
          <span
            aria-hidden
            className={cn(
              "size-2 rounded-full",
              backendOnline ? "status-dot-online bg-primary" : "bg-white/80"
            )}
          />
          {backendOnline ? "Backend Online" : "Backend Offline"}
        </Badge>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <Button
            onClick={() => void handleDetect()}
            disabled={isWaiting || !backendOnline}
          >
            {isWaiting ? (
              <Loader2 className="animate-spin" />
            ) : (
              <ScanSearch />
            )}
            {isWaiting ? "Menunggu ESP32…" : "Detect"}
          </Button>
          {isWaiting ? (
            <span className="text-sm text-muted-foreground">
              Perintah dijemput perangkat dalam beberapa detik.
            </span>
          ) : null}
        </div>

        {isLoading ? (
          <>
            <Skeleton className="aspect-video w-full rounded-lg" />
            <Skeleton className="h-24 rounded-lg" />
          </>
        ) : error ? (
          <div className="py-8 text-center">
            <p className="mb-3 text-sm text-muted-foreground">
              Backend tidak dapat dihubungi.
            </p>
            <button
              className="text-sm font-medium text-primary underline-offset-4 hover:underline"
              onClick={retry}
            >
              Retry
            </button>
          </div>
        ) : latest === null ? (
          <div className="flex aspect-video w-full flex-col items-center justify-center rounded-lg border bg-muted text-center">
            <ImageOff className="mb-2 size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Belum ada riwayat deteksi.
            </p>
          </div>
        ) : (
          <>
            {/* Gambar anotasi deteksi terbaru */}
            <div className="flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg border bg-muted">
              {latest.annotated_image_path ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={`${API_BASE_URL}/${latest.annotated_image_path}`}
                  alt="Gambar anotasi deteksi terbaru"
                  className="h-full w-full object-contain"
                />
              ) : (
                <div className="text-center text-sm text-muted-foreground">
                  <ImageOff className="mx-auto mb-2 size-8" />
                  Gambar anotasi tidak tersedia.
                </div>
              )}
            </div>

            {/* Detail deteksi terbaru */}
            <div>
              <InfoRow label="Label">
                <Badge
                  variant={
                    latest.label === "No Detection" ? "outline" : "secondary"
                  }
                >
                  {latest.label}
                </Badge>
              </InfoRow>
              <InfoRow label="Total Detection">{totalDetectionText}</InfoRow>
              <InfoRow label="Created At">
                {new Date(latest.created_at).toLocaleString("id-ID", {
                  dateStyle: "medium",
                  timeStyle: "medium",
                })}
              </InfoRow>
              <InfoRow label="Device">{deviceText}</InfoRow>
              <InfoRow label="Last Detection">
                {relativeTime(latest.detected_at, nowMs)}
              </InfoRow>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}