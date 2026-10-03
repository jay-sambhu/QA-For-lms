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
  RiGoogleFill,
  RiOpenaiFill,
  RiCpuLine,
  RiVipCrownFill,
  RiEyeLine,
  RiEyeOffLine,
  RiStarFill,
  RiStarLine,
  RiAddLine,
  RiCheckDoubleFill,
} from 'react-icons/ri';
import { SiAnthropic } from 'react-icons/si';
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
  TbBrain,
  TbServer2,
  TbSparkles,
  TbLoader2,
  TbLock,
} from 'react-icons/tb';
import { useAuth } from '../../context/AuthContext';
import styles from '../../app/page.module.css';

export const UserProfileModal: React.FC = () => {
  const { session, userPlan, userRole, isAdmin: authIsAdmin, profileModalOpen, closeProfileModal, signOut } = useAuth();
  const userIsAdmin = authIsAdmin || userRole === 'admin';
  const email = session?.user?.email || 'user@example.com';
  const userId = session?.user?.id || 'anonymous';
  const avatarChar = email.charAt(0).toUpperCase();

  const [copiedId, setCopiedId] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [defaultViewport, setDefaultViewport] = useState('all');

  const handleCopyId = () => {
    navigator.clipboard.writeText(userId);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  // Multi-Model API Keys State
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [quotaData, setQuotaData] = useState<{
    count: number;
    max_allowed: number;
    plan_tier: string;
    is_paid: boolean;
    can_add_more: boolean;
    supported_providers: any[];
  } | null>(null);

  const [loadingKeys, setLoadingKeys] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState('gemini');
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash');
  const [keyNameInput, setKeyNameInput] = useState('');
  const [keyValueInput, setKeyValueInput] = useState('');
  const [endpointInput, setEndpointInput] = useState('');
  const [isDefaultInput, setIsDefaultInput] = useState(true);
  const [showKeySecret, setShowKeySecret] = useState(false);
  const [isSubmittingKey, setIsSubmittingKey] = useState(false);
  const [keyFeedback, setKeyFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);

  // Fetch all user API keys & quotas whenever modal opens
  const fetchUserApiKeys = async () => {
    if (!session?.access_token) return;
    setLoadingKeys(true);
    try {
      const res = await fetch('/api/v1/user/api-keys', {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setApiKeys(data.keys || []);
        setQuotaData({
          count: data.count,
          max_allowed: data.max_allowed,
          plan_tier: data.plan_tier,
          is_paid: data.is_paid,
          can_add_more: data.can_add_more,
          supported_providers: data.supported_providers || [],
        });
        if (!data.keys || data.keys.length === 0) {
          setShowAddForm(true);
        }
      }
    } catch (e) {
      console.error('Failed to load user API keys:', e);
    } finally {
      setLoadingKeys(false);
    }
  };

  useEffect(() => {
    if (profileModalOpen && session?.access_token) {
      fetchUserApiKeys();
    }
  }, [profileModalOpen, session?.access_token]);

  // Update selected model when provider changes
  const handleProviderSelect = (pid: string) => {
    setSelectedProvider(pid);
    const pMeta = quotaData?.supported_providers?.find((p: any) => p.id === pid);
    if (pMeta) {
      setSelectedModel(pMeta.default_model);
      setEndpointInput(pMeta.default_endpoint || '');
    }
    setKeyFeedback(null);
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyValueInput.trim() && selectedProvider !== 'local_llm') {
      setKeyFeedback({ type: 'error', msg: 'API Key string cannot be empty.' });
      return;
    }

    // Check if free user is exceeding quota of 3
    if (quotaData && !quotaData.is_paid && quotaData.count >= 3) {
      setShowUpgradePrompt(true);
      setKeyFeedback({
        type: 'error',
        msg: 'Free tier limit reached (3/3 keys). Upgrade to Pro to connect more models.',
      });
      return;
    }

    setIsSubmittingKey(true);
    setKeyFeedback(null);

    try {
      const res = await fetch('/api/v1/user/api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({
          provider_id: selectedProvider,
          api_key: keyValueInput.trim(),
          key_name: keyNameInput.trim() || undefined,
          model: selectedModel,
          endpoint: endpointInput.trim() || undefined,
          is_default: isDefaultInput,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        if (res.status === 403) {
          setShowUpgradePrompt(true);
        }
        throw new Error(data.detail || 'Failed to save API key');
      }

      setKeyFeedback({ type: 'success', msg: data.message || 'API Key integrated successfully!' });
      setKeyValueInput('');
      setKeyNameInput('');
      setShowAddForm(false);
      setShowUpgradePrompt(false);
      await fetchUserApiKeys();
      setTimeout(() => setKeyFeedback(null), 4000);
    } catch (err: any) {
      setKeyFeedback({ type: 'error', msg: err.message || 'Error saving API key' });
    } finally {
      setIsSubmittingKey(false);
    }
  };

  const handleSetDefaultKey = async (keyId: string) => {
    if (!session?.access_token) return;
    try {
      const res = await fetch(`/api/v1/user/api-keys/${keyId}/default`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        await fetchUserApiKeys();
        setKeyFeedback({ type: 'success', msg: 'Default AI model updated for upcoming scans.' });
        setTimeout(() => setKeyFeedback(null), 3000);
      }
    } catch {
      setKeyFeedback({ type: 'error', msg: 'Failed to update default key' });
    }
  };

  const handleDeleteKey = async (keyId: string, name: string) => {
    if (!session?.access_token) return;
    if (!confirm(`Are you sure you want to remove ${name}?`)) return;

    try {
      const res = await fetch(`/api/v1/user/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        await fetchUserApiKeys();
        setKeyFeedback({ type: 'success', msg: 'API Key removed.' });
        setTimeout(() => setKeyFeedback(null), 3000);
      }
    } catch {
      setKeyFeedback({ type: 'error', msg: 'Failed to remove API key' });
    }
  };

  const getProviderIcon = (id: string, size = 18) => {
    switch (id) {
      case 'gemini':
        return <RiGoogleFill size={size} color="#4285f4" />;
      case 'openai':
        return <RiOpenaiFill size={size} color="#10a37f" />;
      case 'anthropic':
        return <SiAnthropic size={size - 2} color="#d97706" />;
      case 'deepseek':
        return <TbBrain size={size} color="#3b82f6" />;
      case 'local_llm':
        return <TbServer2 size={size} color="#10b981" />;
      default:
        return <RiCpuLine size={size} color="#818cf8" />;
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

            {/* Multi-AI Provider & Model Integration Hub */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
                padding: '18px',
                background: 'rgba(99, 102, 241, 0.05)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
                borderRadius: '16px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <RiCpuLine size={20} color="#818cf8" />
                  <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>
                    Multi-Model &amp; AI Provider Integrations
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      padding: '3px 10px',
                      borderRadius: '8px',
                      background: quotaData?.is_paid
                        ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.25), rgba(99, 102, 241, 0.25))'
                        : apiKeys.length >= 3
                        ? 'rgba(234, 179, 8, 0.18)'
                        : 'rgba(56, 189, 248, 0.15)',
                      color: quotaData?.is_paid
                        ? '#e9d5ff'
                        : apiKeys.length >= 3
                        ? '#facc15'
                        : '#38bdf8',
                      border: `1px solid ${
                        quotaData?.is_paid
                          ? 'rgba(168, 85, 247, 0.4)'
                          : apiKeys.length >= 3
                          ? 'rgba(234, 179, 8, 0.4)'
                          : 'rgba(56, 189, 248, 0.3)'
                      }`,
                    }}
                  >
                    {quotaData?.is_paid
                      ? `UNLIMITED (${(quotaData.plan_tier || 'PRO').toUpperCase()})`
                      : `${apiKeys.length} / 3 KEYS (FREE TIER)`}
                  </span>
                </div>
              </div>

              <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: 0, lineHeight: 1.45 }}>
                Connect your personal API keys for Google Gemini, OpenAI GPT-4o, Anthropic Claude, DeepSeek, or local clusters. Free accounts include up to 3 API keys; upgrade to a subscription plan to add unlimited keys.
              </p>

              {/* Upgrade Paywall Banner when user hits limit */}
              {showUpgradePrompt && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  style={{
                    background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.15), rgba(168, 85, 247, 0.15))',
                    border: '1px solid rgba(234, 179, 8, 0.45)',
                    borderRadius: '12px',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#facc15', fontWeight: 800, fontSize: '0.9rem' }}>
                    <RiVipCrownFill size={18} />
                    <span>API Integration Limit Reached (3 / 3 Keys)</span>
                  </div>
                  <p style={{ color: '#e2e8f0', fontSize: '0.82rem', margin: 0, lineHeight: 1.5 }}>
                    Free tier workspaces are limited to a maximum of 3 API keys. Please start a subscription plan (Pro or Enterprise) to add unlimited AI models, custom endpoints, and priority scan workers.
                  </p>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                    <Link
                      href="/pricing"
                      onClick={closeProfileModal}
                      className="btn btn-primary"
                      style={{
                        background: 'linear-gradient(135deg, #f59e0b, #d946ef)',
                        border: 'none',
                        color: '#fff',
                        fontWeight: 700,
                        fontSize: '0.82rem',
                        padding: '8px 14px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        textDecoration: 'none',
                        borderRadius: '8px',
                      }}
                    >
                      <TbSparkles size={15} /> Activate Subscription Plan →
                    </Link>
                    <button
                      type="button"
                      onClick={() => setShowUpgradePrompt(false)}
                      className="btn btn-secondary"
                      style={{ padding: '8px 12px', fontSize: '0.8rem', borderRadius: '8px' }}
                    >
                      Dismiss
                    </button>
                  </div>
                </motion.div>
              )}

              {/* Feedback Alert */}
              {keyFeedback && (
                <div
                  style={{
                    fontSize: '0.82rem',
                    color: keyFeedback.type === 'error' ? '#ef4444' : '#10b981',
                    background: keyFeedback.type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                    border: `1px solid ${keyFeedback.type === 'error' ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.25)'}`,
                    padding: '8px 12px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  {keyFeedback.type === 'error' ? <TbAlertCircle size={16} /> : <TbCheck size={16} />}
                  <span>{keyFeedback.msg}</span>
                </div>
              )}

              {/* Configured Keys List */}
              {loadingKeys ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '16px', color: '#94a3b8' }}>
                  <TbLoader2 size={18} className="pulse" color="#818cf8" />
                  <span style={{ fontSize: '0.82rem' }}>Loading configured AI integrations...</span>
                </div>
              ) : apiKeys.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {apiKeys.map((k) => (
                    <div
                      key={k.id}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '10px',
                        background: k.is_default ? 'rgba(99, 102, 241, 0.12)' : 'rgba(0, 0, 0, 0.3)',
                        padding: '10px 14px',
                        borderRadius: '10px',
                        border: `1px solid ${k.is_default ? 'rgba(99, 102, 241, 0.4)' : 'rgba(255, 255, 255, 0.08)'}`,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(255, 255, 255, 0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          {getProviderIcon(k.provider_id, 18)}
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#f8fafc' }}>
                              {k.key_name}
                            </span>
                            {k.model && (
                              <span style={{ fontSize: '0.68rem', padding: '1px 6px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '4px', color: '#cbd5e1' }}>
                                {k.model}
                              </span>
                            )}
                          </div>
                          <span style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: '#94a3b8' }}>
                            {k.masked_key}
                          </span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {k.is_default ? (
                          <span
                            style={{
                              fontSize: '0.7rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '6px',
                              background: 'rgba(16, 185, 129, 0.2)',
                              color: '#34d399',
                              border: '1px solid rgba(16, 185, 129, 0.35)',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <RiStarFill size={11} /> DEFAULT
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleSetDefaultKey(k.id)}
                            className="btn btn-secondary"
                            style={{ padding: '4px 10px', fontSize: '0.75rem', borderRadius: '6px' }}
                            title="Set as active model for next scan"
                          >
                            <RiStarLine size={13} /> Set Default
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleDeleteKey(k.id, k.key_name)}
                          className="btn btn-secondary"
                          style={{ padding: '5px 8px', fontSize: '0.75rem', borderRadius: '6px', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                          title="Remove API Key"
                        >
                          <TbTrash size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              {/* Add Key Toggle / Paywall Trigger */}
              {!showAddForm ? (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                  {!quotaData?.is_paid && apiKeys.length >= 3 ? (
                    <button
                      type="button"
                      onClick={() => setShowUpgradePrompt(true)}
                      className="btn btn-secondary"
                      style={{
                        padding: '9px 14px',
                        fontSize: '0.82rem',
                        borderRadius: '8px',
                        borderColor: 'rgba(234, 179, 8, 0.4)',
                        color: '#facc15',
                        background: 'rgba(234, 179, 8, 0.08)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        width: '100%',
                        justifyContent: 'center',
                      }}
                    >
                      <TbLock size={15} /> Add Another AI Model Key (Limit Reached · Upgrade to Unlock)
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => {
                        setShowAddForm(true);
                        setShowUpgradePrompt(false);
                      }}
                      className="btn btn-secondary"
                      style={{
                        padding: '8px 14px',
                        fontSize: '0.82rem',
                        borderRadius: '8px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      <RiAddLine size={15} /> Connect AI Model / Provider Key
                    </button>
                  )}
                </div>
              ) : (
                /* Add API Key Form */
                <form
                  onSubmit={handleCreateApiKey}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                    padding: '14px',
                    background: 'rgba(15, 23, 42, 0.7)',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc' }}>
                      Configure New Model Integration
                    </span>
                    {apiKeys.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setShowAddForm(false)}
                        style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '0.8rem' }}
                      >
                        Cancel
                      </button>
                    )}
                  </div>

                  {/* Provider Selector */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                      AI Provider Platform
                    </label>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(90px, 1fr))', gap: '6px' }}>
                      {['gemini', 'openai', 'anthropic', 'deepseek', 'local_llm'].map((pid) => {
                        const isSel = selectedProvider === pid;
                        const labelMap: Record<string, string> = {
                          gemini: 'Gemini',
                          openai: 'OpenAI',
                          anthropic: 'Claude',
                          deepseek: 'DeepSeek',
                          local_llm: 'Ollama / Local',
                        };
                        return (
                          <button
                            key={pid}
                            type="button"
                            onClick={() => handleProviderSelect(pid)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              gap: '6px',
                              padding: '8px 6px',
                              borderRadius: '8px',
                              background: isSel ? 'rgba(99, 102, 241, 0.25)' : 'rgba(255, 255, 255, 0.03)',
                              border: `1px solid ${isSel ? '#6366f1' : 'rgba(255, 255, 255, 0.08)'}`,
                              color: isSel ? '#ffffff' : '#94a3b8',
                              fontSize: '0.76rem',
                              fontWeight: isSel ? 700 : 500,
                              cursor: 'pointer',
                            }}
                          >
                            {getProviderIcon(pid, 14)}
                            <span>{labelMap[pid]}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Model Selector & Key Label */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8' }}>
                        Model Selection
                      </label>
                      <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        style={{
                          background: '#1e293b',
                          color: '#f8fafc',
                          border: '1px solid rgba(255, 255, 255, 0.12)',
                          borderRadius: '8px',
                          padding: '8px 10px',
                          fontSize: '0.8rem',
                          outline: 'none',
                        }}
                      >
                        {quotaData?.supported_providers
                          ?.find((p: any) => p.id === selectedProvider)
                          ?.models?.map((m: string) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                      </select>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8' }}>
                        Integration Label
                      </label>
                      <input
                        type="text"
                        value={keyNameInput}
                        onChange={(e) => setKeyNameInput(e.target.value)}
                        placeholder={`e.g. My ${selectedProvider.toUpperCase()} Key`}
                        style={{
                          background: 'rgba(15, 23, 42, 0.9)',
                          border: '1px solid rgba(255, 255, 255, 0.12)',
                          borderRadius: '8px',
                          padding: '8px 10px',
                          color: '#f8fafc',
                          fontSize: '0.8rem',
                          outline: 'none',
                        }}
                      />
                    </div>
                  </div>

                  {/* Secret Key Input */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8' }}>
                      Secret API Key
                    </label>
                    <div style={{ position: 'relative' }}>
                      <input
                        type={showKeySecret ? 'text' : 'password'}
                        value={keyValueInput}
                        onChange={(e) => setKeyValueInput(e.target.value)}
                        placeholder={
                          selectedProvider === 'gemini'
                            ? 'AIzaSy...'
                            : selectedProvider === 'openai'
                            ? 'sk-proj-...'
                            : selectedProvider === 'anthropic'
                            ? 'sk-ant-...'
                            : selectedProvider === 'deepseek'
                            ? 'sk-...'
                            : 'Optional token for local cluster'
                        }
                        style={{
                          width: '100%',
                          background: 'rgba(15, 23, 42, 0.9)',
                          border: '1px solid rgba(99, 102, 241, 0.4)',
                          borderRadius: '8px',
                          padding: '9px 36px 9px 12px',
                          color: '#f8fafc',
                          fontSize: '0.85rem',
                          fontFamily: 'monospace',
                          outline: 'none',
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowKeySecret(!showKeySecret)}
                        style={{
                          position: 'absolute',
                          right: '10px',
                          top: '50%',
                          transform: 'translateY(-50%)',
                          background: 'none',
                          border: 'none',
                          color: '#94a3b8',
                          cursor: 'pointer',
                        }}
                      >
                        {showKeySecret ? <RiEyeOffLine size={16} /> : <RiEyeLine size={16} />}
                      </button>
                    </div>
                  </div>

                  {/* Optional Custom Endpoint for DeepSeek / Local */}
                  {(selectedProvider === 'deepseek' || selectedProvider === 'local_llm') && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8' }}>
                        Custom API Endpoint URL
                      </label>
                      <input
                        type="text"
                        value={endpointInput}
                        onChange={(e) => setEndpointInput(e.target.value)}
                        placeholder={selectedProvider === 'deepseek' ? 'https://api.deepseek.com/v1' : 'http://localhost:11434/v1'}
                        style={{
                          background: 'rgba(15, 23, 42, 0.9)',
                          border: '1px solid rgba(255, 255, 255, 0.12)',
                          borderRadius: '8px',
                          padding: '8px 10px',
                          color: '#f8fafc',
                          fontSize: '0.8rem',
                          fontFamily: 'monospace',
                          outline: 'none',
                        }}
                      />
                    </div>
                  )}

                  {/* Default Checkbox */}
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.8rem', color: '#cbd5e1' }}>
                    <input
                      type="checkbox"
                      checked={isDefaultInput}
                      onChange={(e) => setIsDefaultInput(e.target.checked)}
                      style={{ accentColor: '#6366f1' }}
                    />
                    <span>Set as active default model for QA report generation</span>
                  </label>

                  <button
                    type="submit"
                    disabled={isSubmittingKey}
                    className="btn btn-primary"
                    style={{
                      padding: '10px 16px',
                      fontSize: '0.85rem',
                      borderRadius: '8px',
                      fontWeight: 700,
                      marginTop: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                    }}
                  >
                    {isSubmittingKey ? (
                      <>
                        <TbLoader2 size={16} className="pulse" />
                        <span>Saving API Integration...</span>
                      </>
                    ) : (
                      <>
                        <TbSparkles size={16} />
                        <span>Integrate {selectedProvider.toUpperCase()} Key</span>
                      </>
                    )}
                  </button>
                </form>
              )}

              {/* Helpful provider documentation links */}
              <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', paddingTop: '4px', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <a
                  href="https://aistudio.google.com/app/apikey"
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: '0.74rem', color: '#818cf8', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                >
                  <RiGoogleFill size={12} /> Google AI Studio <TbExternalLink size={11} />
                </a>
                <a
                  href="https://platform.openai.com/api-keys"
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: '0.74rem', color: '#34d399', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                >
                  <RiOpenaiFill size={12} /> OpenAI Platform <TbExternalLink size={11} />
                </a>
                <a
                  href="https://console.anthropic.com/"
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: '0.74rem', color: '#fbbf24', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                >
                  <SiAnthropic size={11} /> Anthropic Console <TbExternalLink size={11} />
                </a>
              </div>
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
