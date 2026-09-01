"use client";

import React from 'react';
import { TrendingUp, Users, Globe, Server } from 'lucide-react';
import styles from '../../app/page.module.css';

interface AdminMetricsProps {
  metrics: any;
  usersCount: number;
  scansCount: number;
}

export const AdminMetrics: React.FC<AdminMetricsProps> = ({
  metrics,
  usersCount,
  scansCount,
}) => {
  const mrr = metrics?.financial_metrics?.mrr_usd ?? 0;
  const paidSubs = metrics?.financial_metrics?.total_paid_subscriptions ?? 0;
  const totalUsers = metrics?.platform_overview?.total_users ?? usersCount;
  const totalScans = metrics?.platform_overview?.total_scans ?? scansCount;
  const successRate = metrics?.platform_overview?.scan_success_rate ?? 100;

  return (
    <div className={styles.statsGrid}>
      <div className={styles.statCard}>
        <div className={styles.statHeader}>
          <span>Monthly Recurring Revenue</span>
          <TrendingUp size={18} color="#10b981" />
        </div>
        <div className={styles.statValue}>${mrr}</div>
        <div className={styles.statSub}>{paidSubs} Active Paid Subscriptions</div>
      </div>

      <div className={styles.statCard}>
        <div className={styles.statHeader}>
          <span>Registered Tenants</span>
          <Users size={18} color="#818cf8" />
        </div>
        <div className={styles.statValue}>{totalUsers}</div>
        <div className={styles.statSub}>Multi-tenant workspace accounts</div>
      </div>

      <div className={styles.statCard}>
        <div className={styles.statHeader}>
          <span>Total Scans Executed</span>
          <Globe size={18} color="#38bdf8" />
        </div>
        <div className={styles.statValue}>{totalScans}</div>
        <div className={styles.statSub}>{successRate}% Platform Success Rate</div>
      </div>

      <div className={styles.statCard}>
        <div className={styles.statHeader}>
          <span>Cluster Worker Status</span>
          <Server size={18} color="#34d399" />
        </div>
        <div className={styles.statValue}>Operational</div>
        <div className={styles.statSub}>Redis Queue · Playwright Workers</div>
      </div>
    </div>
  );
};
