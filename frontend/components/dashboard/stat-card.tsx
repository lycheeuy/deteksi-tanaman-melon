import * as React from "react";
import type { LucideIcon } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  hint?: string;
  icon: LucideIcon;
  /** Warna chip icon: leaf (default) atau melon (aksen). */
  tone?: "leaf" | "melon";
}

/** Kartu statistik reusable untuk ringkasan dashboard. */
export function StatCard({
  title,
  value,
  hint,
  icon: Icon,
  tone = "leaf",
}: StatCardProps): React.ReactElement {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <span
          className={cn(
            "flex size-9 items-center justify-center rounded-lg",
            tone === "leaf"
              ? "bg-primary/10 text-primary"
              : "bg-melon/20 text-foreground"
          )}
        >
          <Icon className="size-4" />
        </span>
      </CardHeader>
      <CardContent>
        <p className="font-display text-3xl font-semibold tracking-tight">
          {value}
        </p>
        {hint ? (
          <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
