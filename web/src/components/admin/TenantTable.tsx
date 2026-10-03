"use client";

import React, { useState } from 'react';
import { RiShieldUserFill, RiUser3Line, RiCheckLine } from 'react-icons/ri';
import { TbLoader2 } from 'react-icons/tb';
import styles from '../../app/page.module.css';

interface UserItem {
  id: string;
  email: string;
  role: string;
  plan_tier: string;
  scans_count: number;
  created_at?: string;
}

interface TenantTableProps {
  users: UserItem[];
  sessionToken?: string;
  onRoleUpdated?: () => void;
}

export const TenantTable: React.FC<TenantTableProps> = ({ users, sessionToken, onRoleUpdated }) => {
  const [localUsers, setLocalUsers] = useState<UserItem[]>(users);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [successId, setSuccessId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Sync if parent updates users
  React.useEffect(() => {
    setLocalUsers(users);
  }, [users]);

  const handleRoleChange = async (userId: string, targetRole: 'user' | 'admin') => {
    if (!sessionToken) return;
    setUpdatingId(userId);
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/v1/admin/users/${userId}/role`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({ role: targetRole }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to update user role');
      }
      setLocalUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: targetRole } : u))
      );
      setSuccessId(userId);
      setTimeout(() => setSuccessId(null), 2500);
      onRoleUpdated?.();
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Error updating role');
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className={styles.adminTableCard}>
      <div className={styles.adminTableCardTitle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <RiShieldUserFill size={20} color="#818cf8" />
          <span>Registered Platform Tenants & Role Governance</span>
        </div>
        <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 500 }}>
          {localUsers.length} total users in database
        </span>
      </div>

      {errorMsg && (
        <div style={{ margin: '12px 20px', padding: '10px 14px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '10px', color: '#f87171', fontSize: '0.85rem' }}>
          {errorMsg}
        </div>
      )}

      <div className={styles.adminTableContainer}>
        <table className={styles.adminTable}>
          <thead>
            <tr>
              <th>User ID</th>
              <th>Email Address</th>
              <th>Plan Tier</th>
              <th>Total Scans</th>
              <th>Platform Role</th>
              <th>Change Role</th>
              <th>Joined Date</th>
            </tr>
          </thead>
          <tbody>
            {localUsers.map((u) => {
              const isAdmin = u.role === 'admin';
              const isUpdating = updatingId === u.id;
              const isSuccess = successId === u.id;

              return (
                <tr key={u.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: '#818cf8' }}>
                    {u.id.substring(0, 8)}...
                  </td>
                  <td>
                    <span style={{ color: '#f8fafc', fontWeight: 600 }}>{u.email}</span>
                  </td>
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
                      {u.plan_tier?.toUpperCase() || 'FREE'}
                    </span>
                  </td>
                  <td>
                    <span style={{ color: '#cbd5e1' }}>{u.scans_count} scans</span>
                  </td>
                  <td>
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '3px 10px',
                        borderRadius: '999px',
                        fontSize: '0.74rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        background: isAdmin ? 'rgba(168, 85, 247, 0.18)' : 'rgba(148, 163, 184, 0.14)',
                        color: isAdmin ? '#c084fc' : '#94a3b8',
                        border: `1px solid ${isAdmin ? 'rgba(168, 85, 247, 0.35)' : 'rgba(148, 163, 184, 0.2)'}`,
                      }}
                    >
                      {isAdmin ? <RiShieldUserFill size={13} /> : <RiUser3Line size={13} />}
                      {u.role}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <button
                        type="button"
                        disabled={isUpdating}
                        onClick={() => handleRoleChange(u.id, isAdmin ? 'user' : 'admin')}
                        style={{
                          padding: '5px 12px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          borderRadius: '8px',
                          background: isAdmin ? 'rgba(239, 68, 68, 0.1)' : 'rgba(99, 102, 241, 0.15)',
                          color: isAdmin ? '#f87171' : '#818cf8',
                          border: `1px solid ${isAdmin ? 'rgba(239, 68, 68, 0.25)' : 'rgba(99, 102, 241, 0.35)'}`,
                          cursor: isUpdating ? 'not-allowed' : 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          transition: 'all 0.2s ease',
                        }}
                      >
                        {isUpdating ? (
                          <>
                            <TbLoader2 size={13} className="pulse" />
                            Updating...
                          </>
                        ) : isSuccess ? (
                          <>
                            <RiCheckLine size={14} color="#10b981" />
                            Saved
                          </>
                        ) : isAdmin ? (
                          'Demote to User'
                        ) : (
                          'Promote to Admin'
                        )}
                      </button>
                    </div>
                  </td>
                  <td>{u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}</td>
                </tr>
              );
            })}
            {localUsers.length === 0 && (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: '#94a3b8' }}>
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
