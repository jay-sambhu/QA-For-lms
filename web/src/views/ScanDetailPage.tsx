"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Loader2, AlertTriangle, ArrowLeft, RefreshCw } from 'lucide-react';
import { useAuth, supabase } from '../context/AuthContext';
import { ScanMonitor } from '../components/scan/ScanMonitor';
import { ScanResults } from '../components/scan/ScanResults';
import { QAReport, ProgressPayload, ScanStatus } from '../types/qa';
import styles from '../app/page.module.css';

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

  const [retryCount, setRetryCount] = useState(0);

  // Keep track of consecutive polling errors to avoid console flood and handle backoff
  const consecutiveErrorsRef = useRef(0);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isPollingRef = useRef(false);

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
      await fetch(`/api/v1/scans/${scanId}/cancel`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      setStatus('cancelled');
      setError('Scan was cancelled by user.');
    } catch {
      // Ignore network aborts on cancel
    }
  };

  // Manual retry handler
  const handleManualRetry = () => {
    consecutiveErrorsRef.current = 0;
    setError('');
    setStatus('pending');
    setRetryCount((c) => c + 1);
  };

  // Poll scan state safely without console error storms
  useEffect(() => {
    // 1. Wait until session authentication state is determined
    if (!sessionLoaded || !scanId) return;

    // 2. If user is unauthenticated, show error without firing API requests
    if (!session?.access_token) {
      setError('Please sign in to view this scan.');
      setStatus('error');
      return;
    }

    let isMounted = true;
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
      if (!isMounted || isPollingRef.current) return;
      isPollingRef.current = true;

      try {
        let currentToken = session.access_token;
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

        // Unauthorized: attempt a session refresh before giving up
        if (res.status === 401) {
          if (supabase) {
            try {
              const refreshRes = await supabase.auth.refreshSession();
              if (refreshRes.data?.session?.access_token) {
                scheduleNextPoll(1000);
                return;
              }
            } catch {}
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
          if (data.results) {
            setResults(data.results);
            stopPolling();
            return;
          }
          // If status is completed but results file is still finalizing, poll once more with short delay
          scheduleNextPoll(1000);
          return;
        }

        // Terminal state: Failed
        if (data.status === 'failed') {
          stopPolling();
          const failureDetail =
            data.progress?.message ||
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
        isPollingRef.current = false;
      }
    };

    executePoll();

    return () => {
      isMounted = false;
      stopPolling();
    };
  }, [scanId, session?.access_token, sessionLoaded, retryCount]);

  if (!sessionLoaded) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '120px' }}>
        <Loader2 size={36} className="pulse" color="#6366f1" />
        <p style={{ color: '#94a3b8' }}>Loading verification context...</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '20px 0 60px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <Link
          href="/dashboard"
          className="btn btn-secondary"
          style={{ padding: '8px 14px', fontSize: '0.85rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <ArrowLeft size={14} /> Back to Dashboard
        </Link>
        <span style={{ color: '#64748b', fontSize: '0.85rem', fontFamily: 'monospace' }}>
          Scan ID: {scanId}
        </span>
      </div>

      {/* Running or Pending state */}
      {(status === 'pending' || status === 'running') && (
        <motion.div
          className={styles.actionPanel}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <ScanMonitor
            url={targetUrl || 'Target Web Application'}
            progress={progress}
            elapsedSeconds={elapsedSeconds}
            logFeed={logFeed}
            onStop={handleStopScan}
          />
        </motion.div>
      )}

      {/* Completed state with Report */}
      {status === 'completed' && results && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <ScanResults
            results={results}
            scanId={scanId}
            sessionToken={session?.access_token}
            onNewScan={() => router.push('/dashboard')}
          />
        </motion.div>
      )}

      {/* Failed, Cancelled or Error State */}
      {(status === 'failed' || status === 'cancelled' || status === 'error') && (
        <div className={styles.adminTableCard} style={{ textAlign: 'center', padding: '48px 24px' }}>
          <AlertTriangle size={36} color="#ef4444" style={{ margin: '0 auto 12px' }} />
          <h3 style={{ fontSize: '1.4rem', color: '#f8fafc' }}>
            {status === 'cancelled' ? 'Scan Stopped' : 'Scan Encountered An Issue'}
          </h3>
          <p style={{ color: '#94a3b8', maxWidth: '500px', margin: '8px auto 24px' }}>
            {error || 'The automated QA scan could not complete successfully.'}
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
            {status === 'error' && (
              <button
                type="button"
                onClick={handleManualRetry}
                className="btn btn-secondary"
                style={{ padding: '10px 20px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
              >
                <RefreshCw size={15} /> Retry Connection
              </button>
            )}
            <Link
              href="/dashboard"
              className="btn btn-primary"
              style={{ textDecoration: 'none', padding: '10px 20px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <RefreshCw size={15} /> Launch New Scan
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};
