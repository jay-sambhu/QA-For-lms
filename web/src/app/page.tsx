"use client";

import { useState, useEffect, useCallback } from 'react';
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
} from 'lucide-react';
import { motion } from 'framer-motion';
import { createClient, type Session } from '@supabase/supabase-js';
import styles from './page.module.css';
import { handleDownloadReport } from '../utils/export';

/*
 * These are read at build time by Next.js. If they are missing the Supabase
 * client cannot be constructed, so we detect that here and render an
 * actionable configuration error instead of throwing an opaque
 * "supabaseUrl is required" from deep inside the SDK.
 */
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const supabase =
  supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null;

/*
 * Shape of `final_qa_report_<timestamp>.json`, which is what
 * `GET /api/scans/{id}` embeds as `results`. This must stay in sync with
 * `qa_report_generator.py::generate_json_report`.
 */
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
  manual_verification: string;
  affected_pages_count: number;
  occurrence_count?: number;
  priority?: string;
  root_cause?: { category?: string; summary?: string };
  user_impact?: string;
  regression_status?: string;
  screenshots: string[];
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
    source_report: string;
    target: string;
    pages_crawled: number;
    // Set by stage 4 when Gemini calls failed. A report built on failed AI
    // analysis must not be presented as a clean result.
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
  // Present when the AI Test Case Generator ran and produced results.
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

type ScanStatus = '' | 'pending' | 'running' | 'completed' | 'failed' | 'error';

