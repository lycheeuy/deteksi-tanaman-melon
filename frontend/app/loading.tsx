import * as React from "react";

import { Skeleton } from "@/components/ui/skeleton";

/** Skeleton halaman dashboard saat konten dimuat. */
export default function DashboardLoading(): React.ReactElement {
  return (
    <section className="mx-auto w-full max-w-6xl space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-72" />
      </div>
      <Skeleton className="h-px w-full" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-32 rounded-xl" />
        ))}
      </div>
    </section>
  );
}
