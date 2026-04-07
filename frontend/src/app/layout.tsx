import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "One Piece RAG",
  description: "Assistant encyclopedique One Piece avec citations",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen antialiased [font-family:var(--font-body)]">{children}</body>
    </html>
  );
}
