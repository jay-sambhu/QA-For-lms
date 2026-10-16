"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  LuLoaderCircle as Loader2,
  LuTriangleAlert as AlertTriangle,
  LuArrowLeft as ArrowLeft,
  LuRefreshCw as RefreshCw,
} from 'react-icons/lu';
import { TbCloudDownload, TbFileTypePdf, TbFileSpreadsheet, TbJson, TbMarkdown } from 'react-icons/tb';
import { useAuth, supabase } from '../context/AuthContext';
import { downloadScanReport, type ServerReportFormat } from '../utils/download';
import { ScanMonitor } from '../components/scan/ScanMonitor';
import { ScanResults } from '../components/scan/ScanResults';
import { AdBanner } from '../components/ads/AdBanner';
import { QAReport, ProgressPayload, ScanStatus } from '../types/qa';
import { PageHeader3D, Surface3D, cx } from '../components/three';
import s from '../components/scan/scan3d.module.css';

const FORMAT_ICONS: Record<ServerReportFormat, React.ReactNode> = {
  pdf: <TbFileTypePdf size={16} color="var(--tone-danger)" />,
  xlsx: <TbFileSpreadsheet size={16} color="var(--tone-success)" />,
  json: <TbJson size={16} color="var(--tone-info)" />,
  md: <TbMarkdown size={16} color="var(--tone-violet)" />,
};

const FORMAT_LABELS: Record<ServerReportFormat, string> = {
  pdf: 'PDF',
  xlsx: 'Excel',
  json: 'JSON',
  md: 'Markdown',
};

const statusChip = (status: ScanStatus) => {
  if (status === 'completed') return <span className="chip chip--success chip--dot">Completed</span>;
  if (status === 'failed' || status === 'error') return <span className="chip chip--danger chip--dot">Failed</span>;
  if (status === 'cancelled') return <span className="chip chip--neutral chip--dot">Cancelled</span>;
  return <span className="chip chip--info chip--live">{status === 'pending' ? 'Queued' : 'Running'}</span>;
};

