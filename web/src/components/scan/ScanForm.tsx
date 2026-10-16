"use client";

import React, { useState } from 'react';
import { m as motion, AnimatePresence } from 'framer-motion';
import {
  RiGlobalLine,
  RiLockPasswordLine,
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
  TbRocket,
  TbKey,
  TbLoader2,
} from 'react-icons/tb';
import d from '../dashboard/dashboard3d.module.css';

export type TrialStatus = {
  enabled: boolean;
  total: number;
  used: number;
  remaining: number;
  has_own_key: boolean;
  daily_available: boolean;
};

interface ScanFormProps {
  onSubmit: (data: {
    url: string;
    maxPages: number;
    auth?: { loginUrl?: string; username?: string; password?: string };
  }) => void;
  loading: boolean;
  error?: string;
  /** Free-trial allowance for users without their own AI key (null when unknown) */
  trial?: TrialStatus | null;
  /** Whether the user has connected their own AI key (null while checking) */
  hasApiKey?: boolean | null;
  /** Opens the key setup (profile modal or the key manager) */
  onConfigureKey?: () => void;
}

export const ScanForm: React.FC<ScanFormProps> = ({
  onSubmit,
  loading,
  error,
  trial,
  hasApiKey,
  onConfigureKey,
}) => {
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

  const trialActive = hasApiKey === false && !!trial?.enabled && trial.remaining > 0;
  const trialExhausted = hasApiKey === false && !!trial?.enabled && trial.remaining <= 0;
  const keyMissing = hasApiKey === false && !trial?.enabled;

  return (
    <form onSubmit={handleSubmit} className={d.console} id="scan-launcher">
      <div className={d.panelHead}>
        <div className={d.panelTitleBlock}>
          <span className="icon-well icon-well--solid" aria-hidden="true">
            <TbRocket size={20} />
          </span>
          <div>
            <h2 className={d.panelTitle}>Launch a new QA scan</h2>
            <p className={d.panelSub}>
              Crawls your site on desktop, tablet and mobile, then an AI agent verifies every defect it finds.
            </p>
          </div>
        </div>

        <div className={d.engineRow}>
          {hasApiKey === true && (
            <span className="chip chip--success chip--dot">Your AI key is active</span>
          )}
          {trialActive && trial && (
            <span className="chip chip--info chip--dot">
              Free trial · {trial.remaining} of {trial.total} scan{trial.total === 1 ? '' : 's'} left
            </span>
          )}
          {trialExhausted && <span className="chip chip--warning chip--dot">Free trial used up</span>}
          {keyMissing && <span className="chip chip--danger chip--dot">AI key required</span>}
          {(trialExhausted || keyMissing) && onConfigureKey && (
            <button type="button" className="btn btn-secondary btn-sm" onClick={onConfigureKey}>
              <TbKey size={14} /> Add a free Gemini key
            </button>
          )}
        </div>
      </div>

      <div className={d.inputRow}>
        <div className={d.inputGroup}>
          <RiGlobalLine className={d.inputIcon} size={20} />
          <input
            type="url"
            placeholder="https://example.com or enter your target web application URL"
            className={`${d.field} ${d.urlInput}`}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            aria-label="Target URL"
            required
          />
        </div>

        <select
          id="max-pages"
          className={`${d.field} ${d.pagesSelect}`}
          value={maxPages}
          onChange={(e) => setMaxPages(e.target.value)}
          title="Maximum Pages to Crawl"
          aria-label="Maximum pages to crawl"
        >
          <option value="1">1 page (Quick)</option>
          <option value="5">5 pages</option>
          <option value="10">10 pages (Standard)</option>
          <option value="20">20 pages (Deep)</option>
          <option value="50">50 pages (Full)</option>
        </select>

        <button type="submit" className={`btn btn-primary ${d.launchBtn}`} disabled={loading}>
          {loading ? <TbLoader2 size={16} className="pulse" /> : <TbPlayerPlayFilled size={16} />}
          <span>{loading ? 'Launching…' : 'Run QA Scan'}</span>
        </button>
      </div>

      {/* Quick Sample URLs */}
      <div className={d.quickRow}>
        <span className={d.quickLabel}>
          <TbSparkles size={14} /> Instant demo targets:
        </span>
        <button type="button" onClick={() => setUrl('https://example.com')} className={d.quickPill}>
          <TbWorldWww size={13} /> example.com
        </button>
        <button type="button" onClick={() => setUrl('https://news.ycombinator.com')} className={d.quickPill}>
          <TbWorldWww size={13} /> Hacker News
        </button>
        <button type="button" onClick={() => setUrl('https://httpbin.org/status/200')} className={d.quickPill}>
          <TbWorldWww size={13} /> HTTPBin Demo
        </button>
      </div>

      {/* Authenticated Website Toggle */}
      <div>
        <label className={d.checkRow}>
          <input
            type="checkbox"
            checked={requiresAuth}
            onChange={(e) => setRequiresAuth(e.target.checked)}
            className={d.checkbox}
          />
          <span className={d.checkText}>
            <TbShieldLock size={17} color="#9333ea" /> Provide auto-login credentials (optional)
          </span>
        </label>
      </div>

      {/* Collapsible Auth Inputs */}
      <AnimatePresence>
        {requiresAuth && (
          <motion.div
            className={`surface-inset ${d.authFields}`}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
          >
            <div className={d.fieldGroup}>
              <label className={d.fieldLabel} htmlFor="scan-login-url">
                <RiGlobalLine size={14} /> Login page URL (optional)
              </label>
              <input
                id="scan-login-url"
                type="url"
                placeholder="https://example.com/login"
                value={loginUrl}
                onChange={(e) => setLoginUrl(e.target.value)}
                className={d.field}
              />
            </div>

            <div className={d.fieldGroup}>
              <label className={d.fieldLabel} htmlFor="scan-auth-username">
                <RiUser3Line size={14} /> Username / email
              </label>
              <input
                id="scan-auth-username"
                type="text"
                placeholder="user@example.com"
                value={authUsername}
                onChange={(e) => setAuthUsername(e.target.value)}
                className={d.field}
                autoComplete="username"
              />
            </div>

            <div className={d.fieldGroup}>
              <label className={d.fieldLabel} htmlFor="scan-auth-password">
                <RiLockPasswordLine size={14} /> Password
              </label>
              <div className={d.passwordWrap}>
                <input
                  id="scan-auth-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••••••"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  className={d.field}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className={`${d.iconBtn} ${d.passwordToggle}`}
                  title={showPassword ? 'Hide Password' : 'Show Password'}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <RiEyeOffLine size={16} /> : <RiEyeLine size={16} />}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <div className={`${d.notice} ${d.noticeDanger}`} role="alert">
          <RiErrorWarningFill size={18} className={d.noticeIcon} /> <span>{error}</span>
        </div>
      )}
    </form>
  );
};
