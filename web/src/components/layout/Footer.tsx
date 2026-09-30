import React from "react";
import Link from "next/link";
import { RiShieldFlashFill } from "react-icons/ri";

export const Footer: React.FC = () => {
  return (
    <footer style={styles.footer}>
      <div style={styles.container}>
        {/* Brand Column */}
        <div style={styles.brandCol}>
          <Link href="/" style={styles.logoLink}>
            <img
              src="/logo.png"
              alt="JASUSS.TECH Logo"
              width={38}
              height={38}
              style={styles.logoImg}
            />
            <span style={styles.logoText}>
              JASUSS<span style={{ color: "#38bdf8" }}>.TECH</span>
            </span>
          </Link>
          <p style={styles.brandTagline}>
            Next-Generation Autonomous Web Quality Assurance &amp; Regression Suite powered by Nexus. Multi-viewport crawling, synthetic interaction testing, and compliance audits.
          </p>
        </div>

        {/* Quick Links Column */}
        <div style={styles.linksCol}>
          <span style={styles.colTitle}>Platform</span>
          <Link href="/" style={styles.footerLink}>Home</Link>
          <Link href="/dashboard" style={styles.footerLink}>Dashboard</Link>
          <Link href="/pricing" style={styles.footerLink}>Pricing &amp; Plans</Link>
          <Link href="/blog" style={styles.footerLink}>Engineering Blog</Link>
        </div>

        {/* Capabilities Column */}
        <div style={styles.linksCol}>
          <span style={styles.colTitle}>Testing Capabilities</span>
          <span style={styles.staticLink}>Multi-Viewport Crawling</span>
          <span style={styles.staticLink}>Synthetic Interaction Tests</span>
          <span style={styles.staticLink}>Executive Compliance Audits</span>
          <span style={styles.staticLink}>Root-Cause Defect Triage</span>
        </div>
      </div>

      {/* Bottom Bar */}
      <div style={styles.bottomBar}>
        <p style={{ margin: 0 }}>
          © {new Date().getFullYear()} JASUSS.TECH. All rights reserved. Powered by Nexus Engine.
        </p>
        <div style={styles.statusIndicator}>
          <div style={styles.statusDot} />
          <span>All QA Engine Nodes Operational</span>
        </div>
      </div>
    </footer>
  );
};

const styles: Record<string, React.CSSProperties> = {
  footer: {
    marginTop: "80px",
    padding: "48px 0 28px",
    borderTop: "1px solid rgba(255, 255, 255, 0.08)",
    color: "#64748b",
    fontSize: "0.85rem",
    width: "100%",
  },
  container: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    flexWrap: "wrap",
    gap: "36px",
    marginBottom: "36px",
    textAlign: "left",
  },
  brandCol: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    maxWidth: "380px",
  },
  logoLink: {
    display: "inline-flex",
    alignItems: "center",
    gap: "10px",
    textDecoration: "none",
    color: "#fff",
    fontWeight: 700,
    fontSize: "1.18rem",
  },
  logoImg: {
    borderRadius: "10px",
    objectFit: "cover",
    boxShadow: "0 0 16px rgba(56, 189, 248, 0.3)",
  },
  logoText: {
    letterSpacing: "-0.01em",
  },
  brandTagline: {
    margin: 0,
    color: "#94a3b8",
    fontSize: "0.85rem",
    lineHeight: 1.6,
  },
  linksCol: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    minWidth: "150px",
  },
  colTitle: {
    color: "#f8fafc",
    fontWeight: 700,
    fontSize: "0.88rem",
    marginBottom: "4px",
    letterSpacing: "0.02em",
  },
  footerLink: {
    color: "#94a3b8",
    textDecoration: "none",
    fontSize: "0.84rem",
    transition: "color 0.2s ease",
  },
  staticLink: {
    color: "#64748b",
    fontSize: "0.82rem",
  },
  bottomBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    paddingTop: "24px",
    borderTop: "1px solid rgba(255, 255, 255, 0.05)",
    flexWrap: "wrap",
    gap: "14px",
    fontSize: "0.8rem",
    color: "#64748b",
  },
  statusIndicator: {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    fontSize: "0.78rem",
    color: "#10b981",
  },
  statusDot: {
    width: "7px",
    height: "7px",
    borderRadius: "50%",
    backgroundColor: "#10b981",
    boxShadow: "0 0 6px #10b981",
  },
};
