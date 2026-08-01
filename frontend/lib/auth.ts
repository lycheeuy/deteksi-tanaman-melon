"use client";

/** Nama cookie penyimpan JWT — dibaca juga oleh middleware.ts. */
export const TOKEN_COOKIE = "melon_token";

/** Menyimpan token JWT sebagai cookie (dibaca middleware Next.js). */
export function setToken(token: string, maxAgeSeconds: number): void {
  document.cookie =
    `${TOKEN_COOKIE}=${encodeURIComponent(token)}; ` +
    `path=/; max-age=${maxAgeSeconds}; SameSite=Lax`;
}

/** Mengambil token dari cookie; null bila belum login. */
export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${TOKEN_COOKIE}=`));
  return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : null;
}

/** Menghapus token (logout). */
export function clearToken(): void {
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}