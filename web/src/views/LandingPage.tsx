"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  RiShieldCheckFill,
  RiBug2Line,
  RiLockPasswordLine,
  RiCheckDoubleLine,
  RiSpeedUpLine,
  RiFileDownloadLine,
  RiChromeFill,
} from 'react-icons/ri';
import {
  TbDevices,
  TbBolt,
  TbBrain,
  TbReportAnalytics,
  TbArrowRight,
  TbSparkles,
  TbShieldLock,
} from 'react-icons/tb';
import {
  SiFastapi,
  SiNextdotjs,
  SiRedis,
  SiPython,
  SiTypescript,
} from 'react-icons/si';
import { HiSparkles, HiOutlineCheckCircle } from 'react-icons/hi2';
import { useAuth } from '../context/AuthContext';
import styles from '../app/page.module.css';

export const LandingPage: React.FC = () => {
  const { session, openAuthModal } = useAuth();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '56px', padding: '24px 0 80px' }}>
      {/* Hero Banner */}
      <motion.section
        className={styles.hero}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
      >
        <div className={styles.badge}>
          <HiSparkles size={15} /> Continuous Web Quality & Autonomous Regression Suite
        </div>
        <h1 className={styles.title}>
          Enterprise Automated{' '}
          <span className={styles.gradientText}>Web Quality Assurance</span>
        </h1>
        <p className={styles.subtitle}>
          Full-stack website verification powered by Nexus: multi-viewport crawling, synthetic interaction testing,
          deterministic defect triage, and audit-ready compliance reports.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginTop: '32px', flexWrap: 'wrap' }}>
          {session ? (
            <Link
              href="/dashboard"
              className={styles.launchBtn}
              style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '10px' }}
            >
              <span>Go to QA Dashboard</span>
              <TbArrowRight size={18} />
            </Link>
          ) : (
            <>
              <button
                type="button"
                onClick={() => openAuthModal('signup')}
                className={styles.launchBtn}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '10px' }}
              >
                <TbSparkles size={18} />
                <span>Get Started Free</span>
                <TbArrowRight size={18} />
              </button>

              <button
                type="button"
                onClick={() => openAuthModal('signin')}
                className="btn btn-secondary"
                style={{ padding: '12px 26px', fontSize: '0.95rem', borderRadius: '12px' }}
              >
                Sign In to Workspace
              </button>
            </>
          )}

          <Link
            href="/pricing"
            className="btn btn-secondary"
            style={{ padding: '12px 26px', fontSize: '0.95rem', borderRadius: '12px', textDecoration: 'none' }}
          >
            View Pricing & Plans
          </Link>
        </div>

        {/* Feature Highlights Ticker */}
        <div className={styles.heroHighlightsRow}>
          <div className={styles.heroHighlightItem}>
            <RiCheckDoubleLine size={17} color="#10b981" />
            <span>Zero-Setup Browser Cluster</span>
          </div>
          <div className={styles.heroHighlightItem}>
            <RiSpeedUpLine size={17} color="#38bdf8" />
            <span>Parallel Viewport Auditing</span>
          </div>
          <div className={styles.heroHighlightItem}>
            <TbShieldLock size={17} color="#a855f7" />
            <span>Encrypted In-Memory Auth</span>
          </div>
        </div>
      </motion.section>

      {/* 6-Card Testing Methods Showcase */}
      <section className={styles.methodsSection}>
        <div className={styles.methodsHeader}>
          <h2>Comprehensive QA Testing Methods</h2>
          <p>
            JASUSS executes automated verification pipelines across viewports, interactive elements,
            and performance heuristics to guarantee production stability.
          </p>
        </div>

        <div className={styles.methodsGrid}>
          <div className={styles.methodCard}>
            <div className={styles.methodIconWrapper}>
              <TbDevices size={24} color="#818cf8" />
            </div>
            <div className={styles.methodTitle}>Multi-Viewport Crawling</div>
            <p className={styles.methodDesc}>
              Parallel inspection across Desktop (1920x1080), iPhone 13 (390x844), and iPad (820x1180) to detect layout breakages and overflow.
            </p>
            <div className={styles.methodTagsList}>
              <span className={styles.methodTag}>Desktop</span>
              <span className={styles.methodTag}>Mobile Touch</span>
              <span className={styles.methodTag}>Tablet</span>
            </div>
          </div>

          <div className={styles.methodCard}>
            <div className={styles.methodIconWrapper}>
              <TbBolt size={24} color="#38bdf8" />
            </div>
            <div className={styles.methodTitle}>Synthetic Interactive Testing</div>
            <p className={styles.methodDesc}>
              Automated discovery and execution of interactive buttons, links, inputs, and dialog dismissals to verify client-side responsiveness.
            </p>
            <div className={styles.methodTagsList}>
              <span className={styles.methodTag}>Forms</span>
              <span className={styles.methodTag}>Clicks</span>
              <span className={styles.methodTag}>Navigation</span>
            </div>
          </div>

          <div className={styles.methodCard}>
            <div className={styles.methodIconWrapper}>
              <RiBug2Line size={24} color="#ef4444" />
            </div>
            <div className={styles.methodTitle}>Deterministic Defect Triage</div>
            <p className={styles.methodDesc}>
              Real-time trapping of HTTP 4xx/5xx responses, unhandled JavaScript runtime exceptions, and console error log telemetry.
            </p>
            <div className={styles.methodTagsList}>
              <span className={styles.methodTag}>HTTP 500</span>
              <span className={styles.methodTag}>Console Trace</span>
              <span className={styles.methodTag}>CORS</span>
            </div>
          </div>

          <div className={styles.methodCard}>
            <div className={styles.methodIconWrapper}>
              <RiLockPasswordLine size={24} color="#10b981" />
            </div>
            <div className={styles.methodTitle}>Authenticated Session Testing</div>
            <p className={styles.methodDesc}>
              Form-based authentication flow with transient in-memory credentials and strict zero-leakage security invariants.
            </p>
            <div className={styles.methodTagsList}>
              <span className={styles.methodTag}>Login Portals</span>
              <span className={styles.methodTag}>SecretStr</span>
              <span className={styles.methodTag}>Protected Routes</span>
            </div>
          </div>

          <div className={styles.methodCard}>
            <div className={styles.methodIconWrapper}>
              <TbBrain size={24} color="#a855f7" />
            </div>
            <div className={styles.methodTitle}>AI-Assisted Quality Synthesis</div>
            <p className={styles.methodDesc}>
              Root-cause categorization, severity impact scoring (P0-P4), step-by-step reproduction instructions, and canonical grading.
            </p>
            <div className={styles.methodTagsList}>
              <span className={styles.methodTag}>Root Cause</span>
              <span className={styles.methodTag}>Letter Grade</span>
              <span className={styles.methodTag}>Reproduction</span>
            </div>
          </div>

          <div className={styles.methodCard}>
            <div className={styles.methodIconWrapper}>
              <TbReportAnalytics size={24} color="#f59e0b" />
            </div>
            <div className={styles.methodTitle}>Regression & Executive Exports</div>
            <p className={styles.methodDesc}>
              Historical baseline diffing to identify new vs resolved defects, with one-click export to PDF, Excel, JSON, and Markdown.
            </p>
            <div className={styles.methodTagsList}>
              <span className={styles.methodTag}>PDF Audit</span>
              <span className={styles.methodTag}>Excel Sheets</span>
              <span className={styles.methodTag}>Diffing</span>
            </div>
          </div>
        </div>
      </section>

      {/* Tech Stack Ecosystem Row */}
      <section className={styles.techStackSection}>
        <div className={styles.techStackTitle}>Powered by Modern Open Standards & Enterprise Runtimes</div>
        <div className={styles.techStackGrid}>
          <div className={styles.techStackItem}><SiFastapi size={20} color="#009688" /> FastAPI</div>
          <div className={styles.techStackItem}><RiChromeFill size={20} color="#2e7d32" /> Playwright</div>
          <div className={styles.techStackItem}><SiNextdotjs size={20} color="#ffffff" /> Next.js 16</div>
          <div className={styles.techStackItem}><SiRedis size={20} color="#dc2626" /> Redis</div>
          <div className={styles.techStackItem}><SiPython size={20} color="#3776ab" /> Python 3.12</div>
          <div className={styles.techStackItem}><SiTypescript size={20} color="#3178c6" /> TypeScript</div>
        </div>
      </section>

      {/* Enterprise CTA Banner */}
      <section className={styles.ctaBanner}>
        <div className={styles.ctaBadge}>
          <RiShieldCheckFill size={15} /> Production Ready Platform
        </div>
        <h2 className={styles.ctaTitle}>Ready to Elevate Your Web QA Pipeline?</h2>
        <p className={styles.ctaDesc}>
          Launch automated multi-device crawls, synthetic user journeys, and defect triage on your web application in seconds.
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <Link
            href="/dashboard"
            className={styles.launchBtn}
            style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '10px' }}
          >
            <span>Start Instant Scan</span>
            <TbArrowRight size={18} />
          </Link>
          <Link
            href="/pricing"
            className="btn btn-secondary"
            style={{ padding: '12px 24px', borderRadius: '12px' }}
          >
            Explore Plan Tiers
          </Link>
        </div>
      </section>
    </div>
  );
};
