"use client";

import React from 'react';
import { TbActivity, TbLock, TbLockOpen } from 'react-icons/tb';
import { Surface3D, EmptyState3D } from '../three';
import a from './admin3d.module.css';

interface PipelineInspectorProps {
  scans: Array<{
    id: string;
    user_id: string;
    url: string;
    status: string;
    is_authenticated?: boolean;
    created_at?: string;
    completed_at?: string;
  }>;
}

const statusChip = (status: string) => {
  const s = (status || '').toLowerCase();
  if (s === 'completed') return 'chip chip--sm chip--success chip--dot';
  if (s === 'failed' || s === 'error') return 'chip chip--sm chip--danger chip--dot';
  if (s === 'cancelled') return 'chip chip--sm chip--neutral';
  if (s === 'timeout' || s === 'stalled') return 'chip chip--sm chip--warning chip--dot';
  return 'chip chip--sm chip--info chip--live';
};

const STAGES: { id: string; label: string; tone: string; match: (s: string) => boolean }[] = [
  { id: 'queued', label: 'Queued', tone: 'tone-neutral', match: (s) => s === 'pending' || s === 'queued' },
  { id: 'running', label: 'Running', tone: 'tone-info', match: (s) => s === 'running' || s === 'in_progress' },
  { id: 'completed', label: 'Completed', tone: 'tone-success', match: (s) => s === 'completed' },
  { id: 'failed', label: 'Failed', tone: 'tone-danger', match: (s) => s === 'failed' || s === 'error' || s === 'timeout' },
];

export const PipelineInspector: React.FC<PipelineInspectorProps> = ({ scans }) => {
  const total = scans.length;
  const stageCounts = STAGES.map((stage) => ({
    ...stage,
    count: scans.filter((s) => stage.match((s.status || '').toLowerCase())).length,
  }));

  return (
    <Surface3D as="section" pad="sm" aria-labelledby="pipeline-title">
      <div className={`${a.panelHead} ${a.panelHeadTable}`}>
        <div className={a.panelTitleBlock}>
          <span className="icon-well" aria-hidden="true">
            <TbActivity size={20} />
          </span>
          <div>
            <span className="section-eyebrow">Global pipeline</span>
            <div className={a.panelTitleRow}>
              <h2 id="pipeline-title" className={a.panelTitle}>Scan Pipeline Inspector</h2>
              <span className={a.panelCount}>Showing {scans.length} scans</span>
            </div>
          </div>
        </div>
      </div>

      <div className={a.stageRail} aria-label="Pipeline stages">
        {stageCounts.map((stage, i) => (
          <div
            key={stage.id}
            className={`${a.stage} ${stage.tone}`}
            style={{ ['--enter-delay' as string]: `${i * 60}ms` } as React.CSSProperties}
          >
            <span className={a.stageLabel}>{stage.label}</span>
            <span className={a.stageCount}>{stage.count}</span>
            <span className={a.stageShare}>
              {total > 0 ? `${Math.round((stage.count / total) * 100)}% of shown` : 'No scans yet'}
            </span>
          </div>
        ))}
      </div>

      <div className="table-3d-wrap" style={{ ['--table-max-h' as string]: '560px' } as React.CSSProperties}>
        <table className="table-3d">
          <thead>
            <tr>
              <th>Scan ID</th>
              <th>Target Website URL</th>
              <th>Status</th>
              <th>Auth Mode</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {scans.map((s) => (
              <tr key={s.id}>
                <td className={`${a.idCell} ${a.mono}`}>{s.id.substring(0, 8)}...</td>
                <td className={a.urlCell} title={s.url}>{s.url}</td>
                <td>
                  <span className={statusChip(s.status)}>{s.status.toUpperCase()}</span>
                </td>
                <td>
                  <span className={`chip chip--sm ${s.is_authenticated ? 'chip--violet' : 'chip--neutral'}`}>
                    {s.is_authenticated ? <TbLock size={12} /> : <TbLockOpen size={12} />}
                    {s.is_authenticated ? 'Yes' : 'No'}
                  </span>
                </td>
                <td className={a.metaCell}>{s.created_at ? new Date(s.created_at).toLocaleTimeString() : 'N/A'}</td>
              </tr>
            ))}
            {scans.length === 0 && (
              <tr>
                <td colSpan={5}>
                  <EmptyState3D
                    compact
                    icon={<TbActivity size={16} />}
                    title="No scans recorded in pipeline yet"
                    description="Runs launched by any tenant will appear here in real time."
                  />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Surface3D>
  );
};
