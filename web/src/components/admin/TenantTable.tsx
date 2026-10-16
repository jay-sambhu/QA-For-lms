"use client";

import React, { useState } from 'react';
import { RiShieldUserFill, RiUser3Line, RiCheckLine, RiErrorWarningFill } from 'react-icons/ri';
import { TbLoader2, TbUsers } from 'react-icons/tb';
import { Surface3D, EmptyState3D } from '../three';
import a from './admin3d.module.css';

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

const tierChip = (tier?: string) => {
  if (tier === 'pro') return 'chip chip--sm chip--primary';
  if (tier === 'enterprise') return 'chip chip--sm chip--violet';
  return 'chip chip--sm chip--neutral';
};

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

  const adminCount = localUsers.filter((u) => u.role === 'admin').length;

  return (
    <Surface3D as="section" pad="sm" aria-labelledby="tenants-title">
      <div className={`${a.panelHead} ${a.panelHeadTable}`}>
        <div className={a.panelTitleBlock}>
          <span className="icon-well" aria-hidden="true">
            <TbUsers size={20} />
          </span>
          <div>
            <span className="section-eyebrow">Role governance</span>
            <div className={a.panelTitleRow}>
              <h2 id="tenants-title" className={a.panelTitle}>Registered Platform Tenants</h2>
              <span className="chip chip--sm chip--violet chip--dot">{adminCount} admins</span>
            </div>
          </div>
        </div>
        <span className={a.panelCount}>{localUsers.length} total users in database</span>
      </div>

      {errorMsg && (
        <div className={`${a.notice} ${a.noticeDanger}`} role="alert" style={{ margin: '0 8px 12px' }}>
          <RiErrorWarningFill size={18} />
          {errorMsg}
        </div>
      )}

      <div className="table-3d-wrap" style={{ ['--table-max-h' as string]: '640px' } as React.CSSProperties}>
        <table className="table-3d">
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
                  <td className={`${a.idCell} ${a.mono}`}>{u.id.substring(0, 8)}...</td>
                  <td className={a.emailCell} title={u.email}>{u.email}</td>
                  <td>
                    <span className={tierChip(u.plan_tier)}>{u.plan_tier?.toUpperCase() || 'FREE'}</span>
                  </td>
                  <td>{u.scans_count} scans</td>
                  <td>
                    <span className={`chip chip--sm ${isAdmin ? 'chip--violet chip--solid' : 'chip--neutral'}`}>
                      {isAdmin ? <RiShieldUserFill size={12} /> : <RiUser3Line size={12} />}
                      {u.role.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <div className={a.rowActions}>
                      <button
                        type="button"
                        disabled={isUpdating}
                        onClick={() => handleRoleChange(u.id, isAdmin ? 'user' : 'admin')}
                        className={`btn btn-sm ${isAdmin ? 'btn-danger' : 'btn-primary'}`}
                      >
                        {isUpdating ? (
                          <>
                            <TbLoader2 size={13} className="pulse" />
                            Updating...
                          </>
                        ) : isSuccess ? (
                          <>
                            <RiCheckLine size={14} />
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
                  <td className={a.metaCell}>{u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}</td>
                </tr>
              );
            })}
            {localUsers.length === 0 && (
              <tr>
                <td colSpan={7}>
                  <EmptyState3D
                    compact
                    icon={<TbUsers size={16} />}
                    title="No users recorded yet"
                    description="Tenants appear here as soon as they sign up."
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
