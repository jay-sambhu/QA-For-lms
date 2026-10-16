"use client";

import React from 'react';
import { RiAwardFill } from 'react-icons/ri';
import { ScoreGauge3D, Surface3D, cx, scoreTone } from '../three';
import s from './scan3d.module.css';

interface QualityScoreCardProps {
  score: number;
  letterGrade: string;
  verdict: string;
  className?: string;
  style?: React.CSSProperties;
}

export const QualityScoreCard: React.FC<QualityScoreCardProps> = ({
  score,
  letterGrade,
  verdict,
  className,
  style,
}) => {
  const isHighQuality = score >= 80;
  const isModerateQuality = score >= 60;
  const tone = scoreTone(score);

  return (
    <Surface3D ring pad="lg" className={className} style={style} aria-labelledby="quality-score-title">
      <div className={s.scorePanel}>
        <ScoreGauge3D score={score} grade={letterGrade} label="Quality score" />

        <div className={s.scoreCopy}>
          <span className={cx('chip', `chip--${tone}`, s.wrapChip)}>
            <RiAwardFill size={15} /> {verdict}
          </span>
          <h2 id="quality-score-title" className={s.scoreTitle}>
            {isHighQuality
              ? 'High Software Quality & Reliability'
              : isModerateQuality
              ? 'Quality Anomalies Detected - Review Advised'
              : 'Remediation Required Before Release'}
          </h2>
          <p className={s.scoreDesc}>
            {isHighQuality
              ? 'Target web application successfully passed multi-viewport assertions, layout stability checks, and synthetic user journeys with zero critical runtime exceptions.'
              : isModerateQuality
              ? 'Discovered non-blocking UI anomalies, minor console errors, or responsive padding issues across test viewports.'
              : 'Discovered high-severity defects, unhandled network failures, or layout breaking bugs that require immediate engineering attention.'}
          </p>
        </div>
      </div>
    </Surface3D>
  );
};
