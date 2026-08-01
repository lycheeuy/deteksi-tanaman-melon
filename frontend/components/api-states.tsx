"use client";

import * as React from "react";
import { RefreshCw, type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/** Grid skeleton untuk deretan kartu statistik. */
export function LoadingCards({
  count = 4,
}: {
  count?: number;
}): React.ReactElement {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <Skeleton key={index} className="h-32 rounded-xl" />
      ))}
    </div>
  );
}

/** Skeleton blok konten tunggal (halaman detail/status). */
export function LoadingBlock(): React.ReactElement {
  return (
    <div className="space-y-4">
      <Skeleton className="h-32 rounded-xl" />
      <Skeleton className="h-32 rounded-xl" />
    </div>
  );
}

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
}

/** Empty state konsisten dengan design system (Card + chip icon). */
export function EmptyState({
  icon: Icon,
  title,
  description,
}: EmptyStateProps): React.ReactElement {
  return (
    <Card>
      <CardHeader className="items-center text-center">
        <span className="mb-2 flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="size-6" />
        </span>
        <CardTitle>{title}</CardTitle>
        {description ? (
          <CardDescription>{description}</CardDescription>
        ) : null}
      </CardHeader>
      <CardContent />
    </Card>
  );
}

interface ErrorStateProps {
  message?: string;
  onRetry: () => void;
}

/** Error state dengan tombol Retry. */
export function ErrorState({
  message = "Backend tidak dapat dihubungi.",
  onRetry,
}: ErrorStateProps): React.ReactElement {
  return (
    <Card>
      <CardHeader className="items-center text-center">
        <span className="mb-2 flex size-12 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
          <RefreshCw className="size-6" />
        </span>
        <CardTitle>{message}</CardTitle>
        <CardDescription>
          Pastikan server FastAPI berjalan, lalu coba lagi.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex justify-center">
        <Button variant="outline" onClick={onRetry}>
          <RefreshCw />
          Retry
        </Button>
      </CardContent>
    </Card>
  );
}