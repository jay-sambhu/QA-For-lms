"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  RiRefreshLine,
  RiShieldUserLine,
  RiCheckDoubleLine,
  RiSearchLine,
  RiFileExcel2Line,
} from 'react-icons/ri';
import { FaRegFilePdf } from 'react-icons/fa6';
import {
  TbLoader2,
  TbArrowRight,
  TbChecklist,
  TbKey,
  TbActivity,
  TbDevices,
  TbExternalLink,
  TbLock,
  TbScan,
  TbGift,
} from 'react-icons/tb';
import { useAuth } from '../context/AuthContext';
import { downloadScanReport, type ServerReportFormat } from '../utils/download';
import { ScanForm, type TrialStatus } from '../components/scan/ScanForm';
import { ApiKeyManager } from '../components/dashboard/ApiKeyManager';
import {
  Surface3D,
  StatTile3D,
  PageHeader3D,
  SegmentedTabs3D,
  EmptyState3D,
} from '../components/three';
import d from '../components/dashboard/dashboard3d.module.css';

type StatusFilter = 'all' | 'completed' | 'running' | 'failed';

const normalizeTrial = (data: any): TrialStatus | null => {
  if (!data || typeof data !== 'object' || typeof data.remaining !== 'number') return null;
  return {
    enabled: !!data.enabled,
    total: Number(data.total) || 0,
    used: Number(data.used) || 0,
    remaining: Math.max(0, Number(data.remaining) || 0),
    has_own_key: !!data.has_own_key,
    daily_available: data.daily_available !== false,
  };
};

const statusChip = (status: string) => {
  switch (status) {
    case 'completed':
      return 'chip chip--success chip--dot';
    case 'running':
    case 'pending':
    case 'queued':
      return 'chip chip--info chip--live';
    case 'failed':
    case 'error':
      return 'chip chip--danger chip--dot';
    case 'cancelled':
      return 'chip chip--neutral';
    case 'timeout':
    case 'stalled':
      return 'chip chip--warning chip--dot';
    default:
      return 'chip chip--neutral';
  }
};

const enterDelay = (step: number) => ({ ['--enter-delay' as string]: `${step * 60}ms` }) as React.CSSProperties;

