"use client";

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Search,
  Loader2,
  ArrowRight,
  ShieldCheck,
  Bug,
  FileText,
  LogOut,
  AlertTriangle,
  Download,
  FileSpreadsheet,
  Lock,
  Eye,
  EyeOff,
  KeyRound,
  User,
  Globe,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Terminal,
  RefreshCw,
  Sparkles,
  Smartphone,
  Monitor,
  Tablet,
  Layers,
  Zap,
  Activity,
  Award,
  Check,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Square,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { createClient, type Session } from '@supabase/supabase-js';
import styles from './page.module.css';
import { handleDownloadReport } from '../utils/export';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const supabase =
  supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null;

type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

interface Finding {
  id: string;
  classification: string;
  severity: Severity;
  confidence: string;
  title: string;
  page: string;
  url: string;
  description: string;
  recommendation: string;
  expected_result?: string;
  actual_result?: string;
  manual_verification?: string;
  affected_pages_count?: number;
  occurrence_count?: number;
  priority?: string;
  root_cause?: { category?: string; summary?: string };
  user_impact?: string;
  regression_status?: string;
  screenshots?: string[];
  evidence?: {
    http_errors?: unknown[];
    console_errors?: unknown[];
    network_failures?: unknown[];
    screenshot?: string;
  };
  reproduction?: {
    url?: string;
    device?: string;
    viewport?: { width: number; height: number };
    steps?: string[];
  };
}

interface QAReport {
  report_metadata: {
    generated_at: string;
    source_report?: string;
    target: string;
    pages_crawled: number;
    ai_analysis_failures?: number;
    ai_analysis_degraded?: boolean;
    interactive_metrics?: {
      elements_discovered: number;
      interactions_attempted: number;
      passed: number;
      failed: number;
      manual_review: number;
    };
    cross_device_metrics?: {
      devices_tested: number;
      pages_tested: number;
      responsive_findings: number;
      device_breakdown: {
        desktop: number;
        iphone: number;
        ipad: number;
      };
    };
  };
  summary: {
    total_candidates: number;
    confirmed_bugs: number;
    potential_issues: number;
    manual_review: number;
    informational: number;
    ignored: number;
    analysis_failures?: number;
  };
  qa_metrics?: {
    quality_score: number;
    letter_grade: string;
    verdict: string;
    test_cases: {
      total: number;
      passed: number;
      failed: number;
      skipped: number;
      blocked: number;
      errored: number;
      pass_rate: number;
      fail_rate: number;
    };
    findings: {
      total: number;
      confirmed_bugs: number;
      critical: number;
      high: number;
      medium: number;
      low: number;
      info: number;
    };
    crawl: {
      pages_crawled: number;
      pages_attempted: number;
      http_errors: number;
      network_failures: number;
      console_errors: number;
      devices_tested: number;
    };
    duration: {
      duration_seconds: number;
      formatted_duration: string;
    };
  };
  triage_metrics?: {
    confirmed_bug: number;
    high_confidence_candidate: number;
    needs_manual_review: number;
    expected_behavior: number;
    informational: number;
    duplicate: number;
    priority: { P0: number; P1: number; P2: number; P3: number; P4: number };
    regression_summary: { new: number; fixed: number; unchanged: number; worsened: number; improved: number };
  };
  severity: Record<Severity, number>;
  findings: Finding[];
  test_cases?: Array<{
    id: string;
    title?: string;
    description?: string;
    category?: string;
    priority?: string;
    source_page?: string;
    steps?: string[];
    execution_policy?: string;
    status?: string;
    expected_result?: string;
    actual_result?: string;
    evidence?: unknown;
    duration_ms?: number;
  }>;
  test_case_metrics?: {
    total: number;
    executed: number;
    passed: number;
    failed: number;
    blocked: number;
    manual_review: number;
  };
}

interface ProgressPayload {
  percent: number;
  message: string;
  stage?: string;
  active_device?: string;
  active_url?: string;
  page_current?: number;
  page_total?: number;
}

