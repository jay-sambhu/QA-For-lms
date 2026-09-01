"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Loader2, AlertTriangle, ArrowLeft, RefreshCw } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
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
    if (!scanId || !session) return;
    try {
      await fetch(`/api/scans/${scanId}/cancel`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      setStatus('cancelled');
      setError('Scan was cancelled by user.');
    } catch (e) {
      console.error('Stop scan failed:', e);
    }
  };

  // Poll scan state
  useEffect(() => {
    if (!scanId) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const headers: Record<string, string> = {};
        if (session?.access_token) {
          headers['Authorization'] = `Bearer ${session.access_token}`;
        }

        const res = await fetch(`/api/scans/${scanId}`, { headers });
        if (cancelled) return;

        if (res.status === 404) {
          setError('Scan not found or has expired.');
          setStatus('error');
          return;
        }

        if (!res.ok) return;

        const data = await res.json();
        if (cancelled) return;

        if (data.url) setTargetUrl(data.url);
        setStatus(data.status);

        if (data.status === 'completed') {
          if (data.results) setResults(data.results);
          return;
        }

        if (data.status === 'failed') {
          setError('Scan execution failed. The target site may be unreachable or returned an error.');
          return;
        }

        if (data.status === 'cancelled') {
          setError('Scan was stopped by user.');
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
  }, [scanId, session]);

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
          <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
            <Link
              href="/dashboard"
              className="btn btn-primary"
              style={{ textDecoration: 'none', padding: '10px 20px' }}
            >
              <RefreshCw size={15} /> Launch New Scan
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};
