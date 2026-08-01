import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";

import { Navbar } from "@/components/layout/navbar";
import { Sidebar } from "@/components/layout/sidebar";
import { ThemeProvider } from "@/components/theme-provider";
import { ToastProvider } from "@/components/toast";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Melon Detection Dashboard",
  description:
    "Dashboard monitoring deteksi pemangkasan tanaman melon berbasis " +
    "ESP32-CAM dan MobileNetV2 FOMO.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>): React.ReactElement {
  return (
    <html
      lang="id"
      suppressHydrationWarning
      className={`${inter.variable} ${spaceGrotesk.variable}`}
    >
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <ToastProvider>
          <div className="flex min-h-dvh">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <Navbar />
              <main className="flex-1 p-4 md:p-6">{children}</main>
            </div>
          </div>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}