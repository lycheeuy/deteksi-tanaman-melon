"use client";

import * as React from "react";
import { isAxiosError } from "axios";
import { FileDown, FileSpreadsheet, Loader2 } from "lucide-react";

import { useToast } from "@/components/toast";
import { Button } from "@/components/ui/button";
import api from "@/services/api";

type ExportFormat = "csv" | "excel";

interface ExportButtonsProps {
  /** Filter aktif yang ikut dikirim ke endpoint export. */
  label?: string;
  dateFrom?: string;
  dateTo?: string;
}

/** Mengambil nama file dari header Content-Disposition. */
function filenameFromDisposition(
  disposition: string | undefined,
  fallback: string
): string {
  if (!disposition) return fallback;
  const match = /filename="?([^";]+)"?/.exec(disposition);
  return match ? match[1] : fallback;
}

function mapExportError(err: unknown): string {
  if (isAxiosError(err) && err.response) {
    if (err.response.status === 401) {
      return "Sesi berakhir — silakan login ulang.";
    }
    return "Terjadi kesalahan pada server.";
  }
  return "Backend tidak dapat dihubungi.";
}

/**
 * Tombol Export CSV & Export Excel (reusable).
 * Mengunduh laporan sesuai filter aktif via endpoint terproteksi;
 * file tersimpan otomatis dengan nama dari server.
 */
export function ExportButtons({
  label,
  dateFrom,
  dateTo,
}: ExportButtonsProps): React.ReactElement {
  const { toast } = useToast();
  const [exporting, setExporting] = React.useState<ExportFormat | null>(null);

  const handleExport = async (format: ExportFormat): Promise<void> => {
    if (exporting) return;
    setExporting(format);
    try {
      const params = new URLSearchParams();
      if (label) params.set("label", label);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      const query = params.toString();

      const response = await api.get<Blob>(
        `/report/export/${format}${query ? `?${query}` : ""}`,
        { responseType: "blob" }
      );

      const extension = format === "csv" ? "csv" : "xlsx";
      const filename = filenameFromDisposition(
        response.headers["content-disposition"] as string | undefined,
        `laporan_deteksi_melon.${extension}`
      );

      // Unduh otomatis via object URL sementara.
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);

      toast({
        title: `Export ${format === "csv" ? "CSV" : "Excel"} berhasil`,
        description: filename,
        variant: "success",
      });
    } catch (err: unknown) {
      toast({
        title: "Export gagal",
        description: mapExportError(err),
        variant: "error",
      });
    } finally {
      setExporting(null);
    }
  };

  return (
    <>
      <Button
        variant="outline"
        disabled={exporting !== null}
        onClick={() => void handleExport("csv")}
      >
        {exporting === "csv" ? (
          <Loader2 className="animate-spin" />
        ) : (
          <FileDown />
        )}
        Export CSV
      </Button>
      <Button
        variant="outline"
        disabled={exporting !== null}
        onClick={() => void handleExport("excel")}
      >
        {exporting === "excel" ? (
          <Loader2 className="animate-spin" />
        ) : (
          <FileSpreadsheet />
        )}
        Export Excel
      </Button>
    </>
  );
}