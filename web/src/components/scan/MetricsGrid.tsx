"use client";

import React from 'react';
import { RiBug2Line } from 'react-icons/ri';
import { TbDeviceDesktop, TbClock, TbTestPipe } from 'react-icons/tb';
import { QAReport } from '../../types/qa';
import styles from '../../app/page.module.css';

interface MetricsGridProps {
  results: QAReport;
}

export const MetricsGrid: React.FC<MetricsGridProps> = ({ results }) => {
  const totalTestCases =
    results.qa_metrics?.test_cases?.total ?? results.test_cases?.length ?? 0;
  const passedTestCases = results.qa_metrics?.test_cases?.passed ?? 0;
  const failedTestCases = results.qa_metrics?.test_cases?.failed ?? 0;

  const totalFindings = results.findings?.length ?? 0;
  const confirmedBugs = results.qa_metrics?.findings?.confirmed_bugs ?? 0;

  const pagesCrawled = results.report_metadata?.pages_crawled ?? 1;
  const durationText =
    results.qa_metrics?.duration?.formatted_duration ?? '00:15s';

  return (
    <div className={styles.statsGrid}>
      <div className={styles.statCard}>
        <div className={styles.statHeader}>
          <span>Total Test Cases</span>
          <TbTestPipe size={20} color="#818cf8" />
        </div>
        <div className={styles.statValue}>{totalTestCases}</div>
        <div className={styles.statSub}>
          {passedTestCases} Passed · {failedTestCases} Failed
        </div>
      </div>

      <div className={styles.statCard}>
        <div className={styles.statHeader}>
          <span>Total Findings</span>
          <RiBug2Line size={20} color="#ef4444" />
        </div>
        <div className={styles.statValue}>{totalFindings}</div>
        <div className={styles.statSub}>
          {confirmedBugs} Confirmed {confirmedBugs === 1 ? 'Bug' : 'Bugs'}
        </div>
      </div>

      <div className={styles.statCard}>
        <div className={styles.statHeader}>
          <span>Pages & Devices</span>
          <TbDeviceDesktop size={20} color="#38bdf8" />
        </div>
        <div className={styles.statValue}>{pagesCrawled}</div>
        <div className={styles.statSub}>Desktop · iPhone 13 · iPad</div>
      </div>

      <div className={styles.statCard}>
        <div className={styles.statHeader}>
          <span>Execution Duration</span>
          <TbClock size={20} color="#34d399" />
        </div>
        <div className={styles.statValue}>{durationText}</div>
        <div className={styles.statSub}>Parallel worker pipeline</div>
      </div>
    </div>
  );
};
