import type { Metadata } from "next";
import { Bebas_Neue, Lora } from "next/font/google";
import "./globals.css";

const display = Bebas_Neue({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
});

const body = Lora({
  subsets: ["latin"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "One Piece RAG",
  description: "Assistant encyclopedique One Piece avec citations",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${display.variable} ${body.variable}`}>
      <body className="min-h-screen antialiased [font-family:var(--font-body)]">{children}</body>
    </html>
  );
}
