"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { RefreshCw, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ScanForm } from '../components/scan/ScanForm';
import styles from '../app/page.module.css';

export const DashboardPage: React.FC = () => {
  const router = useRouter();
  const { session, sessionLoaded, openAuthModal } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [recentScans, setRecentScans] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const fetchScanHistory = useCallback(async () => {
    if (!session?.access_token) return;
    setLoadingHistory(true);
    try {
      const res = await fetch('/api/v1/scans', {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setRecentScans(data.scans || []);
      }
    } catch (e) {
      console.error('Failed to load scans:', e);
    } finally {
      setLoadingHistory(false);
    }
  }, [session?.access_token]);

  useEffect(() => {
    if (session) {
      fetchScanHistory();
    }
  }, [session, fetchScanHistory]);

  const handleStartScan = async (data: {
    url: string;
    maxPages: number;
    auth?: { loginUrl?: string; username?: string; password?: string };
  }) => {
    if (!session) {
      openAuthModal('signin');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const payload: any = {
        url: data.url,
        max_pages: data.maxPages,
      };
      if (data.auth) {
        payload.auth = {
          login_url: data.auth.loginUrl,
          username: data.auth.username,
          password: data.auth.password,
        };
      }

      const res = await fetch('/api/v1/scans', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Scan request failed with status ${res.status}`);
      }

      const resData = await res.json();
      router.push(`/dashboard/scan/${resData.scan_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize QA scan');
      setLoading(false);
    }
  };

  if (!sessionLoaded) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '120px' }}>
        <Loader2 size={36} className="pulse" color="#6366f1" />
        <p style={{ color: '#94a3b8' }}>Loading workspace...</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', padding: '20px 0 60px' }}>
      <div className={styles.adminTopBar}>
        <div className={styles.adminTitleBlock}>
          <h2>QA Automation Dashboard</h2>
          <p>Launch autonomous multi-device scans and inspect verified test runs.</p>
        </div>

        <button
          onClick={fetchScanHistory}
          className={styles.exportBtn}
          disabled={loadingHistory}
        >
          <RefreshCw size={14} className={loadingHistory ? 'pulse' : ''} /> Refresh History
        </button>
      </div>

      {/* New Scan Launch Card */}
      <motion.div
        className={styles.actionPanel}
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <ScanForm onSubmit={handleStartScan} loading={loading} error={error} />
      </motion.div>

      {/* Recent Scans History Section */}
      <div className={styles.adminTableCard}>
        <div className={styles.adminTableCardTitle}>
          <span>Recent Automated QA Runs</span>
          <span style={{ fontSize: '0.82rem', color: '#94a3b8', fontWeight: 500 }}>
            {recentScans.length} scans recorded
          </span>
        </div>

        <div className={styles.adminTableContainer}>
          <table className={styles.adminTable}>
            <thead>
              <tr>
                <th>Target Website</th>
                <th>Status</th>
                <th>Auth Mode</th>
                <th>Created At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {recentScans.map((s) => (
                <tr key={s.id}>
                  <td style={{ maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ color: '#f8fafc', fontWeight: 600 }}>{s.url}</span>
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
                  <td>{s.created_at ? new Date(s.created_at).toLocaleString() : 'N/A'}</td>
                  <td>
                    <Link
                      href={`/dashboard/scan/${s.id}`}
                      className="btn btn-secondary"
                      style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px', textDecoration: 'none' }}
                    >
                      View Report →
                    </Link>
                  </td>
                </tr>
              ))}

              {recentScans.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '36px', color: '#94a3b8' }}>
                    No scans launched yet. Enter a target URL above to start your first verification run!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
