"use client";

import React, { useMemo } from 'react';
import { RiGlobalLine, RiStopCircleFill, RiCheckDoubleFill, RiTerminalBoxLine } from 'react-icons/ri';
import {
  TbWorldSearch,
  TbSitemap,
  TbListCheck,
  TbWand,
  TbBolt,
  TbShieldCheck,
  TbBug,
  TbGitCompare,
  TbAward,
  TbClock,
  TbBroadcast,
} from 'react-icons/tb';
import { DeviceDeck } from './DeviceDeck';
import { ProgressPayload } from '../../types/qa';
import { cx } from '../three';
import s from './scan3d.module.css';

interface ScanMonitorProps {
  url: string;
  progress: ProgressPayload | null;
  elapsedSeconds: number;
  logFeed: string[];
  maxPages?: number;
  onStop: () => void;
}

const PIPELINE = [
  { id: 'DISCOVERING', label: 'Discover', icon: <TbWorldSearch size={16} /> },
  { id: 'MODELING', label: 'Model', icon: <TbSitemap size={16} /> },
  { id: 'PLANNING', label: 'Plan', icon: <TbListCheck size={16} /> },
  { id: 'GENERATING', label: 'Generate', icon: <TbWand size={16} /> },
  { id: 'EXECUTING', label: 'Execute', icon: <TbBolt size={16} /> },
  { id: 'VERIFYING', label: 'Verify', icon: <TbShieldCheck size={16} /> },
  { id: 'TRIAGING', label: 'Triage', icon: <TbBug size={16} /> },
  { id: 'REGRESSION', label: 'Regression', icon: <TbGitCompare size={16} /> },
  { id: 'SCORING', label: 'Score', icon: <TbAward size={16} /> },
] as const;

const PHASES = [
  'Stage 1: Multi-Device Crawling',
  'Stage 2: Interactive Testing',
  'Stage 3: Defect Detection',
  'Stage 4: Quality Synthesis',
];

