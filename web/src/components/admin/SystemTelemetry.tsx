"use client";

import React from 'react';
import { RiCpuLine } from 'react-icons/ri';
import { TbCpu, TbDatabase, TbServer2 } from 'react-icons/tb';
import { Surface3D, type Tone } from '../three';
import a from './admin3d.module.css';

interface SystemTelemetryProps {
  system: {
    cluster_health?: string;
    timestamp?: string;
    runtime?: {
      platform?: string;
      environment?: string;
      cpu_utilization_percent?: number;
      memory_used_mb?: number;
      memory_total_mb?: number;
      memory_percent?: number;
    };
    crawler_workers?: {
      status?: string;
      active_nodes?: number;
      broker?: string;
      concurrency?: string;
    };
  } | null;
  /** Also show the runtime and worker details panel (cluster telemetry tab) */
  detail?: boolean;
}

const loadTone = (pct: number): Tone => (pct < 60 ? 'success' : pct < 85 ? 'warning' : 'danger');

const enterDelay = (step: number) =>
  ({ ['--enter-delay' as string]: `${step * 60}ms` }) as React.CSSProperties;

interface MeterProps {
  label: string;
  value: React.ReactNode;
  percent: number;
  tone: Tone;
  icon: React.ReactNode;
  hint: React.ReactNode;
  ariaLabel: string;
}

const Meter: React.FC<MeterProps> = ({ label, value, percent, tone, icon, hint, ariaLabel }) => {
  const fill = Math.round(Math.min(100, Math.max(0, percent)));
  return (
    <Surface3D tilt accent={tone} className={a.meter}>
      <div className={a.meterHead}>
        <div>
          <span className={a.meterLabel}>{label}</span>
          <span className={`stat-number stat-number--accent ${a.meterValue}`} data-depth="1">
            {value}
          </span>
        </div>
        <span className="icon-well" data-depth="2" aria-hidden="true">
          {icon}
        </span>
      </div>
      <div
        className={a.meterStage}
        role="meter"
        aria-label={ariaLabel}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={fill}
      >
        <div className={a.meterTrack}>
          <span className={a.meterFill} style={{ ['--fill' as string]: fill } as React.CSSProperties} />
        </div>
        <div className={a.meterTicks} aria-hidden="true">
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
      </div>
      <span className={a.meterHint}>{hint}</span>
    </Surface3D>
  );
};

export const SystemTelemetry: React.FC<SystemTelemetryProps> = ({ system, detail = false }) => {
  if (!system) return null;

  const cpu = system.runtime?.cpu_utilization_percent ?? 0;
  const memUsed = system.runtime?.memory_used_mb ?? 0;
  const memTotal = system.runtime?.memory_total_mb ?? 0;
  const memPct = system.runtime?.memory_percent ?? 0;
  const nodes = system.crawler_workers?.active_nodes ?? 2;
  const broker = system.crawler_workers?.broker ?? 'Redis Queue';
  const workersOnline = (system.crawler_workers?.status ?? 'online') === 'online';
  const health = system.cluster_health ?? 'operational';

  return (
    <div className={a.stack}>
      <div className="auto-grid" style={{ ['--grid-min' as string]: '240px' } as React.CSSProperties}>
        <div className="enter-3d" style={enterDelay(1)}>
          <Meter
            label="CPU Utilization"
            value={`${cpu}%`}
            percent={cpu}
            tone={loadTone(cpu)}
            icon={<TbCpu size={20} />}
            hint="Real-time host processor load"
            ariaLabel="CPU utilization"
          />
        </div>
        <div className="enter-3d" style={enterDelay(2)}>
          <Meter
            label="Memory Allocation"
            value={`${memUsed} MB`}
            percent={memPct}
            tone={loadTone(memPct)}
            icon={<TbDatabase size={20} />}
            hint={`of ${memTotal} MB total (${memPct}%)`}
            ariaLabel="Memory allocation"
          />
        </div>
        <div className="enter-3d" style={enterDelay(3)}>
          <Meter
            label="Active Worker Pool"
            value={`${nodes} Nodes`}
            percent={workersOnline ? 100 : 0}
            tone={workersOnline ? 'success' : 'danger'}
            icon={<TbServer2 size={20} />}
            hint={broker}
            ariaLabel="Worker pool availability"
          />
        </div>
      </div>

      {detail && (
        <Surface3D as="section" className="enter-3d" style={enterDelay(4)} aria-labelledby="telemetry-detail-title">
          <div className={a.panelHead}>
            <div className={a.panelTitleBlock}>
              <span className="icon-well" aria-hidden="true">
                <RiCpuLine size={20} />
              </span>
              <div>
                <span className="section-eyebrow">Cluster telemetry</span>
                <div className={a.panelTitleRow}>
                  <h2 id="telemetry-detail-title" className={a.panelTitle}>Runtime & worker health</h2>
                  <span className={`chip chip--dot ${health === 'operational' ? 'chip--success' : 'chip--warning'}`}>
                    {health}
                  </span>
                </div>
              </div>
            </div>
            {system.timestamp && (
              <span className={a.panelCount}>
                Sampled {new Date(system.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>

          <div className={a.panelBody}>
            <dl className={`surface-inset ${a.kvList}`}>
              <div className={a.kvRow}>
                <dt className={a.kvKey}>Platform</dt>
                <dd className={a.kvVal}>{system.runtime?.platform ?? 'JASUSS Engine'}</dd>
              </div>
              <div className={a.kvRow}>
                <dt className={a.kvKey}>Environment</dt>
                <dd className={a.kvVal}>{system.runtime?.environment ?? 'production'}</dd>
              </div>
              <div className={a.kvRow}>
                <dt className={a.kvKey}>Worker status</dt>
                <dd className={a.kvVal}>
                  <span className={`chip chip--sm ${workersOnline ? 'chip--success chip--live' : 'chip--danger chip--dot'}`}>
                    {system.crawler_workers?.status ?? 'online'}
                  </span>
                </dd>
              </div>
              <div className={a.kvRow}>
                <dt className={a.kvKey}>Queue broker</dt>
                <dd className={a.kvVal}>{broker}</dd>
              </div>
              <div className={a.kvRow}>
                <dt className={a.kvKey}>Concurrency</dt>
                <dd className={a.kvVal}>{system.crawler_workers?.concurrency ?? 'Multi-Process Chromium Viewports'}</dd>
              </div>
              <div className={a.kvRow}>
                <dt className={a.kvKey}>Memory</dt>
                <dd className={a.kvVal}>
                  {memUsed} MB / {memTotal} MB
                </dd>
              </div>
            </dl>
          </div>
        </Surface3D>
      )}
    </div>
  );
};
