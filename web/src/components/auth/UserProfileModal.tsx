"use client";

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { m as motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import {
  RiUser3Fill,
  RiCloseLine,
  RiShieldUserFill,
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
} from 'react-icons/ri';
import { SiAnthropic } from 'react-icons/si';
import {
  TbCreditCard,
  TbDeviceDesktop,
  TbBell,
  TbCopy,
  TbCheck,
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
  TbCloudDownload,
  TbDatabase,
  TbGift,
} from 'react-icons/tb';
import { useAuth } from '../../context/AuthContext';
import styles from '../../app/page.module.css';

type TrialStatus = {
  enabled: boolean;
  total: number;
  used: number;
  remaining: number;
  has_own_key: boolean;
  daily_available: boolean;
};

const normalizeTrial = (raw: unknown): TrialStatus | null => {
  if (!raw || typeof raw !== 'object') return null;
  const t = raw as Record<string, unknown>;
  const total = Number(t.total ?? 0) || 0;
  const used = Number(t.used ?? 0) || 0;
  const remaining = t.remaining === undefined ? Math.max(0, total - used) : Number(t.remaining) || 0;
  return {
    enabled: Boolean(t.enabled),
    total,
    used,
    remaining,
    has_own_key: Boolean(t.has_own_key),
    daily_available: t.daily_available !== false,
  };
};

const tierChipClass = (isAdmin: boolean, plan: string) => {
  if (isAdmin) return 'chip--violet';
  if (plan === 'pro') return 'chip--primary';
  if (plan === 'enterprise') return 'chip--warning';
  return 'chip--neutral';
};

const PROVIDER_LABELS: Record<string, string> = {
  gemini: 'Gemini',
  openai: 'OpenAI',
  anthropic: 'Claude',
  deepseek: 'DeepSeek',
  local_llm: 'Ollama / Local',
};

export const UserProfileModal: React.FC = () => {
  const { session, userPlan, userRole, isAdmin: authIsAdmin, profileModalOpen, closeProfileModal, signOut } = useAuth();
  const reduceMotion = useReducedMotion();
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
  const [trialStatus, setTrialStatus] = useState<TrialStatus | null>(null);

  const [loadingKeys, setLoadingKeys] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState('gemini');
  const [selectedModel, setSelectedModel] = useState('gemini-3.8-flash');
  const [keyNameInput, setKeyNameInput] = useState('');
  const [keyValueInput, setKeyValueInput] = useState('');
  const [endpointInput, setEndpointInput] = useState('');
  const [isDefaultInput, setIsDefaultInput] = useState(true);
  const [showKeySecret, setShowKeySecret] = useState(false);
  const [isSubmittingKey, setIsSubmittingKey] = useState(false);
  const [keyFeedback, setKeyFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);

  // Free-trial status for users without their own key (older backends have no such endpoint)
  const fetchTrialStatus = useCallback(async () => {
    if (!session?.access_token) return;
    try {
      const res = await fetch('/api/v1/user/trial', {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        setTrialStatus(normalizeTrial(await res.json()));
      }
    } catch {
      // Trial endpoint unavailable; the hub simply hides the trial card
    }
  }, [session?.access_token]);

  // Fetch all user API keys & quotas whenever modal opens
  const fetchUserApiKeys = useCallback(async () => {
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
        if (data.trial && typeof data.trial === 'object') {
          setTrialStatus(normalizeTrial(data.trial));
        } else {
          fetchTrialStatus();
        }
        if (!data.keys || data.keys.length === 0) {
          setShowAddForm(true);
        }
      }
    } catch (e) {
      console.error('Failed to load user API keys:', e);
    } finally {
      setLoadingKeys(false);
    }
  }, [session?.access_token, fetchTrialStatus]);

  // Supabase Storage Quota (20 MB per user)
  const [storageData, setStorageData] = useState<{
    used_bytes: number;
    limit_bytes: number;
    used_mb: number;
    limit_mb: number;
    used_percent: number;
    file_count: number;
    is_quota_exceeded: boolean;
  } | null>(null);
  const [, setLoadingStorage] = useState(false);

  const fetchStorageUsage = useCallback(async () => {
    if (!session?.access_token) return;
    setLoadingStorage(true);
    try {
      const res = await fetch('/api/v1/user/storage', {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setStorageData(data);
      }
    } catch (e) {
      console.error('Failed to load storage usage:', e);
    } finally {
      setLoadingStorage(false);
    }
  }, [session?.access_token]);

  useEffect(() => {
    if (profileModalOpen && session?.access_token) {
      fetchUserApiKeys();
      fetchStorageUsage();
    }
  }, [profileModalOpen, session?.access_token, fetchUserApiKeys, fetchStorageUsage]);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && profileModalOpen) {
        closeProfileModal();
      }
    };
    if (profileModalOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [profileModalOpen, closeProfileModal]);

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

      const data = await res.json().catch(() => ({}));
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
      } else {
        setKeyFeedback({ type: 'error', msg: `Failed to update default key (HTTP ${res.status})` });
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
      } else {
        setKeyFeedback({ type: 'error', msg: `Failed to remove API key (HTTP ${res.status})` });
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
        return <RiCpuLine size={size} color="#4f46e5" />;
    }
  };

  const atFreeLimit = !quotaData?.is_paid && apiKeys.length >= 3;
  const quotaChipTone = quotaData?.is_paid ? 'chip--violet' : atFreeLimit ? 'chip--warning' : 'chip--info';
  const quotaLabel = quotaData?.is_paid
    ? `Unlimited (${(quotaData.plan_tier || 'PRO').toUpperCase()})`
    : `${apiKeys.length} / 3 keys · Free tier`;

  const trialVisible = Boolean(trialStatus?.enabled);
  const trialRemaining = trialStatus?.remaining ?? 0;
  const trialTotal = trialStatus?.total ?? 0;
  const trialTone = trialStatus?.has_own_key ? 'tone-info' : trialRemaining > 0 ? 'tone-success' : 'tone-warning';
  const trialText = trialStatus?.has_own_key
    ? 'Your own key is active, so your scans never use trial credits.'
    : trialRemaining > 0
    ? `Your first ${trialTotal} scans run on our Gemini key with no setup. Add your own free Gemini key for unlimited scans.`
    : `You've used all ${trialTotal} free trial scans. Add your own free Gemini key to keep scanning.`;

  const storagePercent = Math.min(storageData?.used_percent ?? 0, 100);
  const storageTone = storageData?.is_quota_exceeded ? 'tone-danger' : storagePercent > 75 ? 'tone-warning' : 'tone-info';

  const cardMotion = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } }
    : {
        initial: { opacity: 0, y: 28, scale: 0.96, rotateX: 10 },
        animate: { opacity: 1, y: 0, scale: 1, rotateX: 0 },
        exit: { opacity: 0, y: 16, scale: 0.97, rotateX: 6 },
      };

  return (
    <AnimatePresence>
      {profileModalOpen && session && (
        <motion.div
          key="user-profile-modal-overlay"
          className={styles.modalOverlay}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={closeProfileModal}
        >
          <motion.div
            className={`${styles.modalCard} ${styles.profileCard} glass-3d`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="profile-modal-title"
            style={{ transformPerspective: 1400, transformOrigin: '50% 0%' }}
            {...cardMotion}
            transition={{ duration: reduceMotion ? 0.15 : 0.45, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className={styles.modalHeader}>
              <div className={styles.modalLogo} id="profile-modal-title">
                <span className="icon-well icon-well--sm">
                  <RiUser3Fill size={16} />
                </span>
                <span>Account &amp; Workspace Hub</span>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  closeProfileModal();
                }}
                className={styles.modalCloseBtn}
                title="Close"
                aria-label="Close"
              >
                <RiCloseLine size={20} />
              </button>
            </div>

            <div className={styles.profileBody}>
              {/* User Identity Card */}
              <div className={`surface-inset ${styles.profileIdentity}`}>
                <div className={`${styles.profileAvatar} ${userIsAdmin ? styles.profileAvatarAdmin : ''}`} aria-hidden="true">
                  {avatarChar}
                </div>
                <div className={styles.profileIdentityText}>
                  <div className={styles.profileEmailRow}>
                    <span className={styles.profileEmail}>{email}</span>
                    <span className={`chip chip--sm ${tierChipClass(userIsAdmin, userPlan)}`}>
                      {userIsAdmin ? 'ADMIN' : userPlan.toUpperCase()}
                    </span>
                  </div>
                  <div className={styles.profileMeta}>
                    <span>ID: {userId.substring(0, 12)}...</span>
                    <button
                      type="button"
                      onClick={handleCopyId}
                      className={`${styles.profileCopyBtn} ${copiedId ? styles.profileCopyBtnDone : ''}`}
                      title="Copy User ID"
                      aria-label={copiedId ? 'User ID copied' : 'Copy User ID'}
                    >
                      {copiedId ? <TbCheck size={12} /> : <TbCopy size={12} />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Direct Dashboard Launchpad */}
              <div className={styles.profileSection}>
                <span className="section-eyebrow">Quick Dashboard Navigation</span>

                {userIsAdmin ? (
                  <div className={styles.profileNavGrid}>
                    <Link
                      href="/admin"
                      onClick={closeProfileModal}
                      className={`surface-3d surface-3d--interactive surface-3d--accent tone-violet ${styles.profileNavCard}`}
                    >
                      <span className={styles.profileNavCardTitle}>
                        <RiShieldUserFill size={16} /> Admin Console
                      </span>
                      <span className={styles.profileNavCardDesc}>Role governance, telemetry &amp; CMS</span>
                    </Link>

                    <Link
                      href="/dashboard"
                      onClick={closeProfileModal}
                      className={`surface-3d surface-3d--interactive surface-3d--accent tone-primary ${styles.profileNavCard}`}
                    >
                      <span className={styles.profileNavCardTitle}>
                        <TbDashboard size={16} /> QA Dashboard
                      </span>
                      <span className={styles.profileNavCardDesc}>Multi-device autonomous scans</span>
                    </Link>
                  </div>
                ) : (
                  <Link
                    href="/dashboard"
                    onClick={closeProfileModal}
                    className={`surface-3d surface-3d--interactive surface-3d--accent tone-primary ${styles.profileNavWide}`}
                  >
                    <span className={styles.profileNavWideBody}>
                      <span className="icon-well icon-well--sm">
                        <TbDashboard size={18} />
                      </span>
                      <span>
                        <span className={styles.profileNavWideTitle}>Open QA Automation Dashboard</span>
                        <br />
                        <span className={styles.profileNavWideDesc}>Launch multi-device crawl runs &amp; inspect reports</span>
                      </span>
                    </span>
                    <TbArrowRight size={18} className={styles.profileNavArrow} />
                  </Link>
                )}
              </div>

              {/* Multi-AI Provider & Model Integration Hub */}
              <section className={`surface-inset ${styles.profilePanel}`} aria-labelledby="profile-ai-title">
                <div className={styles.profilePanelHead}>
                  <h3 className={styles.profilePanelTitle} id="profile-ai-title">
                    <span className="icon-well icon-well--sm">
                      <RiCpuLine size={18} />
                    </span>
                    <span>Multi-Model &amp; AI Provider Integrations</span>
                  </h3>
                  <span className={`chip chip--sm ${quotaChipTone}`}>{quotaLabel}</span>
                </div>

                <p className={styles.profileHint}>
                  Connect your personal API keys for Google Gemini, OpenAI GPT-4o, Anthropic Claude, DeepSeek, or local clusters. Free accounts include up to 3 API keys; upgrade to a subscription plan to add unlimited keys.
                </p>

                {/* Free trial status (server-side Gemini key for first scans) */}
                {trialVisible && trialStatus && (
                  <div className={`${styles.profileRaised} ${styles.profileTrial} ${trialTone}`}>
                    <span className="icon-well icon-well--sm">
                      <TbGift size={16} />
                    </span>
                    <div className={styles.profileTrialBody}>
                      <div className={styles.profileTrialTitle}>
                        <span>Free trial</span>
                        <span className={`chip chip--sm chip--dot ${trialRemaining > 0 ? 'chip--success' : 'chip--warning'}`}>
                          {trialRemaining} of {trialTotal} scans left
                        </span>
                        {trialRemaining > 0 && !trialStatus.has_own_key && !trialStatus.daily_available && (
                          <span className="chip chip--sm chip--warning">Busy today</span>
                        )}
                      </div>
                      <span className={styles.profileTrialText}>
                        {trialText}{' '}
                        <a
                          href="https://aistudio.google.com/app/apikey"
                          target="_blank"
                          rel="noopener noreferrer"
                          className={styles.profileLink}
                        >
                          Get a free Gemini key
                        </a>
                      </span>
                    </div>
                  </div>
                )}

                {/* Upgrade Paywall Banner when user hits limit */}
                {showUpgradePrompt && (
                  <div className={`${styles.profileUpgrade} enter-3d`}>
                    <div className={styles.profileUpgradeTitle}>
                      <RiVipCrownFill size={18} />
                      <span>API Integration Limit Reached (3 / 3 Keys)</span>
                    </div>
                    <p className={styles.profileUpgradeText}>
                      Free workspaces can connect up to 3 API keys. Remove a key to add another one — Pro and Enterprise plans with more slots are coming soon.
                    </p>
                    <div className={styles.profileRow}>
                      <Link href="/pricing" onClick={closeProfileModal} className="btn btn-primary btn-sm">
                        <TbSparkles size={15} /> View plans →
                      </Link>
                      <button type="button" onClick={() => setShowUpgradePrompt(false)} className="btn btn-secondary btn-sm">
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}

                {/* Feedback Alert */}
                {keyFeedback && (
                  <div
                    className={`${styles.authBanner} ${keyFeedback.type === 'error' ? styles.authBannerError : styles.authBannerSuccess}`}
                    role={keyFeedback.type === 'error' ? 'alert' : 'status'}
                  >
                    {keyFeedback.type === 'error' ? <TbAlertCircle size={16} /> : <TbCheck size={16} />}
                    <span>{keyFeedback.msg}</span>
                  </div>
                )}

                {/* Configured Keys List */}
                {loadingKeys ? (
                  <div className={styles.profileLoading}>
                    <TbLoader2 size={18} className="pulse" />
                    <span>Loading configured AI integrations...</span>
                  </div>
                ) : apiKeys.length > 0 ? (
                  <div className={styles.profileKeyList}>
                    {apiKeys.map((k) => (
                      <div
                        key={k.id}
                        className={`${styles.profileRaised} ${styles.profileKeyRow} ${k.is_default ? styles.profileKeyRowDefault : ''}`}
                      >
                        <div className={styles.profileKeyInfo}>
                          <span className="icon-well icon-well--sm tone-neutral">{getProviderIcon(k.provider_id, 18)}</span>
                          <div className={styles.profileKeyText}>
                            <div className={styles.profileKeyName}>
                              <span>{k.key_name}</span>
                              {k.model && <span className="chip chip--sm chip--neutral">{k.model}</span>}
                            </div>
                            <span className={styles.profileKeyMask}>{k.masked_key}</span>
                          </div>
                        </div>

                        <div className={styles.profileKeyActions}>
                          {k.is_default ? (
                            <span className="chip chip--sm chip--success">
                              <RiStarFill size={11} /> Default
                            </span>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleSetDefaultKey(k.id)}
                              className="btn btn-secondary btn-sm"
                              title="Set as active model for next scan"
                            >
                              <RiStarLine size={13} /> Set Default
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => handleDeleteKey(k.id, k.key_name)}
                            className="btn btn-danger btn-sm"
                            title="Remove API Key"
                          >
                            <TbTrash size={14} />
                            <span className="sr-only">Remove {k.key_name}</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}

                {/* Add Key Toggle / Paywall Trigger */}
                {!showAddForm ? (
                  <div className={styles.profileRow}>
                    {atFreeLimit ? (
                      <button
                        type="button"
                        onClick={() => setShowUpgradePrompt(true)}
                        className={`btn btn-secondary ${styles.profileLimitBtn}`}
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
                        className="btn btn-secondary btn-sm"
                      >
                        <RiAddLine size={15} /> Connect AI Model / Provider Key
                      </button>
                    )}
                  </div>
                ) : (
                  /* Add API Key Form */
                  <form onSubmit={handleCreateApiKey} className={`${styles.profileRaised} ${styles.profileForm}`}>
                    <div className={styles.profileFormHead}>
                      <span className={styles.profileFormTitle}>Configure New Model Integration</span>
                      {apiKeys.length > 0 && (
                        <button type="button" onClick={() => setShowAddForm(false)} className={styles.profileLinkBtn}>
                          Cancel
                        </button>
                      )}
                    </div>

                    {/* Provider Selector */}
                    <div className={styles.profileField}>
                      <span className={styles.profileLabel} id="profile-provider-label">
                        AI Provider Platform
                      </span>
                      <div className={styles.profileProviderGrid} role="group" aria-labelledby="profile-provider-label">
                        {['gemini', 'openai', 'anthropic', 'deepseek', 'local_llm'].map((pid) => {
                          const isSel = selectedProvider === pid;
                          return (
                            <button
                              key={pid}
                              type="button"
                              onClick={() => handleProviderSelect(pid)}
                              className={styles.profileProviderBtn}
                              aria-pressed={isSel}
                            >
                              {getProviderIcon(pid, 14)}
                              <span>{PROVIDER_LABELS[pid]}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Model Selector & Key Label */}
                    <div className={styles.profileGrid2}>
                      <div className={styles.profileField}>
                        <label className={styles.profileLabel} htmlFor="profile-model">
                          Model Selection
                        </label>
                        <select
                          id="profile-model"
                          value={selectedModel}
                          onChange={(e) => setSelectedModel(e.target.value)}
                          className={styles.profileInput}
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

                      <div className={styles.profileField}>
                        <label className={styles.profileLabel} htmlFor="profile-key-name">
                          Integration Label
                        </label>
                        <input
                          id="profile-key-name"
                          type="text"
                          value={keyNameInput}
                          onChange={(e) => setKeyNameInput(e.target.value)}
                          placeholder={`e.g. My ${selectedProvider.toUpperCase()} Key`}
                          className={styles.profileInput}
                        />
                      </div>
                    </div>

                    {/* Secret Key Input */}
                    <div className={styles.profileField}>
                      <label className={styles.profileLabel} htmlFor="profile-key-secret">
                        Secret API Key
                      </label>
                      <div className={styles.profileSecretWrap}>
                        <input
                          id="profile-key-secret"
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
                          className={`${styles.profileInput} ${styles.profileInputMono}`}
                        />
                        <button
                          type="button"
                          onClick={() => setShowKeySecret(!showKeySecret)}
                          className={styles.profileEyeBtn}
                          aria-label={showKeySecret ? 'Hide API key' : 'Show API key'}
                          aria-pressed={showKeySecret}
                        >
                          {showKeySecret ? <RiEyeOffLine size={16} /> : <RiEyeLine size={16} />}
                        </button>
                      </div>
                    </div>

                    {/* Optional Custom Endpoint for DeepSeek / Local */}
                    {(selectedProvider === 'deepseek' || selectedProvider === 'local_llm') && (
                      <div className={styles.profileField}>
                        <label className={styles.profileLabel} htmlFor="profile-endpoint">
                          Custom API Endpoint URL
                        </label>
                        <input
                          id="profile-endpoint"
                          type="text"
                          value={endpointInput}
                          onChange={(e) => setEndpointInput(e.target.value)}
                          placeholder={selectedProvider === 'deepseek' ? 'https://api.deepseek.com/v1' : 'http://localhost:11434/v1'}
                          className={`${styles.profileInput} ${styles.profileInputMono}`}
                        />
                      </div>
                    )}

                    {/* Default Checkbox */}
                    <label className={styles.profileCheck}>
                      <input
                        type="checkbox"
                        checked={isDefaultInput}
                        onChange={(e) => setIsDefaultInput(e.target.checked)}
                      />
                      <span>Set as active default model for QA report generation</span>
                    </label>

                    <button type="submit" disabled={isSubmittingKey} className="btn btn-primary" style={{ width: '100%' }}>
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
                <div className={styles.profileDocLinks}>
                  <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className={styles.profileDocLink}>
                    <RiGoogleFill size={12} /> Google AI Studio <TbExternalLink size={11} />
                  </a>
                  <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className={styles.profileDocLink}>
                    <RiOpenaiFill size={12} /> OpenAI Platform <TbExternalLink size={11} />
                  </a>
                  <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className={styles.profileDocLink}>
                    <SiAnthropic size={11} /> Anthropic Console <TbExternalLink size={11} />
                  </a>
                </div>
              </section>

              {/* Supabase Cloud Storage (20 MB Per-User Limit) */}
              <section className={`surface-inset ${styles.profilePanel} ${storageTone}`} aria-labelledby="profile-storage-title">
                <div className={styles.profilePanelHead}>
                  <h3 className={styles.profilePanelTitle} id="profile-storage-title">
                    <span className="icon-well icon-well--sm">
                      <TbDatabase size={18} />
                    </span>
                    <span>Supabase Cloud Report Storage</span>
                  </h3>
                  <span className="chip chip--sm chip--accent">
                    <TbCloudDownload size={13} /> Direct Cloud Download
                  </span>
                </div>

                {/* Progress bar & metrics */}
                <div className={styles.profileSection}>
                  <div className={styles.profileMeterHead}>
                    <span>Storage Used ({storageData?.file_count ?? 0} files)</span>
                    <span className={`${styles.profileMeterValue} ${storageData?.is_quota_exceeded ? styles.profileMeterValueOver : ''}`}>
                      {storageData ? `${storageData.used_mb.toFixed(2)} MB / ${storageData.limit_mb.toFixed(0)} MB` : '0.00 MB / 20 MB'}{' '}
                      <span style={{ color: 'var(--text-subtle)', fontWeight: 500 }}>
                        ({storageData ? `${storageData.used_percent.toFixed(1)}%` : '0%'})
                      </span>
                    </span>
                  </div>

                  <div
                    className={styles.profileMeter}
                    role="progressbar"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.round(storagePercent)}
                    aria-label="Cloud storage used"
                  >
                    <div className={styles.profileMeterFill} style={{ transform: `scaleX(${storagePercent / 100})` }} />
                  </div>
                </div>

                <div className={styles.profileMeterNote}>
                  <span>Dedicated 20 MB bucket quota per user</span>
                  <span>Reports stored in Supabase bucket</span>
                </div>

                {storageData?.is_quota_exceeded && (
                  <div className={`${styles.authBanner} ${styles.authBannerError}`} role="alert">
                    <TbAlertCircle size={15} />
                    <span>20 MB quota limit reached. Delete older scans to free cloud storage space.</span>
                  </div>
                )}
              </section>

              {/* Subscription & Plan Status */}
              <div className={`surface-inset ${styles.profilePlanRow}`}>
                <div>
                  <div className={styles.profilePlanLabel}>Current Subscription</div>
                  <div className={styles.profilePlanValue}>{userPlan} Tier</div>
                </div>
                <Link href="/pricing" onClick={closeProfileModal} className="btn btn-primary btn-sm">
                  <TbCreditCard size={14} /> View plans
                </Link>
              </div>

              {/* Account Preferences */}
              <div className={styles.profileSection}>
                <span className="section-eyebrow">Preferences</span>

                <div className={`${styles.profileRaised} ${styles.profilePrefRow}`}>
                  <label className={styles.profilePrefLabel} htmlFor="profile-notifications">
                    <TbBell size={16} /> Email Scan Reports
                  </label>
                  <input
                    id="profile-notifications"
                    type="checkbox"
                    checked={notificationsEnabled}
                    onChange={(e) => setNotificationsEnabled(e.target.checked)}
                    style={{ width: '16px', height: '16px', accentColor: 'var(--primary)' }}
                  />
                </div>

                <div className={`${styles.profileRaised} ${styles.profilePrefRow} tone-info`}>
                  <label className={styles.profilePrefLabel} htmlFor="profile-viewport">
                    <TbDeviceDesktop size={16} /> Default Testing Viewport
                  </label>
                  <select
                    id="profile-viewport"
                    value={defaultViewport}
                    onChange={(e) => setDefaultViewport(e.target.value)}
                    className={styles.profileInput}
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
                onClick={async () => {
                  closeProfileModal();
                  await signOut();
                }}
                className={`btn btn-secondary ${styles.profileLogoutBtn}`}
              >
                <RiLogoutBoxRLine size={16} />
                <span>Log Out</span>
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
