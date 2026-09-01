"use client";

import React from 'react';
import styles from '../../app/page.module.css';

interface SystemTelemetryProps {
  system: {
    runtime?: {
      cpu_utilization_percent?: number;
      memory_used_mb?: number;
      memory_total_mb?: number;
      memory_percent?: number;
    };
    crawler_workers?: {
      active_nodes?: number;
      broker?: string;
    };
  } | null;
}

export const SystemTelemetry: React.FC<SystemTelemetryProps> = ({ system }) => {
  if (!system) return null;

  return (
    <div className={styles.telemetryGrid}>
      <div className={styles.telemetryCard}>
        <div className={styles.telemetryTitle}>CPU Utilization</div>
        <div className={styles.telemetryValue}>
          {system.runtime?.cpu_utilization_percent ?? 0}%
        </div>
        <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Real-time host processor load</span>
      </div>

      <div className={styles.telemetryCard}>
        <div className={styles.telemetryTitle}>Memory Allocation</div>
        <div className={styles.telemetryValue}>
          {system.runtime?.memory_used_mb ?? 0} MB
        </div>
        <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
          of {system.runtime?.memory_total_mb ?? 0} MB Total ({system.runtime?.memory_percent ?? 0}%)
        </span>
      </div>

      <div className={styles.telemetryCard}>
        <div className={styles.telemetryTitle}>Active Worker Pool</div>
        <div className={styles.telemetryValue}>
          {system.crawler_workers?.active_nodes ?? 2} Nodes
        </div>
        <span style={{ fontSize: '0.78rem', color: '#34d399' }}>
          {system.crawler_workers?.broker ?? 'Redis Queue'}
        </span>
      </div>
    </div>
  );
};
