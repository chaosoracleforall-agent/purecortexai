import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Providers from "@/components/Providers";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PURECORTEX | Sovereign AI Agent Infrastructure",
  description: "Deploy, tokenize, and engage with autonomous AI agents on Algorand. Powered by Tri-Brain cognitive consensus and the $CORTEX token.",
  openGraph: {
    title: "PURECORTEX | Sovereign AI Agent Infrastructure",
    description: "The premier infrastructure for autonomous agentic commerce on Algorand.",
    url: "https://purecortex.ai",
    siteName: "PURECORTEX",
    type: "website",
    images: [{ url: "https://purecortex.ai/og-image.png", width: 1200, height: 630, alt: "PURECORTEX" }],
  },
  twitter: {
    card: "summary_large_image",
    site: "@purecortexai",
    title: "PURECORTEX | Sovereign AI Agent Infrastructure",
    description: "Deploy, tokenize, and engage with autonomous AI agents on Algorand.",
    images: ["https://purecortex.ai/og-image.png"],
  },
  icons: { icon: "/favicon.png" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <meta name="theme-color" content="#050505" />
      </head>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
