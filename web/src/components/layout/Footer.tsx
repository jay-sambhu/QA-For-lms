import React from "react";
import Link from "next/link";
import s from "./shell3d.module.css";

export const Footer: React.FC = () => {
  return (
    <footer className={s.footer}>
      <div className={s.footerStage} aria-hidden="true">
        <div className={s.footerGlow} />
        <div className={s.footerFloor} />
      </div>

      <div className={s.footerInner}>
        {/* Brand Column */}
        <div className={s.footerBrand}>
          <Link href="/" className={s.footerLogo} aria-label="JASUSS.TECH home">
            <img src="/logo-icon.png" alt="" width={36} height={36} className={s.footerLogoMark} />
            <span>
              JASUSS<span className={s.logoSub}>.TECH</span>
            </span>
          </Link>
          <p className={s.footerTagline}>
            Next-Generation Autonomous Web Quality Assurance &amp; Regression Suite powered by Nexus. Multi-viewport crawling, synthetic interaction testing, and compliance audits.
          </p>
        </div>

        {/* Quick Links Column */}
        <nav className={s.footerCol} aria-label="Platform">
          <span className={`section-eyebrow ${s.footerColTitle}`}>Platform</span>
          <Link href="/" className={s.footerLink}>Home</Link>
          <Link href="/dashboard" className={s.footerLink}>Dashboard</Link>
          <Link href="/pricing" className={s.footerLink}>Pricing &amp; Plans</Link>
          <Link href="/blog" className={s.footerLink}>Engineering Blog</Link>
        </nav>

        {/* Capabilities Column */}
        <div className={s.footerCol}>
          <span className={`section-eyebrow ${s.footerColTitle}`}>Testing Capabilities</span>
          <span className={s.footerStatic}>Multi-Viewport Crawling</span>
          <span className={s.footerStatic}>Synthetic Interaction Tests</span>
          <span className={s.footerStatic}>Executive Compliance Audits</span>
          <span className={s.footerStatic}>Root-Cause Defect Triage</span>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className={s.footerBottom}>
        <p>
          © {new Date().getFullYear()} JASUSS.TECH. All rights reserved. Powered by Nexus Engine.
        </p>
        <span className="chip chip--success chip--dot">All QA Engine Nodes Operational</span>
      </div>
    </footer>
  );
};
