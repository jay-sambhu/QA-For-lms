"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RiRefreshLine,
  RiShieldUserFill,
  RiLockPasswordFill,
  RiArticleLine,
  RiDashboardLine,
  RiCpuLine,
  RiKey2Line,
} from 'react-icons/ri';
import {
  TbLoader2,
  TbArrowLeft,
  TbUsers,
  TbActivity,
  TbArrowRight,
  TbBrain,
} from 'react-icons/tb';
import { useAuth } from '../context/AuthContext';
import { AdminMetrics } from '../components/admin/AdminMetrics';
import { TenantTable } from '../components/admin/TenantTable';
import { PipelineInspector } from '../components/admin/PipelineInspector';
import { SystemTelemetry } from '../components/admin/SystemTelemetry';
import { AIProviderConfig } from '../components/admin/AIProviderConfig';
import { ApiKeyManager } from '../components/admin/ApiKeyManager';
import { BlogManager } from '../components/admin/BlogManager';
import styles from '../app/page.module.css';

type AdminTab = 'overview' | 'users' | 'scans' | 'blogs' | 'ai' | 'system';

export const AdminPage: React.FC = () => {
  const router = useRouter();
  const { session, sessionLoaded, userRole, isAdmin, openAuthModal } = useAuth();
  const [activeTab, setActiveTab] = useState<AdminTab>('overview');
  const [metrics, setMetrics] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [scans, setScans] = useState<any[]>([]);
  const [system, setSystem] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchAdminData = useCallback(async () => {
    setLoading(true);
    try {
      const headers: Record<string, string> = {};
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
      const [mRes, uRes, sRes, sysRes] = await Promise.all([
        fetch('/api/v1/admin/metrics', { headers }),
        fetch('/api/v1/admin/users', { headers }),
        fetch('/api/v1/admin/scans', { headers }),
        fetch('/api/v1/admin/system', { headers }),
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
  }, [session?.access_token]);

  // Route Authentication & Authorization Guard
  useEffect(() => {
    if (sessionLoaded) {
      if (!session) {
        router.replace('/');
      } else if (!isAdmin && userRole !== 'admin') {
        router.replace('/dashboard');
      }
    }
  }, [sessionLoaded, session, isAdmin, userRole, router]);

  useEffect(() => {
    if (isAdmin || userRole === 'admin') {
      fetchAdminData();
    }
  }, [isAdmin, userRole, fetchAdminData]);

  if (!sessionLoaded) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '120px' }}>
        <TbLoader2 size={36} className="pulse" color="#6366f1" />
        <p style={{ color: '#94a3b8' }}>Verifying administrator credentials...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '120px' }}>
        <TbLoader2 size={36} className="pulse" color="#6366f1" />
        <p style={{ color: '#94a3b8' }}>Session unauthenticated. Redirecting to home...</p>
      </div>
    );
  }

  // Access Control Guard: Non-admin users are restricted and bounced to dashboard
  if (!isAdmin && userRole !== 'admin') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '120px' }}>
        <TbLoader2 size={36} className="pulse" color="#6366f1" />
        <p style={{ color: '#94a3b8' }}>Administrator privileges required. Redirecting to dashboard...</p>
      </div>
    );
  }

  const tabs: { id: AdminTab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: 'overview', label: 'Overview', icon: <RiDashboardLine size={16} /> },
    { id: 'users', label: 'Tenants & Roles', icon: <TbUsers size={16} />, count: users.length },
    { id: 'scans', label: 'Global Scans', icon: <TbActivity size={16} />, count: scans.length },
    { id: 'blogs', label: 'Dynamic Blog CMS', icon: <RiArticleLine size={16} /> },
    { id: 'ai', label: 'AI Reasoning & Keys', icon: <TbBrain size={16} /> },
    { id: 'system', label: 'Cluster Telemetry', icon: <RiCpuLine size={16} /> },
  ];

  return (
    <motion.div
      className={styles.adminView}
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      style={{ padding: '20px 0 60px', display: 'flex', flexDirection: 'column', gap: '24px' }}
    >
      {/* Top Glass Header */}
      <div
        className={styles.adminTopBar}
        style={{
          background: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(168, 85, 247, 0.25)',
          borderRadius: '20px',
          padding: '24px',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.35)',
        }}
      >
        <div className={styles.adminTitleBlock}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.3), rgba(99, 102, 241, 0.3))',
                border: '1px solid rgba(168, 85, 247, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#c084fc',
              }}
            >
              <RiShieldUserFill size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ margin: 0, fontSize: '1.45rem', fontWeight: 800 }}>Admin Operations Console</h2>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: '999px',
                    fontSize: '0.7rem',
                    fontWeight: 800,
                    letterSpacing: '0.05em',
                    background: 'rgba(168, 85, 247, 0.2)',
                    color: '#c084fc',
                    border: '1px solid rgba(168, 85, 247, 0.4)',
                  }}
                >
                  SUPER ADMIN
                </span>
              </div>
              <p style={{ margin: '2px 0 0', fontSize: '0.86rem', color: '#94a3b8' }}>
                System-wide governance, user role promotion, cluster health, and dynamic content.
              </p>
            </div>
          </div>
        </div>

        <div className={styles.adminActions} style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <Link
            href="/dashboard"
            className="btn btn-secondary"
            style={{
              padding: '8px 16px',
              fontSize: '0.84rem',
              borderRadius: '10px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(99, 102, 241, 0.1)',
              borderColor: 'rgba(99, 102, 241, 0.3)',
              color: '#818cf8',
            }}
          >
            <span>Launch QA Scanner (User View)</span>
            <TbArrowRight size={14} />
          </Link>

          <button
            onClick={fetchAdminData}
            className={styles.exportBtn}
            disabled={loading}
            style={{ padding: '8px 16px', fontSize: '0.84rem' }}
          >
            <RiRefreshLine size={16} className={loading ? 'pulse' : ''} /> Refresh Telemetry
          </button>
        </div>
      </div>

      {/* Glassmorphic Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          overflowX: 'auto',
          padding: '6px',
          background: 'rgba(15, 23, 42, 0.6)',
          backdropFilter: 'blur(16px)',
          borderRadius: '14px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 18px',
                borderRadius: '10px',
                fontSize: '0.86rem',
                fontWeight: 600,
                color: isActive ? '#ffffff' : '#94a3b8',
                background: isActive
                  ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.4) 0%, rgba(168, 85, 247, 0.4) 100%)'
                  : 'transparent',
                border: `1px solid ${isActive ? 'rgba(168, 85, 247, 0.5)' : 'transparent'}`,
                boxShadow: isActive ? '0 4px 15px rgba(99, 102, 241, 0.25)' : 'none',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.2s ease',
              }}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {typeof tab.count === 'number' && (
                <span
                  style={{
                    padding: '1px 6px',
                    borderRadius: '999px',
                    fontSize: '0.72rem',
                    background: isActive ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                    color: isActive ? '#fff' : '#64748b',
                  }}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <AnimatePresence mode="wait">
        {activeTab === 'overview' && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}
          >
            {/* KPI Cards */}
            <AdminMetrics
              metrics={metrics}
              usersCount={users.length}
              scansCount={scans.length}
            />

            {/* Quick Summary Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
              <SystemTelemetry system={system} />
              <AIProviderConfig />
            </div>

            {/* Scans Snippet */}
            <PipelineInspector scans={scans.slice(0, 10)} />
          </motion.div>
        )}

        {activeTab === 'users' && (
          <motion.div
            key="users"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <TenantTable
              users={users}
              sessionToken={session?.access_token}
              onRoleUpdated={fetchAdminData}
            />
          </motion.div>
        )}

        {activeTab === 'scans' && (
          <motion.div
            key="scans"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <PipelineInspector scans={scans} />
          </motion.div>
        )}

        {activeTab === 'blogs' && (
          <motion.div
            key="blogs"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <BlogManager />
          </motion.div>
        )}

        {activeTab === 'ai' && (
          <motion.div
            key="ai"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}
          >
            <AIProviderConfig />
            <ApiKeyManager />
          </motion.div>
        )}

        {activeTab === 'system' && (
          <motion.div
            key="system"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <SystemTelemetry system={system} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
