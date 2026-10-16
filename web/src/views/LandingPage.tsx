"use client";

import React from 'react';
import Link from 'next/link';
import {
  RiShieldCheckFill,
  RiBug2Line,
  RiLockPasswordLine,
  RiCheckboxCircleFill,
  RiChromeFill,
} from 'react-icons/ri';
import {
  TbDevices,
  TbBolt,
  TbBrain,
  TbReportAnalytics,
  TbArrowRight,
  TbSparkles,
  TbGift,
} from 'react-icons/tb';
import {
  SiFastapi,
  SiNextdotjs,
  SiRedis,
  SiPython,
  SiTypescript,
} from 'react-icons/si';
import { HiSparkles } from 'react-icons/hi2';
import { useAuth } from '../context/AuthContext';
import { Hero3DMap } from '../components/three/Hero3DMap';
import { Tilt3D } from '../components/three/Tilt3D';
import { Reveal } from '../components/three/Reveal';
import styles from '../app/page.module.css';
import c from '../app/content3d.module.css';

const METHODS = [
  {
    icon: <TbDevices size={24} color="#4f46e5" />,
    tint: 'rgba(99, 102, 241, 0.1)',
    title: 'Multi-Viewport Crawling',
    desc: 'Inspects Desktop (1920×1080), iPhone 13 and iPad layouts to catch breakage and overflow on every screen.',
    tags: ['Desktop', 'Mobile', 'Tablet'],
  },
  {
    icon: <TbBolt size={24} color="#0284c7" />,
    tint: 'rgba(14, 165, 233, 0.1)',
    title: 'Synthetic Interaction Testing',
    desc: 'Finds and exercises buttons, links, inputs and dialogs to verify the site actually responds.',
    tags: ['Forms', 'Clicks', 'Navigation'],
  },
  {
    icon: <RiBug2Line size={24} color="#dc2626" />,
    tint: 'rgba(239, 68, 68, 0.1)',
    title: 'Deterministic Defect Triage',
    desc: 'Traps HTTP 4xx/5xx responses, unhandled JavaScript exceptions and console errors as they happen.',
    tags: ['HTTP 500', 'Console', 'CORS'],
  },
  {
    icon: <RiLockPasswordLine size={24} color="#059669" />,
    tint: 'rgba(16, 185, 129, 0.1)',
    title: 'Authenticated Sessions',
    desc: 'Logs in with transient, in-memory credentials to test protected routes without leaking secrets.',
    tags: ['Login', 'Protected Routes'],
  },
  {
    icon: <TbBrain size={24} color="#9333ea" />,
    tint: 'rgba(168, 85, 247, 0.1)',
    title: 'AI Quality Synthesis',
    desc: 'Root-cause analysis, P0–P4 severity, reproduction steps and a canonical letter grade.',
    tags: ['Root Cause', 'Grade', 'Repro'],
  },
  {
    icon: <TbReportAnalytics size={24} color="#d97706" />,
    tint: 'rgba(245, 158, 11, 0.12)',
    title: 'Regression & Exports',
    desc: 'Diffs against previous scans to flag new vs resolved defects, with PDF, Excel, JSON and Markdown export.',
    tags: ['PDF', 'Excel', 'Diffing'],
  },
];

const STEPS = [
  { title: 'Point it at your site', desc: 'Paste a URL, optionally add a login. No SDK or code changes required to start.' },
  { title: 'We map every page in 3D', desc: 'Headless browsers crawl each viewport, click through flows and record evidence.' },
  { title: 'Get a graded report', desc: 'AI triage turns raw findings into prioritised defects you can export and share.' },
];

