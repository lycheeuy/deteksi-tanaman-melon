/** Kontrak response API backend FastAPI (Phase 28A). */

/** Response GET /health. */
export interface HealthResponse {
  status: "ok" | "degraded";
  database: "connected" | "disconnected";
  model: "loaded" | "not_loaded";
  version: string;
}

/** Response GET /system/info. */
export interface SystemInfoResponse {
  app_version: string;
  tensorflow_version: string;
  model_input_size: number[] | string;
  total_labels: number;
  model_path: string;
}

/** Jumlah deteksi per label. */
export interface LabelCount {
  label: string;
  count: number;
}

/** Response GET /dashboard/summary. */
export interface DashboardSummaryResponse {
  total_detection: number;
  today_detection: number;
  no_detection: number;
  labels: LabelCount[];
  database: "connected" | "disconnected";
  model: "loaded" | "not_loaded";
  backend: "online";
}

/** Satu objek terdeteksi pada grid FOMO. */
export interface DetectionItem {
  class_id: number;
  label: string;
  confidence: number;
  grid_x: number;
  grid_y: number;
}

/** Response POST /detect. */
export interface DetectResponse {
  success: boolean;
  message: string;
  record_id: string;
  image_path: string;
  annotated_image_path: string;
  total_detection: number;
  detections: DetectionItem[];
}

/** Satu record riwayat pada GET /dashboard/recent. */
export interface RecentDetectionItem {
  id: string;
  image_path: string;
  annotated_image_path: string | null;
  label: string;
  action: string;
  detected_at: string;
  created_at: string;
  updated_at: string;
}

/** Response GET /dashboard/recent. */
export interface RecentHistoryResponse {
  items: RecentDetectionItem[];
}

/** Data user hasil autentikasi. */
export interface AuthUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

/** Response POST /auth/login. */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

/** Response GET /history (list terpaginate). */
export interface HistoryListResponse {
  items: RecentDetectionItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** Response GET /monitor (Phase 37). */
export interface MonitorResponse {
  backend: "online";
  database: "connected" | "disconnected";
  model: "loaded" | "not_loaded";
  cpu: { percent: number };
  memory: { percent: number; used_mb: number; total_mb: number };
  disk: { percent: number; used_gb: number; total_gb: number };
  latency_ms: number;
  uptime_seconds: number;
  last_update: string;
}