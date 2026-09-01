"use client";

import React from 'react';
import { Monitor, Smartphone, Tablet } from 'lucide-react';
import styles from '../../app/page.module.css';

interface DeviceDeckProps {
  activeDeviceName: string;
  activeUrl?: string;
  defaultUrl?: string;
}

export const DeviceDeck: React.FC<DeviceDeckProps> = ({
  activeDeviceName,
  activeUrl,
  defaultUrl,
}) => {
  const devices = [
    {
      id: 'desktop',
      name: 'Desktop Chrome',
      resolution: '1920 × 1080',
      icon: <Monitor size={18} />,
    },
    {
      id: 'iphone',
      name: 'iPhone 13',
      resolution: '390 × 844 (Touch)',
      icon: <Smartphone size={18} />,
    },
    {
      id: 'ipad',
      name: 'iPad (gen 7)',
      resolution: '820 × 1180 (Tablet)',
      icon: <Tablet size={18} />,
    },
  ];

  return (
    <div className={styles.deviceDeckSection}>
      <div className={styles.deviceDeckTitleRow}>
        <span>Live Multi-Device Emulation Viewports</span>
        <span style={{ color: '#34d399', fontSize: '0.75rem' }}>● 3 ISOLATED CONTEXTS ACTIVE</span>
      </div>

      <div className={styles.deviceDeckGrid}>
        {devices.map((dev) => {
          const isCrawlingThis =
            activeDeviceName.toLowerCase().includes(dev.id) ||
            activeDeviceName.toLowerCase().includes(dev.name.toLowerCase());

          return (
            <div
              key={dev.id}
              className={`${styles.deviceCard} ${isCrawlingThis ? styles.deviceCardActive : ''}`}
            >
              <div className={styles.deviceCardHeader}>
                <div className={styles.deviceIconName}>
                  <span style={{ color: isCrawlingThis ? '#818cf8' : '#64748b' }}>{dev.icon}</span>
                  <span>{dev.name}</span>
                </div>
                <span
                  className={`${styles.deviceStatusPill} ${
                    isCrawlingThis ? styles.devicePillActive : styles.devicePillIdle
                  }`}
                >
                  {isCrawlingThis ? 'Crawling Now' : 'Ready'}
                </span>
              </div>

              <div className={styles.deviceMockupFrame}>
                <div style={{ color: isCrawlingThis ? '#38bdf8' : '#94a3b8', fontSize: '0.78rem' }}>
                  {isCrawlingThis
                    ? activeUrl || defaultUrl || 'Navigating DOM...'
                    : 'Waiting for viewport pass...'}
                </div>
                <span className={styles.deviceResolution}>{dev.resolution}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
