"use client";

import * as React from "react";
import { Tags } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { LabelCount } from "@/types";

interface LabelStatsProps {
  labels: LabelCount[];
  noDetection: number;
}

/** Kartu statistik jumlah deteksi per label (data nyata dari DB). */
export function LabelStats({
  labels,
  noDetection,
}: LabelStatsProps): React.ReactElement {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Detections per Label</CardTitle>
      </CardHeader>
      <CardContent>
        {labels.length === 0 && noDetection === 0 ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            <Tags className="mx-auto mb-2 size-6" />
            Belum ada riwayat deteksi.
          </div>
        ) : (
          <ul className="space-y-2">
            {labels.map((item) => (
              <li
                key={item.label}
                className="flex items-center justify-between gap-3 text-sm"
              >
                <span className="truncate">{item.label}</span>
                <span className="font-medium tabular-nums">{item.count}</span>
              </li>
            ))}
            <li className="flex items-center justify-between gap-3 border-t pt-2 text-sm text-muted-foreground">
              <span>No Detection</span>
              <span className="font-medium tabular-nums">{noDetection}</span>
            </li>
          </ul>
        )}
      </CardContent>
    </Card>
  );
}