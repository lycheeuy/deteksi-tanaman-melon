import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Nama cookie JWT — harus sama dengan lib/auth.ts. */
const TOKEN_COOKIE = "melon_token";

/** Route yang hanya boleh diakses setelah login. */
const PROTECTED_PREFIXES = ["/detect", "/history", "/system"] as const;

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const hasToken = Boolean(request.cookies.get(TOKEN_COOKIE)?.value);

  const isProtected = PROTECTED_PREFIXES.some((prefix) =>
    pathname.startsWith(prefix)
  );

  // Belum login menuju halaman terproteksi -> ke /login.
  if (isProtected && !hasToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Sudah login menuju /login -> langsung ke dashboard.
  if (pathname === "/login" && hasToken) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/detect/:path*", "/history/:path*", "/system/:path*", "/login"],
};