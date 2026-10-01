import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { AuthProvider } from "../context/AuthContext";
import { NavBar } from "../components/layout/NavBar";
import { Footer } from "../components/layout/Footer";
import { AuthModal } from "../components/auth/AuthModal";
import { UserProfileModal } from "../components/auth/UserProfileModal";
import { AdBlockerDetector } from "../components/ads/AdBlockerDetector";
import { SideAdRails } from "../components/ads/SideAdRails";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteUrl = process.env.NEXT_PUBLIC_APP_URL || "https://www.jasuss.tech";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "JASUSS.TECH — Autonomous Web Quality Assurance & Regression Platform",
    template: "%s | JASUSS.TECH",
  },
  description:
    "JASUSS.TECH: Next-generation automated web quality assurance suite powered by Nexus. End-to-end multi-viewport crawling, synthetic interaction testing, defect triage, and executive compliance audits.",
  keywords: [
    "automated web testing",
    "web quality assurance",
    "autonomous QA agent",
    "regression testing",
    "multi-viewport audit",
    "defect triage",
    "synthetic user testing",
    "website audit",
  ],
  authors: [{ name: "JASUSS.TECH" }],
  creator: "JASUSS.TECH",
  publisher: "JASUSS.TECH",
  alternates: {
    canonical: siteUrl,
  },
  openGraph: {
    title: "JASUSS.TECH — Autonomous Web Quality Assurance & Regression Platform",
    description:
      "Enterprise autonomous web quality assurance suite. Multi-viewport crawling, synthetic user interactions, automated triage, and compliance audits.",
    url: siteUrl,
    siteName: "JASUSS.TECH",
    images: [
      {
        url: "/logo.png",
        width: 800,
        height: 800,
        alt: "JASUSS.TECH Logo",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "JASUSS.TECH — Autonomous Web Quality Assurance & Regression Platform",
    description:
      "Enterprise autonomous web quality assurance suite. Multi-viewport crawling, synthetic user interactions, automated triage, and compliance audits.",
    images: ["/logo.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  icons: {
    icon: "/favicon.ico",
    shortcut: "/logo.png",
    apple: "/logo.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#060911",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <Script
          src="https://accounts.google.com/gsi/client"
          strategy="afterInteractive"
        />
        <Script
          id="google-adsense"
          async
          src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID || "ca-pub-9888591397038663"}`}
          crossOrigin="anonymous"
          strategy="afterInteractive"
        />
        <AuthProvider>
          <SideAdRails>
            <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
              <div className="siteContainer">
                <NavBar />
                <main style={{ flex: 1 }}>{children}</main>
                <Footer />
              </div>
            </div>
          </SideAdRails>
          <AuthModal />
          <UserProfileModal />
          <AdBlockerDetector />
        </AuthProvider>
      </body>
    </html>
  );
}
