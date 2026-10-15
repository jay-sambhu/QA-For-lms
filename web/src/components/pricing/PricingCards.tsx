"use client";

import React from 'react';
import Link from 'next/link';
import { HiCheck, HiOutlineSparkles } from 'react-icons/hi2';
import { RiShieldStarLine, RiInformationLine } from 'react-icons/ri';
import { useAuth } from '../../context/AuthContext';
import styles from '../../app/page.module.css';
import { Tilt3D } from '../three/Tilt3D';

// Paid checkout is paused during the free beta. Set NEXT_PUBLIC_CONTACT_EMAIL at
// build time to show a "Contact us" button on the Enterprise plan.
const CONTACT_EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL || '';

export const PricingCards: React.FC = () => {
  const { session, openAuthModal } = useAuth();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', maxWidth: '1100px', margin: '0 auto', width: '100%' }}>
      <div className={styles.betaNotice}>
        <RiInformationLine size={18} />
        <span>
          JASUSS is <strong>free during the beta</strong>. Paid plans are coming soon — the Starter plan is open to everyone today.
        </span>
      </div>

      <div className={styles.pricingGrid}>
        {/* Starter Plan */}
        <Tilt3D className={styles.planCard} max={6}>
          <div className={styles.planHeader}>
            <div className={styles.planName}>Community Starter</div>
            <div className={styles.planPriceRow}>
              <span className={styles.planPrice}>$0</span>
              <span className={styles.planInterval}>/ month</span>
            </div>
            <div className={styles.planDesc}>Ideal for developers and open-source projects auditing basic sites.</div>
          </div>

          <div className={styles.planFeaturesList}>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> 10 Automated Scans / mo</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Up to 10 Pages per Scan</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Multi-Viewport (Desktop, Mobile, Tablet)</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Deterministic Defect Triage</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> PDF &amp; Excel Report Downloads</div>
          </div>

          {session ? (
            <Link href="/dashboard" className={`${styles.planSelectBtn} ${styles.planSelectBtnPrimary}`}>
              Go to dashboard
            </Link>
          ) : (
            <button
              type="button"
              onClick={() => openAuthModal('signup')}
              className={`${styles.planSelectBtn} ${styles.planSelectBtnPrimary}`}
            >
              Start free
            </button>
          )}
        </Tilt3D>

        {/* Pro Plan */}
        <Tilt3D className={`${styles.planCard} ${styles.planCardHighlighted}`} max={6}>
          <div className={styles.planPopularBadge}>
            <HiOutlineSparkles size={13} /> Coming soon
          </div>
          <div className={styles.planHeader}>
            <div className={styles.planName}>Professional QA</div>
            <div className={styles.planPriceRow}>
              <span className={styles.planPrice}>$49</span>
              <span className={styles.planInterval}>/ month</span>
            </div>
            <div className={styles.planDesc}>Continuous testing for growth teams, SaaS applications, and QA engineers.</div>
          </div>

          <div className={styles.planFeaturesList}>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> 200 Automated Scans / mo</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Up to 50 Pages Deep Crawling</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Authenticated Route & Session Crawling</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Executive PDF & Excel Multi-Tab Exports</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Priority Processing Queue</div>
          </div>

          <button type="button" disabled className={styles.planSelectBtn}>
            Coming soon
          </button>
        </Tilt3D>

        {/* Enterprise Plan */}
        <Tilt3D className={styles.planCard} max={6}>
          <div className={styles.planHeader}>
            <div className={styles.planName}>
              <RiShieldStarLine size={18} color="#9333ea" style={{ display: 'inline', marginRight: '6px' }} />
              Enterprise Suite
            </div>
            <div className={styles.planPriceRow}>
              <span className={styles.planPrice}>$199</span>
              <span className={styles.planInterval}>/ month</span>
            </div>
            <div className={styles.planDesc}>Full compliance platform with dedicated cluster workers and priority SLA.</div>
          </div>

          <div className={styles.planFeaturesList}>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Unlimited Automated QA Scans</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Deep Unlimited Page Discovery</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Custom MFA & Complex Auth Portals</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> Dedicated Worker Node & SLA</div>
            <div className={styles.planFeatureItem}><HiCheck size={16} color="#10b981" /> 24/7 Priority Support</div>
          </div>

          {CONTACT_EMAIL ? (
            <a
              href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent('JASUSS Enterprise')}`}
              className={styles.planSelectBtn}
            >
              Contact us
            </a>
          ) : (
            <button type="button" disabled className={styles.planSelectBtn}>
              Coming soon
            </button>
          )}
        </Tilt3D>
      </div>
    </div>
  );
};