export const DashboardPage: React.FC = () => {
  const router = useRouter();
  const { session, sessionLoaded, userPlan, isAdmin, openAuthModal, openProfileModal } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [recentScans, setRecentScans] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [hasApiKey, setHasApiKey] = useState<boolean | null>(null);
  const [apiKeysCount, setApiKeysCount] = useState<number>(0);
  const [trial, setTrial] = useState<TrialStatus | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [downloadingScanId, setDownloadingScanId] = useState<string | null>(null);

  const handleDirectDownload = async (scanId: string, format: ServerReportFormat) => {
    if (!session?.access_token) return;
    setDownloadingScanId(`${scanId}-${format}`);
    try {
      await downloadScanReport(scanId, format, session.access_token);
    } catch (e) {
      console.error('Download error:', e);
      const reason = e instanceof Error ? e.message : '';
      alert(`Could not download the requested report${reason ? `: ${reason}` : ''}. You can open the scan report to view details.`);
    } finally {
      setDownloadingScanId(null);
    }
  };

  const fetchTrial = useCallback(async () => {
    if (!session?.access_token) return;
    try {
      const res = await fetch('/api/v1/user/trial', {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        setTrial(normalizeTrial(await res.json()));
      } else if (res.status === 404) {
        setTrial(null);
      }
    } catch {
      // Ignore background network errors
    }
  }, [session?.access_token]);

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
        if (data.trial) setTrial(normalizeTrial(data.trial));
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
      // One retry: a transient backend/auth hiccup must not leave the
      // dashboard claiming the user has never run a scan.
      for (let attempt = 1; attempt <= 2; attempt++) {
        const res = await fetch('/api/v1/scans', {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setRecentScans(data.scans || []);
          break;
        }
        if (attempt === 1 && res.status !== 401) {
          await new Promise((r) => setTimeout(r, 1500));
          continue;
        }
        console.error('Failed to load scans: HTTP', res.status);
      }
    } catch (e) {
      console.error('Failed to load scans:', e);
    } finally {
      setLoadingHistory(false);
    }
  }, [session?.access_token]);

  // Depend on the token (via the callbacks), not the session object: Supabase emits a new
  // session object on tab refocus/token refresh, which used to trigger redundant refetches.
  useEffect(() => {
    fetchScanHistory();
    checkApiKey();
    fetchTrial();
  }, [fetchScanHistory, checkApiKey, fetchTrial]);

  const scrollToAiManager = () => {
    const el = document.getElementById('ai-models-manager');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    } else {
      openProfileModal();
    }
  };

  const scrollToLauncher = () => {
    const el = document.getElementById('scan-launcher');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.querySelector<HTMLInputElement>('input[type="url"]')?.focus({ preventScroll: true });
    }
  };

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
        if (res.status === 400 && /API key is required/i.test(errData.detail || '')) {
          setHasApiKey(false);
          fetchTrial();
          openProfileModal();
        }
        throw new Error(errData.detail || `Scan request failed with status ${res.status}`);
      }

      const resData = await res.json();
      if (resData.used_trial && typeof resData.trial_remaining === 'number') {
        const remaining = Math.max(0, resData.trial_remaining);
        setTrial((prev) =>
          prev ? { ...prev, remaining, used: Math.max(0, prev.total - remaining) } : prev
        );
      }
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
  const failedCount = recentScans.filter((s) => s.status === 'failed' || s.status === 'error').length;
  const successRate = totalScansCount > 0 ? Math.round((completedCount / totalScansCount) * 100) : 100;

  const trialActive = hasApiKey === false && !!trial?.enabled && trial.remaining > 0;
  const trialExhausted = hasApiKey === false && !!trial?.enabled && trial.remaining <= 0;
  const keyMissing = hasApiKey === false && !trial?.enabled;

  const aiTile = (() => {
    if (hasApiKey === null) {
      return { accent: 'neutral' as const, value: 'Checking…', hint: 'Looking up your AI keys', icon: <TbKey size={20} /> };
    }
    if (hasApiKey) {
      return {
        accent: 'success' as const,
        value: `${apiKeysCount} ${apiKeysCount === 1 ? 'key' : 'keys'} active`,
        hint: 'Click to manage your AI keys',
        icon: <TbKey size={20} />,
      };
    }
    if (trialActive && trial) {
      return {
        accent: 'info' as const,
        value: 'Free trial',
        hint: `${trial.remaining} of ${trial.total} free scan${trial.total === 1 ? '' : 's'} left · add your own key anytime`,
        icon: <TbGift size={20} />,
      };
    }
    if (trialExhausted) {
      return {
        accent: 'warning' as const,
        value: 'Trial used up',
        hint: 'Add a free Gemini key to keep scanning',
        icon: <TbKey size={20} />,
      };
    }
    return {
      accent: 'danger' as const,
      value: 'Key required',
      hint: 'Click to configure your AI key',
      icon: <TbKey size={20} />,
    };
  })();

  if (!sessionLoaded) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '120px' }}>
        <TbLoader2 size={36} className="pulse" style={{ color: 'var(--primary)' }} />
        <p style={{ color: 'var(--text-muted)' }}>Loading workspace...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '120px' }}>
        <TbLoader2 size={36} className="pulse" style={{ color: 'var(--primary)' }} />
        <p style={{ color: 'var(--text-muted)' }}>Session unauthenticated. Redirecting to home...</p>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <div className="enter-3d">
        <PageHeader3D
          eyebrow="Workspace"
          title="QA Automation Dashboard"
          badge={`${userPlan.toUpperCase()} TIER`}
          subtitle="Launch autonomous multi-device browser testing agents and inspect AI-verified defect reports."
          actions={
            <>
              <button type="button" className="btn btn-primary" onClick={scrollToLauncher}>
                <TbScan size={16} /> New scan
              </button>
              <button
                type="button"
                onClick={fetchScanHistory}
                className="btn btn-secondary"
                disabled={loadingHistory}
              >
                <RiRefreshLine size={16} className={loadingHistory ? 'pulse' : ''} /> Refresh history
              </button>
              {isAdmin && (
                <Link href="/admin" className="btn btn-secondary">
                  <RiShieldUserLine size={16} />
                  <span>Admin Console</span>
                  <TbExternalLink size={14} />
                </Link>
              )}
            </>
          }
        />
      </div>

      {/* KPI tiles */}
      <div className="bento" style={{ ['--grid-gap' as string]: '16px' } as React.CSSProperties}>
        <div className="span-3 enter-3d" style={enterDelay(1)}>
          <StatTile3D
            label="Total automated scans"
            value={totalScansCount}
            icon={<TbActivity size={20} />}
            hint={`${completedCount} completed · ${runningCount} active`}
          />
        </div>
        <div className="span-3 enter-3d" style={enterDelay(2)}>
          <StatTile3D
            label="Verification pass rate"
            value={`${successRate}%`}
            accent="success"
            icon={<RiCheckDoubleLine size={20} />}
            hint="Across all crawled pages & viewport states"
          />
        </div>
        <div className="span-3 enter-3d" style={enterDelay(3)}>
          <StatTile3D
            label="AI engine & BYOK"
            value={aiTile.value}
            compact
            valueAccent
            accent={aiTile.accent}
            icon={aiTile.icon}
            hint={aiTile.hint}
            onClick={scrollToAiManager}
            actionLabel={`AI engine: ${aiTile.value}. ${aiTile.hint}`}
          >
            {trialActive && trial && trial.total > 0 && trial.total <= 10 && (
              <div className={d.trialTrack} aria-hidden="true">
                {Array.from({ length: trial.total }, (_, i) => (
                  <span key={i} className={`${d.trialStep} ${i < trial.remaining ? d.trialStepFilled : ''}`} />
                ))}
              </div>
            )}
          </StatTile3D>
        </div>
        <div className="span-3 enter-3d" style={enterDelay(4)}>
          <StatTile3D
            label="Browser matrix"
            value="3 viewports"
            compact
            accent="info"
            icon={<TbDevices size={20} />}
            hint="Desktop 1920 · Tablet 768 · Mobile 375"
          />
        </div>
      </div>

      {/* Reminder when the user cannot scan without adding a key */}
      {session && (trialExhausted || keyMissing) && (
        <Surface3D
          accent={trialExhausted ? 'warning' : 'danger'}
          pad="sm"
          className={`enter-3d ${d.banner}`}
          role="status"
          style={enterDelay(5)}
        >
          <div className={d.bannerBody}>
            <span className="icon-well" aria-hidden="true">
              <TbKey size={22} />
            </span>
            <div>
              <p className={d.bannerTitle}>
                {trialExhausted
                  ? `You've used your ${trial?.total ?? 0} free trial scan${trial?.total === 1 ? '' : 's'}`
                  : 'An AI API key is required for AI QA analysis'}
              </p>
              <p className={d.bannerText}>
                {trialExhausted
                  ? 'Add your own free Gemini API key to keep scanning. OpenAI, Claude, DeepSeek and local LLMs work too.'
                  : 'Your tests crawl freely, but generating AI defect reports requires an active AI API key (Gemini, OpenAI, Claude, DeepSeek, or Local LLM).'}
              </p>
            </div>
          </div>
          <button type="button" onClick={scrollToAiManager} className="btn btn-primary">
            <TbKey size={16} /> {trialExhausted ? 'Add a free Gemini key' : 'Configure API keys below'}
          </button>
        </Surface3D>
      )}

      {/* New Scan Launch Console */}
      <Surface3D ring pad="lg" className="enter-3d" style={enterDelay(5)}>
        <ScanForm
          onSubmit={handleStartScan}
          loading={loading}
          error={error}
          trial={trial}
          hasApiKey={hasApiKey}
          onConfigureKey={scrollToAiManager}
        />
      </Surface3D>

      {/* Recent Scans History Section */}
      <Surface3D as="section" pad="sm" className="enter-3d" style={enterDelay(6)} aria-labelledby="run-history-title">
        <div className={d.panelHead} style={{ padding: '8px 8px 16px' }}>
          <div className={d.panelTitleBlock}>
            <span className="icon-well" aria-hidden="true">
              <TbChecklist size={20} />
            </span>
            <div>
              <span className="section-eyebrow">Run history</span>
              <div className={d.panelTitleRow}>
                <h2 id="run-history-title" className={d.panelTitle}>Autonomous QA runs</h2>
                <span className={d.panelCount}>
                  {filteredScans.length} of {recentScans.length} scans
                </span>
              </div>
            </div>
          </div>

          {/* Search & Filter Controls */}
          <div className={d.panelTools}>
            <div className={d.search}>
              <RiSearchLine size={14} className={d.searchIcon} />
              <input
                type="text"
                placeholder="Filter by target URL..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={`${d.field} ${d.searchInput}`}
                aria-label="Filter runs by target URL"
              />
            </div>

            <SegmentedTabs3D
              size="sm"
              ariaLabel="Filter runs by status"
              tabs={[
                { id: 'all', label: 'All', badge: totalScansCount },
                { id: 'completed', label: 'Completed', badge: completedCount },
                { id: 'running', label: 'Running', badge: runningCount },
                { id: 'failed', label: 'Failed', badge: failedCount },
              ]}
              active={statusFilter}
              onChange={setStatusFilter}
            />
          </div>
        </div>

        <div className="table-3d-wrap" style={{ ['--table-max-h' as string]: '560px' } as React.CSSProperties}>
          <table className="table-3d">
            <thead>
              <tr>
                <th>Target web application</th>
                <th>Run status</th>
                <th>Auth session</th>
                <th>Initiated at</th>
                <th>Actions &amp; reports</th>
              </tr>
            </thead>
            <tbody>
              {filteredScans.map((s) => {
                const isCompleted = s.status === 'completed';
                const isRunning = s.status === 'running' || s.status === 'pending';

                return (
                  <tr key={s.id}>
                    <td>
                      <div className={d.urlCell} title={s.url}>{s.url}</div>
                    </td>
                    <td>
                      <span className={statusChip(String(s.status || 'unknown'))}>
                        {String(s.status || 'unknown')}
                      </span>
                    </td>
                    <td>
                      {s.is_authenticated ? (
                        <span className="chip chip--sm chip--primary">
                          <TbLock size={11} /> Authenticated
                        </span>
                      ) : (
                        <span className={d.metaCell}>Public</span>
                      )}
                    </td>
                    <td className={d.metaCell}>
                      {s.created_at ? new Date(s.created_at).toLocaleString() : 'N/A'}
                    </td>
                    <td>
                      <div className={d.rowActions}>
                        <Link
                          href={`/dashboard/scan/${s.id}`}
                          className={`btn ${isRunning ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                        >
                          <span>{isRunning ? 'Live monitor' : 'View report'}</span>
                          <TbArrowRight size={14} />
                        </Link>

                        {isCompleted && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleDirectDownload(s.id, 'pdf')}
                              disabled={downloadingScanId === `${s.id}-pdf`}
                              className="btn btn-secondary btn-sm"
                              title="Direct Cloud Download PDF Report"
                            >
                              {downloadingScanId === `${s.id}-pdf` ? (
                                <TbLoader2 size={13} className="pulse" />
                              ) : (
                                <FaRegFilePdf size={13} color="#e11d48" />
                              )}
                              <span>PDF</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDirectDownload(s.id, 'xlsx')}
                              disabled={downloadingScanId === `${s.id}-xlsx`}
                              className="btn btn-secondary btn-sm"
                              title="Direct Cloud Download Excel Workbook"
                            >
                              {downloadingScanId === `${s.id}-xlsx` ? (
                                <TbLoader2 size={13} className="pulse" />
                              ) : (
                                <RiFileExcel2Line size={13} color="#059669" />
                              )}
                              <span>Excel</span>
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}

              {filteredScans.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    {recentScans.length === 0 ? (
                      <EmptyState3D
                        compact
                        icon={<TbScan size={16} />}
                        title={loadingHistory ? 'Loading your runs…' : 'No scans yet'}
                        description={
                          loadingHistory
                            ? undefined
                            : 'Paste a target URL in the launch console above to map, test and grade your first site.'
                        }
                        action={
                          loadingHistory ? undefined : (
                            <button type="button" className="btn btn-primary btn-sm" onClick={scrollToLauncher}>
                              <TbScan size={14} /> Start your first scan
                            </button>
                          )
                        }
                      />
                    ) : (
                      <EmptyState3D compact title="No runs match this filter" description="Try another status or clear the URL filter." />
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Surface3D>

      {/* Dedicated Multi-AI Provider & Model Integration Hub */}
      {session && (
        <div className="enter-3d" style={enterDelay(6)}>
          <ApiKeyManager onKeysUpdated={checkApiKey} />
        </div>
      )}
    </div>
  );
};
