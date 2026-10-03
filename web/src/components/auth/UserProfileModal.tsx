"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RiUser3Fill,
  RiCloseLine,
  RiShieldUserLine,
  RiShieldUserFill,
  RiDashboardLine,
  RiLogoutBoxRLine,
} from 'react-icons/ri';
import {
  TbCreditCard,
  TbDeviceDesktop,
  TbBell,
  TbCopy,
  TbCheck,
  TbKey,
  TbExternalLink,
  TbTrash,
  TbAlertCircle,
  TbDashboard,
  TbArrowRight,
} from 'react-icons/tb';
import { useAuth } from '../../context/AuthContext';
import styles from '../../app/page.module.css';

export const UserProfileModal: React.FC = () => {
  const { session, userPlan, userRole, isAdmin: authIsAdmin, profileModalOpen, closeProfileModal, signOut } = useAuth();
  const userIsAdmin = authIsAdmin || userRole === 'admin';
  const [copiedId, setCopiedId] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [defaultViewport, setDefaultViewport] = useState('all');

  // Gemini API Key state
  const [hasApiKey, setHasApiKey] = useState(false);
  const [maskedKey, setMaskedKey] = useState<string | null>(null);
  const [newApiKey, setNewApiKey] = useState('');
  const [editingKey, setEditingKey] = useState(false);
  const [isKeySaving, setIsKeySaving] = useState(false);
  const [keyFeedback, setKeyFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  // Fetch API key status whenever modal opens
  useEffect(() => {
    if (!profileModalOpen || !session?.access_token) return;

    let isMounted = true;
    const fetchApiKeyStatus = async () => {
      try {
        const res = await fetch('/api/v1/user/api-key', {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (res.ok && isMounted) {
          const data = await res.json();
          setHasApiKey(!!data.has_key);
          setMaskedKey(data.masked_key || null);
          if (!data.has_key) {
            setEditingKey(true);
          } else {
            setEditingKey(false);
          }
        }
      } catch {
        // Ignore background network errors
      }
    };

    fetchApiKeyStatus();
    return () => {
      isMounted = false;
    };
  }, [profileModalOpen, session?.access_token]);

  if (!profileModalOpen || !session) return null;

  const email = session.user?.email || 'User';
  const userId = session.user?.id || 'usr_anonymous';
  const avatarChar = email[0].toUpperCase();

  const handleCopyId = () => {
    navigator.clipboard.writeText(userId);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleSaveApiKey = async () => {
    if (!newApiKey.trim() || !session?.access_token) return;
    setIsKeySaving(true);
    setKeyFeedback(null);

    try {
      const res = await fetch('/api/v1/user/api-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ api_key: newApiKey.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to save API key');
      }

      setHasApiKey(true);
      setMaskedKey(data.masked_key || `${newApiKey.slice(0, 6)}...${newApiKey.slice(-4)}`);
      setEditingKey(false);
      setNewApiKey('');
      setKeyFeedback({ type: 'success', msg: 'Gemini API key saved! Ready for AI scans.' });
      setTimeout(() => setKeyFeedback(null), 4000);
    } catch (err: any) {
      setKeyFeedback({ type: 'error', msg: err.message || 'Error saving API key' });
    } finally {
      setIsKeySaving(false);
    }
  };

  const handleDeleteApiKey = async () => {
    if (!session?.access_token) return;
    if (!confirm('Are you sure you want to remove your saved Gemini API key? Scans will require an API key to run.')) return;

    setIsKeySaving(true);
    setKeyFeedback(null);

    try {
      const res = await fetch('/api/v1/user/api-key', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) throw new Error('Failed to remove API key');

      setHasApiKey(false);
      setMaskedKey(null);
      setEditingKey(true);
      setNewApiKey('');
      setKeyFeedback({ type: 'success', msg: 'API key removed.' });
      setTimeout(() => setKeyFeedback(null), 3000);
    } catch (err: any) {
      setKeyFeedback({ type: 'error', msg: err.message || 'Error removing API key' });
    } finally {
      setIsKeySaving(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        className={styles.modalOverlay}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={closeProfileModal}
      >
        <motion.div
          className={styles.modalCard}
          style={{ maxWidth: '520px', maxHeight: '90vh', overflowY: 'auto' }}
          initial={{ scale: 0.95, y: 15, opacity: 0 }}
          animate={{ scale: 1, y: 0, opacity: 1 }}
          exit={{ scale: 0.95, y: 15, opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className={styles.modalHeader}>
            <div className={styles.modalLogo}>
              <RiUser3Fill size={20} color="#6366f1" />
              <span>Account &amp; Workspace Hub</span>
            </div>
            <button
              type="button"
              onClick={closeProfileModal}
              className={styles.modalCloseBtn}
              title="Close"
            >
              <RiCloseLine size={20} />
            </button>
          </div>

          <div className={styles.modalBody} style={{ gap: '18px' }}>
            {/* User Identity Card */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '16px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '14px' }}>
              <div style={{ width: '52px', height: '52px', borderRadius: '16px', background: userIsAdmin ? 'linear-gradient(135deg, #a855f7, #6366f1)' : 'linear-gradient(135deg, #6366f1, #38bdf8)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem', fontWeight: 800, color: '#fff', boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)' }}>
                {avatarChar}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>{email}</span>
                  <span
                    className={`${styles.tierPill} ${
                      userIsAdmin
                        ? styles.tierEnterprise
                        : userPlan === 'pro'
                        ? styles.tierPro
                        : userPlan === 'enterprise'
                        ? styles.tierEnterprise
                        : styles.tierFree
                    }`}
                    style={
                      userIsAdmin
                        ? {
                            background: 'rgba(168, 85, 247, 0.2)',
                            color: '#c084fc',
                            border: '1px solid rgba(168, 85, 247, 0.4)',
                            fontWeight: 800,
                          }
                        : undefined
                    }
                  >
                    {userIsAdmin ? 'ADMIN' : userPlan.toUpperCase()}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: '#64748b' }}>
                  <span>ID: {userId.substring(0, 12)}...</span>
                  <button onClick={handleCopyId} style={{ color: copiedId ? '#10b981' : '#94a3b8', display: 'inline-flex', alignItems: 'center', gap: '3px' }} title="Copy User ID">
                    {copiedId ? <TbCheck size={12} /> : <TbCopy size={12} />}
                  </button>
                </div>
              </div>
            </div>

            {/* Direct Dashboard Launchpad */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b' }}>
                Quick Dashboard Navigation
              </div>

              {userIsAdmin ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <Link
                    href="/admin"
                    onClick={closeProfileModal}
                    style={{
                      padding: '12px 14px',
                      borderRadius: '12px',
                      background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.22), rgba(99, 102, 241, 0.22))',
                      border: '1px solid rgba(168, 85, 247, 0.45)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                      textDecoration: 'none',
                      boxShadow: '0 4px 15px rgba(168, 85, 247, 0.15)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#e9d5ff', fontWeight: 700, fontSize: '0.88rem' }}>
                      <RiShieldUserFill size={16} color="#c084fc" /> Admin Console
                    </div>
                    <span style={{ fontSize: '0.72rem', color: '#c4b5fd' }}>Role governance, telemetry &amp; CMS</span>
                  </Link>

                  <Link
                    href="/dashboard"
                    onClick={closeProfileModal}
                    style={{
                      padding: '12px 14px',
                      borderRadius: '12px',
                      background: 'rgba(99, 102, 241, 0.12)',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                      textDecoration: 'none',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#818cf8', fontWeight: 700, fontSize: '0.88rem' }}>
                      <TbDashboard size={16} /> QA Dashboard
                    </div>
                    <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Multi-device autonomous scans</span>
                  </Link>
                </div>
              ) : (
                <Link
                  href="/dashboard"
                  onClick={closeProfileModal}
                  style={{
                    padding: '14px 16px',
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(79, 70, 229, 0.2))',
                    border: '1px solid rgba(99, 102, 241, 0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    textDecoration: 'none',
                    boxShadow: '0 4px 18px rgba(99, 102, 241, 0.2)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'rgba(99, 102, 241, 0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8' }}>
                      <TbDashboard size={20} />
                    </div>
                    <div>
                      <div style={{ color: '#f8fafc', fontWeight: 700, fontSize: '0.92rem' }}>Open QA Automation Dashboard</div>
                      <div style={{ color: '#94a3b8', fontSize: '0.78rem' }}>Launch multi-device crawl runs &amp; inspect reports</div>
                    </div>
                  </div>
                  <TbArrowRight size={18} color="#818cf8" />
                </Link>
              )}
            </div>

            {/* Google Gemini API Key Configuration Section */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', padding: '16px', background: 'rgba(99, 102, 241, 0.05)', border: '1px solid rgba(99, 102, 241, 0.25)', borderRadius: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <TbKey size={18} color="#818cf8" />
                  <span style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f8fafc' }}>
                    Google Gemini API Key
                  </span>
                </div>
                <span
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '6px',
                    background: hasApiKey ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                    color: hasApiKey ? '#10b981' : '#f59e0b',
                    border: `1px solid ${hasApiKey ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`
                  }}
                >
                  {hasApiKey ? 'CONFIGURED' : 'REQUIRED FOR SCANS'}
                </span>
              </div>

              <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: 0, lineHeight: 1.4 }}>
                Required to generate autonomous AI QA reports, bug triaging, and quality gates. Scans execute strictly using your personal API key and will never use a shared developer key.
              </p>

              {hasApiKey && !editingKey ? (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.3)', padding: '10px 14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.88rem', color: '#a5b4fc', letterSpacing: '0.05em' }}>
                    {maskedKey}
                  </span>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      onClick={() => { setEditingKey(true); setNewApiKey(''); }}
                      className="btn btn-secondary"
                      style={{ padding: '5px 12px', fontSize: '0.78rem', borderRadius: '6px' }}
                    >
                      Update
                    </button>
                    <button
                      type="button"
                      onClick={handleDeleteApiKey}
                      disabled={isKeySaving}
                      className="btn btn-secondary"
                      style={{ padding: '5px 10px', fontSize: '0.78rem', borderRadius: '6px', color: '#f87171', borderColor: 'rgba(239,68,68,0.3)' }}
                      title="Remove API Key"
                    >
                      <TbTrash size={14} />
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      type="password"
                      value={newApiKey}
                      onChange={(e) => setNewApiKey(e.target.value)}
                      placeholder="Enter your Gemini API key (e.g. AIzaSy...)"
                      style={{
                        flex: 1,
                        background: 'rgba(15, 23, 42, 0.8)',
                        border: '1px solid rgba(99, 102, 241, 0.4)',
                        borderRadius: '8px',
                        padding: '9px 12px',
                        color: '#f8fafc',
                        fontSize: '0.85rem',
                        outline: 'none',
                        fontFamily: 'monospace'
                      }}
                    />
                    <button
                      type="button"
                      onClick={handleSaveApiKey}
                      disabled={isKeySaving || !newApiKey.trim()}
                      className="btn btn-primary"
                      style={{ padding: '9px 16px', fontSize: '0.82rem', borderRadius: '8px', whiteSpace: 'nowrap' }}
                    >
                      {isKeySaving ? 'Saving...' : 'Save Key'}
                    </button>
                    {hasApiKey && (
                      <button
                        type="button"
                        onClick={() => { setEditingKey(false); setNewApiKey(''); }}
                        className="btn btn-secondary"
                        style={{ padding: '9px 12px', fontSize: '0.82rem', borderRadius: '8px' }}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              )}

              {keyFeedback && (
                <div style={{ fontSize: '0.8rem', color: keyFeedback.type === 'error' ? '#ef4444' : '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {keyFeedback.type === 'error' ? <TbAlertCircle size={15} /> : <TbCheck size={15} />}
                  <span>{keyFeedback.msg}</span>
                </div>
              )}

              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: '0.78rem', color: '#818cf8', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '5px', alignSelf: 'flex-start' }}
              >
                <span>Get a free Google Gemini API Key from Google AI Studio</span>
                <TbExternalLink size={13} />
              </a>
            </div>

            {/* Subscription & Plan Status */}
            <div style={{ padding: '14px', background: 'rgba(99, 102, 241, 0.06)', border: '1px solid rgba(99, 102, 241, 0.2)', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#c7d2fe' }}>Current Subscription</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', textTransform: 'capitalize' }}>{userPlan} Tier</div>
              </div>
              <Link
                href="/pricing"
                onClick={closeProfileModal}
                className="btn btn-primary"
                style={{ padding: '7px 14px', fontSize: '0.82rem', borderRadius: '8px' }}
              >
                <TbCreditCard size={14} /> Upgrade Plan
              </Link>
            </div>

            {/* Account Preferences */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b' }}>
                Preferences
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <span style={{ fontSize: '0.88rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <TbBell size={16} color="#818cf8" /> Email Scan Reports
                </span>
                <input
                  type="checkbox"
                  checked={notificationsEnabled}
                  onChange={(e) => setNotificationsEnabled(e.target.checked)}
                  style={{ width: '16px', height: '16px', accentColor: '#6366f1' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <span style={{ fontSize: '0.88rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <TbDeviceDesktop size={16} color="#38bdf8" /> Default Testing Viewport
                </span>
                <select
                  value={defaultViewport}
                  onChange={(e) => setDefaultViewport(e.target.value)}
                  style={{ background: '#1e293b', color: '#f8fafc', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '6px', padding: '4px 8px', fontSize: '0.8rem' }}
                >
                  <option value="all">Desktop + Mobile + Tablet</option>
                  <option value="desktop">Desktop Only</option>
                  <option value="mobile">Mobile Only</option>
                </select>
              </div>
            </div>

            {/* Log Out Button */}
            <button
              type="button"
              onClick={signOut}
              className="btn btn-secondary"
              style={{ padding: '10px 16px', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.06)', width: '100%', marginTop: '4px' }}
            >
              <RiLogoutBoxRLine size={16} />
              <span>Log Out</span>
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
