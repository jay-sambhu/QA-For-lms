"use client";

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { RiRefreshLine, RiShieldUserFill, RiLockPasswordFill } from 'react-icons/ri';
import { TbLoader2, TbArrowLeft } from 'react-icons/tb';
import { useAuth } from '../context/AuthContext';
import { AdminMetrics } from '../components/admin/AdminMetrics';
import { TenantTable } from '../components/admin/TenantTable';
import { PipelineInspector } from '../components/admin/PipelineInspector';
import { SystemTelemetry } from '../components/admin/SystemTelemetry';
import { AIProviderConfig } from '../components/admin/AIProviderConfig';
import styles from '../app/page.module.css';

export const AdminPage: React.FC = () => {
  const { session, sessionLoaded, userRole, openAuthModal } = useAuth();
  const [metrics, setMetrics] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [scans, setScans] = useState<any[]>([]);
  const [system, setSystem] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchAdminData = useCallback(async () => {
    setLoading(true);
    try {
      const [mRes, uRes, sRes, sysRes] = await Promise.all([
        fetch('/api/v1/admin/metrics'),
        fetch('/api/v1/admin/users'),
        fetch('/api/v1/admin/scans'),
        fetch('/api/v1/admin/system'),
      ]);
      if (mRes.ok) setMetrics(await mRes.json());
      if (uRes.ok) {
        const uData = await uRes.json();
        setUsers(uData.users || []);
      }
      if (sRes.ok) {
        const sData = await sRes.json();
        setScans(sData.scans || []);
      }
      if (sysRes.ok) setSystem(await sysRes.json());
    } catch (err) {
      console.error('Failed to load admin telemetry:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (userRole === 'admin') {
      fetchAdminData();
    }
  }, [userRole, fetchAdminData]);

  if (!sessionLoaded) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '120px' }}>
        <TbLoader2 size={36} className="pulse" color="#6366f1" />
        <p style={{ color: '#94a3b8' }}>Verifying admin authorization...</p>
      </div>
    );
  }

  // Access Control Guard: Non-admin users are restricted
  if (userRole !== 'admin') {
    return (
      <div style={{ maxWidth: '540px', margin: '80px auto', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '18px', padding: '40px 24px', background: 'rgba(18, 25, 44, 0.85)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '24px', backdropFilter: 'blur(16px)' }}>
        <div style={{ width: '64px', height: '64px', borderRadius: '20px', background: 'rgba(239, 68, 68, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ef4444' }}>
          <RiLockPasswordFill size={32} />
        </div>
        <h2 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#f8fafc' }}>Administrator Access Restricted</h2>
        <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.6 }}>
          This section is restricted to administrative personnel with elevated platform governance privileges.
        </p>

        <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
          <Link
            href="/dashboard"
            className="btn btn-primary"
            style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <TbArrowLeft size={16} /> Return to QA Dashboard
          </Link>
          {!session && (
            <button
              onClick={() => openAuthModal('signin')}
              className="btn btn-secondary"
            >
              Sign In with Admin Account
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className={styles.adminView}
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      style={{ padding: '20px 0 60px', display: 'flex', flexDirection: 'column', gap: '28px' }}
    >
      <div className={styles.adminTopBar}>
        <div className={styles.adminTitleBlock}>
          <h2>
            <RiShieldUserFill size={26} color="#6366f1" style={{ display: 'inline', marginRight: '8px' }} />
            JASUSS Admin & Cluster Telemetry
          </h2>
          <p>Global platform oversight, revenue metrics, active tenants, and worker nodes.</p>
        </div>

        <div className={styles.adminActions}>
          <button
            onClick={fetchAdminData}
            className={styles.exportBtn}
            disabled={loading}
          >
            <RiRefreshLine size={16} className={loading ? 'pulse' : ''} /> Refresh Telemetry
          </button>
        </div>
      </div>

      {/* 4 Admin KPI Cards */}
      <AdminMetrics
        metrics={metrics}
        usersCount={users.length}
        scansCount={scans.length}
      />

      {/* Multi-AI Provider & Engine Setup */}
      <AIProviderConfig />

      {/* Host System Telemetry */}
      <SystemTelemetry system={system} />

      {/* Tenant Directory */}
      <TenantTable users={users} />

      {/* Pipeline Inspector */}
      <PipelineInspector scans={scans} />
    </motion.div>
  );
};
