"use client";

import * as React from "react";
import { isAxiosError } from "axios";
import {
  ChevronLeft,
  ChevronRight,
  History,
  Search,
  Trash2,
} from "lucide-react";

import { EmptyState, ErrorState } from "@/components/api-states";
import { useToast } from "@/components/toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import api, { API_BASE_URL } from "@/services/api";
import { useApiGet } from "@/lib/use-api-get";
import type { HistoryListResponse } from "@/types";

/**
 * Opsi label diambil dari backend (GET /labels) sebagai single source
 * of truth, sehingga tidak ada salinan nama label yang di-hardcode di
 * frontend. "No Detection" ditambahkan sebagai opsi filter khusus
 * record tanpa deteksi.
 */
const NO_DETECTION_OPTION = "No Detection";

const PAGE_SIZE = 10;

const inputClass =
  "h-9 rounded-md border border-input bg-background px-3 text-sm " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

function mapDeleteError(err: unknown): string {
  if (isAxiosError(err) && err.response) {
    if (err.response.status === 401) return "Sesi berakhir — silakan login ulang.";
    if (err.response.status === 404) return "Record tidak ditemukan.";
    return "Terjadi kesalahan pada server.";
  }
  return "Backend tidak dapat dihubungi.";
}

export default function HistoryPage(): React.ReactElement {
  const { toast } = useToast();

  // Nilai input (belum diterapkan) vs filter aktif (memicu fetch).
  const [searchInput, setSearchInput] = React.useState<string>("");
  const [search, setSearch] = React.useState<string>("");
  const [label, setLabel] = React.useState<string>("");
  const { data: labelData } = useApiGet<{ labels: string[] }>("/labels");
  const labelOptions: readonly string[] = [
    ...(labelData?.labels ?? []),
    NO_DETECTION_OPTION,
  ];
  const [dateFrom, setDateFrom] = React.useState<string>("");
  const [dateTo, setDateTo] = React.useState<string>("");
  const [page, setPage] = React.useState<number>(1);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = React.useState<boolean>(false);

  // Query string dirakit dari filter aktif; perubahan path memicu
  // refetch otomatis di useApiGet.
  const query = React.useMemo(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(PAGE_SIZE));
    if (search) params.set("search", search);
    if (label) params.set("label", label);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return params.toString();
  }, [page, search, label, dateFrom, dateTo]);

  const { data, isLoading, error, retry } = useApiGet<HistoryListResponse>(
    `/history?${query}`
  );

  // Kosongkan pilihan setiap data berganti halaman/filter.
  React.useEffect(() => {
    setSelected(new Set());
  }, [query]);

  const applySearch = (): void => {
    setPage(1);
    setSearch(searchInput.trim());
  };

  const toggleSelect = (id: string): void => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = (): void => {
    if (!data) return;
    setSelected((current) =>
      current.size === data.items.length
        ? new Set()
        : new Set(data.items.map((item) => item.id))
    );
  };

  const deleteSingle = async (id: string): Promise<void> => {
    if (!window.confirm("Hapus record ini? Gambar terkait ikut terhapus.")) {
      return;
    }
    setIsDeleting(true);
    try {
      await api.delete(`/history/${id}`);
      toast({ title: "Record dihapus.", variant: "success" });
      retry();
    } catch (err: unknown) {
      toast({ title: "Gagal menghapus", description: mapDeleteError(err), variant: "error" });
    } finally {
      setIsDeleting(false);
    }
  };

  const deleteSelected = async (): Promise<void> => {
    if (selected.size === 0) return;
    if (
      !window.confirm(
        `Hapus ${selected.size} record terpilih? Gambar terkait ikut terhapus.`
      )
    ) {
      return;
    }
    setIsDeleting(true);
    try {
      const response = await api.delete<{ deleted: number }>("/history", {
        data: { ids: Array.from(selected) },
      });
      toast({
        title: `${response.data.deleted} record dihapus.`,
        variant: "success",
      });
      retry();
    } catch (err: unknown) {
      toast({ title: "Gagal menghapus", description: mapDeleteError(err), variant: "error" });
    } finally {
      setIsDeleting(false);
    }
  };

  const allSelected =
    data !== null && data.items.length > 0 && selected.size === data.items.length;

  return (
    <section className="mx-auto w-full max-w-6xl space-y-6">
      <div>
        <h2 className="font-display text-2xl font-semibold tracking-tight">
          Detection History
        </h2>
        <p className="text-sm text-muted-foreground">
          Riwayat seluruh deteksi yang tersimpan di database.
        </p>
      </div>

      {/* Panel filter */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filter</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="flex min-w-48 flex-1 flex-col gap-1.5">
            <label htmlFor="search" className="text-xs text-muted-foreground">
              Cari label / nama file
            </label>
            <div className="flex gap-2">
              <input
                id="search"
                type="text"
                className={`${inputClass} w-full`}
                placeholder="mis. tunas"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") applySearch();
                }}
              />
              <Button variant="outline" size="icon" onClick={applySearch} aria-label="Cari">
                <Search />
              </Button>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="label" className="text-xs text-muted-foreground">
              Label
            </label>
            <select
              id="label"
              className={inputClass}
              value={label}
              onChange={(event) => {
                setPage(1);
                setLabel(event.target.value);
              }}
            >
              <option value="">Semua label</option>
              {labelOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="date-from" className="text-xs text-muted-foreground">
              Dari tanggal
            </label>
            <input
              id="date-from"
              type="date"
              className={inputClass}
              value={dateFrom}
              onChange={(event) => {
                setPage(1);
                setDateFrom(event.target.value);
              }}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="date-to" className="text-xs text-muted-foreground">
              Sampai tanggal
            </label>
            <input
              id="date-to"
              type="date"
              className={inputClass}
              value={dateTo}
              onChange={(event) => {
                setPage(1);
                setDateTo(event.target.value);
              }}
            />
          </div>

          <Button
            variant="destructive"
            disabled={selected.size === 0 || isDeleting}
            onClick={() => void deleteSelected()}
          >
            <Trash2 />
            Hapus ({selected.size})
          </Button>
        </CardContent>
      </Card>

      {/* Daftar */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-16 rounded-xl" />
          ))}
        </div>
      ) : error || !data ? (
        <ErrorState onRetry={retry} />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={History}
          title="Belum ada riwayat deteksi."
          description={
            search || label || dateFrom || dateTo
              ? "Tidak ada record yang cocok dengan filter — coba longgarkan pencarian."
              : "Riwayat akan muncul setelah deteksi pertama tersimpan."
          }
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="p-3">
                      <input
                        type="checkbox"
                        aria-label="Pilih semua di halaman ini"
                        checked={allSelected}
                        onChange={toggleSelectAll}
                      />
                    </th>
                    <th className="p-3">Gambar</th>
                    <th className="p-3">Label</th>
                    <th className="p-3">Action</th>
                    <th className="p-3">Waktu</th>
                    <th className="p-3 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr key={item.id} className="border-b last:border-0">
                      <td className="p-3">
                        <input
                          type="checkbox"
                          aria-label="Pilih record"
                          checked={selected.has(item.id)}
                          onChange={() => toggleSelect(item.id)}
                        />
                      </td>
                      <td className="p-3">
                        <div className="size-12 overflow-hidden rounded-md border bg-muted">
                          {item.annotated_image_path ? (
                            /* eslint-disable-next-line @next/next/no-img-element */
                            <img
                              src={`${API_BASE_URL}/${item.annotated_image_path}`}
                              alt=""
                              className="h-full w-full object-cover"
                            />
                          ) : null}
                        </div>
                      </td>
                      <td className="p-3">
                        <Badge
                          variant={
                            item.label === "No Detection"
                              ? "outline"
                              : "secondary"
                          }
                        >
                          {item.label}
                        </Badge>
                      </td>
                      <td className="p-3 text-muted-foreground">
                        {item.action}
                      </td>
                      <td className="p-3 text-muted-foreground">
                        {new Date(item.detected_at).toLocaleString("id-ID", {
                          dateStyle: "medium",
                          timeStyle: "short",
                        })}
                      </td>
                      <td className="p-3 text-right">
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label="Hapus record"
                          disabled={isDeleting}
                          onClick={() => void deleteSingle(item.id)}
                        >
                          <Trash2 className="text-destructive" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between border-t p-3 text-sm">
              <span className="text-muted-foreground">
                {data.total} record · halaman {data.page} dari{" "}
                {Math.max(data.total_pages, 1)}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((current) => current - 1)}
                >
                  <ChevronLeft />
                  Sebelumnya
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= data.total_pages}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Berikutnya
                  <ChevronRight />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </section>
  );
}