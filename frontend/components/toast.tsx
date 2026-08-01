"use client";

import * as React from "react";
import { AlertCircle, CheckCircle2, X } from "lucide-react";

import { cn } from "@/lib/utils";

/* ============================================================
   Sistem toast ringan tanpa dependency: Provider + useToast.
   Auto-dismiss 4,5 detik; bisa ditutup manual.
   ============================================================ */

type ToastVariant = "success" | "error";

interface ToastItem {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
}

type ToastInput = Omit<ToastItem, "id">;

interface ToastContextValue {
  toast: (item: ToastInput) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

const AUTO_DISMISS_MS = 4_500;

export function ToastProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const [items, setItems] = React.useState<ToastItem[]>([]);

  const dismiss = React.useCallback((id: number): void => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const toast = React.useCallback(
    (input: ToastInput): void => {
      const id = Date.now() + Math.random();
      setItems((current) => [...current, { ...input, id }]);
      setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
    },
    [dismiss]
  );

  const value = React.useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Viewport toast: pojok kanan bawah, di atas semua konten. */}
      <div
        aria-live="polite"
        className="pointer-events-none fixed bottom-4 right-4 z-100 flex w-full max-w-sm flex-col gap-2"
      >
        {items.map((item) => (
          <div
            key={item.id}
            role="status"
            className={cn(
              "pointer-events-auto flex items-start gap-3 rounded-lg border bg-card p-3 shadow-lg",
              item.variant === "success"
                ? "border-primary/40"
                : "border-destructive/50"
            )}
          >
            {item.variant === "success" ? (
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" />
            ) : (
              <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
            )}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{item.title}</p>
              {item.description ? (
                <p className="text-xs text-muted-foreground">
                  {item.description}
                </p>
              ) : null}
            </div>
            <button
              aria-label="Tutup notifikasi"
              className="text-muted-foreground transition-colors hover:text-foreground"
              onClick={() => dismiss(item.id)}
            >
              <X className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** Hook pemicu toast. Wajib dipakai di dalam ToastProvider. */
export function useToast(): ToastContextValue {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast harus dipakai di dalam <ToastProvider>.");
  }
  return context;
}