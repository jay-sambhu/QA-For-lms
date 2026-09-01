"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Sparkles,
  ArrowRight,
  Monitor,
  Zap,
  Bug,
  Lock,
  Cpu,
  GitCompare,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import styles from '../app/page.module.css';

export const LandingPage: React.FC = () => {
  const { session, openAuthModal } = useAuth();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '48px', padding: '20px 0 60px' }}>
      {/* Hero Banner */}
      <motion.section
        className={styles.hero}
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className={styles.badge}>
          <Sparkles size={14} /> Continuous Web Quality & Regression Suite
        </div>
        <h1 className={styles.title}>
          Enterprise Automated{' '}
          <span className={styles.gradientText}>Web Quality Assurance</span>
        </h1>
        <p className={styles.subtitle}>
          Full-stack website verification: multi-viewport crawling, synthetic interaction testing,
          automated defect triage, and executive compliance reports.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginTop: '28px', flexWrap: 'wrap' }}>
          {session ? (
            <Link
              href="/dashboard"
              className={styles.launchBtn}
              style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <span>Go to QA Dashboard</span>
              <ArrowRight size={18} />
            </Link>
          ) : (
            <>
              <button
                type="button"
                onClick={() => openAuthModal('signup')}
                className={styles.launchBtn}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
              >
                <span>Get Started Free</span>
                <ArrowRight size={18} />
              </button>

              <button
                type="button"
                onClick={() => openAuthModal('signin')}
                className="btn btn-secondary"
                style={{ padding: '12px 24px', fontSize: '0.95rem', borderRadius: '12px' }}
              >
                Sign In
              </button>
            </>
          )}

          <Link
            href="/pricing"
            className="btn btn-secondary"
            style={{ padding: '12px 24px', fontSize: '0.95rem', borderRadius: '12px', textDecoration: 'none' }}
          >
            View Pricing & Plans
          </Link>
        </div>
      </motion.section>

      {/* 6-Card Testing Methods Showcase */}
      <section className={styles.methodsSection}>
        <div className={styles.methodsHeader}>
          <h2>Comprehensive QA Testing Methods</h2>
          <p>
            JASUSS executes automated verification pipelines across viewports, interactive elements,
            and performance heuristics to ensure production reliability.
          </p>
        </div>

        <div className={styles.methodsGrid}>
          <div className={styles.methodCard}>
            <div className={styles.methodIconWrapper}>
              <Monitor size={22} color="#818cf8" />
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
              <Zap size={22} color="#38bdf8" />
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
              <Bug size={22} color="#ef4444" />
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
              <Lock size={22} color="#10b981" />
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
              <Cpu size={22} color="#a855f7" />
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
              <GitCompare size={22} color="#f59e0b" />
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

      {/* Enterprise CTA Banner */}
      <section style={{ background: 'linear-gradient(180deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '20px', padding: '40px', textAlign: 'center' }}>
        <h2 style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f8fafc' }}>Ready to Elevate Your Web QA?</h2>
        <p style={{ color: '#94a3b8', maxWidth: '600px', margin: '12px auto 24px' }}>
          Launch automated multi-device crawls and defect detection on your web application in seconds.
        </p>
        <Link
          href="/dashboard"
          className={styles.launchBtn}
          style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
        >
          <span>Start Instant Scan</span>
          <ArrowRight size={18} />
        </Link>
      </section>
    </div>
  );
};
