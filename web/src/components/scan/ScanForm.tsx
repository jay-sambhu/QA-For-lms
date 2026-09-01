"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ArrowRight, Lock, KeyRound, User, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import styles from '../../app/page.module.css';

interface ScanFormProps {
  onSubmit: (data: {
    url: string;
    maxPages: number;
    auth?: { loginUrl?: string; username?: string; password?: string };
  }) => void;
  loading: boolean;
  error?: string;
}

export const ScanForm: React.FC<ScanFormProps> = ({ onSubmit, loading, error }) => {
  const [url, setUrl] = useState('');
  const [maxPages, setMaxPages] = useState('10');
  const [requiresAuth, setRequiresAuth] = useState(false);
  const [loginUrl, setLoginUrl] = useState('');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    const payload: {
      url: string;
      maxPages: number;
      auth?: { loginUrl?: string; username?: string; password?: string };
    } = {
      url: url.trim(),
      maxPages: parseInt(maxPages, 10) || 10,
    };

    if (requiresAuth) {
      payload.auth = {
        loginUrl: loginUrl.trim() || undefined,
        username: authUsername.trim() || undefined,
        password: authPassword || undefined,
      };
    }

    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
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

        <button type="submit" className={styles.launchBtn} disabled={loading}>
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

      {error && (
        <div style={{ color: 'var(--danger)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={16} /> {error}
        </div>
      )}
    </form>
  );
};
