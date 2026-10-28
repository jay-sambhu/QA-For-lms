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
  TbCopy,
  TbCheck,
  TbExternalLink,
  TbTrash,
  TbAlertCircle,
  TbDashboard,
  TbArrowRight,
  TbSparkles,
  TbLoader2,
  TbLock,
  TbCloudDownload,
  TbDatabase,
  TbGift,
} from 'react-icons/tb';
import { useAuth } from '../../context/AuthContext';
import { SegmentedTabs3D } from '../three';
import { useApiKeys, ProviderIcon, PROVIDER_LABELS, KEY_PLACEHOLDERS, FREE_KEY_LIMIT } from './useApiKeys';
import s from './auth3d.module.css';

type ProfileTab = 'models' | 'storage';

type StorageUsage = {
  used_bytes: number;
  limit_bytes: number;
  used_mb: number;
  limit_mb: number;
  used_percent: number;
  file_count: number;
  is_quota_exceeded: boolean;
};

const tierChipClass = (isAdmin: boolean, plan: string) => {
  if (isAdmin) return 'chip--violet';
  if (plan === 'pro') return 'chip--primary';
  if (plan === 'enterprise') return 'chip--warning';
  return 'chip--neutral';
};

export const UserProfileModal: React.FC = () => {
  const { session, profileModalOpen, closeProfileModal, signOut, userPlan, userRole, isAdmin: authIsAdmin } = useAuth();
  const reduceMotion = useReducedMotion();
  const token = session?.access_token;

  const userIsAdmin = authIsAdmin || userRole === 'admin';
  const email = session?.user?.email || 'user@example.com';
  const userId = session?.user?.id || 'anonymous';
  const avatarChar = email.charAt(0).toUpperCase();

  const [tab, setTab] = useState<ProfileTab>('models');
  const [copiedId, setCopiedId] = useState(false);

  const handleCopyId = async () => {
    try {
      await navigator.clipboard.writeText(userId);
      setCopiedId(true);
      window.setTimeout(() => setCopiedId(false), 2000);
    } catch {
      setCopiedId(false);
    }
  };

  const {
    keys,
    quota,
    trial,
    providers,
    loading: loadingKeys,
    busyId,
    feedback,
    setFeedback,
    atFreeLimit,
    refresh: refreshKeys,
    addKey,
    setDefault,
    deleteKey,
  } = useApiKeys(token, { auto: false });

  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState('gemini');
  const [selectedModel, setSelectedModel] = useState('gemini-3.8-flash');
  const [keyNameInput, setKeyNameInput] = useState('');
  const [keyValueInput, setKeyValueInput] = useState('');
  const [endpointInput, setEndpointInput] = useState('');
  const [isDefaultInput, setIsDefaultInput] = useState(true);
  const [showKeySecret, setShowKeySecret] = useState(false);
  const [isSubmittingKey, setIsSubmittingKey] = useState(false);
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);

  const [storageData, setStorageData] = useState<StorageUsage | null>(null);

  const fetchStorageUsage = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch('/api/v1/user/storage', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setStorageData(await res.json());
    } catch (e) {
      console.error('Failed to load storage usage:', e);
    }
  }, [token]);

  useEffect(() => {
    if (!profileModalOpen || !token) return;
    void refreshKeys().then((loaded) => {
      if (loaded && loaded.length === 0) setShowAddForm(true);
    });
    void fetchStorageUsage();
  }, [profileModalOpen, token, refreshKeys, fetchStorageUsage]);

  // Close on Escape key press
  useEffect(() => {
    if (!profileModalOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeProfileModal();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [profileModalOpen, closeProfileModal]);

  const currentProvider = providers.find((p) => p.id === selectedProvider);

  const handleProviderSelect = (pid: string) => {
    setSelectedProvider(pid);
    const meta = providers.find((p) => p.id === pid);
    if (meta) {
      if (meta.default_model) setSelectedModel(meta.default_model);
      setEndpointInput(meta.default_endpoint || '');
    }
    setFeedback(null);
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingKey(true);
    try {
      const result = await addKey({
        provider_id: selectedProvider,
        api_key: keyValueInput,
        key_name: keyNameInput,
        model: selectedModel,
        endpoint: endpointInput,
        is_default: isDefaultInput,
      });
      if (result.limitReached) setShowUpgradePrompt(true);
      if (result.ok) {
        setKeyValueInput('');
        setKeyNameInput('');
        setShowAddForm(false);
        setShowUpgradePrompt(false);
      }
    } finally {
      setIsSubmittingKey(false);
    }
  };

  const handleDeleteKey = async (keyId: string, name: string) => {
    if (!confirm(`Are you sure you want to remove ${name}?`)) return;
    await deleteKey(keyId);
  };

  const quotaChipTone = quota?.is_paid ? 'chip--violet' : atFreeLimit ? 'chip--warning' : 'chip--info';
  const quotaLabel = quota?.is_paid
    ? `Unlimited (${(quota.plan_tier || 'PRO').toUpperCase()})`
    : `${keys.length} / ${FREE_KEY_LIMIT} keys · Free tier`;

  const trialVisible = Boolean(trial?.enabled);
  const trialRemaining = trial?.remaining ?? 0;
  const trialTotal = trial?.total ?? 0;
  const trialTone = trial?.has_own_key ? 'tone-info' : trialRemaining > 0 ? 'tone-success' : 'tone-warning';
  const trialText = trial?.has_own_key
    ? 'Your own key is active, so your scans never use trial credits.'
    : trialRemaining > 0
    ? `Your first ${trialTotal} scans run on our Gemini key with no setup. Add your own free Gemini key for unlimited scans.`
    : `You've used all ${trialTotal} free trial scans. Add your own free Gemini key to keep scanning.`;

  const storagePercent = Math.min(storageData?.used_percent ?? 0, 100);
  const storageTone = storageData?.is_quota_exceeded ? 'tone-danger' : storagePercent > 75 ? 'tone-warning' : 'tone-info';
  const showEndpoint = selectedProvider === 'local_llm' || Boolean(currentProvider?.requires_endpoint);

  const cardMotion = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } }
    : {
        initial: { opacity: 0, y: 28, scale: 0.96, rotateX: 10 },
        animate: { opacity: 1, y: 0, scale: 1, rotateX: 0 },
        exit: { opacity: 0, y: 16, scale: 0.97, rotateX: 6 },
      };

  const feedbackNotice = feedback && (
    <div
      className={`${s.notice} ${feedback.type === 'error' ? 'tone-danger' : 'tone-success'}`}
      role={feedback.type === 'error' ? 'alert' : 'status'}
    >
      {feedback.type === 'error' ? <TbAlertCircle size={16} /> : <TbCheck size={16} />}
      <span>{feedback.msg}</span>
    </div>
  );

  return (
    <AnimatePresence>
      {profileModalOpen && session && (
        <motion.div
          key="user-profile-modal-overlay"
          className={s.modalOverlay}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={closeProfileModal}
        >
          <motion.div
            className={`${s.modalCard} ${s.profileCard} glass-3d`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="profile-modal-title"
            style={{ transformPerspective: 1400, transformOrigin: '50% 0%' }}
            {...cardMotion}
            transition={{ duration: reduceMotion ? 0.15 : 0.45, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={s.modalHeader}>
              <div className={s.modalLogo} id="profile-modal-title">
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
                className={s.iconBtn}
                title="Close"
                aria-label="Close"
              >
                <RiCloseLine size={20} />
              </button>
            </div>

            <div className={s.profileBody}>
              {/* Identity */}
              <div className={`surface-inset ${s.identity}`}>
                <div className={`${s.avatar} ${userIsAdmin ? s.avatarAdmin : ''}`} aria-hidden="true">
                  {avatarChar}
                </div>
                <div className={s.identityText}>
                  <div className={s.emailRow}>
                    <span className={s.email}>{email}</span>
                    <span className={`chip chip--sm ${tierChipClass(userIsAdmin, userPlan)}`}>
                      {userIsAdmin ? 'ADMIN' : userPlan.toUpperCase()}
                    </span>
                  </div>
                  <div className={s.meta}>
                    <span>ID: {userId.substring(0, 12)}...</span>
                    <button
                      type="button"
                      onClick={handleCopyId}
                      className={`${s.iconBtn} ${s.iconBtnSm} ${copiedId ? s.copyDone : ''}`}
                      title="Copy User ID"
                      aria-label={copiedId ? 'User ID copied' : 'Copy User ID'}
                    >
                      {copiedId ? <TbCheck size={13} /> : <TbCopy size={13} />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Quick navigation */}
              <div className={s.navRow}>
                {userIsAdmin && (
                  <Link href="/admin" onClick={closeProfileModal} className={`btn btn-secondary tone-violet ${s.navBtn}`}>
                    <span className={s.navBtnBody}>
                      <span className="icon-well icon-well--sm">
                        <RiShieldUserFill size={16} />
                      </span>
                      <span className={s.navBtnText}>
                        <span>Admin Console</span>
                        <span className={s.navBtnDesc}>Role governance, telemetry &amp; CMS</span>
                      </span>
                    </span>
                    <TbArrowRight size={16} aria-hidden="true" />
                  </Link>
                )}
                <Link href="/dashboard" onClick={closeProfileModal} className={`btn btn-secondary tone-primary ${s.navBtn}`}>
                  <span className={s.navBtnBody}>
                    <span className="icon-well icon-well--sm">
                      <TbDashboard size={16} />
                    </span>
                    <span className={s.navBtnText}>
                      <span>QA Dashboard</span>
                      <span className={s.navBtnDesc}>Multi-device autonomous scans &amp; reports</span>
                    </span>
                  </span>
                  <TbArrowRight size={16} aria-hidden="true" />
                </Link>
              </div>

              <SegmentedTabs3D<ProfileTab>
                size="sm"
                fullWidth
                ariaLabel="Account sections"
                idPrefix="profile"
                tabs={[
                  { id: 'models', label: 'AI models & keys', icon: <RiCpuLine size={15} />, badge: keys.length },
                  { id: 'storage', label: 'Storage & plan', icon: <TbDatabase size={15} /> },
                ]}
                active={tab}
                onChange={setTab}
              />

              {tab === 'models' && (
                <section
                  className={`surface-inset ${s.panel}`}
                  role="tabpanel"
                  id="profile-panel-models"
                  aria-labelledby="profile-tab-models"
                >
                  <div className={s.panelHead}>
                    <h3 className={s.panelTitle}>
                      <span className="icon-well icon-well--sm">
                        <RiCpuLine size={18} />
                      </span>
                      <span>AI provider integrations</span>
                    </h3>
                    <span className={`chip chip--sm ${quotaChipTone}`}>{quotaLabel}</span>
                  </div>

                  <p className={s.hint}>
                    Connect your personal API keys for Google Gemini, OpenAI, Anthropic Claude, DeepSeek or a local LLM. Free accounts include up to {FREE_KEY_LIMIT} keys; the default key generates your QA reports.
                  </p>

                  {trialVisible && trial && (
                    <div className={`${s.notice} ${s.noticeStart} ${trialTone}`}>
                      <span className="icon-well icon-well--sm">
                        <TbGift size={16} />
                      </span>
                      <div className={s.noticeBody}>
                        <div className={s.noticeTitle}>
                          <span>Free trial</span>
                          <span className={`chip chip--sm chip--dot ${trialRemaining > 0 ? 'chip--success' : 'chip--warning'}`}>
                            {trialRemaining} of {trialTotal} scans left
                          </span>
                          {trialRemaining > 0 && !trial.has_own_key && !trial.daily_available && (
                            <span className="chip chip--sm chip--warning">Busy today</span>
                          )}
                        </div>
                        <span className={s.noticeText}>
                          {trialText}{' '}
                          <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className={s.link}>
                            Get a free Gemini key
                          </a>
                        </span>
                      </div>
                    </div>
                  )}

                  {showUpgradePrompt && (
                    <div className={`${s.notice} ${s.noticeStart} tone-warning enter-3d`} role="status">
                      <span className="icon-well icon-well--sm">
                        <RiVipCrownFill size={16} />
                      </span>
                      <div className={s.noticeBody}>
                        <div className={s.noticeTitle}>API integration limit reached ({FREE_KEY_LIMIT} / {FREE_KEY_LIMIT} keys)</div>
                        <span className={s.noticeText}>
                          Free workspaces can connect up to {FREE_KEY_LIMIT} API keys. Remove a key to add another one — Pro and Enterprise plans with more slots are coming soon.
                        </span>
                        <div className={s.actions}>
                          <Link href="/pricing" onClick={closeProfileModal} className="btn btn-primary btn-sm">
                            <TbSparkles size={15} /> View plans
                          </Link>
                          <button type="button" onClick={() => setShowUpgradePrompt(false)} className="btn btn-secondary btn-sm">
                            Dismiss
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {!showAddForm && feedbackNotice}

                  {loadingKeys ? (
                    <div className={s.loading}>
                      <TbLoader2 size={18} className="pulse" />
                      <span>Loading configured AI integrations...</span>
                    </div>
                  ) : keys.length > 0 ? (
                    <div className={s.rowList}>
                      {keys.map((k) => (
                        <div key={k.id} className={`${s.row} ${k.is_default ? s.rowDefault : ''}`}>
                          <div className={s.rowInfo}>
                            <span className="icon-well icon-well--sm icon-well--inset tone-neutral">
                              <ProviderIcon id={k.provider_id} size={18} />
                            </span>
                            <div className={s.rowText}>
                              <div className={s.rowName}>
                                <span>{k.key_name || `${(k.provider_id || '').toUpperCase()} Engine`}</span>
                                {k.model && <span className="chip chip--sm chip--neutral">{k.model}</span>}
                              </div>
                              <span className={`${s.rowMask} ${s.mono}`}>{k.masked_key}</span>
                            </div>
                          </div>

                          <div className={s.rowActions}>
                            {k.is_default ? (
                              <span className="chip chip--sm chip--success">
                                <RiStarFill size={11} /> Default
                              </span>
                            ) : (
                              <button
                                type="button"
                                onClick={() => setDefault(k.id)}
                                disabled={busyId === k.id}
                                className="btn btn-secondary btn-sm"
                                title="Set as active model for next scan"
                              >
                                {busyId === k.id ? <TbLoader2 size={13} className="pulse" /> : <RiStarLine size={13} />} Set default
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => handleDeleteKey(k.id, k.key_name || 'this key')}
                              disabled={busyId === k.id}
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

                  {!showAddForm ? (
                    <div className={s.actions}>
                      {atFreeLimit ? (
                        <button type="button" onClick={() => setShowUpgradePrompt(true)} className={`btn btn-secondary ${s.limitBtn}`}>
                          <TbLock size={15} /> Add another key (limit reached · upgrade to unlock)
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
                          <RiAddLine size={15} /> Connect AI model / provider key
                        </button>
                      )}
                    </div>
                  ) : (
                    <form onSubmit={handleCreateApiKey} className={s.form}>
                      <div className={s.formHead}>
                        <span className={s.formTitle}>Configure new model integration</span>
                        {keys.length > 0 && (
                          <button type="button" onClick={() => setShowAddForm(false)} className="btn btn-ghost btn-sm">
                            Cancel
                          </button>
                        )}
                      </div>

                      <div className={s.formGroup}>
                        <span className={s.formLabel} id="profile-provider-label">
                          AI provider platform
                        </span>
                        <SegmentedTabs3D<string>
                          size="sm"
                          fullWidth
                          ariaLabel="AI provider"
                          tabs={providers.map((p) => ({
                            id: p.id,
                            label: PROVIDER_LABELS[p.id] || p.name.split(' ')[0],
                            icon: <ProviderIcon id={p.id} size={14} />,
                          }))}
                          active={selectedProvider}
                          onChange={handleProviderSelect}
                        />
                      </div>

                      <div className={s.grid2}>
                        <div className={s.formGroup}>
                          <label className={s.formLabel} htmlFor="profile-model">
                            Model selection
                          </label>
                          <select
                            id="profile-model"
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            className={s.field}
                          >
                            {(currentProvider?.models?.length ? currentProvider.models : [selectedModel]).map((m) => (
                              <option key={m} value={m}>
                                {m}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div className={s.formGroup}>
                          <label className={s.formLabel} htmlFor="profile-key-name">
                            Integration label
                          </label>
                          <input
                            id="profile-key-name"
                            type="text"
                            value={keyNameInput}
                            onChange={(e) => setKeyNameInput(e.target.value)}
                            placeholder={`e.g. My ${selectedProvider.toUpperCase()} Key`}
                            className={s.field}
                          />
                        </div>
                      </div>

                      <div className={s.formGroup}>
                        <label className={s.formLabel} htmlFor="profile-key-secret">
                          {selectedProvider === 'local_llm' ? 'Authorization token (optional for Ollama)' : 'Secret API key'}
                        </label>
                        <div className={s.secretWrap}>
                          <input
                            id="profile-key-secret"
                            type={showKeySecret ? 'text' : 'password'}
                            value={keyValueInput}
                            onChange={(e) => setKeyValueInput(e.target.value)}
                            placeholder={KEY_PLACEHOLDERS[selectedProvider] || 'Enter secret API key token'}
                            required={selectedProvider !== 'local_llm'}
                            autoComplete="off"
                            className={`${s.field} ${s.mono}`}
                          />
                          <button
                            type="button"
                            onClick={() => setShowKeySecret(!showKeySecret)}
                            className={`${s.iconBtn} ${s.iconBtnSm}`}
                            aria-label={showKeySecret ? 'Hide API key' : 'Show API key'}
                            aria-pressed={showKeySecret}
                          >
                            {showKeySecret ? <RiEyeOffLine size={16} /> : <RiEyeLine size={16} />}
                          </button>
                        </div>
                      </div>

                      {showEndpoint && (
                        <div className={s.formGroup}>
                          <label className={s.formLabel} htmlFor="profile-endpoint">
                            Custom API endpoint URL
                          </label>
                          <input
                            id="profile-endpoint"
                            type="url"
                            value={endpointInput}
                            onChange={(e) => setEndpointInput(e.target.value)}
                            placeholder={currentProvider?.default_endpoint || 'http://localhost:11434/v1'}
                            className={`${s.field} ${s.mono}`}
                          />
                        </div>
                      )}

                      <label className={s.check}>
                        <input type="checkbox" checked={isDefaultInput} onChange={(e) => setIsDefaultInput(e.target.checked)} />
                        <span>Set as active default model for QA report generation</span>
                      </label>

                      {feedbackNotice}

                      <button type="submit" disabled={isSubmittingKey} className="btn btn-primary" style={{ width: '100%' }}>
                        {isSubmittingKey ? (
                          <>
                            <TbLoader2 size={16} className="pulse" />
                            <span>Saving API integration...</span>
                          </>
                        ) : (
                          <>
                            <TbSparkles size={16} />
                            <span>Integrate {selectedProvider.toUpperCase()} key</span>
                          </>
                        )}
                      </button>
                    </form>
                  )}

                  <div className={s.docLinks}>
                    <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className={s.docLink}>
                      <RiGoogleFill size={12} /> Google AI Studio <TbExternalLink size={11} />
                    </a>
                    <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className={s.docLink}>
                      <RiOpenaiFill size={12} /> OpenAI Platform <TbExternalLink size={11} />
                    </a>
                    <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className={s.docLink}>
                      <SiAnthropic size={11} /> Anthropic Console <TbExternalLink size={11} />
                    </a>
                  </div>
                </section>
              )}

              {tab === 'storage' && (
                <div className={s.stack} role="tabpanel" id="profile-panel-storage" aria-labelledby="profile-tab-storage">
                  <section className={`surface-inset ${s.panel} ${storageTone}`} aria-labelledby="profile-storage-title">
                    <div className={s.panelHead}>
                      <h3 className={s.panelTitle} id="profile-storage-title">
                        <span className="icon-well icon-well--sm">
                          <TbDatabase size={18} />
                        </span>
                        <span>Cloud report storage</span>
                      </h3>
                      <span className="chip chip--sm chip--accent">
                        <TbCloudDownload size={13} /> Direct cloud download
                      </span>
                    </div>

                    <div className={s.stack}>
                      <div className={s.meterHead}>
                        <span>Storage used ({storageData?.file_count ?? 0} files)</span>
                        <span className={`${s.meterValue} ${storageData?.is_quota_exceeded ? s.meterOver : ''}`}>
                          {storageData ? `${storageData.used_mb.toFixed(2)} MB / ${storageData.limit_mb.toFixed(0)} MB` : '0.00 MB / 20 MB'}{' '}
                          <span style={{ color: 'var(--text-subtle)', fontWeight: 500 }}>
                            ({storageData ? `${storageData.used_percent.toFixed(1)}%` : '0%'})
                          </span>
                        </span>
                      </div>

                      <div
                        className="neu-track neu-track--lg"
                        style={{ '--p': `${storagePercent}%` } as React.CSSProperties}
                        role="progressbar"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={Math.round(storagePercent)}
                        aria-label="Cloud storage used"
                      />
                    </div>

                    <div className={s.meterNote}>
                      <span>Dedicated 20 MB bucket quota per user</span>
                      <span>Reports stored in Supabase bucket</span>
                    </div>

                    {storageData?.is_quota_exceeded && (
                      <div className={`${s.notice} tone-danger`} role="alert">
                        <TbAlertCircle size={15} />
                        <span>20 MB quota limit reached. Delete older scans to free cloud storage space.</span>
                      </div>
                    )}
                  </section>

                  <div className={`surface-inset ${s.planRow}`}>
                    <div>
                      <div className={s.planLabel}>Current subscription</div>
                      <div className={s.planValue}>{userPlan} Tier</div>
                    </div>
                    <Link href="/pricing" onClick={closeProfileModal} className="btn btn-primary btn-sm">
                      <TbCreditCard size={14} /> View plans
                    </Link>
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={async () => {
                  closeProfileModal();
                  await signOut();
                }}
                className={`btn btn-secondary ${s.logoutBtn}`}
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