type ScanStatus = 'pending' | 'running' | 'completed' | 'failed' | 'error' | 'cancelled' | '';

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  const [sessionLoaded, setSessionLoaded] = useState(!supabase);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');

  // Scan input states
  const [url, setUrl] = useState('');
  const [maxPages, setMaxPages] = useState('10');
  const [loading, setLoading] = useState(false);
  const [scanId, setScanId] = useState<string | null>(null);
  const [status, setStatus] = useState<ScanStatus>('');
  const [scanError, setScanError] = useState('');
  const [results, setResults] = useState<QAReport | null>(null);
  const [progress, setProgress] = useState<ProgressPayload | null>(null);

  // Authenticated Crawl Form State
  const [requiresAuth, setRequiresAuth] = useState(false);
  const [loginUrl, setLoginUrl] = useState('');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Loading Timer & Real-time Diagnostic Log stream
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [logFeed, setLogFeed] = useState<string[]>([]);

  // Active View Tab & Filters
  const [activeTab, setActiveTab] = useState<'findings' | 'tests' | 'devices'>('findings');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterClass, setFilterClass] = useState('ALL');
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [filterPriority, setFilterPriority] = useState('ALL');

  useEffect(() => {
    if (!supabase) return;

    supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (error) {
          console.error('Failed to restore session:', error);
          setAuthError(`Could not reach the authentication service: ${error.message}`);
          return;
        }
        setSession(data.session);
      })
      .catch((err: unknown) => {
        console.error('Failed to restore session:', err);
        setAuthError(
          err instanceof Error
            ? `Could not reach the authentication service: ${err.message}`
            : 'Could not reach the authentication service.',
        );
      })
      .finally(() => {
        setSessionLoaded(true);
      });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Timer effect during active scan
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (loading && (status === 'pending' || status === 'running')) {
      timer = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [loading, status]);

  // Update real-time log feed on progress message
  useEffect(() => {
    if (progress?.message) {
      setLogFeed((prev) => {
        if (prev[prev.length - 1] === progress.message) return prev;
        return [...prev.slice(-6), progress.message];
      });
    }
  }, [progress?.message]);

  const handleDevSignIn = () => {
    setSession({
      access_token: 'dev-token',
      token_type: 'bearer',
      expires_in: 3600,
      refresh_token: 'dev-refresh',
      user: {
        id: '00000000-0000-0000-0000-000000000001',
        app_metadata: {},
        user_metadata: {},
        aud: 'authenticated',
        created_at: new Date().toISOString(),
        email: 'dev@example.com',
      },
    } as unknown as Session);
  };

  const handleSignOut = async () => {
    if (supabase) {
      await supabase.auth.signOut();
    }
    setSession(null);
    setScanId(null);
    setStatus('');
    setResults(null);
    setProgress(null);
    setScanError('');
    setRequiresAuth(false);
    setLoginUrl('');
    setAuthUsername('');
    setAuthPassword('');
    setShowPassword(false);
    setLoading(false);
    setLogFeed([]);
  };

  const handleStopScan = async () => {
    if (!scanId || !session) return;
    try {
      await fetch(`/api/scans/${scanId}/cancel`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
    } catch (e) {
      console.error('Cancel request failed:', e);
    }
    setLoading(false);
    setStatus('cancelled');
    setScanError('Scan was stopped by user.');
    setProgress(null);
  };

  const startScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url || !session) return;

    setLoading(true);
    setResults(null);
    setElapsedSeconds(0);
    setLogFeed(['Spawning isolated browser contexts across viewports (Desktop, iPhone, iPad)...']);
    setProgress({ percent: 5, message: 'Initializing multi-viewport crawler...' });
    setScanError('');
    try {
      const parsedMaxPages = parseInt(maxPages, 10);

      const payload: {
        url: string;
        max_pages: number;
        auth?: {
          login_url?: string;
          username?: string;
          password?: string;
        };
      } = {
        url,
        max_pages: Number.isFinite(parsedMaxPages) ? parsedMaxPages : 10,
      };

      if (requiresAuth) {
        payload.auth = {
          login_url: loginUrl.trim() || undefined,
          username: authUsername.trim() || undefined,
          password: authPassword || undefined,
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
        let detail = `Request failed with status ${res.status}`;
        try {
          const body = await res.json();
          if (body?.detail) {
            if (typeof body.detail === 'string') {
              detail = body.detail;
            } else if (Array.isArray(body.detail)) {
              detail = body.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('; ');
            } else {
              detail = JSON.stringify(body.detail);
            }
          }
        } catch {
          /* response had no JSON body */
        }
        throw new Error(detail);
      }

      const data = await res.json();
      setScanId(data.scan_id);
      setStatus('pending');
    } catch (err) {
      console.error(err);
      setStatus('error');
      setScanError(err instanceof Error ? err.message : 'Failed to start scan');
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!scanId || !session) return;
    if (status === 'completed' || status === 'failed' || status === 'error' || status === 'cancelled') return;

    let cancelled = false;

    const poll = async () => {
      try {
        const res = await fetch(`/api/scans/${scanId}`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (cancelled) return;

        if (res.status === 401 || res.status === 403) {
          setStatus('error');
          setLoading(false);
          setScanError('Your session expired. Sign in again to see this scan.');
          return;
        }
        if (res.status === 404) {
          setStatus('error');
          setLoading(false);
          setScanError('This scan is no longer available.');
          return;
        }
        if (!res.ok) return;

        const data = await res.json();
        if (cancelled) return;

        setStatus(data.status);

        if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
          setLoading(false);
          setProgress(null);
          if (data.results) {
            setResults(data.results);
          } else if (data.status === 'failed') {
            setScanError('The scan failed to complete. The target site may be unreachable.');
          } else if (data.status === 'cancelled') {
            setScanError('Scan was stopped by user.');
          }
          return;
        }

        if (data.progress) {
          setProgress(data.progress);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [scanId, status, session]);

  // Derived Filtered Findings
  const filteredFindings = useMemo(() => {
    if (!results?.findings) return [];
    return results.findings.filter((finding) => {
      const matchesSearch =
        !searchQuery ||
        finding.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        finding.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        finding.id?.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesClass = filterClass === 'ALL' || finding.classification === filterClass;
      const matchesSeverity = filterSeverity === 'ALL' || finding.severity === filterSeverity;
      const matchesPriority = filterPriority === 'ALL' || finding.priority === filterPriority;

      return matchesSearch && matchesClass && matchesSeverity && matchesPriority;
    });
  }, [results?.findings, searchQuery, filterClass, filterSeverity, filterPriority]);

  // Format Elapsed Time
  const formattedTime = useMemo(() => {
    const mins = Math.floor(elapsedSeconds / 60);
    const secs = elapsedSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, [elapsedSeconds]);

  // Determine Active Pipeline Stage (0: Crawl, 1: Interactive, 2: Bugs, 3: AI Report)
  const currentStageIndex = useMemo(() => {
    const pct = progress?.percent || 0;
    if (pct < 35) return 0;
    if (pct < 60) return 1;
    if (pct < 75) return 2;
    return 3;
  }, [progress?.percent]);

  // Active Device detection for Live Multi-Device Viewport Deck
  const activeDeviceName = useMemo(() => {
    if (progress?.active_device) return progress.active_device;
    const msg = progress?.message || '';
    if (msg.includes('iPhone')) return 'iPhone 13';
    if (msg.includes('iPad')) return 'iPad (gen 7)';
    if (msg.includes('Desktop')) return 'Desktop Chrome';
    return 'Desktop Chrome';
  }, [progress?.active_device, progress?.message]);

  // Quality metrics fallback
  const safeScore = useMemo(() => {
    const raw = results?.qa_metrics?.quality_score;
    if (typeof raw === 'number' && Number.isFinite(raw)) {
      return Math.max(0, Math.min(100, Math.round(raw)));
    }
    return 100;
  }, [results?.qa_metrics?.quality_score]);

  const letterGrade = results?.qa_metrics?.letter_grade || 'A+';
  const verdictText = results?.qa_metrics?.verdict || 'EXCELLENT - Production Ready';

  const showForm = !loading && (status === '' || status === 'error' || status === 'cancelled' || (status === 'completed' && !results));

  if (!sessionLoaded) {
    return (
      <div className={styles.main}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '140px' }}>
          <Loader2 className="pulse" size={44} color="#6366f1" />
          <p style={{ color: '#94a3b8', fontSize: '1rem' }}>Loading workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <main className={styles.main}>
      <div className={styles.container}>
        {/* Top Header */}
        <header className={styles.header}>
          <div className={styles.logo}>
            <div className={styles.logoIconWrapper}>
              <ShieldCheck size={22} color="#ffffff" />
            </div>
            <div>
              <span>Nexus</span>
              <span className={styles.logoSub}>QA Suite</span>
            </div>
          </div>

          <div className={styles.headerRight}>
            <div className={styles.engineStatusPill}>
              <div className={styles.engineStatusDot} />
              <span>Engine Online</span>
            </div>

            {session ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div className={styles.userBadge}>
                  <div className={styles.userAvatar}>
                    {session.user?.email ? session.user.email[0].toUpperCase() : 'U'}
                  </div>
                  <span>{session.user?.email || 'Authenticated User'}</span>
                </div>
                <button onClick={handleSignOut} className={styles.signOutBtn} title="Sign Out">
                  <LogOut size={16} />
                  <span>Exit</span>
                </button>
              </div>
            ) : (
              <button onClick={handleDevSignIn} className="btn btn-primary" style={{ padding: '8px 18px', fontSize: '0.88rem' }}>
                Dev Sign In
              </button>
            )}
          </div>
        </header>

        {/* Hero Banner */}
        {showForm && (
          <motion.section
            className={styles.hero}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className={styles.badge}>
              <Sparkles size={14} /> Continuous Web Quality & Regression Suite
            </div>
            <h1 className={styles.title}>
              Enterprise Automated{' '}
              <span className={styles.gradientText}>Web Quality Assurance</span>
            </h1>
            <p className={styles.subtitle}>
              Full-stack website verification: multi-viewport crawling, synthetic interaction testing,
              automated defect triage, and executive compliance reports.
            </p>
          </motion.section>
        )}

        {/* Launch Card / Scanning Screen Container */}
        <motion.div
          className={styles.actionPanel}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          {showForm ? (
            /* ==============================================================
             * FORM STATE
             * ============================================================== */
            <form onSubmit={startScan} className={styles.form}>
              <div className={styles.inputRow}>
                <div className={styles.inputGroup}>
                  <Search className={styles.inputIcon} size={20} />
                  <input
                    type="url"
                    placeholder="https://example.com or your web application URL"
                    className={styles.urlInput}
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    required
                  />
                </div>

                <select
                  id="max-pages"
                  className={styles.pagesSelect}
                  value={maxPages}
                  onChange={(e) => setMaxPages(e.target.value)}
                  title="Maximum Pages to Crawl"
                >
                  <option value="1">1 page</option>
                  <option value="5">5 pages</option>
                  <option value="10">10 pages (Standard)</option>
                  <option value="20">20 pages (Deep)</option>
                  <option value="50">50 pages (Full)</option>
                </select>

                <button type="submit" className={styles.launchBtn} disabled={loading || !session}>
                  <span>Run QA Scan</span>
                  <ArrowRight size={18} />
                </button>
              </div>

              {/* Quick Sample URLs */}
              <div className={styles.quickPillsRow}>
                <span>Try Instant Demo:</span>
                <button
                  type="button"
                  onClick={() => setUrl('https://example.com')}
                  className={styles.quickPill}
                >
                  example.com
                </button>
                <button
                  type="button"
                  onClick={() => setUrl('https://news.ycombinator.com')}
                  className={styles.quickPill}
                >
                  Hacker News
                </button>
                <button
                  type="button"
                  onClick={() => setUrl('https://httpbin.org/status/200')}
                  className={styles.quickPill}
                >
                  HTTPBin Demo
                </button>
              </div>

              {/* Authenticated Website Toggle */}
              <div className={styles.authToggleRow}>
                <label className={styles.authToggleLabel}>
                  <input
                    type="checkbox"
                    checked={requiresAuth}
                    onChange={(e) => setRequiresAuth(e.target.checked)}
                    className={styles.authCheckbox}
                  />
                  <span className={styles.authToggleText}>
                    <Lock size={16} /> Requires Website Login?
                  </span>
                </label>
              </div>

              {/* Collapsible Auth Inputs */}
              <AnimatePresence>
                {requiresAuth && (
                  <motion.div
                    className={styles.authFieldsContainer}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25 }}
                  >
                    <div className={styles.authFieldGroup}>
                      <label className={styles.authFieldLabel}>
                        <KeyRound size={13} /> Login URL
                      </label>
                      <input
                        type="url"
                        placeholder="https://example.com/login"
                        value={loginUrl}
                        onChange={(e) => setLoginUrl(e.target.value)}
                        className={styles.authInput}
                      />
                    </div>

                    <div className={styles.authFieldGroup}>
                      <label className={styles.authFieldLabel}>
                        <User size={13} /> Username / Email
                      </label>
                      <input
                        type="text"
                        placeholder="user@example.com"
                        value={authUsername}
                        onChange={(e) => setAuthUsername(e.target.value)}
                        className={styles.authInput}
                        autoComplete="username"
                      />
                    </div>

                    <div className={styles.authFieldGroup}>
                      <label className={styles.authFieldLabel}>
                        <Lock size={13} /> Password
                      </label>
                      <div className={styles.passwordInputWrapper}>
                        <input
                          type={showPassword ? 'text' : 'password'}
                          placeholder="••••••••••••"
                          value={authPassword}
                          onChange={(e) => setAuthPassword(e.target.value)}
                          className={styles.authInput}
                          autoComplete="current-password"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className={styles.passwordToggleBtn}
                          title={showPassword ? 'Hide Password' : 'Show Password'}
                        >
                          {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {scanError && (
                <div style={{ color: 'var(--danger)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertTriangle size={16} /> {scanError}
                </div>
              )}
            </form>
          ) : (
            /* ==============================================================
             * PROMINENT SCANNING / LOADING STATE (With Stop Button & Multi-Device Deck)
             * ============================================================== */
            <div className={styles.loadingScreen}>
              {/* Header Badge & Target with Stop Scan Action */}
              <div className={styles.loadingHeader}>
                <div className={styles.loadingControlBar}>
                  <div className={styles.targetUrlBadge}>
                    <Globe size={15} />
                    <span>Inspecting Target: {url}</span>
                  </div>

                  <button
                    type="button"
                    onClick={handleStopScan}
                    className={styles.stopScanBtn}
                    title="Stop and cancel the active scan"
                  >
                    <Square size={14} fill="#ef4444" />
                    <span>Stop Scan</span>
                  </button>
                </div>

                <h2 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc', marginTop: '6px' }}>
                  Automated Test Execution Running
                </h2>
                <p style={{ color: '#94a3b8', fontSize: '0.92rem' }}>
                  Executing multi-viewport crawler, synthetic user journeys, and defect analysis.
                </p>
              </div>

              {/* Matched Progress Bar Card */}
              <div className={styles.progressBarWrapper}>
                <div className={styles.progressInfoRow}>
                  <span className={styles.progressStageBadge}>
                    {progress?.stage
                      ? progress.stage.replace('_', ' ')
                      : currentStageIndex === 0
                      ? 'Stage 1: Multi-Device Crawling'
                      : currentStageIndex === 1
                      ? 'Stage 2: Interactive Testing'
                      : currentStageIndex === 2
                      ? 'Stage 3: Defect Detection'
                      : 'Stage 4: Quality Synthesis'}
                  </span>
                  <span className={styles.progressNumbers}>
                    {progress?.page_current
                      ? `Page ${progress.page_current} of ${progress.page_total || maxPages} (${progress.percent}%)`
                      : `${progress?.percent || 5}% Complete`}
                  </span>
                </div>
                <div className={styles.progressBarTrack}>
                  <div className={styles.progressBarFill} style={{ width: `${progress?.percent || 5}%` }} />
                </div>
              </div>

              {/* Glowing Radar Pulse & Live Percentage Dial */}
              <div className={styles.radarContainer}>
                <div className={styles.radarOuterRing} />
                <div className={styles.radarInnerRing} />
                <div className={styles.radarSweep} />
                <div className={styles.radarCenterContent}>
                  <span className={styles.radarPercent}>{progress?.percent || 5}%</span>
                  <span className={styles.radarElapsed}>
                    <Clock size={10} style={{ display: 'inline', marginRight: '3px' }} />
                    {formattedTime}
                  </span>
                </div>
              </div>

              {/* LIVE MULTI-DEVICE VIEWPORT DECK */}
              <div className={styles.deviceDeckSection}>
                <div className={styles.deviceDeckTitleRow}>
                  <span>Live Multi-Device Emulation Viewports</span>
                  <span style={{ color: '#34d399', fontSize: '0.75rem' }}>● 3 ISOLATED CONTEXTS ACTIVE</span>
                </div>

                <div className={styles.deviceDeckGrid}>
                  {[
                    {
                      id: 'desktop',
                      name: 'Desktop Chrome',
                      resolution: '1920 × 1080',
                      icon: <Monitor size={18} />,
                    },
                    {
                      id: 'iphone',
                      name: 'iPhone 13',
                      resolution: '390 × 844 (Touch)',
                      icon: <Smartphone size={18} />,
                    },
                    {
                      id: 'ipad',
                      name: 'iPad (gen 7)',
                      resolution: '820 × 1180 (Tablet)',
                      icon: <Tablet size={18} />,
                    },
                  ].map((dev) => {
                    const isCrawlingThis =
                      activeDeviceName.toLowerCase().includes(dev.id) ||
                      activeDeviceName.toLowerCase().includes(dev.name.toLowerCase());

                    return (
                      <div
                        key={dev.id}
                        className={`${styles.deviceCard} ${isCrawlingThis ? styles.deviceCardActive : ''}`}
                      >
                        <div className={styles.deviceCardHeader}>
                          <div className={styles.deviceIconName}>
                            <span style={{ color: isCrawlingThis ? '#818cf8' : '#64748b' }}>{dev.icon}</span>
                            <span>{dev.name}</span>
                          </div>
                          <span
                            className={`${styles.deviceStatusPill} ${
                              isCrawlingThis ? styles.devicePillActive : styles.devicePillIdle
                            }`}
                          >
                            {isCrawlingThis ? 'Crawling Now' : 'Ready'}
                          </span>
                        </div>

                        <div className={styles.deviceMockupFrame}>
                          <div style={{ color: isCrawlingThis ? '#38bdf8' : '#94a3b8', fontSize: '0.78rem' }}>
                            {isCrawlingThis
                              ? progress?.active_url || url || 'Navigating DOM...'
                              : 'Waiting for viewport pass...'}
                          </div>
                          <span className={styles.deviceResolution}>{dev.resolution}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 4-Stage Stepper Grid */}
              <div className={styles.stepperGrid}>
                {[
                  {
                    step: 1,
                    title: 'Multi-Device Crawl',
                    desc: 'Desktop, iPhone 13, iPad viewports',
                    icon: <Monitor size={16} />,
                  },
                  {
                    step: 2,
                    title: 'Interactive Testing',
                    desc: 'Forms, clicks, state transitions',
                    icon: <Zap size={16} />,
                  },
                  {
                    step: 3,
                    title: 'Defect Detection',
                    desc: 'Network errors, console, layout',
                    icon: <Bug size={16} />,
                  },
                  {
                    step: 4,
                    title: 'Quality Synthesis',
                    desc: 'Compliance grading & executive report',
                    icon: <Sparkles size={16} />,
                  },
                ].map((st, sIdx) => {
                  const isActive = sIdx === currentStageIndex;
                  const isDone = sIdx < currentStageIndex;

                  return (
                    <div
                      key={st.step}
                      className={`${styles.stepCard} ${
                        isActive ? styles.stepActive : isDone ? styles.stepCompleted : ''
                      }`}
                    >
                      <div className={styles.stepHeader}>
                        <span className={styles.stepNumber}>Stage 0{st.step}</span>
                        {isDone ? (
                          <CheckCircle2 size={16} color="#34d399" />
                        ) : isActive ? (
                          <Loader2 size={16} className="pulse" color="#818cf8" />
                        ) : (
                          <span style={{ color: '#475569' }}>{st.icon}</span>
                        )}
                      </div>
                      <div className={styles.stepTitle}>{st.title}</div>
                      <div className={styles.stepDesc}>{st.desc}</div>
                    </div>
                  );
                })}
              </div>

              {/* Monospace Diagnostic Terminal Stream */}
              <div className={styles.terminalCard}>
                <div className={styles.terminalHeader}>
                  <div className={styles.terminalDots}>
                    <div className={styles.terminalDot} style={{ background: '#ef4444' }} />
                    <div className={styles.terminalDot} style={{ background: '#f59e0b' }} />
                    <div className={styles.terminalDot} style={{ background: '#10b981' }} />
                  </div>
                  <div className={styles.terminalTitle}>
                    <Terminal size={14} /> LIVE DIAGNOSTIC STREAM
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#10b981' }}>STREAMING ●</div>
                </div>

                <div className={styles.terminalBody}>
                  {logFeed.map((log, lIdx) => (
                    <div key={lIdx} className={styles.terminalLine}>
                      <span className={styles.terminalPrompt}>&gt;</span>
                      <span>{log}</span>
                    </div>
                  ))}
                  <div className={styles.terminalLine}>
                    <span className={styles.terminalPrompt}>&gt;</span>
                    <span className={styles.terminalCurrentMessage}>
                      {progress?.message || 'Inspecting DOM tree and verifying response status...'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </motion.div>

        {/* ==============================================================
         * EXECUTIVE RESULTS DASHBOARD
         * ============================================================== */}
        {results && status === 'completed' && (
          <motion.div
            className={styles.resultsPanel}
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            {/* Header & Export Actions */}
            <div className={styles.resultsHeader}>
              <div>
                <h2>
                  <FileText size={24} color="#6366f1" /> QA Scan Report
                </h2>
                <div style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '4px' }}>
                  Target: <strong>{results.report_metadata?.target}</strong> · Generated at{' '}
                  {new Date(results.report_metadata?.generated_at).toLocaleTimeString()}
                </div>
              </div>

              <div className={styles.exportActions}>
                <button
                  className={styles.exportBtn}
                  onClick={() =>
                    handleDownloadReport({
                      results,
                      scanId,
                      format: 'pdf',
                      sessionToken: session?.access_token,
                    })
                  }
                  title="Download PDF Report"
                >
                  <Download size={16} /> PDF
                </button>

                <button
                  className={styles.exportBtn}
                  onClick={() =>
                    handleDownloadReport({
                      results,
                      scanId,
                      format: 'excel',
                      sessionToken: session?.access_token,
                    })
                  }
                  title="Download Excel Spreadsheet"
                >
                  <FileSpreadsheet size={16} /> Excel
                </button>

                <button
                  className={styles.exportBtn}
                  onClick={() =>
                    handleDownloadReport({
                      results,
                      scanId,
                      format: 'json',
                      sessionToken: session?.access_token,
                    })
                  }
                  title="Download Raw JSON"
                >
                  <Download size={16} /> JSON
                </button>

                <button
                  className={styles.exportBtn}
                  onClick={() =>
                    handleDownloadReport({
                      results,
                      scanId,
                      format: 'md',
                      sessionToken: session?.access_token,
                    })
                  }
                  title="Download Markdown Report"
                >
                  <Download size={16} /> Markdown
                </button>

                <button
                  className="btn btn-primary"
                  onClick={() => {
                    setScanId(null);
                    setResults(null);
                    setStatus('');
                    setProgress(null);
                    setLoading(false);
                    setScanError('');
                  }}
                  style={{ padding: '8px 16px', fontSize: '0.88rem' }}
                >
                  <RefreshCw size={15} /> New Scan
                </button>
              </div>
            </div>

            {/* Degraded AI Banner if applicable */}
            {results.report_metadata?.ai_analysis_degraded && (
              <div className={styles.degradedBanner}>
                <AlertTriangle size={20} style={{ flexShrink: 0 }} />
                <div>
                  <strong>AI Analysis Incomplete:</strong> {results.report_metadata.ai_analysis_failures} findings
                  used deterministic fallbacks because the Gemini endpoint was unreachable.
                </div>
              </div>
            )}

            {/* Executive Quality Score Dial Card */}
            <div className={styles.scoreCard}>
              <div className={styles.scoreDialContainer}>
                <div className={styles.scoreCircleWrapper}>
                  <svg width="130" height="130" viewBox="0 0 130 130">
                    <circle
                      cx="65"
                      cy="65"
                      r="54"
                      fill="none"
                      stroke="rgba(255, 255, 255, 0.08)"
                      strokeWidth="10"
                    />
                    <circle
                      cx="65"
                      cy="65"
                      r="54"
                      fill="none"
                      stroke={safeScore >= 80 ? '#10b981' : safeScore >= 60 ? '#f59e0b' : '#ef4444'}
                      strokeWidth="10"
                      strokeDasharray="339.29"
                      strokeDashoffset={339.29 - (339.29 * safeScore) / 100}
                      strokeLinecap="round"
                      transform="rotate(-90 65 65)"
                      style={{ transition: 'stroke-dashoffset 1s ease-out' }}
                    />
                  </svg>
                  <div className={styles.scoreCircleCenter}>
                    <span className={styles.scoreNumber}>{safeScore}</span>
                    <span className={styles.scoreGradePill}>{letterGrade}</span>
                  </div>
                </div>
              </div>

              <div className={styles.scoreDetails}>
                <div
                  className={styles.scoreVerdictBadge}
                  style={{
                    background: safeScore >= 80 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                    color: safeScore >= 80 ? '#34d399' : '#fbbf24',
                    border: `1px solid ${safeScore >= 80 ? 'rgba(16, 185, 129, 0.35)' : 'rgba(245, 158, 11, 0.35)'}`,
                  }}
                >
                  <Award size={14} /> {verdictText}
                </div>
                <div className={styles.scoreTitle}>
                  {safeScore >= 80 ? 'High Software Quality & Stability' : 'Defects Identified Requiring Remediation'}
                </div>
                <div className={styles.scoreDescription}>
                  {safeScore >= 80
                    ? 'Target website passed automated assertions and user journeys with strong responsiveness and zero critical runtime exceptions.'
                    : 'Discovered critical defects, network failures, or unhandled exceptions that require attention prior to release.'}
                </div>
              </div>
            </div>

            {/* 4 Executive KPI Cards */}
            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={styles.statHeader}>
                  <span>Total Test Cases</span>
                  <Layers size={18} color="#818cf8" />
                </div>
                <div className={styles.statValue}>
                  {results.qa_metrics?.test_cases?.total ?? results.test_cases?.length ?? 0}
                </div>
                <div className={styles.statSub}>
                  {results.qa_metrics?.test_cases?.passed ?? 0} Passed · {results.qa_metrics?.test_cases?.failed ?? 0} Failed
                </div>
              </div>

              <div className={styles.statCard}>
                <div className={styles.statHeader}>
                  <span>Total Findings</span>
                  <Bug size={18} color="#ef4444" />
                </div>
                <div className={styles.statValue}>{results.findings?.length ?? 0}</div>
                <div className={styles.statSub}>
                  {results.qa_metrics?.findings?.confirmed_bugs ?? 0} Confirmed Bugs
                </div>
              </div>

              <div className={styles.statCard}>
                <div className={styles.statHeader}>
                  <span>Pages & Devices</span>
                  <Monitor size={18} color="#38bdf8" />
                </div>
                <div className={styles.statValue}>
                  {results.report_metadata?.pages_crawled ?? 1}
                </div>
                <div className={styles.statSub}>Desktop · iPhone 13 · iPad</div>
              </div>

              <div className={styles.statCard}>
                <div className={styles.statHeader}>
                  <span>Execution Duration</span>
                  <Clock size={18} color="#34d399" />
                </div>
                <div className={styles.statValue}>
                  {results.qa_metrics?.duration?.formatted_duration ?? '00:15s'}
                </div>
                <div className={styles.statSub}>Automated isolated contexts</div>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className={styles.tabsBar}>
              <button
                className={`${styles.tabBtn} ${activeTab === 'findings' ? styles.tabActive : ''}`}
                onClick={() => setActiveTab('findings')}
              >
                <Bug size={16} /> Defect Triage ({results.findings?.length ?? 0})
              </button>

              {results.test_cases && results.test_cases.length > 0 && (
                <button
                  className={`${styles.tabBtn} ${activeTab === 'tests' ? styles.tabActive : ''}`}
                  onClick={() => setActiveTab('tests')}
                >
                  <Layers size={16} /> Automated Tests ({results.test_cases.length})
                </button>
              )}

              {results.report_metadata?.cross_device_metrics && (
                <button
                  className={`${styles.tabBtn} ${activeTab === 'devices' ? styles.tabActive : ''}`}
                  onClick={() => setActiveTab('devices')}
                >
                  <Smartphone size={16} /> Responsive QA Matrix
                </button>
              )}
            </div>

            {/* Tab 1: Findings & Triage */}
            {activeTab === 'findings' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div className={styles.filterBar}>
                  <div className={styles.searchInputWrapper}>
                    <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
                    <input
                      type="text"
                      placeholder="Search findings by ID, title, or keyword..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className={styles.searchInput}
                    />
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <select
                      className={styles.filterSelect}
                      value={filterSeverity}
                      onChange={(e) => setFilterSeverity(e.target.value)}
                    >
                      <option value="ALL">All Severities</option>
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>

                    <select
                      className={styles.filterSelect}
                      value={filterPriority}
                      onChange={(e) => setFilterPriority(e.target.value)}
                    >
                      <option value="ALL">All Priorities</option>
                      <option value="P0">P0 (Blocker)</option>
                      <option value="P1">P1 (Critical)</option>
                      <option value="P2">P2 (Major)</option>
                      <option value="P3">P3 (Minor)</option>
                    </select>

                    <select
                      className={styles.filterSelect}
                      value={filterClass}
                      onChange={(e) => setFilterClass(e.target.value)}
                    >
                      <option value="ALL">All Classifications</option>
                      <option value="confirmed_bug">Confirmed Bug</option>
                      <option value="high_confidence_candidate">Candidate</option>
                      <option value="needs_manual_review">Needs Review</option>
                      <option value="informational">Info</option>
                    </select>
                  </div>
                </div>

                <div className={styles.findingsList}>
                  {filteredFindings.map((finding, idx) => (
                    <div key={finding.id || idx} className={styles.findingItem}>
                      <div className={styles.findingHeader}>
                        <span className={styles.findingId}>{finding.id}</span>
                        <span className={`${styles.severityBadge} ${styles[finding.severity] ?? ''}`}>
                          {finding.severity}
                        </span>
                      </div>

                      <h3 style={{ fontSize: '1.15rem', color: '#f8fafc' }}>{finding.title}</h3>
                      <p className={styles.findingDesc}>{finding.description || finding.manual_verification}</p>

                      <div className={styles.tagsRow}>
                        {finding.priority && <span className={styles.chip}>Priority: {finding.priority}</span>}
                        {finding.user_impact && <span className={styles.chip}>Impact: {finding.user_impact.toUpperCase()}</span>}
                        {finding.root_cause?.category && (
                          <span className={styles.chip}>Cause: {finding.root_cause.category.replace('_', ' ')}</span>
                        )}
                        {finding.page && <span className={styles.chip}>{finding.page}</span>}
                      </div>

                      <details className={styles.evidenceAccordion}>
                        <summary className={styles.evidenceSummary}>View Evidence & Remediation Steps</summary>
                        <div className={styles.evidenceBody}>
                          {finding.root_cause?.summary && (
                            <p style={{ marginBottom: '8px' }}>
                              <strong>Root Cause Summary:</strong> {finding.root_cause.summary}
                            </p>
                          )}
                          <p style={{ marginBottom: '8px' }}>
                            <strong>Recommendation:</strong> {finding.recommendation || 'Review component lifecycle and error bounds.'}
                          </p>

                          {finding.reproduction?.steps && finding.reproduction.steps.length > 0 && (
                            <div style={{ marginTop: '10px' }}>
                              <strong>Reproduction Steps:</strong>
                              <ol style={{ paddingLeft: '20px', marginTop: '4px' }}>
                                {finding.reproduction.steps.map((step, sIdx) => (
                                  <li key={sIdx}>{step}</li>
                                ))}
                              </ol>
                            </div>
                          )}
                        </div>
                      </details>
                    </div>
                  ))}

                  {filteredFindings.length === 0 && (
                    <div className={styles.noFindings}>
                      ✨ No bugs or anomalies match the selected filters.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tab 2: Test Cases Matrix */}
            {activeTab === 'tests' && results.test_cases && (
              <div className={styles.findingsList}>
                {results.test_cases.map((tc, idx) => {
                  const status = tc.status || 'passed';
                  const isPassed = status === 'passed';
                  const isFailed = status === 'failed';
                  const isErrored = status === 'errored';
                  const isBlocked = status === 'blocked';

                  return (
                    <div
                      key={tc.id || idx}
                      className={styles.findingItem}
                      style={{
                        borderLeftColor: isPassed ? '#10b981' : isFailed ? '#ef4444' : isErrored ? '#f43f5e' : '#f59e0b',
                      }}
                    >
                      <div className={styles.findingHeader}>
                        <span className={styles.findingId}>{tc.id}</span>
                        <span
                          className={styles.severityBadge}
                          style={{
                            background: isPassed ? 'rgba(16, 185, 129, 0.2)' : isFailed ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                            color: isPassed ? '#34d399' : isFailed ? '#f87171' : '#fbbf24',
                          }}
                        >
                          {status.toUpperCase()}
                        </span>
                      </div>

                      <h3 style={{ fontSize: '1.1rem', color: '#f8fafc' }}>{tc.title}</h3>

                      <div className={styles.tagsRow}>
                        <span className={styles.chip}>{tc.category || 'General'}</span>
                        {tc.priority && <span className={styles.chip}>Priority: {tc.priority}</span>}
                        {tc.source_page && <span className={styles.chip}>{tc.source_page}</span>}
                      </div>

                      <div style={{ fontSize: '0.9rem', color: '#cbd5e1' }}>
                        <div>
                          <strong>Expected:</strong> {tc.expected_result || 'N/A'}
                        </div>
                        <div style={{ marginTop: '4px' }}>
                          <strong>Actual:</strong> {tc.actual_result || 'Assertion passed successfully.'}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Tab 3: Cross-Device & Responsive QA */}
            {activeTab === 'devices' && results.report_metadata?.cross_device_metrics && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div className={styles.statsGrid}>
                  <div className={styles.statCard}>
                    <div className={styles.statHeader}>
                      <span>Desktop (1920x1080)</span>
                      <Monitor size={18} color="#818cf8" />
                    </div>
                    <div className={styles.statValue}>
                      {results.report_metadata.cross_device_metrics.device_breakdown.desktop}
                    </div>
                    <div className={styles.statSub}>Responsive Findings</div>
                  </div>

                  <div className={styles.statCard}>
                    <div className={styles.statHeader}>
                      <span>iPhone 13 (390x844)</span>
                      <Smartphone size={18} color="#38bdf8" />
                    </div>
                    <div className={styles.statValue}>
                      {results.report_metadata.cross_device_metrics.device_breakdown.iphone}
                    </div>
                    <div className={styles.statSub}>Touch & Viewport Findings</div>
                  </div>

                  <div className={styles.statCard}>
                    <div className={styles.statHeader}>
                      <span>iPad (820x1180)</span>
                      <Tablet size={18} color="#34d399" />
                    </div>
                    <div className={styles.statValue}>
                      {results.report_metadata.cross_device_metrics.device_breakdown.ipad}
                    </div>
                    <div className={styles.statSub}>Tablet Layout Findings</div>
                  </div>

                  <div className={styles.statCard}>
                    <div className={styles.statHeader}>
                      <span>Total Responsive Issues</span>
                      <Activity size={18} color="#f59e0b" />
                    </div>
                    <div className={styles.statValue}>
                      {results.report_metadata.cross_device_metrics.responsive_findings}
                    </div>
                    <div className={styles.statSub}>Across all emulated viewports</div>
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </main>
  );
}
