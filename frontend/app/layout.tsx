import type { Metadata } from "next";
import { Special_Elite, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const ibmPlexSans = IBM_Plex_Sans({
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-ibm-plex-sans",
});

const specialElite = Special_Elite({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-special-elite",
});

const ibmPlexMono = IBM_Plex_Mono({
  weight: ["400", "500", "600"],
  subsets: ["latin"],
  variable: "--font-ibm-plex-mono",
});

export const metadata: Metadata = {
  title: "Fraud Intelligence Platform",
  description: "Enterprise Transaction Fraud Intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${ibmPlexSans.variable} ${specialElite.variable} ${ibmPlexMono.variable} antialiased min-h-screen bg-paper text-ink font-sans`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
