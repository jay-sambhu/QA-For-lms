"use client";

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { m as motion, AnimatePresence } from 'framer-motion';
import {
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
  TbKey,
  TbTrash,
  TbAlertCircle,
  TbBrain,
  TbServer2,
  TbSparkles,
  TbLoader2,
  TbCheck,
  TbArrowRight,
  TbChevronUp,
} from 'react-icons/tb';
import { useAuth } from '../../context/AuthContext';
import { Surface3D, EmptyState3D } from '../three';
import d from './dashboard3d.module.css';

interface ApiKeyManagerProps {
  onKeysUpdated?: () => void;
}

export const ApiKeyManager: React.FC<ApiKeyManagerProps> = ({ onKeysUpdated }) => {
  const { session } = useAuth();

  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [quotaData, setQuotaData] = useState<{
    count: number;
    max_allowed: number;
    plan_tier: string;
    is_paid: boolean;
    can_add_more: boolean;
    supported_providers: any[];
  } | null>(null);

  const [loading, setLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState('gemini');
  const [selectedModel, setSelectedModel] = useState('gemini-3.8-flash');
  const [keyNameInput, setKeyNameInput] = useState('');
  const [keyValueInput, setKeyValueInput] = useState('');
  const [endpointInput, setEndpointInput] = useState('');
  const [isDefaultInput, setIsDefaultInput] = useState(true);
  const [showKeySecret, setShowKeySecret] = useState(false);
  const [revealedKeyIds, setRevealedKeyIds] = useState<{ [id: string]: boolean }>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [settingDefaultId, setSettingDefaultId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Fetch API keys and quota details
  const fetchApiKeys = useCallback(async () => {
    if (!session?.access_token) return;
    setLoading(true);
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

        // Automatically open form if user has no keys yet
        if (!data.keys || data.keys.length === 0) {
          setShowAddForm(true);
        }
      }
    } catch (e) {
      console.error('Failed to load user API keys in ApiKeyManager:', e);
    } finally {
      setLoading(false);
    }
  }, [session?.access_token]);

  useEffect(() => {
    fetchApiKeys();
  }, [fetchApiKeys]);

  const handleProviderSelect = (pid: string) => {
    setSelectedProvider(pid);
    const pMeta = quotaData?.supported_providers?.find((p: any) => p.id === pid);
    if (pMeta) {
      setSelectedModel(pMeta.default_model);
      setEndpointInput(pMeta.default_endpoint || '');
    }
    setFeedback(null);
  };

  const handleAddKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyValueInput.trim() && selectedProvider !== 'local_llm') {
      setFeedback({ type: 'error', msg: 'Please provide a valid API Key token.' });
      return;
    }

    // Client-side guard for free tier quota
    if (quotaData && !quotaData.is_paid && quotaData.count >= 3) {
      setShowUpgradeModal(true);
      setFeedback({
        type: 'error',
        msg: 'Free tier limit reached (3/3 keys). Upgrade to Pro to connect more models.',
      });
      return;
    }

    setIsSubmitting(true);
    setFeedback(null);

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
          setShowUpgradeModal(true);
        }
        throw new Error(data.detail || 'Failed to save API key');
      }

      setFeedback({ type: 'success', msg: data.message || 'API Key connected successfully!' });
      setKeyValueInput('');
      setKeyNameInput('');
      setShowAddForm(false);
      setShowUpgradeModal(false);
      await fetchApiKeys();
      if (onKeysUpdated) onKeysUpdated();
      setTimeout(() => setFeedback(null), 4000);
    } catch (err: any) {
      setFeedback({ type: 'error', msg: err.message || 'Error saving API key' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSetDefaultKey = async (keyId: string) => {
    setSettingDefaultId(keyId);
    try {
      const res = await fetch(`/api/v1/user/api-keys/${keyId}/default`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (res.ok) {
        await fetchApiKeys();
        if (onKeysUpdated) onKeysUpdated();
      }
    } catch (e) {
      console.error('Failed to set default key:', e);
    } finally {
      setSettingDefaultId(null);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to disconnect this API key?')) return;
    setDeletingId(keyId);
    try {
      const res = await fetch(`/api/v1/user/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (res.ok) {
        await fetchApiKeys();
        if (onKeysUpdated) onKeysUpdated();
      }
    } catch (e) {
      console.error('Failed to delete key:', e);
    } finally {
      setDeletingId(null);
    }
  };

  const renderProviderIcon = (id: string, size = 18) => {
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

  const currentProviderMeta = quotaData?.supported_providers?.find(
    (p: any) => p.id === selectedProvider
  );

  const isFreeLimitReached = !!quotaData && !quotaData.is_paid && quotaData.count >= 3;

  const quotaChipTone = quotaData?.is_paid ? 'chip--violet' : isFreeLimitReached ? 'chip--warning' : 'chip--info';

  return (
    <Surface3D as="section" id="ai-models-manager" accent aria-labelledby="ai-models-title" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      {/* Header bar */}
      <div className={d.panelHead}>
        <div className={d.panelTitleBlock}>
          <span className="icon-well" aria-hidden="true">
            <RiCpuLine size={22} />
          </span>
          <div>
            <div className={d.panelTitleRow}>
              <h2 id="ai-models-title" className={d.panelTitle}>
                AI models &amp; providers
              </h2>
              {/* Quota Badge */}
              <span className={`chip chip--sm ${quotaChipTone}`}>
                {quotaData?.is_paid ? (
                  <>
                    <RiVipCrownFill size={12} />
                    <span>UNLIMITED ({(quotaData.plan_tier || 'PRO').toUpperCase()})</span>
                  </>
                ) : (
                  <>
                    <TbKey size={12} />
                    <span>{apiKeys.length} / 3 KEYS (FREE TIER)</span>
                  </>
                )}
              </span>
            </div>
            <p className={d.panelSub}>
              Bring your own key for Google Gemini, OpenAI, Claude, DeepSeek or a local LLM (Ollama). The default key generates your QA defect reports.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className={d.panelTools}>
          <button
            type="button"
            onClick={() => {
              if (isFreeLimitReached && !showAddForm) {
                setShowUpgradeModal(true);
              } else {
                setShowAddForm(!showAddForm);
              }
            }}
            className={`btn ${showAddForm ? 'btn-secondary' : 'btn-primary'} btn-sm`}
            aria-expanded={showAddForm}
            aria-controls="ai-key-add-form"
          >
            {showAddForm ? (
              <>
                <TbChevronUp size={16} /> Hide add form
              </>
            ) : (
              <>
                <RiAddLine size={16} /> Add AI key / model
              </>
            )}
          </button>
        </div>
      </div>

      {/* Subscription Paywall Prompt if limit reached */}
      {(showUpgradeModal || (isFreeLimitReached && showAddForm)) && (
        <div className={`surface-inset tone-warning enter-3d ${d.upgradeNotice}`} role="status">
          <div className={d.upgradeBody}>
            <span className="icon-well" aria-hidden="true">
              <RiVipCrownFill size={20} />
            </span>
            <div>
              <div className={d.upgradeTitle}>Free tier maximum reached (3 of 3 allowed keys)</div>
              <div className={d.upgradeText}>
                The Free plan supports up to 3 AI model keys. Remove a key to add another one — Pro and Enterprise plans with more slots are coming soon.
              </div>
            </div>
          </div>
          <div className={d.upgradeActions}>
            <Link href="/pricing" className="btn btn-primary btn-sm">
              <TbSparkles size={16} /> View plans <TbArrowRight size={16} />
            </Link>
            <button type="button" onClick={() => setShowUpgradeModal(false)} className="btn btn-secondary btn-sm">
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Inline Add API Key Drawer Form */}
      <AnimatePresence>
        {showAddForm && (
          <motion.form
            id="ai-key-add-form"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            onSubmit={handleAddKey}
            className={`surface-inset ${d.addForm}`}
          >
            <div className={d.formHead}>
              <div className={d.formTitle}>Connect a new AI provider &amp; model</div>
              <span className={d.formMeta}>Stored encrypted · Zero shared telemetry</span>
            </div>

            {/* Provider Selector Tabs */}
            <div className={d.fieldGroup}>
              <span className={d.fieldLabel}>Select AI platform provider</span>
              <div className={d.providerGrid} role="group" aria-label="AI provider">
                {(quotaData?.supported_providers || [
                  { id: 'gemini', name: 'Google Gemini' },
                  { id: 'openai', name: 'OpenAI' },
                  { id: 'anthropic', name: 'Anthropic' },
                  { id: 'deepseek', name: 'DeepSeek' },
                  { id: 'local_llm', name: 'Local LLM' },
                ]).map((p: any) => {
                  const isSelected = selectedProvider === p.id;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => handleProviderSelect(p.id)}
                      className={d.providerBtn}
                      aria-pressed={isSelected}
                    >
                      {renderProviderIcon(p.id, 16)}
                      <span>{p.name.split(' ')[0]}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Model & Label Selection Grid */}
            <div className={d.fieldGrid}>
              {/* Model Dropdown */}
              <div className={d.fieldGroup}>
                <label className={d.fieldLabel} htmlFor="ai-key-model">
                  Model target
                </label>
                <select
                  id="ai-key-model"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className={d.field}
                >
                  {(currentProviderMeta?.models || [selectedModel]).map((m: string) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>

              {/* Friendly Label Name */}
              <div className={d.fieldGroup}>
                <label className={d.fieldLabel} htmlFor="ai-key-name">
                  Key label (optional)
                </label>
                <input
                  id="ai-key-name"
                  type="text"
                  placeholder={`e.g. My ${selectedProvider.toUpperCase()} Work Key`}
                  value={keyNameInput}
                  onChange={(e) => setKeyNameInput(e.target.value)}
                  className={d.field}
                />
              </div>
            </div>

            {/* Secret API Key Input */}
            <div className={d.fieldGroup}>
              <label className={d.fieldLabel} htmlFor="ai-key-secret">
                {selectedProvider === 'local_llm'
                  ? 'Authorization token (optional for Ollama)'
                  : `API secret key for ${currentProviderMeta?.name || selectedProvider}`}
              </label>
              <div className={d.passwordWrap}>
                <input
                  id="ai-key-secret"
                  type={showKeySecret ? 'text' : 'password'}
                  placeholder={
                    selectedProvider === 'gemini'
                      ? 'AIzaSy...'
                      : selectedProvider === 'openai'
                      ? 'sk-proj-...'
                      : selectedProvider === 'anthropic'
                      ? 'sk-ant-...'
                      : 'Enter secret API key token'
                  }
                  value={keyValueInput}
                  onChange={(e) => setKeyValueInput(e.target.value)}
                  required={selectedProvider !== 'local_llm'}
                  className={`${d.field} ${d.mono}`}
                  autoComplete="off"
                />
                <button
                  type="button"
                  onClick={() => setShowKeySecret(!showKeySecret)}
                  className={`${d.iconBtn} ${d.passwordToggle}`}
                  aria-label={showKeySecret ? 'Hide API key' : 'Show API key'}
                >
                  {showKeySecret ? <RiEyeOffLine size={16} /> : <RiEyeLine size={16} />}
                </button>
              </div>
            </div>

            {/* Custom Endpoint Input (if Ollama or custom proxy) */}
            {(selectedProvider === 'local_llm' || currentProviderMeta?.requires_endpoint) && (
              <div className={d.fieldGroup}>
                <label className={d.fieldLabel} htmlFor="ai-key-endpoint">
                  Custom endpoint URL (Ollama or OpenAI-compatible gateway)
                </label>
                <input
                  id="ai-key-endpoint"
                  type="url"
                  placeholder="http://localhost:11434/v1"
                  value={endpointInput}
                  onChange={(e) => setEndpointInput(e.target.value)}
                  className={`${d.field} ${d.mono}`}
                />
              </div>
            )}

            {/* Set Default Checkbox */}
            <label className={d.checkRow} htmlFor="dashboard-is-default-key">
              <input
                type="checkbox"
                id="dashboard-is-default-key"
                checked={isDefaultInput}
                onChange={(e) => setIsDefaultInput(e.target.checked)}
                className={d.checkbox}
              />
              <span className={d.checkText}>Set this model as the active default engine for automated QA crawls</span>
            </label>

            {/* Feedback message */}
            {feedback && (
              <div
                className={`${d.notice} ${feedback.type === 'error' ? d.noticeDanger : d.noticeSuccess}`}
                role={feedback.type === 'error' ? 'alert' : 'status'}
              >
                {feedback.type === 'error' ? (
                  <TbAlertCircle size={16} className={d.noticeIcon} />
                ) : (
                  <TbCheck size={16} className={d.noticeIcon} />
                )}
                <span>{feedback.msg}</span>
              </div>
            )}

            {/* Submit button */}
            <div className={d.formActions}>
              <button type="button" onClick={() => setShowAddForm(false)} className="btn btn-secondary btn-sm">
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || (isFreeLimitReached && !quotaData?.is_paid)}
                className="btn btn-primary btn-sm"
              >
                {isSubmitting ? (
                  <>
                    <TbLoader2 className="pulse" size={16} /> Storing key...
                  </>
                ) : (
                  <>
                    <TbCheck size={16} /> Save &amp; connect key
                  </>
                )}
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      {/* Feedback shown after the form closes (e.g. a successful save) */}
      {feedback && !showAddForm && (
        <div
          className={`${d.notice} ${feedback.type === 'error' ? d.noticeDanger : d.noticeSuccess}`}
          role={feedback.type === 'error' ? 'alert' : 'status'}
        >
          {feedback.type === 'error' ? (
            <TbAlertCircle size={16} className={d.noticeIcon} />
          ) : (
            <TbCheck size={16} className={d.noticeIcon} />
          )}
          <span>{feedback.msg}</span>
        </div>
      )}

      {/* List of Connected API Keys */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <div className={d.keysHead}>
          <span className="section-eyebrow">Active AI keys ({apiKeys.length} connected)</span>
          <span className={d.keysHint}>Click the star to switch the default QA engine</span>
        </div>

        {loading ? (
          <div className={d.loadingRow}>
            <TbLoader2 size={16} className="pulse" /> Loading connected API keys...
          </div>
        ) : apiKeys.length === 0 ? (
          <EmptyState3D
            compact
            icon={<TbKey size={16} />}
            title="No AI model keys connected yet"
            description="Connect your Google Gemini, OpenAI, Claude or DeepSeek API key to enable autonomous QA defect analysis and report generation."
            action={
              <button type="button" onClick={() => setShowAddForm(true)} className="btn btn-primary btn-sm">
                <RiAddLine size={16} /> Connect first API key
              </button>
            }
          />
        ) : (
          <div className="auto-grid" style={{ ['--grid-min' as string]: '280px', ['--grid-gap' as string]: '12px' } as React.CSSProperties}>
            {apiKeys.map((key) => {
              const isDefault = !!key.is_default;
              const isRevealed = !!revealedKeyIds[key.id];

              return (
                <div key={key.id} className={`${d.keyCard} ${isDefault ? d.keyCardDefault : ''}`}>
                  <div className={d.keyTop}>
                    <div className={d.keyIdent}>
                      <span className={d.keyIcon} aria-hidden="true">
                        {renderProviderIcon(key.provider_id, 18)}
                      </span>
                      <div>
                        <div className={d.keyName}>
                          {key.key_name || `${(key.provider_id || '').toUpperCase()} Engine`}
                        </div>
                        <div className={d.keyModel}>
                          <span className={`chip chip--sm chip--neutral ${d.mono}`}>{key.model || 'default-model'}</span>
                        </div>
                      </div>
                    </div>

                    {/* Default Status Badge / Action */}
                    {isDefault ? (
                      <span className="chip chip--sm chip--success">
                        <RiStarFill size={11} /> Default engine
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleSetDefaultKey(key.id)}
                        disabled={settingDefaultId === key.id}
                        title="Set as Default QA Model"
                        className="btn btn-secondary btn-sm"
                      >
                        {settingDefaultId === key.id ? <TbLoader2 size={12} className="pulse" /> : <RiStarLine size={12} />} Set default
                      </button>
                    )}
                  </div>

                  {/* Masked Key Display & Actions */}
                  <div className={`${d.keyMask} ${d.mono}`}>
                    <span>
                      {isRevealed
                        ? key.masked_key || '••••••••••••'
                        : (key.masked_key || '••••••••••••').replace(/^(AIzaSy|sk-proj-|sk-ant-).*(.{4})$/, '$1...$2')}
                    </span>
                    <div className={d.keyMaskActions}>
                      <button
                        type="button"
                        onClick={() =>
                          setRevealedKeyIds((prev) => ({ ...prev, [key.id]: !prev[key.id] }))
                        }
                        title={isRevealed ? 'Mask key' : 'Show masked snippet'}
                        aria-label={isRevealed ? 'Mask key' : 'Show masked snippet'}
                        className={d.iconBtn}
                      >
                        {isRevealed ? <RiEyeOffLine size={14} /> : <RiEyeLine size={14} />}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteKey(key.id)}
                        disabled={deletingId === key.id}
                        title="Disconnect API Key"
                        aria-label="Disconnect API key"
                        className={`${d.iconBtn} ${d.iconBtnDanger}`}
                      >
                        {deletingId === key.id ? <TbLoader2 size={14} className="pulse" /> : <TbTrash size={14} />}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Surface3D>
  );
};
