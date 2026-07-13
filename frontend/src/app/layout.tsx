import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Syne, Space_Mono } from "next/font/google";
import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"],
  variable: "--font-syne",
  display: "swap",
});

const spaceMono = Space_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-space-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "One Piece RAG",
  description: "Assistant encyclopedique One Piece avec citations",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr" className={`${syne.variable} ${spaceMono.variable}`}>
      <body className="min-h-screen font-mono antialiased">{children}</body>
    </html>
  );
}
