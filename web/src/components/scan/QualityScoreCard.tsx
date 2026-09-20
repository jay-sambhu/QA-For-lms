"use client";

import React from 'react';
import { RiAwardFill } from 'react-icons/ri';
import styles from '../../app/page.module.css';

interface QualityScoreCardProps {
  score: number;
  letterGrade: string;
  verdict: string;
}

export const QualityScoreCard: React.FC<QualityScoreCardProps> = ({
  score,
  letterGrade,
  verdict,
}) => {
  const isHighQuality = score >= 80;
  const isModerateQuality = score >= 60;

  const strokeColor = isHighQuality ? '#10b981' : isModerateQuality ? '#f59e0b' : '#ef4444';
  const badgeBg = isHighQuality
    ? 'rgba(16, 185, 129, 0.15)'
    : isModerateQuality
    ? 'rgba(245, 158, 11, 0.15)'
    : 'rgba(239, 68, 68, 0.15)';
  const badgeColor = isHighQuality ? '#34d399' : isModerateQuality ? '#fbbf24' : '#f87171';
  const badgeBorder = `1px solid ${
    isHighQuality
      ? 'rgba(16, 185, 129, 0.35)'
      : isModerateQuality
      ? 'rgba(245, 158, 11, 0.35)'
      : 'rgba(239, 68, 68, 0.35)'
  }`;

  return (
    <div className={styles.scoreCard}>
      <div className={styles.scoreDialContainer}>
        <div className={styles.scoreCircleWrapper}>
          <svg width="130" height="130" viewBox="0 0 130 130">
            <circle
              cx="65"
              cy="65"
              r="54"
              fill="none"
              stroke="rgba(255, 255, 255, 0.08)"
              strokeWidth="10"
            />
            <circle
              cx="65"
              cy="65"
              r="54"
              fill="none"
              stroke={strokeColor}
              strokeWidth="10"
              strokeDasharray="339.29"
              strokeDashoffset={339.29 - (339.29 * score) / 100}
              strokeLinecap="round"
              transform="rotate(-90 65 65)"
              style={{ transition: 'stroke-dashoffset 1s ease-out' }}
            />
          </svg>
          <div className={styles.scoreCircleCenter}>
            <span className={styles.scoreNumber}>{score}</span>
            <span className={styles.scoreGradePill}>{letterGrade}</span>
          </div>
        </div>
      </div>

      <div className={styles.scoreDetails}>
        <div
          className={styles.scoreVerdictBadge}
          style={{
            background: badgeBg,
            color: badgeColor,
            border: badgeBorder,
          }}
        >
          <RiAwardFill size={15} /> {verdict}
        </div>
        <div className={styles.scoreTitle}>
          {isHighQuality
            ? 'High Software Quality & Reliability'
            : isModerateQuality
            ? 'Quality Anomalies Detected - Review Advised'
            : 'Remediation Required Before Release'}
        </div>
        <div className={styles.scoreDescription}>
          {isHighQuality
            ? 'Target web application successfully passed multi-viewport assertions, layout stability checks, and synthetic user journeys with zero critical runtime exceptions.'
            : isModerateQuality
            ? 'Discovered non-blocking UI anomalies, minor console errors, or responsive padding issues across test viewports.'
            : 'Discovered high-severity defects, unhandled network failures, or layout breaking bugs that require immediate engineering attention.'}
        </div>
      </div>
    </div>
  );
};
