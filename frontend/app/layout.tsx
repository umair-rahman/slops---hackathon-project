import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Marginalia — find what's missing in AI peer reviews",
  description:
    "Detect AI-generated peer reviews via 3-layer signal triangulation. Specificity, asymmetry, and batch DNA. No LLM-as-judge.",
  openGraph: {
    title: "Marginalia",
    description: "Find what's missing in AI peer reviews.",
    type: "website",
  },
  keywords: ["AI detection", "peer review", "academic integrity", "openreview", "ICLR", "NeurIPS"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#08080b] text-[#fafaf9] min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
