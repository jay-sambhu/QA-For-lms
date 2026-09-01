import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "../context/AuthContext";
import { NavBar } from "../components/layout/NavBar";
import { Footer } from "../components/layout/Footer";
import { AuthModal } from "../components/auth/AuthModal";
import { UserProfileModal } from "../components/auth/UserProfileModal";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "JASUSS — Enterprise Web Quality Assurance & Regression Platform (Powered by Nexus)",
  description:
    "JASUSS: Next-generation automated web quality assurance suite powered by Nexus. End-to-end multi-viewport crawling, synthetic interaction testing, defect triage, and executive compliance audits.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <AuthProvider>
          <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
            <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "0 24px", width: "100%", flex: 1, display: "flex", flexDirection: "column" }}>
              <NavBar />
              <main style={{ flex: 1 }}>{children}</main>
              <Footer />
            </div>
          </div>
          <AuthModal />
          <UserProfileModal />
        </AuthProvider>
      </body>
    </html>
  );
}
