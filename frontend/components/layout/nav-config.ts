import {
  Activity,
  History,
  LayoutDashboard,
  ScanSearch,
} from "lucide-react";

import type { NavItem } from "@/types";

/** Konfigurasi navigasi tunggal — dipakai sidebar desktop dan Sheet
 *  mobile agar keduanya selalu konsisten. */
export const NAV_ITEMS: readonly NavItem[] = [
  { title: "Dashboard", href: "/", icon: LayoutDashboard },
  { title: "Detect Image", href: "/detect", icon: ScanSearch },
  { title: "Detection History", href: "/history", icon: History },
  { title: "System Status", href: "/system", icon: Activity },
] as const;
