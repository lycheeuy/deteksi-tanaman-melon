import * as React from "react";

import { SidebarNav } from "@/components/layout/sidebar-nav";

/** Sidebar tetap untuk layar md ke atas. */
export function Sidebar(): React.ReactElement {
  return (
    <aside className="hidden w-64 shrink-0 border-r bg-card p-4 md:flex md:flex-col">
      <SidebarNav />
    </aside>
  );
}
