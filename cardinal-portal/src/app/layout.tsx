import type { Metadata } from "next";
import { Geist, Geist_Mono, Newsreader, Source_Serif_4 } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { brandAppearance } from "@/components/brand/clerk-appearance";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const newsreader = Newsreader({
  variable: "--font-serif-display",
  subsets: ["latin"],
});

const sourceSerif4 = Source_Serif_4({
  variable: "--font-serif-text",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Cardinal Element",
  description: "A Growth Engine Built for the AI Era.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider appearance={brandAppearance}>
      <html
        lang="en"
        className={`${geistSans.variable} ${geistMono.variable} ${newsreader.variable} ${sourceSerif4.variable} h-full antialiased`}
      >
        <body className="min-h-full flex flex-col bg-background text-foreground">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
