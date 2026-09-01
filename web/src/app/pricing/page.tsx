"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ShieldCheck } from 'lucide-react';
import { PricingCards } from '../../components/pricing/PricingCards';
import styles from '../page.module.css';

export default function PricingPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '36px', padding: '20px 0 60px' }}>
      <motion.section
        className={styles.hero}
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <div className={styles.badge}>
          <Sparkles size={14} /> Transparent & Flexible Plans
        </div>
        <h1 className={styles.title}>
          Scale Your QA With{' '}
          <span className={styles.gradientText}>JASUSS Enterprise</span>
        </h1>
        <p className={styles.subtitle}>
          Choose the automated testing plan that fits your engineering team. Multiple secure payment gateways supported globally.
        </p>
      </motion.section>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        <PricingCards />
      </motion.div>
    </div>
  );
}
