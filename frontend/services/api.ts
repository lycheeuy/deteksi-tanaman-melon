import axios, { type AxiosInstance } from "axios";

/**
 * Base URL backend FastAPI. Dapat dioverride via .env.local:
 *   NEXT_PUBLIC_API_URL=http://localhost:8000
 */
export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Axios instance tunggal untuk seluruh pemanggilan API. */
export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
  headers: {
    Accept: "application/json",
  },
});

// Sisipkan header Authorization dari cookie token (bila ada).
// Berjalan hanya di browser; request server-side tidak tersentuh.
api.interceptors.request.use((config) => {
  if (typeof document !== "undefined") {
    const match = document.cookie
      .split("; ")
      .find((row) => row.startsWith("melon_token="));
    const token = match
      ? decodeURIComponent(match.split("=").slice(1).join("="))
      : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export default api;