"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RiGlobalLine,
  RiLockPasswordLine,
  RiKey2Line,
  RiUser3Line,
  RiEyeLine,
  RiEyeOffLine,
  RiErrorWarningFill,
} from 'react-icons/ri';
import {
  TbPlayerPlayFilled,
  TbSparkles,
  TbWorldWww,
  TbShieldLock,
} from 'react-icons/tb';
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
          <RiGlobalLine className={styles.inputIcon} size={20} color="#818cf8" />
          <input
            type="url"
            placeholder="https://example.com or enter your target web application URL"
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
          <option value="1">1 page (Quick)</option>
          <option value="5">5 pages</option>
          <option value="10">10 pages (Standard)</option>
          <option value="20">20 pages (Deep)</option>
          <option value="50">50 pages (Full)</option>
        </select>

        <button type="submit" className={styles.launchBtn} disabled={loading}>
          <TbPlayerPlayFilled size={16} />
          <span>Run QA Scan</span>
        </button>
      </div>

      {/* Quick Sample URLs */}
      <div className={styles.quickPillsRow}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
          <TbSparkles size={14} color="#818cf8" /> Instant Demo Targets:
        </span>
        <button
          type="button"
          onClick={() => setUrl('https://example.com')}
          className={styles.quickPill}
        >
          <TbWorldWww size={13} /> example.com
        </button>
        <button
          type="button"
          onClick={() => setUrl('https://news.ycombinator.com')}
          className={styles.quickPill}
        >
          <TbWorldWww size={13} /> Hacker News
        </button>
        <button
          type="button"
          onClick={() => setUrl('https://httpbin.org/status/200')}
          className={styles.quickPill}
        >
          <TbWorldWww size={13} /> HTTPBin Demo
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
            <TbShieldLock size={17} color="#a855f7" /> Requires Authenticated Portal Login?
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
                <RiKey2Line size={14} /> Login URL
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
                <RiUser3Line size={14} /> Username / Email
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
                <RiLockPasswordLine size={14} /> Password
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
                  {showPassword ? <RiEyeOffLine size={16} /> : <RiEyeLine size={16} />}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <div style={{ color: 'var(--danger)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
          <RiErrorWarningFill size={18} /> {error}
        </div>
      )}
    </form>
  );
};
