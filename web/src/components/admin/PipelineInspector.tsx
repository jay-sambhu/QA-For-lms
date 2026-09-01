"use client";

import React from 'react';
import styles from '../../app/page.module.css';

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

export const PipelineInspector: React.FC<PipelineInspectorProps> = ({ scans }) => {
  return (
    <div className={styles.adminTableCard}>
      <div className={styles.adminTableCardTitle}>
        <span>Global Scan Pipeline Inspector</span>
        <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 500 }}>
          Showing {scans.length} scans
        </span>
      </div>

      <div className={styles.adminTableContainer}>
        <table className={styles.adminTable}>
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
                <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: '#94a3b8' }}>
                  {s.id.substring(0, 8)}...
                </td>
                <td style={{ maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <span style={{ color: '#f8fafc', fontWeight: 500 }}>{s.url}</span>
                </td>
                <td>
                  <span
                    className={styles.severityBadge}
                    style={{
                      background:
                        s.status === 'completed'
                          ? 'rgba(16, 185, 129, 0.15)'
                          : s.status === 'failed'
                          ? 'rgba(239, 68, 68, 0.15)'
                          : 'rgba(99, 102, 241, 0.15)',
                      color:
                        s.status === 'completed'
                          ? '#34d399'
                          : s.status === 'failed'
                          ? '#f87171'
                          : '#818cf8',
                    }}
                  >
                    {s.status.toUpperCase()}
                  </span>
                </td>
                <td>{s.is_authenticated ? '🔒 Yes' : 'No'}</td>
                <td>{s.created_at ? new Date(s.created_at).toLocaleTimeString() : 'N/A'}</td>
              </tr>
            ))}
            {scans.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
                  No scans recorded in pipeline yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