const POLL_INTERVAL_MS = 3000;

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  // `supabase` is a module constant, so when it is null there is no session to
  // wait for and we are "loaded" from the first render. Deriving the initial
  // value avoids a setState call in the effect body below, which would trigger
  // a cascading render.
  const [sessionLoaded, setSessionLoaded] = useState(!supabase);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');

  const [url, setUrl] = useState('');
  const [maxPages, setMaxPages] = useState('10');
  const [loading, setLoading] = useState(false);
  const [scanId, setScanId] = useState<string | null>(null);
  const [status, setStatus] = useState<ScanStatus>('');
  const [scanError, setScanError] = useState('');
  const [results, setResults] = useState<QAReport | null>(null);
  const [progress, setProgress] = useState<{percent: number, message: string} | null>(null);

  // Authenticated Crawl Form State
  const [requiresAuth, setRequiresAuth] = useState(false);
  const [loginUrl, setLoginUrl] = useState('');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  
  // Triage Filters
  const [filterClass, setFilterClass] = useState<string>('ALL');
  const [filterPriority, setFilterPriority] = useState<string>('ALL');
  const [filterRegression, setFilterRegression] = useState<string>('ALL');

  useEffect(() => {
    if (!supabase) return;

    // `sessionLoaded` gates the whole UI, so this promise must settle on every
    // path. Without the catch, an unreachable Supabase project or a bad URL
    // leaves the app on the loading spinner forever with no explanation.
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

  const handleSignUp = useCallback(async () => {
    if (!supabase) return;
    setAuthLoading(true);
    setAuthError('');
    const { error } = await supabase.auth.signUp({ email, password });
    setAuthError(error ? error.message : 'Check your email for the confirmation link!');
    setAuthLoading(false);
  }, [email, password]);

  const handleSignIn = useCallback(async () => {
    if (!supabase) return;
    setAuthLoading(true);
    setAuthError('');
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) setAuthError(error.message);
    setAuthLoading(false);
  }, [email, password]);

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
    // Clear scan state so a different user never sees the previous one's report.
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
  };


  const startScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url || !session) return;

    setLoading(true);
    setResults(null);
    setProgress({percent: 0, message: "Initializing..."});
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
        // Surface the server's reason instead of a generic message.
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
    if (status === 'completed' || status === 'failed' || status === 'error') return;

    let cancelled = false;

    const poll = async () => {
      try {
        // The status endpoint is owner-scoped, so the access token is required.
        const res = await fetch(`/api/scans/${scanId}`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (cancelled) return;

        // A 401 or 404 will never recover on its own: the token is no longer
        // valid, or the scan does not exist / is not ours. Polling those
        // forever leaves the user watching a spinner that can never finish, so
        // stop and say why. Other failures (502, network blips) are treated as
        // transient and retried on the next tick.
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

        if (data.status === 'completed' || data.status === 'failed') {
          setLoading(false);
          setProgress(null);
          setResults(data.results ?? null);
          if (data.status === 'failed') {
            setScanError('The scan pipeline failed. Check the API logs for details.');
          }
        } else if (data.progress) {
          setProgress(data.progress);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    const interval = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [scanId, status, session]);

  if (!supabase) {
    return (
      <main className={styles.main}>
        <div className={styles.container} style={{ maxWidth: '520px', margin: 'auto' }}>
          <div className={`glass-panel ${styles.actionPanel}`}>
            <div className={styles.header}>
              <AlertTriangle size={48} color="var(--danger)" />
              <h2>Configuration required</h2>
              <p className={styles.subtext}>
                Set <code>NEXT_PUBLIC_SUPABASE_URL</code> and{' '}
                <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> in <code>web/.env.local</code>, then
                restart the dev server.
              </p>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // Avoid flashing the sign-in screen before the stored session is restored.
  if (!sessionLoaded) {
    return (
      <main className={styles.main}>
        <div className={styles.container} style={{ margin: 'auto', textAlign: 'center' }}>
          <Loader2 className="pulse" size={40} color="var(--primary)" />
        </div>
      </main>
    );
  }

  if (!session) {
    return (
      <main className={styles.main}>
        <div className={styles.container} style={{ maxWidth: '400px', margin: 'auto' }}>
          <motion.div
            className={`glass-panel ${styles.actionPanel}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className={styles.header} style={{ marginBottom: '20px' }}>
              <ShieldCheck size={48} color="var(--primary)" />
              <h2>Welcome to Antigravity QA</h2>
              <p className={styles.subtext}>Please sign in to access the platform.</p>
            </div>

            {/* onSubmit makes the Enter key sign in rather than doing nothing. */}
            <form
              className={styles.form}
              onSubmit={(e) => {
                e.preventDefault();
                void handleSignIn();
              }}
            >
              <input
                type="email"
                placeholder="Email Address"
                className="input-field"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <input
                type="password"
                placeholder="Password"
                className="input-field"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />

              {authError && (
                <div style={{ color: 'var(--danger)', fontSize: '0.9rem', textAlign: 'center' }}>
                  {authError}
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  disabled={authLoading}
                >
                  {authLoading ? <Loader2 className="pulse" /> : 'Sign In'}
                </button>
                <button
                  type="button"
                  onClick={() => void handleSignUp()}
                  className="btn"
                  style={{ flex: 1, background: 'rgba(255,255,255,0.1)' }}
                  disabled={authLoading}
                >
                  Sign Up
                </button>
                <button
                  type="button"
                  onClick={handleDevSignIn}
                  className="btn"
                  style={{ flex: 1, background: 'rgba(99, 102, 241, 0.2)', border: '1px solid var(--primary)' }}
                >
                  Dev Sign In
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      </main>
    );
  }

  const severity = results?.severity;
  const summary = results?.summary;
  const findings = results?.findings ?? [];
  
  const filteredFindings = findings.filter(f => {
    if (filterClass !== 'ALL' && f.classification !== filterClass) return false;
    if (filterPriority !== 'ALL' && (f.priority || 'P3') !== filterPriority) return false;
    if (filterRegression !== 'ALL' && (f.regression_status || 'NEW') !== filterRegression) return false;
    return true;
  });
  
  const showForm = !scanId || status === 'completed' || status === 'failed' || status === 'error';

  return (
    <main className={styles.main}>
      <div style={{ position: 'absolute', top: 20, right: 20 }}>
        <button
          onClick={handleSignOut}
          className="btn"
          style={{ background: 'rgba(255,255,255,0.1)', padding: '8px 16px', fontSize: '0.9rem' }}
        >
          <LogOut size={16} /> Sign Out
        </button>
      </div>

      <div className={styles.container}>

        {/* Header Section */}
        <motion.div
          className={styles.header}
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className={styles.badge}>
            <ShieldCheck size={16} /> AI-Powered QA Platform
          </div>
          <h1 className={styles.title}>
            Automate Your Web Testing with{' '}
            <span className={styles.gradientText}>Antigravity QA</span>
          </h1>
          <p className={styles.subtitle}>
            Enter any URL below. Our AI QA Agent will crawl your site, detect deterministic bugs,
            and use Gemini to generate a professional QA report—all while you wait.
          </p>
        </motion.div>

        {/* Action Panel */}
        <motion.div
          className={`glass-panel ${styles.actionPanel}`}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {showForm ? (
            <form onSubmit={startScan} className={styles.form}>
              <div className={styles.inputGroup}>
                <Search className={styles.inputIcon} size={20} />
                <input
                  type="url"
                  placeholder="https://example.com"
                  className="input-field"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  style={{ paddingLeft: '48px' }}
                  required
                />
              </div>
              <div className={styles.optionsGroup}>
                <label htmlFor="max-pages">Max Pages:</label>
                <select
                  id="max-pages"
                  className="input-field"
                  style={{ width: '120px' }}
                  value={maxPages}
                  onChange={(e) => setMaxPages(e.target.value)}
                >
                  <option value="1">1 page</option>
                  <option value="5">5 pages</option>
                  <option value="10">10 pages</option>
                  <option value="20">20 pages</option>
                  <option value="50">50 pages</option>
                </select>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="pulse" /> Starting...
                    </>
                  ) : (
                    <>
                      Run QA Scan <ArrowRight size={18} />
                    </>
                  )}
                </button>
              </div>

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

              {requiresAuth && (
                <motion.div
                  className={styles.authFieldsContainer}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <div className={styles.authFieldGroup}>
                    <label className={styles.authFieldLabel}>
                      <KeyRound size={14} /> Login URL
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
                      <User size={14} /> Username / Email
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
                      <Lock size={14} /> Password
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
              {scanError && (
                <div
                  style={{
                    color: 'var(--danger)',
                    fontSize: '0.9rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  <AlertTriangle size={16} /> {scanError}
                </div>
              )}
            </form>
          ) : (
            <div className={styles.statusPanel}>
              {!progress && <Loader2 className="pulse" size={48} color="var(--primary)" />}
              <h2>Scan in Progress</h2>
              <p>
                Status:{' '}
                <span style={{ textTransform: 'uppercase', color: 'var(--accent)' }}>{status}</span>
              </p>
              
              {progress ? (
                <div className={styles.progressWrapper}>
                  <div className={styles.progressText}>
                    <span>{progress.message}</span>
                    <span>{progress.percent}%</span>
                  </div>
                  <div className={styles.progressBarContainer}>
                    <div 
                      className={styles.progressBarFill} 
                      style={{ width: `${progress.percent}%` }}
                    />
                  </div>
                </div>
              ) : (
                <p className={styles.subtext}>
                  The agent is currently crawling and analyzing your website. This may take a few
                  minutes...
                </p>
              )}
            </div>
          )}
        </motion.div>

        {/* Results Section */}
        {results && status === 'completed' && (
          <motion.div
            className={`glass-panel ${styles.resultsPanel}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className={styles.resultsHeader}>
              <h2>
                <FileText size={24} /> QA Scan Report for{' '}
                {results.report_metadata?.target ?? 'Unknown target'}
              </h2>
              <div className={styles.exportActions}>
                <button
                  className={`btn ${styles.exportBtn}`}
                  onClick={() =>
                    handleDownloadReport({
                      results,
                      scanId,
                      format: 'pdf',
                      sessionToken: session?.access_token,
                    })
                  }
                  title="Download PDF"
                >
                  <Download size={18} /> PDF
                </button>
                <button
                  className={`btn ${styles.exportBtn}`}
                  onClick={() =>
                    handleDownloadReport({
                      results,
                      scanId,
                      format: 'excel',
                      sessionToken: session?.access_token,
                    })
                  }
                  title="Download Excel"
                >
                  <FileSpreadsheet size={18} /> Excel
                </button>
                <button
                  className={`btn ${styles.exportBtn}`}
                  onClick={() =>
                    handleDownloadReport({
                      results,
                      scanId,
                      format: 'json',
                      sessionToken: session?.access_token,
                    })
                  }
                  title="Download JSON"
                >
                  <Download size={18} /> JSON
                </button>
                <button
                  className={`btn ${styles.exportBtn}`}
                  onClick={() =>
                    handleDownloadReport({
                      results,
                      scanId,
                      format: 'md',
                      sessionToken: session?.access_token,
                    })
                  }
                  title="Download Markdown"
                >
                  <Download size={18} /> Markdown
                </button>
              </div>
            </div>


            {/* The markdown report warns about failed AI analysis; the UI has to
                as well, otherwise a scan where every Gemini call failed looks
                identical to a clean one. */}
            {results.report_metadata?.ai_analysis_degraded && (
              <div className={styles.degradedBanner}>
                <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                <span>
                  <strong>AI analysis was incomplete.</strong>{' '}
                  {results.report_metadata.ai_analysis_failures ?? 0} finding(s) could not be
                  analysed by the model, so their severity and recommendation below are
                  deterministic fallbacks rather than AI verdicts. Re-run the scan once the model
                  is reachable.
                </span>
              </div>
            )}

            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <h3>Total Findings</h3>
                <div className={styles.statValue}>{summary?.total_candidates ?? 0}</div>
              </div>
              <div className={styles.statCard}>
                <h3>Needs Review</h3>
                <div className={styles.statValue}>{summary?.manual_review ?? 0}</div>
              </div>
              <div className={styles.statCard}>
                <h3>Severity (High/Med/Low)</h3>
                <div className={styles.statValue}>
                  {(severity?.critical ?? 0) + (severity?.high ?? 0)} / {severity?.medium ?? 0} /{' '}
                  {severity?.low ?? 0}
                </div>
              </div>
              <div className={styles.statCard}>
                <h3>Pages Crawled</h3>
                <div className={styles.statValue}>
                  {results.report_metadata?.pages_crawled ?? 0}
                </div>
              </div>
            </div>

            {results.report_metadata?.interactive_metrics && (
              <div style={{ marginTop: '20px' }}>
                <h3 style={{ marginBottom: '10px' }}>Interactive Testing</h3>
                <div className={styles.statsGrid}>
                  <div className={styles.statCard}>
                    <h3>Elements Discovered</h3>
                    <div className={styles.statValue}>{results.report_metadata.interactive_metrics.elements_discovered}</div>
                  </div>
                  <div className={styles.statCard}>
                    <h3>Interactions Attempted</h3>
                    <div className={styles.statValue}>{results.report_metadata.interactive_metrics.interactions_attempted}</div>
                  </div>
                  <div className={styles.statCard}>
                    <h3>Passed / Failed</h3>
                    <div className={styles.statValue}>
                      {results.report_metadata.interactive_metrics.passed} / {results.report_metadata.interactive_metrics.failed}
                    </div>
                  </div>
                  <div className={styles.statCard}>
                    <h3>Destructive Skipped</h3>
                    <div className={styles.statValue}>{results.report_metadata.interactive_metrics.manual_review}</div>
                  </div>
                </div>
              </div>
            )}

            {results.report_metadata?.cross_device_metrics && (
              <div style={{ marginTop: '20px' }}>
                <h3 style={{ marginBottom: '10px' }}>Cross-Device & Responsive QA</h3>
                <div className={styles.statsGrid}>
                  <div className={styles.statCard}>
                    <h3>Devices Tested</h3>
                    <div className={styles.statValue}>Desktop | iPhone | iPad</div>
                  </div>
                  <div className={styles.statCard}>
                    <h3>Responsive Findings</h3>
                    <div className={styles.statValue}>{results.report_metadata.cross_device_metrics.responsive_findings}</div>
                  </div>
                  <div className={styles.statCard}>
                    <h3>Device Breakdown</h3>
                    <div className={styles.statValue}>
                      Desktop: {results.report_metadata.cross_device_metrics.device_breakdown.desktop} | iPhone: {results.report_metadata.cross_device_metrics.device_breakdown.iphone} | iPad: {results.report_metadata.cross_device_metrics.device_breakdown.ipad}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {results.triage_metrics && results.triage_metrics.priority && results.triage_metrics.regression_summary && (
              <div style={{ marginTop: '20px' }}>
                <h3 style={{ marginBottom: '10px' }}>AI Bug Triage Metrics</h3>
                <div className={styles.statsGrid}>
                  <div className={styles.statCard}>
                    <h3>Classification</h3>
                    <div className={styles.statValue} style={{ fontSize: '1rem', lineHeight: '1.4' }}>
                      Bugs: {results.triage_metrics.confirmed_bug ?? 0} | Candidates: {results.triage_metrics.high_confidence_candidate ?? 0}<br/>
                      Review: {results.triage_metrics.needs_manual_review ?? 0} | Duplicates: {results.triage_metrics.duplicate ?? 0}
                    </div>
                  </div>
                  <div className={styles.statCard}>
                    <h3>Priority (P0-P4)</h3>
                    <div className={styles.statValue} style={{ fontSize: '1rem', lineHeight: '1.4' }}>
                      P0: {results.triage_metrics.priority.P0 ?? 0} | P1: {results.triage_metrics.priority.P1 ?? 0} | P2: {results.triage_metrics.priority.P2 ?? 0}<br/>
                      P3: {results.triage_metrics.priority.P3 ?? 0} | P4: {results.triage_metrics.priority.P4 ?? 0}
                    </div>
                  </div>
                  <div className={styles.statCard}>
                    <h3>Regression</h3>
                    <div className={styles.statValue} style={{ fontSize: '1rem', lineHeight: '1.4' }}>
                      New: {results.triage_metrics.regression_summary.new ?? 0} | Fixed: {results.triage_metrics.regression_summary.fixed ?? 0}<br/>
                      Unchanged: {results.triage_metrics.regression_summary.unchanged ?? 0} | Worsened: {results.triage_metrics.regression_summary.worsened ?? 0}
                    </div>
                  </div>
                </div>
              </div>
            )}


            <div style={{ marginTop: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ marginBottom: '10px' }}>AI Bug Triage Findings</h3>
              
              <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                <select className="input-field" style={{ padding: '4px 8px', width: '130px', fontSize: '0.9rem' }} value={filterClass} onChange={e => setFilterClass(e.target.value)}>
                  <option value="ALL">All Class</option>
                  <option value="confirmed_bug">Confirmed Bug</option>
                  <option value="high_confidence_candidate">Candidate</option>
                  <option value="needs_manual_review">Review</option>
                  <option value="informational">Info</option>
                </select>
                <select className="input-field" style={{ padding: '4px 8px', width: '110px', fontSize: '0.9rem' }} value={filterPriority} onChange={e => setFilterPriority(e.target.value)}>
                  <option value="ALL">All Priority</option>
                  <option value="P0">P0</option>
                  <option value="P1">P1</option>
                  <option value="P2">P2</option>
                  <option value="P3">P3</option>
                  <option value="P4">P4</option>
                </select>
                <select className="input-field" style={{ padding: '4px 8px', width: '130px', fontSize: '0.9rem' }} value={filterRegression} onChange={e => setFilterRegression(e.target.value)}>
                  <option value="ALL">All Regression</option>
                  <option value="NEW">New</option>
                  <option value="UNCHANGED">Unchanged</option>
                  <option value="WORSENED">Worsened</option>
                  <option value="IMPROVED">Improved</option>
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
                  <h3>{finding.title}</h3>
                  <p className={styles.findingDesc}>
                    {finding.description || finding.manual_verification}
                  </p>
                  <div className={styles.findingFooter}>
                    <Bug size={16} /> Affects {finding.affected_pages_count ?? 1}{' '}
                    {finding.affected_pages_count === 1 ? 'page' : 'pages'}
                    {/* Pages and events are different numbers: one page can fail
                        the same request many times. */}
                    {(finding.occurrence_count ?? 0) > (finding.affected_pages_count ?? 0)
                      ? ` · ${finding.occurrence_count} occurrences`
                      : ''}
                    {finding.page ? ` · ${finding.page}` : ''}
                  </div>
                  
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '10px' }}>
                    {finding.priority && <span className={styles.badge}><AlertTriangle size={12} style={{marginRight: '4px'}}/> Priority: {finding.priority}</span>}
                    {finding.regression_status && <span className={styles.badge}><ShieldCheck size={12} style={{marginRight: '4px'}}/> Regression: {finding.regression_status}</span>}
                    {finding.user_impact && <span className={styles.badge}>Impact: {finding.user_impact.toUpperCase()}</span>}
                    {finding.root_cause?.category && <span className={styles.badge}>Root Cause: {finding.root_cause.category.replace('_', ' ')}</span>}
                  </div>
                  
                  <details style={{marginTop: '15px', background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '8px', cursor: 'pointer'}}>
                    <summary style={{fontWeight: 'bold', outline: 'none'}}>Evidence & Reproduction</summary>
                    <div style={{marginTop: '10px', fontSize: '0.9rem', lineHeight: '1.5'}}>
                      {finding.root_cause?.summary && <p><strong>Root Cause:</strong> {finding.root_cause.summary}</p>}
                      <p><strong>Expected Result:</strong> {finding.expected_result || 'Not specified.'}</p>
                      <p><strong>Actual Result:</strong> {finding.actual_result || 'Not specified.'}</p>
                      <p><strong>Recommendation:</strong> {finding.recommendation || 'Not specified.'}</p>
                      
                      {finding.reproduction && finding.reproduction.steps && finding.reproduction.steps.length > 0 && (
                        <div style={{marginTop: '10px'}}>
                          <strong>Reproduction Steps:</strong>
                          <ol style={{paddingLeft: '20px', marginTop: '5px'}}>
                            {finding.reproduction.steps.map((step, sIdx) => (
                              <li key={sIdx}>{step}</li>
                            ))}
                          </ol>
                        </div>
                      )}
                      
                      {finding.reproduction?.device && (
                         <p style={{marginTop: '10px'}}><strong>Device:</strong> {finding.reproduction.device}</p>
                      )}
                      {finding.reproduction?.viewport && (
                         <p><strong>Viewport:</strong> {finding.reproduction.viewport.width}x{finding.reproduction.viewport.height}</p>
                      )}
                    </div>
                  </details>
                </div>
              ))}
              {filteredFindings.length === 0 && (
                <div className={styles.noFindings}>
                  No deterministic bugs or AI candidates found matching the filters!
                </div>
              )}
            </div>
            
            {results.test_cases && results.test_cases.length > 0 && (
              <div style={{ marginTop: '40px' }}>
                <h3 style={{ marginBottom: '10px' }}>Test Cases Executed</h3>
                
                {results.test_case_metrics && (
                  <div className={styles.statsGrid} style={{ marginBottom: '20px' }}>
                    <div className={styles.statCard}>
                      <h3>Total Tests</h3>
                      <div className={styles.statValue}>{results.test_case_metrics.total}</div>
                    </div>
                    <div className={styles.statCard}>
                      <h3>Passed / Failed</h3>
                      <div className={styles.statValue}>{results.test_case_metrics.passed} / {results.test_case_metrics.failed}</div>
                    </div>
                    <div className={styles.statCard}>
                      <h3>Manual Review</h3>
                      <div className={styles.statValue}>{results.test_case_metrics.manual_review}</div>
                    </div>
                  </div>
                )}
                
                <div className={styles.findingsList}>
                  {results.test_cases.map((tc, idx: number) => {
                    const status = (tc.status || tc.execution_policy || 'manual_review');
                    const isFailed = status === 'failed';
                    const isPassed = status === 'passed';
                    
                    return (
                      <div key={tc.id || idx} className={styles.findingItem} style={{ borderLeftColor: isFailed ? 'var(--danger)' : isPassed ? 'var(--success)' : 'var(--warning)' }}>
                        <div className={styles.findingHeader}>
                          <span className={styles.findingId}>{tc.id}</span>
                          <span className={styles.severityBadge} style={{ background: isFailed ? 'var(--danger)' : isPassed ? 'var(--success)' : 'var(--warning)', color: '#fff' }}>
                            {status.toUpperCase()}
                          </span>
                        </div>
                        <h3>{tc.title}</h3>
                        <div className={styles.findingFooter}>
                          <FileText size={16} /> {tc.category} ({tc.priority} priority) &middot; {tc.source_page}
                        </div>
                        
                        <details style={{marginTop: '15px', background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '8px', cursor: 'pointer'}}>
                          <summary style={{fontWeight: 'bold', outline: 'none'}}>Execution Details</summary>
                          <div style={{marginTop: '10px', fontSize: '0.9rem', lineHeight: '1.5'}}>
                            <p><strong>Expected Result:</strong> {tc.expected_result || 'Not specified.'}</p>
                            <p><strong>Actual Result:</strong> {tc.actual_result || 'Not specified.'}</p>
                            
                            {tc.steps && tc.steps.length > 0 && (
                              <div style={{marginTop: '10px'}}>
                                <strong>Execution Steps:</strong>
                                <ol style={{paddingLeft: '20px', marginTop: '5px'}}>
                                  {tc.steps.map((step: string, sIdx: number) => (
                                    <li key={sIdx}>{step}</li>
                                  ))}
                                </ol>
                              </div>
                            )}
                          </div>
                        </details>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </motion.div>
        )}

      </div>
    </main>
  );
}
