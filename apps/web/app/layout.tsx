import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { SessionProvider } from "next-auth/react";
import "./globals.css";
import { Analytics } from "@vercel/analytics/react";

export const metadata: Metadata = {
  title: "tier-zero — engineering review for any GitHub profile",
  description:
    "A multi-agent system that audits originality, depth, and bio-vs-code alignment.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="font-sans antialiased">
        <SessionProvider>{children}</SessionProvider>
        <Analytics />
        <footer className="border-t border-zinc-900 bg-zinc-950 py-6 text-center">
          <p className="px-6 text-[11px] uppercase tracking-[0.18em] text-zinc-600">
            AI-generated analysis &middot; Opinion only, not factual claims &middot;{" "}
            <a href="/terms" className="hover:text-zinc-400">Terms</a>
            {" "}&middot;{" "}
            <a href="/privacy" className="hover:text-zinc-400">Privacy</a>
            {" "}&middot;{" "}
            <a href="/about" className="hover:text-zinc-400">About</a>
          </p>
        </footer>
      </body>
    </html>
  );
}