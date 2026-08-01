"use client";

import * as React from "react";
import { isAxiosError } from "axios";
import {
  Download,
  ImageOff,
  Loader2,
  RotateCcw,
  ScanSearch,
  Upload,
  UploadCloud,
} from "lucide-react";

import { EmptyState, ErrorState } from "@/components/api-states";
import { ProgressBar } from "@/components/progress-bar";
import { useToast } from "@/components/toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import api, { API_BASE_URL } from "@/services/api";
import { cn } from "@/lib/utils";
import type { DetectResponse } from "@/types";

/* ============================================================
   Aturan validasi file (client-side, sebelum request dikirim)
   ============================================================ */
const ALLOWED_MIME_TYPES: readonly string[] = ["image/jpeg", "image/png"];
const MAX_FILE_SIZE_BYTES: number = 10 * 1024 * 1024;

function validateFile(file: File): string | null {
  if (!ALLOWED_MIME_TYPES.includes(file.type)) {
    return "Format gambar tidak valid. Gunakan JPG atau PNG.";
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
    return `Ukuran gambar terlalu besar (${sizeMb} MB). Maksimal 10 MB.`;
  }
  return null;
}

function mapRequestError(err: unknown): string {
  if (isAxiosError(err) && err.response) {
    switch (err.response.status) {
      case 400:
        return "Format gambar tidak valid.";
      case 413:
        return "Ukuran gambar terlalu besar.";
      default:
        return "Terjadi kesalahan pada server.";
    }
  }
  return "Backend tidak dapat dihubungi.";
}

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

