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
  title: "PureCortex | Sovereign AI Agent Infrastructure",
  description: "Deploy, tokenize, and engage with autonomous AI agents on Algorand. Powered by Dual-Brain cognitive consensus and the $CORTEX token.",
  openGraph: {
    title: "PureCortex | Sovereign AI Agent Infrastructure",
    description: "The premier infrastructure for autonomous agentic commerce on Algorand.",
    url: "https://purecortex.ai",
    siteName: "PureCortex",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    site: "@purecortexai",
    title: "PureCortex | Sovereign AI Agent Infrastructure",
    description: "Deploy, tokenize, and engage with autonomous AI agents on Algorand.",
  },
  icons: { icon: "/favicon.ico" },
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
