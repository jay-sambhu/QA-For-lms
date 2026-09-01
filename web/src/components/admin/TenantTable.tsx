"use client";

import React from 'react';
import styles from '../../app/page.module.css';

interface TenantTableProps {
  users: Array<{
    id: string;
    email: string;
    role: string;
    plan_tier: string;
    scans_count: number;
    created_at?: string;
  }>;
}

export const TenantTable: React.FC<TenantTableProps> = ({ users }) => {
  return (
    <div className={styles.adminTableCard}>
      <div className={styles.adminTableCardTitle}>
        <span>Registered Platform Tenants & Subscribers</span>
        <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 500 }}>
          Showing {users.length} users
        </span>
      </div>

      <div className={styles.adminTableContainer}>
        <table className={styles.adminTable}>
          <thead>
            <tr>
              <th>User ID</th>
              <th>Email Address</th>
              <th>Plan Tier</th>
              <th>Total Scans</th>
              <th>Role</th>
              <th>Joined Date</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: '#818cf8' }}>
                  {u.id.substring(0, 8)}...
                </td>
                <td>{u.email}</td>
                <td>
                  <span
                    className={`${styles.tierPill} ${
                      u.plan_tier === 'pro'
                        ? styles.tierPro
                        : u.plan_tier === 'enterprise'
                        ? styles.tierEnterprise
                        : styles.tierFree
                    }`}
                  >
                    {u.plan_tier || 'FREE'}
                  </span>
                </td>
                <td>{u.scans_count} scans</td>
                <td style={{ textTransform: 'capitalize' }}>{u.role}</td>
                <td>{u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}</td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
                  No users recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