export default function DetectPage(): React.ReactElement {
  const { toast } = useToast();
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [file, setFile] = React.useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<DetectResponse | null>(null);
  const [elapsed, setElapsed] = React.useState<number | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = React.useState<number | null>(
    null
  );
  const [isDragActive, setIsDragActive] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);
  const [validationError, setValidationError] = React.useState<string | null>(
    null
  );

  React.useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  /** Jalur tunggal penerimaan file — dipakai input maupun drag & drop. */
  const acceptFile = (selected: File): void => {
    const message = validateFile(selected);
    if (message) {
      setValidationError(message);
      toast({ title: message, variant: "error" });
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
    setResult(null);
    setElapsed(null);
    setError(null);
    setValidationError(null);
  };

  const handleFileChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ): void => {
    const selected = event.target.files?.[0] ?? null;
    if (selected) acceptFile(selected);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>): void => {
    event.preventDefault();
    setIsDragActive(false);
    if (isLoading) return;
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) acceptFile(dropped);
  };

  const handleDetect = async (): Promise<void> => {
    if (!file || isLoading) return;
    const message = validateFile(file);
    if (message) {
      setValidationError(message);
      return;
    }

    setIsLoading(true);
    setError(null);
    setUploadProgress(0);
    const started = performance.now();
    try {
      const formData = new FormData();
      formData.append("image", file);
      const response = await api.post<DetectResponse>("/detect", formData, {
        onUploadProgress: (event) => {
          if (event.total) {
            setUploadProgress(Math.round((event.loaded / event.total) * 100));
          }
        },
      });
      setResult(response.data);
      setElapsed((performance.now() - started) / 1000);
      toast({
        title: "Deteksi selesai",
        description: `${response.data.total_detection} objek terdeteksi.`,
        variant: "success",
      });
    } catch (err: unknown) {
      const mapped = mapRequestError(err);
      setResult(null);
      setError(mapped);
      toast({ title: "Deteksi gagal", description: mapped, variant: "error" });
    } finally {
      setIsLoading(false);
      setUploadProgress(null);
    }
  };

  const handleReset = (): void => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setResult(null);
    setElapsed(null);
    setError(null);
    setValidationError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  /** Mengunduh gambar anotasi sebagai file. */
  const handleDownload = async (): Promise<void> => {
    if (!result) return;
    try {
      const response = await fetch(
        `${API_BASE_URL}/${result.annotated_image_path}`
      );
      if (!response.ok) throw new Error(String(response.status));
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download =
        result.annotated_image_path.split("/").pop() ?? "annotated.jpg";
      anchor.click();
      URL.revokeObjectURL(url);
      toast({ title: "Gambar anotasi diunduh.", variant: "success" });
    } catch {
      toast({
        title: "Gagal mengunduh gambar anotasi.",
        variant: "error",
      });
    }
  };

  return (
    <section className="mx-auto w-full max-w-6xl space-y-6">
      <div>
        <h2 className="font-display text-2xl font-semibold tracking-tight">
          Detect Image
        </h2>
        <p className="text-sm text-muted-foreground">
          Unggah foto tanaman melon untuk dianalisis oleh model AI.
        </p>
      </div>

      {/* Panel pemilihan gambar */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pilih Gambar</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png"
            className="hidden"
            onChange={handleFileChange}
          />

          {/* Zona drag & drop — juga bisa diklik untuk memilih file. */}
          <div
            role="button"
            tabIndex={0}
            aria-label="Pilih atau letakkan gambar"
            onClick={() => !isLoading && inputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !isLoading) {
                inputRef.current?.click();
              }
            }}
            onDragOver={(event) => {
              event.preventDefault();
              if (!isLoading) setIsDragActive(true);
            }}
            onDragLeave={() => setIsDragActive(false)}
            onDrop={handleDrop}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
              isDragActive
                ? "border-primary bg-primary/5"
                : "border-input hover:border-primary/50",
              isLoading && "pointer-events-none opacity-60"
            )}
          >
            <UploadCloud className="size-8 text-muted-foreground" />
            <p className="text-sm font-medium">
              Tarik &amp; letakkan gambar di sini
            </p>
            <p className="text-xs text-muted-foreground">
              atau klik untuk memilih file (.jpg / .png, maks. 10 MB)
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              onClick={() => void handleDetect()}
              disabled={!file || isLoading}
            >
              {isLoading ? <Loader2 className="animate-spin" /> : <Upload />}
              {isLoading ? "Mendeteksi…" : "Upload & Detect"}
            </Button>
            <Button variant="ghost" onClick={handleReset} disabled={isLoading}>
              <RotateCcw />
              Reset
            </Button>
            {file ? (
              <span className="text-sm text-muted-foreground">
                {file.name}
              </span>
            ) : null}
          </div>

          {isLoading && uploadProgress !== null ? (
            <div className="space-y-1">
              <ProgressBar value={uploadProgress} />
              <p className="text-xs text-muted-foreground">
                {uploadProgress < 100
                  ? `Mengunggah… ${uploadProgress}%`
                  : "Memproses inferensi…"}
              </p>
            </div>
          ) : null}

          {validationError ? (
            <p className="text-sm font-medium text-destructive">
              {validationError}
            </p>
          ) : null}

          {previewUrl && !result ? (
            <div className="max-w-sm overflow-hidden rounded-lg border">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewUrl}
                alt="Preview gambar terpilih"
                className="w-full object-contain"
              />
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Area hasil */}
      {!file && !result ? (
        <EmptyState
          icon={ImageOff}
          title="Belum ada gambar dipilih."
          description="Tarik & letakkan atau pilih file .jpg / .png (maks. 10 MB)."
        />
      ) : isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-32 rounded-xl" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={() => void handleDetect()} />
      ) : result ? (
        <div className="space-y-4">
          <Separator />

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Original Image</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-hidden rounded-lg border">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={previewUrl ?? `${API_BASE_URL}/${result.image_path}`}
                    alt="Gambar asli"
                    className="w-full object-contain"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Annotated Image</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-hidden rounded-lg border">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`${API_BASE_URL}/${result.annotated_image_path}`}
                    alt="Gambar hasil anotasi"
                    className="w-full object-contain"
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Ringkasan</CardTitle>
              </CardHeader>
              <CardContent>
                <InfoRow label="Status">
                  <Badge variant="secondary">{result.message}</Badge>
                </InfoRow>
                <InfoRow label="Total Detection">
                  {result.total_detection}
                </InfoRow>
                <InfoRow label="Processing Time">
                  {elapsed !== null ? `${elapsed.toFixed(2)} s` : "-"}
                </InfoRow>
                <InfoRow label="Record ID">
                  <span className="font-mono text-xs">
                    {result.record_id}
                  </span>
                </InfoRow>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Detections</CardTitle>
              </CardHeader>
              <CardContent>
                {result.total_detection === 0 ? (
                  <p className="py-6 text-center text-sm text-muted-foreground">
                    Tidak ada hasil deteksi.
                  </p>
                ) : (
                  <div className="space-y-1">
                    {result.detections.map((detection, index) => (
                      <InfoRow
                        key={`${detection.grid_x}-${detection.grid_y}-${index}`}
                        label={detection.label}
                      >
                        {(detection.confidence * 100).toFixed(2)}% · grid (
                        {detection.grid_x}, {detection.grid_y})
                      </InfoRow>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void handleDetect()} disabled={isLoading}>
              <ScanSearch />
              Detect Again
            </Button>
            <Button variant="outline" onClick={() => void handleDownload()}>
              <Download />
              Download Annotated
            </Button>
            <Button variant="ghost" onClick={handleReset} disabled={isLoading}>
              <RotateCcw />
              Reset
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}