const titleCase = (value: string) =>
  value
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

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
    const stage = progress?.stage?.toUpperCase();
    if (stage === 'DISCOVERING' || stage === 'CREATED') return 0;
    if (stage === 'MODELING' || stage === 'PLANNING' || stage === 'GENERATING') return 1;
    if (stage === 'EXECUTING') return 2;
    if (
      stage === 'VERIFYING' ||
      stage === 'TRIAGING' ||
      stage === 'REGRESSION' ||
      stage === 'SCORING' ||
      stage === 'COMPLETED'
    )
      return 3;

    const pct = progress?.percent || 0;
    if (pct < 35) return 0;
    if (pct < 55) return 1;
    if (pct < 75) return 2;
    return 3;
  }, [progress?.stage, progress?.percent]);

  const pipelineIndex = useMemo(() => {
    const stage = progress?.stage?.toUpperCase();
    if (stage === 'CREATED') return 0;
    if (stage === 'COMPLETED') return PIPELINE.length;
    const known = PIPELINE.findIndex((p) => p.id === stage);
    if (known >= 0) return known;
    const pct = Math.max(0, Math.min(100, progress?.percent || 0));
    return Math.min(PIPELINE.length - 1, Math.floor((pct / 100) * PIPELINE.length));
  }, [progress?.stage, progress?.percent]);

  const activeDeviceName = useMemo(() => {
    if (progress?.active_device) return progress.active_device;
    const msg = progress?.message || '';
    if (msg.includes('iPhone')) return 'iPhone 13';
    if (msg.includes('iPad')) return 'iPad (gen 7)';
    if (msg.includes('Desktop')) return 'Desktop Chrome';
    return 'Desktop Chrome';
  }, [progress?.active_device, progress?.message]);

  const percent = Math.max(0, Math.min(100, progress?.percent || 5));
  const stageLabel = progress?.stage ? titleCase(progress.stage) : PHASES[currentStageIndex];
  const pageLabel = progress?.page_current
    ? `Page ${progress.page_current} of ${progress.page_total || maxPages}`
    : PHASES[currentStageIndex];
  const allDone = pipelineIndex >= PIPELINE.length;

  return (
    <div className={s.monitor}>
      <div className={s.monitorHead}>
        <div className={s.target}>
          <span className="icon-well" aria-hidden="true">
            <RiGlobalLine size={20} />
          </span>
          <div className={s.targetCopy}>
            <span className="section-eyebrow">Inspecting target</span>
            <span className={cx(s.targetUrl, s.truncate)} title={url}>
              {url}
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={onStop}
          className="btn btn-danger btn-sm"
          title="Stop and cancel the active scan"
        >
          <RiStopCircleFill size={16} />
          <span>Stop Scan</span>
        </button>
      </div>

      <div className={s.readout}>
        <span className={cx('stat-number stat-number--accent', s.readoutPct)}>{percent}%</span>
        <div className={s.readoutMeta}>
          <span className="chip chip--info chip--live">{stageLabel}</span>
          <span className={s.readoutNumbers}>{pageLabel}</span>
          <span className={cx('chip chip--neutral', s.mono, s.readoutElapsed)}>
            <TbClock size={13} /> {formattedTime}
          </span>
        </div>
        <div
          className={s.progressTrack}
          role="progressbar"
          aria-label="Scan progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <span className={s.progressFill} style={{ ['--p' as string]: percent / 100 } as React.CSSProperties} />
        </div>
        <p className={s.currentMessage} aria-live="polite">
          {progress?.message || 'Inspecting DOM tree and verifying response status...'}
        </p>
      </div>

      <div className={s.pipeline}>
        <div className={s.pipelineHead}>
          <span className="section-eyebrow">
            <TbBolt size={14} /> Autonomous pipeline
          </span>
          <span className={s.readoutNumbers}>
            {allDone ? 'All stages complete' : `${Math.min(pipelineIndex + 1, PIPELINE.length)} of ${PIPELINE.length} stages`}
          </span>
        </div>
        <div className={s.pipelineStage}>
          <ol className={cx(s.pipeTrack, allDone && s.pipeDoneAll)} aria-label="Pipeline stages">
            {PIPELINE.map((st, i) => {
              const isDone = i < pipelineIndex;
              const isActive = i === pipelineIndex;
              return (
                <li
                  key={st.id}
                  className={cx(s.pipeBlock, isDone && s.pipeDone, isActive && s.pipeActive)}
                  aria-current={isActive ? 'step' : undefined}
                >
                  <span className={s.pipeSide} aria-hidden="true" />
                  <span className={s.pipeFace}>
                    <span className={s.pipeIcon} aria-hidden="true">
                      {isDone ? <RiCheckDoubleFill size={16} /> : st.icon}
                    </span>
                    <span className={s.pipeLabel}>{st.label}</span>
                    <span className={s.pipeStep}>
                      0{i + 1}
                      <span className="sr-only">{isDone ? ' complete' : isActive ? ' in progress' : ' pending'}</span>
                    </span>
                  </span>
                </li>
              );
            })}
          </ol>
        </div>
      </div>

      <DeviceDeck activeDeviceName={activeDeviceName} activeUrl={progress?.active_url} defaultUrl={url} />

      <div className={cx('surface-inset', s.terminal)}>
        <div className={s.terminalHead}>
          <span className="section-eyebrow">
            <RiTerminalBoxLine size={14} /> Live diagnostic telemetry
          </span>
          <span className="chip chip--sm chip--success chip--live">
            <TbBroadcast size={12} /> Streaming
          </span>
        </div>
        <div className={cx(s.terminalBody, s.mono)}>
          {logFeed.map((log, lIdx) => (
            <div key={lIdx} className={s.terminalLine}>
              <span className={s.terminalPrompt}>&gt;</span>
              <span>{log}</span>
            </div>
          ))}
          <div className={s.terminalLine}>
            <span className={s.terminalPrompt}>&gt;</span>
            <span className={s.terminalLive}>
              {progress?.message || 'Inspecting DOM tree and verifying response status...'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
