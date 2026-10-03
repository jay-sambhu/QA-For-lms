"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RiRefreshLine,
  RiShieldUserLine,
  RiCheckDoubleLine,
  RiTimeLine,
  RiSearchLine,
  RiArrowRightLine,
} from 'react-icons/ri';
import {
  TbLoader2,
  TbArrowRight,
  TbChecklist,
  TbKey,
  TbActivity,
  TbDeviceDesktop,
  TbDeviceMobile,
  TbDevices,
  TbSparkles,
  TbExternalLink,
} from 'react-icons/tb';
import { useAuth } from '../context/AuthContext';
import { ScanForm } from '../components/scan/ScanForm';
import styles from '../app/page.module.css';

export const DashboardPage: React.FC = () => {
  const router = useRouter();
  const { session, sessionLoaded, userRole, userPlan, isAdmin, openAuthModal, openProfileModal } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [recentScans, setRecentScans] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [hasApiKey, setHasApiKey] = useState<boolean | null>(null);
  const [apiKeysCount, setApiKeysCount] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'completed' | 'running' | 'failed'>('all');

  const checkApiKey = useCallback(async () => {
    if (!session?.access_token) return;
    try {
      const res = await fetch('/api/v1/user/api-keys', {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setHasApiKey(data.count > 0);
        setApiKeysCount(data.count || 0);
      } else {
        const legacyRes = await fetch('/api/v1/user/api-key', {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (legacyRes.ok) {
          const lData = await legacyRes.json();
          setHasApiKey(!!lData.has_key);
          setApiKeysCount(lData.has_key ? 1 : 0);
        }
      }
    } catch {
      // Ignore background network errors
    }
  }, [session?.access_token]);

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
      checkApiKey();
    }
  }, [session, fetchScanHistory, checkApiKey]);

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
        if (res.status === 400 && errData.detail?.includes('Gemini API key')) {
          setHasApiKey(false);
          openProfileModal();
        }
        throw new Error(errData.detail || `Scan request failed with status ${res.status}`);
      }

      const resData = await res.json();
      router.push(`/dashboard/scan/${resData.scan_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize QA scan');
      setLoading(false);
    }
  };

  // Filtered Scans
  const filteredScans = useMemo(() => {
    return recentScans.filter((s) => {
      const matchesSearch =
        !searchQuery || s.url?.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'running' && (s.status === 'running' || s.status === 'pending')) ||
        s.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [recentScans, searchQuery, statusFilter]);

  // Route Authentication Guard: Unauthenticated users are bounced to home
  useEffect(() => {
    if (sessionLoaded && !session) {
      router.replace('/');
    }
  }, [sessionLoaded, session, router]);

  // Calculated KPI metrics
  const totalScansCount = recentScans.length;
  const completedCount = recentScans.filter((s) => s.status === 'completed').length;
  const runningCount = recentScans.filter((s) => s.status === 'running' || s.status === 'pending').length;
  const successRate = totalScansCount > 0 ? Math.round((completedCount / totalScansCount) * 100) : 100;

  if (!sessionLoaded) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '120px' }}>
        <TbLoader2 size={36} className="pulse" color="#6366f1" />
        <p style={{ color: '#94a3b8' }}>Loading workspace...</p>
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '20px 0 60px' }}>
      {/* Top Glassmorphic Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
          padding: '24px',
          background: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '20px',
          boxShadow: '0 12px 32px rgba(0, 0, 0, 0.35)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc' }}>
              QA Automation Dashboard
            </h2>
            <span
              className={`${styles.tierPill} ${
                userPlan === 'pro'
                  ? styles.tierPro
                  : userPlan === 'enterprise'
                  ? styles.tierEnterprise
                  : styles.tierFree
              }`}
            >
              {userPlan.toUpperCase()} TIER
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '0.9rem', color: '#94a3b8' }}>
            Launch autonomous multi-device browser testing agents and inspect AI-verified defect reports.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Admin Switcher Card */}
          {isAdmin && (
            <Link
              href="/admin"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(99, 102, 241, 0.2))',
                border: '1px solid rgba(168, 85, 247, 0.4)',
                color: '#c084fc',
                fontSize: '0.84rem',
                fontWeight: 700,
                textDecoration: 'none',
                boxShadow: '0 4px 15px rgba(168, 85, 247, 0.15)',
                transition: 'all 0.2s ease',
              }}
            >
              <RiShieldUserLine size={16} />
              <span>Admin Console</span>
              <TbExternalLink size={14} />
            </Link>
          )}

          <button
            onClick={fetchScanHistory}
            className={styles.exportBtn}
            disabled={loadingHistory}
            style={{ padding: '8px 16px', fontSize: '0.84rem' }}
          >
            <RiRefreshLine size={16} className={loadingHistory ? 'pulse' : ''} /> Refresh History
          </button>
        </div>
      </div>

      {/* 4 Glassmorphism Metric Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '16px',
        }}
      >
        {/* Card 1: Total Scans */}
        <div
          style={{
            padding: '20px',
            borderRadius: '16px',
            background: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#94a3b8' }}>Total Automated Scans</span>
            <TbActivity size={20} color="#818cf8" />
          </div>
          <div style={{ fontSize: '1.9rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
            {totalScansCount}
          </div>
          <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
            {completedCount} completed · {runningCount} active
          </div>
        </div>

        {/* Card 2: Success Rate */}
        <div
          style={{
            padding: '20px',
            borderRadius: '16px',
            background: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#94a3b8' }}>Verification Pass Rate</span>
            <RiCheckDoubleLine size={20} color="#10b981" />
          </div>
          <div style={{ fontSize: '1.9rem', fontWeight: 800, color: '#34d399', letterSpacing: '-0.02em' }}>
            {successRate}%
          </div>
          <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
            Across all crawled pages & viewport states
          </div>
        </div>

        {/* Card 3: AI Engine BYOK Status */}
        <div
          onClick={openProfileModal}
          style={{
            padding: '20px',
            borderRadius: '16px',
            background: hasApiKey
              ? 'rgba(16, 185, 129, 0.05)'
              : 'rgba(239, 68, 68, 0.06)',
            backdropFilter: 'blur(16px)',
            border: `1px solid ${hasApiKey ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.3)'}`,
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#94a3b8' }}>AI Models & BYOK</span>
            <TbKey size={20} color={hasApiKey ? '#34d399' : '#f87171'} />
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: hasApiKey ? '#34d399' : '#f87171', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '9px',
                height: '9px',
                borderRadius: '50%',
                background: hasApiKey ? '#10b981' : '#ef4444',
                boxShadow: hasApiKey ? '0 0 10px #10b981' : '0 0 10px #ef4444',
              }}
            />
            {hasApiKey ? `${apiKeysCount} ${apiKeysCount === 1 ? 'Key' : 'Keys'} Active` : 'Key Required'}
          </div>
          <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
            {hasApiKey ? 'Click to manage multi-model keys' : 'Click to configure AI API Key →'}
          </div>
        </div>

        {/* Card 4: Viewports Pool */}
        <div
          style={{
            padding: '20px',
            borderRadius: '16px',
            background: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#94a3b8' }}>Browser Matrix</span>
            <TbDevices size={20} color="#38bdf8" />
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#38bdf8' }}>
            3 Active Viewports
          </div>
          <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
            Desktop (1920p) · Tablet (768p) · Mobile (375p)
          </div>
        </div>
      </div>

      {/* Reminder if user has not yet configured their AI API key */}
      {session && hasApiKey === false && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            padding: '18px 24px',
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: '16px',
            backdropFilter: 'blur(16px)',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                background: 'rgba(239, 68, 68, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#f87171',
              }}
            >
              <TbKey size={22} />
            </div>
            <div>
              <div style={{ fontSize: '0.98rem', fontWeight: 700, color: '#f8fafc' }}>
                AI API Key Required for AI QA Analysis
              </div>
              <div style={{ fontSize: '0.84rem', color: '#94a3b8', marginTop: '3px' }}>
                Your tests crawl freely, but generating AI defect reports requires an active AI API key (Gemini, OpenAI, Claude, DeepSeek, or Local LLM).
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={openProfileModal}
            className="btn btn-primary"
            style={{
              padding: '9px 18px',
              fontSize: '0.84rem',
              borderRadius: '10px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
              borderColor: 'rgba(255, 255, 255, 0.2)',
            }}
          >
            <TbKey size={16} /> Enter API Key Now
          </button>
        </motion.div>
      )}

      {/* New Scan Launch Card */}
      <motion.div
        className={styles.actionPanel}
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        style={{
          background: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.4)',
        }}
      >
        <ScanForm onSubmit={handleStartScan} loading={loading} error={error} />
      </motion.div>

      {/* Recent Scans History Section */}
      <div
        className={styles.adminTableCard}
        style={{
          background: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 16px 40px rgba(0, 0, 0, 0.35)',
        }}
      >
        <div
          className={styles.adminTableCardTitle}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <TbChecklist size={20} color="#818cf8" />
            <span style={{ fontWeight: 700 }}>Autonomous QA Run History</span>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 500, marginLeft: '6px' }}>
              ({filteredScans.length} of {recentScans.length} scans)
            </span>
          </div>

          {/* Search & Filter Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative' }}>
              <RiSearchLine
                size={14}
                style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }}
              />
              <input
                type="text"
                placeholder="Filter by target URL..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  padding: '5px 10px 5px 30px',
                  fontSize: '0.8rem',
                  color: '#f8fafc',
                  outline: 'none',
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '4px', background: 'rgba(255, 255, 255, 0.03)', padding: '2px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
              {(['all', 'completed', 'running', 'failed'] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setStatusFilter(filter)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    textTransform: 'capitalize',
                    background: statusFilter === filter ? 'rgba(99, 102, 241, 0.3)' : 'transparent',
                    color: statusFilter === filter ? '#ffffff' : '#94a3b8',
                    border: `1px solid ${statusFilter === filter ? 'rgba(99, 102, 241, 0.4)' : 'transparent'}`,
                    cursor: 'pointer',
                  }}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className={styles.adminTableContainer}>
          <table className={styles.adminTable}>
            <thead>
              <tr>
                <th>Target Web Application</th>
                <th>Run Status</th>
                <th>Auth Session</th>
                <th>Initiated At</th>
                <th>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {filteredScans.map((s) => {
                const isCompleted = s.status === 'completed';
                const isRunning = s.status === 'running' || s.status === 'pending';
                const isFailed = s.status === 'failed' || s.status === 'error';

                return (
                  <tr key={s.id}>
                    <td style={{ maxWidth: '340px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span style={{ color: '#f8fafc', fontWeight: 600 }}>{s.url}</span>
                    </td>
                    <td>
                      <span
                        className={styles.severityBadge}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          background: isCompleted
                            ? 'rgba(16, 185, 129, 0.15)'
                            : isFailed
                            ? 'rgba(239, 68, 68, 0.15)'
                            : 'rgba(99, 102, 241, 0.15)',
                          color: isCompleted
                            ? '#34d399'
                            : isFailed
                            ? '#f87171'
                            : '#818cf8',
                          border: `1px solid ${
                            isCompleted
                              ? 'rgba(16, 185, 129, 0.3)'
                              : isFailed
                              ? 'rgba(239, 68, 68, 0.3)'
                              : 'rgba(99, 102, 241, 0.3)'
                          }`,
                        }}
                      >
                        {isRunning && <TbLoader2 size={12} className="pulse" />}
                        {s.status.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.82rem', color: s.is_authenticated ? '#34d399' : '#64748b' }}>
                        {s.is_authenticated ? '🔒 Authenticated' : 'Public'}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                      {s.created_at ? new Date(s.created_at).toLocaleString() : 'N/A'}
                    </td>
                    <td>
                      <Link
                        href={`/dashboard/scan/${s.id}`}
                        className="btn btn-secondary"
                        style={{
                          padding: '6px 14px',
                          fontSize: '0.8rem',
                          borderRadius: '8px',
                          textDecoration: 'none',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          background: isRunning ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                          borderColor: isRunning ? 'rgba(99, 102, 241, 0.35)' : 'rgba(255, 255, 255, 0.1)',
                          color: isRunning ? '#818cf8' : '#f8fafc',
                        }}
                      >
                        <span>{isRunning ? 'Live Monitor' : 'View Report'}</span>
                        <TbArrowRight size={14} />
                      </Link>
                    </td>
                  </tr>
                );
              })}

              {filteredScans.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '42px', color: '#94a3b8' }}>
                    {recentScans.length === 0
                      ? 'No scans launched yet. Enter a target URL in the panel above to begin your first automated QA run!'
                      : 'No scans match your search query.'}
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
