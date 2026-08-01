import type { LucideIcon } from "lucide-react";

/** Item navigasi sidebar. */
export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
}

/** Status koneksi backend untuk indikator navbar. */
export type BackendStatus = "online" | "offline" | "checking";

/** Ringkasan statistik dashboard. */
export interface DashboardStats {
  totalDetection: number;
  todayDetection: number;
  backendStatus: BackendStatus;
  modelStatus: "loaded" | "not_loaded";
}