export const LandingPage: React.FC = () => {
  const { session, openAuthModal } = useAuth();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '88px', padding: '8px 0 96px' }}>
      {/* Hero: copy + 3D site map */}
      <section className={styles.heroSplit}>
        <Reveal className={styles.heroCopy}>
          <div className={styles.badge}>
            <HiSparkles size={14} /> Autonomous web QA
          </div>
          <h1 className={styles.title}>
            See your website <span className={styles.gradientText}>mapped, tested and graded</span> in minutes
          </h1>
          <p className={styles.subtitle}>
            JASUSS crawls every page across desktop, tablet and mobile, exercises real interactions and turns
            what it finds into a prioritised, audit-ready report.
          </p>

          <div className={styles.heroActions}>
            {session ? (
              <Link href="/dashboard" className={styles.launchBtn} style={{ textDecoration: 'none' }}>
                <span>Go to dashboard</span>
                <TbArrowRight size={18} />
              </Link>
            ) : (
              <>
                <button type="button" onClick={() => openAuthModal('signup')} className={styles.launchBtn}>
                  <TbSparkles size={18} />
                  <span>Start free scan</span>
                  <TbArrowRight size={18} />
                </button>
                <button
                  type="button"
                  onClick={() => openAuthModal('signin')}
                  className="btn btn-secondary"
                  style={{ height: '52px', padding: '0 24px', borderRadius: '12px' }}
                >
                  Sign in
                </button>
              </>
            )}
          </div>

          <p className={c.trialNote}>
            <TbGift size={16} />
            <span><strong>Free to start</strong> during beta, no credit card required.</span>
          </p>

          <div className={styles.heroChecks}>
            <span><RiCheckboxCircleFill size={16} color="#059669" /> No setup</span>
            <span><RiCheckboxCircleFill size={16} color="#059669" /> 3 viewports</span>
            <span><RiCheckboxCircleFill size={16} color="#059669" /> PDF &amp; Excel reports</span>
          </div>
        </Reveal>

        <Reveal delay={150}>
          <Hero3DMap />
        </Reveal>
      </section>

      {/* How it works */}
      <section>
        <Reveal className={styles.methodsHeader}>
          <span className={styles.sectionEyebrow}>How it works</span>
          <h2>From URL to graded report in three steps</h2>
        </Reveal>
        <div className={styles.stepsGrid}>
          {STEPS.map((step, i) => (
            <Reveal key={step.title} delay={i * 120}>
              <Tilt3D className={styles.stepCard}>
                <div className={styles.stepNumber} data-depth="2">{i + 1}</div>
                <div className={styles.stepTitle} data-depth="1">{step.title}</div>
                <p className={styles.stepDesc}>{step.desc}</p>
              </Tilt3D>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Testing methods */}
      <section className={styles.methodsSection}>
        <Reveal className={styles.methodsHeader}>
          <span className={styles.sectionEyebrow}>What gets tested</span>
          <h2>Comprehensive QA, automatically</h2>
          <p>Every scan runs the full suite across viewports, interactions and runtime health.</p>
        </Reveal>

        <div className={styles.methodsGrid}>
          {METHODS.map((m, i) => (
            <Reveal key={m.title} delay={(i % 3) * 100}>
              <Tilt3D className={styles.methodCard}>
                <div className={styles.methodIconWrapper} style={{ background: m.tint }} data-depth="2">
                  {m.icon}
                </div>
                <div className={styles.methodTitle} data-depth="1">{m.title}</div>
                <p className={styles.methodDesc}>{m.desc}</p>
                <div className={styles.methodTagsList}>
                  {m.tags.map((t) => (
                    <span key={t} className={styles.methodTag}>{t}</span>
                  ))}
                </div>
              </Tilt3D>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Tech stack */}
      <Reveal as="section" className={styles.techStackSection}>
        <div className={styles.techStackTitle}>Built on open, proven runtimes</div>
        <div className={styles.techStackGrid}>
          <div className={styles.techStackItem}><SiFastapi size={20} color="#009688" /> FastAPI</div>
          <div className={styles.techStackItem}><RiChromeFill size={20} color="#2e7d32" /> Playwright</div>
          <div className={styles.techStackItem}><SiNextdotjs size={20} color="var(--text-heading)" /> Next.js</div>
          <div className={styles.techStackItem}><SiRedis size={20} color="#dc2626" /> Redis</div>
          <div className={styles.techStackItem}><SiPython size={20} color="#3776ab" /> Python</div>
          <div className={styles.techStackItem}><SiTypescript size={20} color="#3178c6" /> TypeScript</div>
        </div>
      </Reveal>

      {/* CTA */}
      <Reveal>
        <Tilt3D className={styles.ctaBanner} max={3}>
          <div className={styles.ctaBadge}>
            <RiShieldCheckFill size={15} /> Production ready
          </div>
          <h2 className={styles.ctaTitle} data-depth="1">Ready to see your site in a new dimension?</h2>
          <p className={styles.ctaDesc}>
            Launch a multi-device crawl, synthetic user journeys and defect triage on your web app in seconds.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }} data-depth="1">
            <Link href="/dashboard" className={styles.launchBtn} style={{ textDecoration: 'none' }}>
              <span>Start a scan</span>
              <TbArrowRight size={18} />
            </Link>
            <Link href="/pricing" className="btn btn-secondary" style={{ height: '52px', padding: '0 24px', borderRadius: '12px' }}>
              See pricing
            </Link>
          </div>
        </Tilt3D>
      </Reveal>
    </div>
  );
};
