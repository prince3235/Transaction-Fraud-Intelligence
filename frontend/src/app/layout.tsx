import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Sentinel — Transaction Fraud Intelligence",
  description:
    "Enterprise real-time transaction fraud detection platform. ML-powered scoring, explainable AI, case management, and compliance operations for modern fintechs and payment processors.",
  keywords: [
    "fraud detection",
    "transaction monitoring",
    "ML inference",
    "explainable AI",
    "SHAP",
    "compliance",
    "case management",
    "fintech",
  ],
  authors: [{ name: "Sentinel Platform" }],
  icons: {
    icon: "https://z-cdn.chatglm.cn/z-ai/static/logo.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}
      >
        {children}
        <Toaster />
        <Sonner />
      </body>
    </html>
  );
}
