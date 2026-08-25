"use client";

import { useState, useEffect } from 'react';
import { Search, Loader2, ArrowRight, ShieldCheck, Bug, FileText, LogIn, LogOut } from 'lucide-react';
import { motion } from 'framer-motion';
import { createClient } from '@supabase/supabase-js';
import styles from './page.module.css';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default function Home() {
  const [session, setSession] = useState<any>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');

  const [url, setUrl] = useState('');
  const [maxPages, setMaxPages] = useState('10');
  const [loading, setLoading] = useState(false);
  const [scanId, setScanId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('');
  const [results, setResults] = useState<any>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) setAuthError(error.message);
    else setAuthError('Check your email for the confirmation link!');
    setAuthLoading(false);
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) setAuthError(error.message);
    setAuthLoading(false);
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
  };

  const startScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url || !session) return;
    
    setLoading(true);
    setResults(null);
    try {
      const res = await fetch('/api/scans', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ url, max_pages: parseInt(maxPages) })
      });
      
      if (!res.ok) {
        throw new Error("Failed to start scan");
      }
      
      const data = await res.json();
      setScanId(data.scan_id);
      setStatus('pending');
    } catch (err) {
      console.error(err);
      setStatus('error');
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!scanId || status === 'completed' || status === 'failed') return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/scans/${scanId}`);
        if (!res.ok) return;
        const data = await res.json();
        setStatus(data.status);
        if (data.status === 'completed' || data.status === 'failed') {
          setLoading(false);
          setResults(data.results);
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [scanId, status]);

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
            
            <form className={styles.form}>
              <input 
                type="email" 
                placeholder="Email Address" 
                className="input-field" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <input 
                type="password" 
                placeholder="Password" 
                className="input-field" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              
              {authError && <div style={{ color: 'var(--danger)', fontSize: '0.9rem', textAlign: 'center' }}>{authError}</div>}
              
              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <button type="button" onClick={handleSignIn} className="btn btn-primary" style={{ flex: 1 }} disabled={authLoading}>
                  {authLoading ? <Loader2 className="pulse" /> : 'Sign In'}
                </button>
                <button type="button" onClick={handleSignUp} className="btn" style={{ flex: 1, background: 'rgba(255,255,255,0.1)' }} disabled={authLoading}>
                  Sign Up
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <div style={{ position: 'absolute', top: 20, right: 20 }}>
        <button onClick={handleSignOut} className="btn" style={{ background: 'rgba(255,255,255,0.1)', padding: '8px 16px', fontSize: '0.9rem' }}>
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
          <h1 className={styles.title}>Automate Your Web Testing with <span className={styles.gradientText}>Antigravity QA</span></h1>
          <p className={styles.subtitle}>
            Enter any URL below. Our AI QA Agent will crawl your site, detect deterministic bugs, and use Gemini to generate a professional QA report—all while you wait.
          </p>
        </motion.div>

        {/* Action Panel */}
        <motion.div 
          className={`glass-panel ${styles.actionPanel}`}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {!scanId || status === 'completed' || status === 'failed' ? (
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
                <label>Max Pages:</label>
                <select 
                  className="input-field" 
                  style={{ width: '120px' }}
                  value={maxPages}
                  onChange={(e) => setMaxPages(e.target.value)}
                >
                  <option value="5">5 pages</option>
                  <option value="10">10 pages</option>
                  <option value="20">20 pages</option>
                  <option value="50">50 pages</option>
                </select>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? <><Loader2 className="pulse" /> Starting...</> : <>Run QA Scan <ArrowRight size={18} /></>}
                </button>
              </div>
            </form>
          ) : (
            <div className={styles.statusPanel}>
              <Loader2 className="pulse" size={48} color="var(--primary)" />
              <h2>Scan in Progress</h2>
              <p>Status: <span style={{ textTransform: 'uppercase', color: 'var(--accent)' }}>{status}</span></p>
              <p className={styles.subtext}>The agent is currently crawling and analyzing your website. This may take a few minutes...</p>
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
              <h2><FileText size={24} /> QA Scan Report for {results.target}</h2>
            </div>
            
            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <h3>Total Findings</h3>
                <div className={styles.statValue}>{results.summary.total_candidates}</div>
              </div>
              <div className={styles.statCard}>
                <h3>Needs Review</h3>
                <div className={styles.statValue}>{results.summary.needs_manual_review}</div>
              </div>
              <div className={styles.statCard}>
                <h3>Severity (High/Med/Low)</h3>
                <div className={styles.statValue}>
                  {results.summary.severity_counts.high} / {results.summary.severity_counts.medium} / {results.summary.severity_counts.low}
                </div>
              </div>
            </div>

            <div className={styles.findingsList}>
              {results.findings && results.findings.map((finding: any, idx: number) => (
                <div key={idx} className={styles.findingItem}>
                  <div className={styles.findingHeader}>
                    <span className={styles.findingId}>{finding.id}</span>
                    <span className={`${styles.severityBadge} ${styles[finding.severity]}`}>{finding.severity}</span>
                  </div>
                  <h3>{finding.title}</h3>
                  <p className={styles.findingDesc}>{finding.summary || finding.reasoning}</p>
                  <div className={styles.findingFooter}>
                    <Bug size={16} /> {finding.candidate?.occurrences || 1} Occurrences across {finding.candidate?.affected_pages?.length || 1} pages
                  </div>
                </div>
              ))}
              {(!results.findings || results.findings.length === 0) && (
                <div className={styles.noFindings}>
                  No deterministic bugs or AI candidates found! Your site looks healthy.
                </div>
              )}
            </div>
          </motion.div>
        )}

      </div>
    </main>
  );
}
