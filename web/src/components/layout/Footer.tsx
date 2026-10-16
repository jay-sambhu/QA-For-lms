import React from "react";
import Link from "next/link";
import styles from "../../app/page.module.css";

export const Footer: React.FC = () => {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerStage} aria-hidden="true">
        <div className={styles.footerGlow} />
        <div className={styles.footerFloor} />
      </div>

      <div className={styles.footerInner}>
        {/* Brand Column */}
        <div className={styles.footerBrand}>
          <Link href="/" className={styles.footerLogo} aria-label="JASUSS.TECH home">
            <img src="/logo-icon.png" alt="" width={36} height={36} className={styles.footerLogoMark} />
            <span>
              JASUSS<span className={styles.logoSub}>.TECH</span>
            </span>
          </Link>
          <p className={styles.footerTagline}>
            Next-Generation Autonomous Web Quality Assurance &amp; Regression Suite powered by Nexus. Multi-viewport crawling, synthetic interaction testing, and compliance audits.
          </p>
        </div>

        {/* Quick Links Column */}
        <nav className={styles.footerCol} aria-label="Platform">
          <span className={`section-eyebrow ${styles.footerColTitle}`}>Platform</span>
          <Link href="/" className={styles.footerLink}>Home</Link>
          <Link href="/dashboard" className={styles.footerLink}>Dashboard</Link>
          <Link href="/pricing" className={styles.footerLink}>Pricing &amp; Plans</Link>
          <Link href="/blog" className={styles.footerLink}>Engineering Blog</Link>
        </nav>

        {/* Capabilities Column */}
        <div className={styles.footerCol}>
          <span className={`section-eyebrow ${styles.footerColTitle}`}>Testing Capabilities</span>
          <span className={styles.footerStatic}>Multi-Viewport Crawling</span>
          <span className={styles.footerStatic}>Synthetic Interaction Tests</span>
          <span className={styles.footerStatic}>Executive Compliance Audits</span>
          <span className={styles.footerStatic}>Root-Cause Defect Triage</span>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className={styles.footerBottom}>
        <p>
          © {new Date().getFullYear()} JASUSS.TECH. All rights reserved. Powered by Nexus Engine.
        </p>
        <span className="chip chip--success chip--dot">All QA Engine Nodes Operational</span>
      </div>
    </footer>
  );
};
