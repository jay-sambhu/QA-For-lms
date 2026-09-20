"use client";

import React from 'react';
import { TbDeviceDesktop, TbDeviceMobile, TbDeviceTablet, TbActivity } from 'react-icons/tb';
import { CrossDeviceMetrics } from '../../../types/qa';
import styles from '../../../app/page.module.css';

interface DevicesTabProps {
  crossDeviceMetrics?: CrossDeviceMetrics;
}

export const DevicesTab: React.FC<DevicesTabProps> = ({ crossDeviceMetrics }) => {
  if (!crossDeviceMetrics) {
    return (
      <div className={styles.noFindings}>
        No responsive viewport telemetry recorded for this scan.
      </div>
    );
  }

  const breakdown = crossDeviceMetrics.device_breakdown || {
    desktop: 0,
    iphone: 0,
    ipad: 0,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span>Desktop (1920x1080)</span>
            <TbDeviceDesktop size={20} color="#818cf8" />
          </div>
          <div className={styles.statValue}>{breakdown.desktop}</div>
          <div className={styles.statSub}>Responsive Findings</div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span>iPhone 13 (390x844)</span>
            <TbDeviceMobile size={20} color="#38bdf8" />
          </div>
          <div className={styles.statValue}>{breakdown.iphone}</div>
          <div className={styles.statSub}>Touch & Viewport Findings</div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span>iPad (820x1180)</span>
            <TbDeviceTablet size={20} color="#34d399" />
          </div>
          <div className={styles.statValue}>{breakdown.ipad}</div>
          <div className={styles.statSub}>Tablet Layout Findings</div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span>Total Responsive Issues</span>
            <TbActivity size={20} color="#f59e0b" />
          </div>
          <div className={styles.statValue}>
            {crossDeviceMetrics.responsive_findings ?? 0}
          </div>
          <div className={styles.statSub}>Across all emulated viewports</div>
        </div>
      </div>
    </div>
  );
};
