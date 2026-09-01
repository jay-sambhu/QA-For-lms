"use client";

import React, { useMemo } from 'react';
import {
  RiGlobalLine,
  RiStopCircleFill,
  RiCheckDoubleFill,
  RiBug2Line,
  RiTerminalBoxLine,
} from 'react-icons/ri';
import {
  TbDeviceDesktop,
  TbBolt,
  TbSparkles,
  TbClock,
  TbLoader2,
  TbBroadcast,
} from 'react-icons/tb';
import { DeviceDeck } from './DeviceDeck';
import { ProgressPayload } from '../../types/qa';
import styles from '../../app/page.module.css';

interface ScanMonitorProps {
  url: string;
  progress: ProgressPayload | null;
  elapsedSeconds: number;
  logFeed: string[];
  maxPages?: number;
  onStop: () => void;
}

export const ScanMonitor: React.FC<ScanMonitorProps> = ({
  url,
  progress,
  elapsedSeconds,
  logFeed,
  maxPages = 10,
  onStop,
}) => {
  const formattedTime = useMemo(() => {
    const mins = Math.floor(elapsedSeconds / 60);
    const secs = elapsedSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, [elapsedSeconds]);

  const currentStageIndex = useMemo(() => {
    const pct = progress?.percent || 0;
    if (pct < 35) return 0;
    if (pct < 60) return 1;
    if (pct < 75) return 2;
    return 3;
  }, [progress?.percent]);

  const activeDeviceName = useMemo(() => {
    if (progress?.active_device) return progress.active_device;
    const msg = progress?.message || '';
    if (msg.includes('iPhone')) return 'iPhone 13';
    if (msg.includes('iPad')) return 'iPad (gen 7)';
    if (msg.includes('Desktop')) return 'Desktop Chrome';
    return 'Desktop Chrome';
  }, [progress?.active_device, progress?.message]);

  const stages = [
    {
      step: 1,
      title: 'Multi-Device Crawl',
      desc: 'Desktop, iPhone 13, iPad viewports',
      icon: <TbDeviceDesktop size={18} />,
    },
    {
      step: 2,
      title: 'Interactive Testing',
      desc: 'Forms, clicks, state transitions',
      icon: <TbBolt size={18} />,
    },
    {
      step: 3,
      title: 'Defect Detection',
      desc: 'Network errors, console, layout',
      icon: <RiBug2Line size={18} />,
    },
    {
      step: 4,
      title: 'Quality Synthesis',
      desc: 'Compliance grading & executive report',
      icon: <TbSparkles size={18} />,
    },
  ];

  return (
    <div className={styles.loadingScreen}>
      <div className={styles.loadingHeader}>
        <div className={styles.loadingControlBar}>
          <div className={styles.targetUrlBadge}>
            <RiGlobalLine size={16} />
            <span>Inspecting Target: {url}</span>
          </div>

          <button
            type="button"
            onClick={onStop}
            className={styles.stopScanBtn}
            title="Stop and cancel the active scan"
          >
            <RiStopCircleFill size={16} color="#ef4444" />
            <span>Stop Scan</span>
          </button>
        </div>

        <h2 style={{ fontSize: '1.8rem', fontWeight: 700, color: '#f8fafc', marginTop: '8px' }}>
          Automated Test Execution Running
        </h2>
        <p style={{ color: '#94a3b8', fontSize: '0.94rem' }}>
          Executing multi-viewport crawler, synthetic user journeys, and defect analysis in parallel.
        </p>
      </div>

      {/* Progress Bar Track */}
      <div className={styles.progressBarWrapper}>
        <div className={styles.progressInfoRow}>
          <span className={styles.progressStageBadge}>
            {progress?.stage
              ? progress.stage.replace('_', ' ')
              : currentStageIndex === 0
              ? 'Stage 1: Multi-Device Crawling'
              : currentStageIndex === 1
              ? 'Stage 2: Interactive Testing'
              : currentStageIndex === 2
              ? 'Stage 3: Defect Detection'
              : 'Stage 4: Quality Synthesis'}
          </span>
          <span className={styles.progressNumbers}>
            {progress?.page_current
              ? `Page ${progress.page_current} of ${progress.page_total || maxPages} (${progress.percent}%)`
              : `${progress?.percent || 5}% Complete`}
          </span>
        </div>
        <div className={styles.progressBarTrack}>
          <div className={styles.progressBarFill} style={{ width: `${progress?.percent || 5}%` }} />
        </div>
      </div>

      {/* Glowing Radar Pulse */}
      <div className={styles.radarContainer}>
        <div className={styles.radarOuterRing} />
        <div className={styles.radarInnerRing} />
        <div className={styles.radarSweep} />
        <div className={styles.radarCenterContent}>
          <span className={styles.radarPercent}>{progress?.percent || 5}%</span>
          <span className={styles.radarElapsed}>
            <TbClock size={12} style={{ display: 'inline', marginRight: '3px' }} />
            {formattedTime}
          </span>
        </div>
      </div>

      {/* Live Device Deck */}
      <DeviceDeck
        activeDeviceName={activeDeviceName}
        activeUrl={progress?.active_url}
        defaultUrl={url}
      />

      {/* 4-Stage Stepper Grid */}
      <div className={styles.stepperGrid}>
        {stages.map((st, sIdx) => {
          const isActive = sIdx === currentStageIndex;
          const isDone = sIdx < currentStageIndex;

          return (
            <div
              key={st.step}
              className={`${styles.stepCard} ${
                isActive ? styles.stepActive : isDone ? styles.stepCompleted : ''
              }`}
            >
              <div className={styles.stepHeader}>
                <span className={styles.stepNumber}>Stage 0{st.step}</span>
                {isDone ? (
                  <RiCheckDoubleFill size={18} color="#34d399" />
                ) : isActive ? (
                  <TbLoader2 size={18} className="pulse" color="#818cf8" />
                ) : (
                  <span style={{ color: '#475569' }}>{st.icon}</span>
                )}
              </div>
              <div className={styles.stepTitle}>{st.title}</div>
              <div className={styles.stepDesc}>{st.desc}</div>
            </div>
          );
        })}
      </div>

      {/* Monospace Terminal */}
      <div className={styles.terminalCard}>
        <div className={styles.terminalHeader}>
          <div className={styles.terminalDots}>
            <div className={styles.terminalDot} style={{ background: '#ef4444' }} />
            <div className={styles.terminalDot} style={{ background: '#f59e0b' }} />
            <div className={styles.terminalDot} style={{ background: '#10b981' }} />
          </div>
          <div className={styles.terminalTitle}>
            <RiTerminalBoxLine size={16} /> LIVE DIAGNOSTIC TELEMETRY STREAM
          </div>
          <div style={{ fontSize: '0.75rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <TbBroadcast size={14} /> STREAMING ●
          </div>
        </div>

        <div className={styles.terminalBody}>
          {logFeed.map((log, lIdx) => (
            <div key={lIdx} className={styles.terminalLine}>
              <span className={styles.terminalPrompt}>&gt;</span>
              <span>{log}</span>
            </div>
          ))}
          <div className={styles.terminalLine}>
            <span className={styles.terminalPrompt}>&gt;</span>
            <span className={styles.terminalCurrentMessage}>
              {progress?.message || 'Inspecting DOM tree and verifying response status...'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
