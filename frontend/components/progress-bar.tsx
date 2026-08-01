"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

interface ProgressBarProps {
  /** Nilai 0-100. */
  value: number;
  /** Warna peringatan otomatis saat nilai >= 80 (mis. pemakaian resource). */
  warnAt?: number;
}

/** Bar progres reusable (tanpa dependency). */
export function ProgressBar({
  value,
  warnAt,
}: ProgressBarProps): React.ReactElement {
  const clamped = Math.min(100, Math.max(0, value));
  const isWarning = warnAt !== undefined && clamped >= warnAt;
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className="h-2 w-full overflow-hidden rounded-full bg-muted"
    >
      <div
        className={cn(
          "h-full rounded-full transition-[width] duration-300",
          isWarning ? "bg-destructive" : "bg-primary"
        )}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}