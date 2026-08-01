"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Menu } from "lucide-react";

import { SidebarNav } from "@/components/layout/sidebar-nav";
import { ModeToggle } from "@/components/mode-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { clearToken, getToken } from "@/lib/auth";
import { useApiGet } from "@/lib/use-api-get";
import type { BackendStatus, HealthResponse } from "@/types";
import { cn } from "@/lib/utils";

/** Indikator status backend dengan titik berdenyut saat online. */
function BackendStatusBadge({
  status,
}: {
  status: BackendStatus;
}): React.ReactElement {
  if (status === "checking") {
    return (
      <Badge variant="secondary" className="px-3 py-1">
        <span aria-hidden className="size-2 rounded-full bg-muted-foreground/50" />
        Checking…
      </Badge>
    );
  }

  const isOnline = status === "online";
  return (
    <Badge
      variant={isOnline ? "secondary" : "destructive"}
      className="px-3 py-1"
    >
      <span
        aria-hidden
        className={cn(
          "size-2 rounded-full",
          isOnline ? "status-dot-online bg-primary" : "bg-white/80"
        )}
      />
      {isOnline ? "Online" : "Offline"}
    </Badge>
  );
}

/** Navbar atas: judul, status backend (real via GET /health), dark
 *  mode, dan menu mobile. */
export function Navbar(): React.ReactElement {
  const [open, setOpen] = React.useState(false);
  const router = useRouter();
  const pathname = usePathname();
  // Status backend di-refresh otomatis setiap 30 detik (senyap).
  const { data, isLoading, error } = useApiGet<HealthResponse>("/health", {
    refreshMs: 30_000,
  });

  // Cek keberadaan token setelah mount (dan setiap pindah halaman)
  // agar tombol Logout hanya tampil saat sudah login.
  const [loggedIn, setLoggedIn] = React.useState<boolean>(false);
  React.useEffect(() => {
    setLoggedIn(getToken() !== null);
  }, [pathname]);

  const handleLogout = (): void => {
    clearToken();
    setLoggedIn(false);
    router.push("/login");
    router.refresh();
  };

  const backendStatus: BackendStatus = isLoading
    ? "checking"
    : error || !data
      ? "offline"
      : "online";

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur md:px-6">
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            aria-label="Open navigation"
          >
            <Menu />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-72 p-4">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarNav onNavigate={() => setOpen(false)} />
        </SheetContent>
      </Sheet>

      <h1 className="font-display text-base font-semibold sm:text-lg">
        Melon Detection Dashboard
      </h1>

      <div className="ml-auto flex items-center gap-2">
        <BackendStatusBadge status={backendStatus} />
        <ModeToggle />
        {loggedIn ? (
          <Button
            variant="ghost"
            size="icon"
            aria-label="Logout"
            onClick={handleLogout}
          >
            <LogOut />
          </Button>
        ) : null}
      </div>
    </header>
  );
}