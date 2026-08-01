"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Leaf } from "lucide-react";

import { NAV_ITEMS } from "@/components/layout/nav-config";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

interface SidebarNavProps {
  /** Dipanggil saat item diklik (untuk menutup Sheet di mobile). */
  onNavigate?: () => void;
}

/** Isi navigasi sidebar — dipakai di desktop dan di dalam Sheet mobile. */
export function SidebarNav({
  onNavigate,
}: SidebarNavProps): React.ReactElement {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col">
      <Link
        href="/"
        onClick={onNavigate}
        className="flex items-center gap-2.5 px-2 py-1.5"
      >
        <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Leaf className="size-5" />
        </span>
        <span className="font-display text-base font-semibold leading-tight">
          Deteksi Melon
          <span className="block text-xs font-normal text-muted-foreground">
            Smart pruning monitor
          </span>
        </span>
      </Link>

      <Separator className="my-4" />

      <nav className="flex flex-1 flex-col gap-1" aria-label="Main">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="size-4 shrink-0" />
              {item.title}
            </Link>
          );
        })}
      </nav>

      <p className="px-3 pb-2 text-xs text-muted-foreground">
        ESP32-CAM · MobileNetV2 FOMO
      </p>
    </div>
  );
}
