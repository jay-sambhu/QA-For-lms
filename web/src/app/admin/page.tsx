"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, Loader2, Shield } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { AdminMetrics } from '../../components/admin/AdminMetrics';
import { TenantTable } from '../../components/admin/TenantTable';
import { PipelineInspector } from '../../components/admin/PipelineInspector';
import { SystemTelemetry } from '../../components/admin/SystemTelemetry';
import styles from '../page.module.css';

export default function AdminPage() {
  const { session, sessionLoaded, userRole } = useAuth();
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
    fetchAdminData();
  }, [fetchAdminData]);

  if (!sessionLoaded) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '120px' }}>
        <Loader2 size={36} className="pulse" color="#6366f1" />
        <p style={{ color: '#94a3b8' }}>Verifying admin authorization...</p>
      </div>
    );
  }

  return (
    <motion.div
      className={styles.adminView}
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      style={{ padding: '20px 0 60px' }}
    >
      <div className={styles.adminTopBar}>
        <div className={styles.adminTitleBlock}>
          <h2>JASUSS Admin & Cluster Telemetry</h2>
          <p>Global platform oversight, revenue metrics, active tenants, and worker nodes.</p>
        </div>

        <div className={styles.adminActions}>
          <button
            onClick={fetchAdminData}
            className={styles.exportBtn}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'pulse' : ''} /> Refresh Telemetry
          </button>
        </div>
      </div>

      {/* 4 Admin KPI Cards */}
      <AdminMetrics
        metrics={metrics}
        usersCount={users.length}
        scansCount={scans.length}
      />

      {/* Host System Telemetry */}
      <SystemTelemetry system={system} />

      {/* Tenant Directory */}
      <TenantTable users={users} />

      {/* Pipeline Inspector */}
      <PipelineInspector scans={scans} />
    </motion.div>
  );
}