export const ScanDetailPage: React.FC = () => {
  const params = useParams();
  const router = useRouter();
  const scanId = params?.id as string;
  const { session, sessionLoaded } = useAuth();

  const [status, setStatus] = useState<ScanStatus>('pending');
  const [targetUrl, setTargetUrl] = useState('');
  const [progress, setProgress] = useState<ProgressPayload | null>(null);
  const [results, setResults] = useState<QAReport | null>(null);
  const [error, setError] = useState('');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [logFeed, setLogFeed] = useState<string[]>([
    'Initializing isolated browser environments across viewports...',
  ]);
  // When a scan is completed but the report data isn't available inline,
  // show cloud download buttons instead of looping forever.
  const [reportUnavailable, setReportUnavailable] = useState(false);

  const [retryCount, setRetryCount] = useState(0);

  // Keep track of consecutive polling errors to avoid console flood and handle backoff
  const consecutiveErrorsRef = useRef(0);
  // How many times we've seen status=completed with no results payload yet
  const completedNoResultsRef = useRef(0);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  // Latest access token, read by the poller without restarting it on every token refresh
  const accessTokenRef = useRef<string | undefined>(session?.access_token);
  const hasSession = !!session?.access_token;
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  useEffect(() => {
    accessTokenRef.current = session?.access_token;
  }, [session?.access_token]);

  // Elapsed timer
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (status === 'pending' || status === 'running') {
      timer = setInterval(() => setElapsedSeconds((p) => p + 1), 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [status]);

  // Update real-time log feed
  useEffect(() => {
    if (progress?.message) {
      setLogFeed((prev) => {
        if (prev[prev.length - 1] === progress.message) return prev;
        return [...prev.slice(-6), progress.message];
      });
    }
  }, [progress?.message]);

  // Stop Scan handler
  const handleStopScan = async () => {
    if (!scanId || !session?.access_token) return;
    try {
      const res = await fetch(`/api/v1/scans/${scanId}/cancel`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        alert(body.detail || `Could not stop the scan (HTTP ${res.status}).`);
        return;
      }
      setStatus('cancelled');
      setError('Scan was cancelled by user.');
    } catch {
      alert('Network error while stopping the scan. Please try again.');
    }
  };

  const handleReportDownload = async (fmt: ServerReportFormat) => {
    if (!scanId || !session?.access_token) return;
    setDownloadingFormat(fmt);
    try {
      await downloadScanReport(scanId, fmt, session.access_token);
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Download failed. Please try again.');
    } finally {
      setDownloadingFormat(null);
    }
  };

  // Manual retry handler
  const handleManualRetry = () => {
    consecutiveErrorsRef.current = 0;
    completedNoResultsRef.current = 0;
    setReportUnavailable(false);
    setError('');
    setStatus('pending');
    setRetryCount((c) => c + 1);
  };

  // Poll scan state safely without console error storms
  useEffect(() => {
    // 1. Wait until session authentication state is determined
    if (!sessionLoaded || !scanId) return;

    // 2. If user is unauthenticated, show error without firing API requests
    if (!hasSession) {
      setError('Please sign in to view this scan.');
      setStatus('error');
      return;
    }

    let isMounted = true;
    // Per-effect in-flight guard. (A shared ref used to stay `true` when the effect restarted
    // mid-request, so the new poller bailed out and polling silently stopped forever.)
    let inFlight = false;
    consecutiveErrorsRef.current = 0;

    const stopPolling = () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };

    const scheduleNextPoll = (delayMs: number) => {
      if (!isMounted) return;
      stopPolling();
      pollTimerRef.current = setTimeout(() => {
        executePoll();
      }, delayMs);
    };

    const executePoll = async () => {
      if (!isMounted || inFlight) return;
      inFlight = true;

      try {
        let currentToken = accessTokenRef.current;
        if (supabase) {
          try {
            const { data } = await supabase.auth.getSession();
            if (data?.session?.access_token) {
              currentToken = data.session.access_token;
            }
          } catch {}
        }

        const headers: Record<string, string> = {
          Authorization: `Bearer ${currentToken}`,
        };

        const res = await fetch(`/api/v1/scans/${scanId}`, { headers });
        if (!isMounted) return;

        // Terminal state: Scan not found (retry twice for newly enqueued scans during DB commit lag)
        if (res.status === 404) {
          consecutiveErrorsRef.current += 1;
          if (consecutiveErrorsRef.current < 3) {
            scheduleNextPoll(1500);
            return;
          }
          stopPolling();
          setError('Scan not found or has expired.');
          setStatus('error');
          return;
        }

        // Unauthorized: attempt a session refresh before giving up.
        // On fresh page loads after sign-up, the session token may not have
        // propagated to localStorage yet — retry up to 3 times with backoff.
        if (res.status === 401) {
          consecutiveErrorsRef.current += 1;
          if (consecutiveErrorsRef.current <= 3) {
            // Try to refresh the Supabase session first
            if (supabase) {
              try {
                const refreshRes = await supabase.auth.refreshSession();
                if (refreshRes.data?.session?.access_token) {
                  scheduleNextPoll(500);
                  return;
                }
              } catch {}
            }
            // Session not ready yet — wait and retry
            scheduleNextPoll(1500);
            return;
          }
          stopPolling();
          setError('Session expired or unauthorized. Please sign in again.');
          setStatus('error');
          return;
        }

        // Forbidden
        if (res.status === 403) {
          stopPolling();
          setError('You do not have permission to view this scan.');
          setStatus('error');
          return;
        }

        // Server errors: 500, 502 Bad Gateway, 503, 504
        if (!res.ok) {
          consecutiveErrorsRef.current += 1;
          if (consecutiveErrorsRef.current >= 10) {
            stopPolling();
            setError(
              res.status === 502
                ? 'Backend service is temporarily restarting (502 Bad Gateway). Please retry in a few moments.'
                : `Scan service returned an error (${res.status}). Click retry to check again.`
            );
            setStatus('error');
            return;
          }
          // Exponential backoff for temporary gateway / server hiccups (2s -> 4s -> 6s... up to 8s)
          const backoff = Math.min(8000, 2000 * Math.min(4, consecutiveErrorsRef.current));
          scheduleNextPoll(backoff);
          return;
        }

        // Successful response - reset consecutive error counter
        consecutiveErrorsRef.current = 0;
        const data = await res.json();
        if (!isMounted) return;

        if (data.url) setTargetUrl(data.url);
        setStatus(data.status);

        if (data.progress) {
          setProgress(data.progress);
        }

        // Terminal state: Completed
        if (data.status === 'completed') {
          setStatus('completed');
          if (data.results) {
            // Report data arrived inline — render it immediately
            completedNoResultsRef.current = 0;
            setResults(data.results);
            stopPolling();
            return;
          }
          // The backend confirmed the report is in Supabase but too large to serve inline
          if (data.has_cloud_report) {
            stopPolling();
            setReportUnavailable(true);
            return;
          }
          // Report not yet available anywhere — poll a few more times then show download UI
          completedNoResultsRef.current += 1;
          if (completedNoResultsRef.current >= 5) {
            stopPolling();
            setReportUnavailable(true);
            return;
          }
          scheduleNextPoll(2000);
          return;
        }

        // Terminal state: Failed
        if (data.status === 'failed') {
          stopPolling();
          // Only a FAILED-stage message explains the failure; otherwise the last
          // message is a stale progress update like "Crawling page 2/10".
          const failureDetail =
            (data.progress?.stage === 'FAILED' && data.progress?.message) ||
            'Scan execution failed. The target site may be unreachable or returned an error.';
          setError(failureDetail);
          return;
        }

        // Terminal state: Cancelled
        if (data.status === 'cancelled') {
          stopPolling();
          setError('Scan was stopped by user.');
          return;
        }

        // Scan is still pending or running - schedule next poll in 2000ms
        scheduleNextPoll(2000);
      } catch {
        if (!isMounted) return;
        consecutiveErrorsRef.current += 1;
        if (consecutiveErrorsRef.current >= 5) {
          stopPolling();
          setError('Network connection error while checking scan status. Please retry.');
          setStatus('error');
          return;
        }
        const backoff = Math.min(8000, 2000 * consecutiveErrorsRef.current);
        scheduleNextPoll(backoff);
      } finally {
        inFlight = false;
      }
    };

    executePoll();

    return () => {
      isMounted = false;
      stopPolling();
    };
  }, [scanId, hasSession, sessionLoaded, retryCount]);

  // Route Authentication Guard: Unauthenticated users are bounced to home
  useEffect(() => {
    if (sessionLoaded && !session) {
      router.replace('/');
    }
  }, [sessionLoaded, session, router]);


  if (!sessionLoaded) {
    return (
      <div className={s.centered}>
        <Loader2 size={36} className="pulse" color="var(--primary)" />
        <p>Loading verification context...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className={s.centered}>
        <Loader2 size={36} className="pulse" color="var(--primary)" />
        <p>Session unauthenticated. Redirecting to home...</p>
      </div>
    );
  }

  const isLive = status === 'pending' || status === 'running';
  const isTerminalIssue = status === 'failed' || status === 'cancelled' || status === 'error';
  const headerTitle = isLive
    ? 'Automated Test Execution'
    : status === 'completed'
    ? 'Autonomous QA Scan Report'
    : status === 'cancelled'
    ? 'Scan Stopped'
    : isTerminalIssue
    ? 'Scan Encountered An Issue'
    : 'Scan Report';
  const headerSubtitle = isLive
    ? 'Executing multi-viewport crawler, synthetic user journeys, and defect analysis in parallel.'
    : status === 'completed'
    ? 'AI-verified findings, automated test cases and responsive QA results for this run.'
    : 'Review the outcome below or launch a new scan from the dashboard.';
  const headerAccent = isLive ? 'info' : status === 'completed' ? 'success' : isTerminalIssue ? (status === 'cancelled' ? 'neutral' : 'danger') : undefined;

  return (
    <div className="page-shell">
      <div className="enter-3d">
        <PageHeader3D
          eyebrow="Scan report"
          title={headerTitle}
          badge={statusChip(status)}
          subtitle={headerSubtitle}
          accent={headerAccent}
          actions={
            <Link href="/dashboard" className="btn btn-secondary btn-sm">
              <ArrowLeft size={14} /> Back to Dashboard
            </Link>
          }
        >
          <span className={cx(s.mono, s.truncate)} style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>
            Scan ID: {scanId}
          </span>
        </PageHeader3D>
      </div>

      {/* Running or Pending state */}
      {isLive && (
        <>
          <Surface3D ring pad="lg" className="enter-3d" style={{ ['--enter-delay' as string]: '60ms' } as React.CSSProperties}>
            <ScanMonitor
              url={targetUrl || 'Target Web Application'}
              progress={progress}
              elapsedSeconds={elapsedSeconds}
              logFeed={logFeed}
              onStop={handleStopScan}
            />
          </Surface3D>
          {/* Ad banner — only for logged-in users during scan wait */}
          <div className="enter-3d" style={{ ['--enter-delay' as string]: '120ms' } as React.CSSProperties}>
            <AdBanner isAuthenticated={!!session?.access_token} />
          </div>
        </>
      )}

      {/* Completed state with Report */}
      {status === 'completed' && results && (
        <ScanResults
          results={results}
          scanId={scanId}
          sessionToken={session?.access_token}
          onNewScan={() => router.push('/dashboard')}
        />
      )}

      {/* Completed state while report is finalizing — transient, max ~10 s */}
      {status === 'completed' && !results && !reportUnavailable && (
        <>
          <Surface3D accent="success" pad="lg" className="enter-3d" role="status">
            <div className={s.state}>
              <Loader2 size={40} className="pulse" color="var(--tone-success)" />
              <h2 className={s.stateTitle}>Finalizing Quality Synthesis & Report...</h2>
              <p className={s.stateDesc}>
                Multi-viewport execution is complete. Generating compliance grading and executive findings.
              </p>
              <div className={s.stateActions}>
                <button type="button" onClick={handleManualRetry} className="btn btn-secondary btn-sm">
                  <RefreshCw size={14} /> Refresh Report Status
                </button>
              </div>
            </div>
          </Surface3D>
          <div className="enter-3d" style={{ ['--enter-delay' as string]: '60ms' } as React.CSSProperties}>
            <AdBanner isAuthenticated={!!session?.access_token} />
          </div>
        </>
      )}

      {/* Completed but report not available inline — offer direct cloud downloads */}
      {status === 'completed' && !results && reportUnavailable && (
        <Surface3D accent="success" pad="lg" className="enter-3d">
          <div className={s.state}>
            <span className="icon-well icon-well--solid icon-well--lg tone-success" aria-hidden="true">
              <TbCloudDownload size={24} />
            </span>
            <h2 className={s.stateTitle}>Report Ready — Download Directly</h2>
            <p className={s.stateDesc}>
              Your QA report has been generated and saved to your cloud storage. Use the buttons below to
              download it directly — no re-scanning required.
            </p>
            <div className={s.stateActions}>
              {(['pdf', 'xlsx', 'json', 'md'] as const).map((fmt) => (
                <button
                  type="button"
                  key={fmt}
                  onClick={() => handleReportDownload(fmt)}
                  disabled={downloadingFormat === fmt}
                  className="btn btn-secondary"
                >
                  {downloadingFormat === fmt ? <Loader2 size={16} className="pulse" /> : FORMAT_ICONS[fmt]}
                  {FORMAT_LABELS[fmt]}
                </button>
              ))}
            </div>
            <div className={s.stateActions}>
              <button type="button" onClick={handleManualRetry} className="btn btn-primary btn-sm">
                <RefreshCw size={14} /> Try Load Report Again
              </button>
            </div>
          </div>
        </Surface3D>
      )}

      {/* Failed, Cancelled or Error State */}
      {isTerminalIssue && (
        <Surface3D accent={status === 'cancelled' ? 'neutral' : 'danger'} pad="lg" className="enter-3d" role="alert">
          <div className={s.state}>
            <span
              className={cx('icon-well icon-well--solid icon-well--lg', status === 'cancelled' ? 'tone-neutral' : 'tone-danger')}
              aria-hidden="true"
            >
              <AlertTriangle size={24} />
            </span>
            <h2 className={s.stateTitle}>
              {status === 'cancelled' ? 'Scan Stopped' : 'Scan Encountered An Issue'}
            </h2>
            <p className={s.stateDesc}>
              {error || 'The automated QA scan could not complete successfully.'}
            </p>
            <div className={s.stateActions}>
              {status === 'error' && (
                <button type="button" onClick={handleManualRetry} className="btn btn-secondary">
                  <RefreshCw size={15} /> Retry Connection
                </button>
              )}
              <Link href="/dashboard" className="btn btn-primary">
                <RefreshCw size={15} /> Launch New Scan
              </Link>
            </div>
          </div>
        </Surface3D>
      )}
    </div>
  );
};
