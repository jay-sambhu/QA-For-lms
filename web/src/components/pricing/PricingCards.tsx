"use client";

import React, { useState } from 'react';
import {
  CreditCard,
  ShoppingBag,
  Zap,
  DollarSign,
  Check,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import styles from '../../app/page.module.css';

export const PricingCards: React.FC = () => {
  const { session, openAuthModal, refreshPlan } = useAuth();
  const [selectedGateway, setSelectedGateway] = useState<'stripe' | 'lemonsqueezy' | 'razorpay' | 'paypal'>('stripe');
  const [billingLoading, setBillingLoading] = useState(false);
  const [billingMessage, setBillingMessage] = useState('');

  const handleCheckout = async (planId: string) => {
    if (!session) {
      openAuthModal('signin');
      return;
    }

    setBillingLoading(true);
    setBillingMessage('');
    try {
      const res = await fetch('/api/v1/billing/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          plan_id: planId,
          gateway: selectedGateway,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Checkout failed');

      if (data.checkout_url) {
        setBillingMessage(`Redirecting to secure ${selectedGateway.toUpperCase()} checkout...`);
        setTimeout(() => {
          window.location.href = data.checkout_url;
        }, 1000);
      } else {
        setBillingMessage(data.message || 'Plan upgraded successfully!');
        await refreshPlan();
      }
    } catch (err) {
      setBillingMessage(err instanceof Error ? err.message : 'Checkout failed.');
    } finally {
      setBillingLoading(false);
    }
  };

  const gateways = [
    { id: 'stripe', name: 'Stripe', icon: <CreditCard size={16} /> },
    { id: 'lemonsqueezy', name: 'LemonSqueezy', icon: <ShoppingBag size={16} /> },
    { id: 'razorpay', name: 'Razorpay', icon: <Zap size={16} /> },
    { id: 'paypal', name: 'PayPal', icon: <DollarSign size={16} /> },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', maxWidth: '1080px', margin: '0 auto', width: '100%' }}>
      {billingMessage && (
        <div className={`${styles.authBanner} ${billingMessage.includes('Redirecting') || billingMessage.includes('success') ? styles.authBannerSuccess : styles.authBannerError}`}>
          {billingMessage.includes('Redirecting') || billingMessage.includes('success') ? (
            <CheckCircle2 size={16} />
          ) : (
            <AlertCircle size={16} />
          )}
          <span>{billingMessage}</span>
        </div>
      )}

      {/* Gateway Selector */}
      <div className={styles.gatewaySelectSection}>
        <div className={styles.gatewaySelectLabel}>Select Payment Gateway & Merchant</div>
        <div className={styles.gatewayGrid}>
          {gateways.map((gw) => (
            <button
              key={gw.id}
              type="button"
              onClick={() => setSelectedGateway(gw.id as any)}
              className={`${styles.gatewayOption} ${selectedGateway === gw.id ? styles.gatewayOptionActive : ''}`}
            >
              {gw.icon}
              <span>{gw.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 3 Plan Cards */}
      <div className={styles.pricingGrid}>
        {/* Starter Plan */}
        <div className={styles.planCard}>
          <div className={styles.planHeader}>
            <div className={styles.planName}>Community Starter</div>
            <div className={styles.planPriceRow}>
              <span className={styles.planPrice}>$0</span>
              <span className={styles.planInterval}>/ month</span>
            </div>
            <div className={styles.planDesc}>Ideal for developers and open-source projects auditing basic sites.</div>
          </div>

          <div className={styles.planFeaturesList}>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> 10 Automated Scans / mo</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Multi-Viewport (Desktop, Mobile, Tablet)</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Deterministic Defect Triage</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Executive Score & Grading</div>
          </div>

          <button
            type="button"
            disabled={billingLoading}
            onClick={() => handleCheckout('free')}
            className={styles.planSelectBtn}
          >
            Select Starter ($0)
          </button>
        </div>

        {/* Pro Plan */}
        <div className={`${styles.planCard} ${styles.planCardHighlighted}`}>
          <div className={styles.planPopularBadge}>Recommended</div>
          <div className={styles.planHeader}>
            <div className={styles.planName}>Professional QA</div>
            <div className={styles.planPriceRow}>
              <span className={styles.planPrice}>$49</span>
              <span className={styles.planInterval}>/ month</span>
            </div>
            <div className={styles.planDesc}>Continuous testing for growth teams, SaaS applications, and QA engineers.</div>
          </div>

          <div className={styles.planFeaturesList}>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> 200 Automated Scans / mo</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Up to 50 Pages Deep Crawling</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Authenticated Route & Session Crawling</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Executive PDF & Excel Multi-Tab Exports</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Priority Processing Queue</div>
          </div>

          <button
            type="button"
            disabled={billingLoading}
            onClick={() => handleCheckout('pro')}
            className={`${styles.planSelectBtn} ${styles.planSelectBtnPrimary}`}
          >
            {billingLoading ? 'Processing...' : `Upgrade with ${selectedGateway.toUpperCase()}`}
          </button>
        </div>

        {/* Enterprise Plan */}
        <div className={styles.planCard}>
          <div className={styles.planHeader}>
            <div className={styles.planName}>Enterprise Suite</div>
            <div className={styles.planPriceRow}>
              <span className={styles.planPrice}>$199</span>
              <span className={styles.planInterval}>/ month</span>
            </div>
            <div className={styles.planDesc}>Full compliance platform with dedicated cluster workers and priority SLA.</div>
          </div>

          <div className={styles.planFeaturesList}>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Unlimited Automated QA Scans</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Deep Unlimited Page Discovery</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Custom MFA & Complex Auth Portals</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> Dedicated Worker Node & SLA</div>
            <div className={styles.planFeatureItem}><Check size={14} color="#10b981" /> 24/7 Priority Support</div>
          </div>

          <button
            type="button"
            disabled={billingLoading}
            onClick={() => handleCheckout('enterprise')}
            className={styles.planSelectBtn}
          >
            {billingLoading ? 'Processing...' : `Select Enterprise (${selectedGateway.toUpperCase()})`}
          </button>
        </div>
      </div>
    </div>
  );
};
