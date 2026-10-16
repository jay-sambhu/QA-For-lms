"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  RiRefreshLine,
  RiShieldUserFill,
  RiArticleLine,
  RiDashboardLine,
  RiCpuLine,
} from 'react-icons/ri';
import {
  TbLoader2,
  TbUsers,
  TbActivity,
  TbArrowRight,
  TbBrain,
} from 'react-icons/tb';
import { useAuth } from '../context/AuthContext';
import { PageHeader3D, SegmentedTabs3D } from '../components/three';
import { AdminMetrics } from '../components/admin/AdminMetrics';
import { TenantTable } from '../components/admin/TenantTable';
import { PipelineInspector } from '../components/admin/PipelineInspector';
import { SystemTelemetry } from '../components/admin/SystemTelemetry';
import { AIProviderConfig } from '../components/admin/AIProviderConfig';
import { ApiKeyManager } from '../components/admin/ApiKeyManager';
import { BlogManager } from '../components/admin/BlogManager';
import a from '../components/admin/admin3d.module.css';

type AdminTab = 'overview' | 'users' | 'scans' | 'blogs' | 'ai' | 'system';

const enterDelay = (step: number) =>
  ({ ['--enter-delay' as string]: `${step * 60}ms` }) as React.CSSProperties;

export const AdminPage: React.FC = () => {
  const router = useRouter();
  const { session, sessionLoaded, roleLoaded, userRole, isAdmin } = useAuth();
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
      } else if (roleLoaded && !isAdmin && userRole !== 'admin') {
        // Only bounce once the backend role is known; before that the context
        // still holds the default 'user' role and admins were sent away.
        router.replace('/dashboard');
      }
    }
  }, [sessionLoaded, roleLoaded, session, isAdmin, userRole, router]);

  useEffect(() => {
    if (isAdmin || userRole === 'admin') {
      fetchAdminData();
    }
  }, [isAdmin, userRole, fetchAdminData]);

  if (!sessionLoaded || (session && !roleLoaded)) {
    return (
      <div className={a.center}>
        <TbLoader2 size={36} className={`pulse ${a.centerIcon}`} />
        <p>Verifying administrator credentials...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className={a.center}>
        <TbLoader2 size={36} className={`pulse ${a.centerIcon}`} />
        <p>Session unauthenticated. Redirecting to home...</p>
      </div>
    );
  }

  // Access Control Guard: Non-admin users are restricted and bounced to dashboard
  if (!isAdmin && userRole !== 'admin') {
    return (
      <div className={a.center}>
        <TbLoader2 size={36} className={`pulse ${a.centerIcon}`} />
        <p>Administrator privileges required. Redirecting to dashboard...</p>
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
    <div className="page-shell tone-violet">
      <div className="enter-3d">
        <PageHeader3D
          icon={<RiShieldUserFill size={24} />}
          eyebrow="Admin console"
          title="Admin Operations Console"
          badge="SUPER ADMIN"
          subtitle="System-wide governance, user role promotion, cluster health, and dynamic content."
          actions={
            <>
              <button
                type="button"
                onClick={fetchAdminData}
                className="btn btn-primary"
                disabled={loading}
              >
                <RiRefreshLine size={16} className={loading ? 'pulse' : ''} /> Refresh Telemetry
              </button>
              <Link href="/dashboard" className="btn btn-secondary">
                <span>Launch QA Scanner (User View)</span>
                <TbArrowRight size={14} />
              </Link>
            </>
          }
        />
      </div>

      <div className="enter-3d" style={enterDelay(1)}>
        <SegmentedTabs3D
          ariaLabel="Admin sections"
          idPrefix="admin"
          tabs={tabs.map((t) => ({ id: t.id, label: t.label, icon: t.icon, badge: t.count }))}
          active={activeTab}
          onChange={setActiveTab}
        />
      </div>

      <div
        key={activeTab}
        role="tabpanel"
        id={`admin-panel-${activeTab}`}
        aria-labelledby={`admin-tab-${activeTab}`}
        className={`enter-3d ${a.stack}`}
      >
        {activeTab === 'overview' && (
          <>
            <AdminMetrics
              metrics={metrics}
              usersCount={users.length}
              scansCount={scans.length}
            />

            <SystemTelemetry system={system} />

            <AIProviderConfig />

            <PipelineInspector scans={scans.slice(0, 10)} />
          </>
        )}

        {activeTab === 'users' && (
          <TenantTable
            users={users}
            sessionToken={session?.access_token}
            onRoleUpdated={fetchAdminData}
          />
        )}

        {activeTab === 'scans' && <PipelineInspector scans={scans} />}

        {activeTab === 'blogs' && <BlogManager />}

        {activeTab === 'ai' && (
          <>
            <AIProviderConfig />
            <ApiKeyManager />
          </>
        )}

        {activeTab === 'system' && <SystemTelemetry system={system} detail />}
      </div>
    </div>
  );
};
