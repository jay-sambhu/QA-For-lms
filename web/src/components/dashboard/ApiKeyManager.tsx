"use client";

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
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
  RiCheckDoubleFill,
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
  TbShieldCheck,
  TbCheck,
  TbInfoCircle,
  TbArrowRight,
  TbChevronDown,
  TbChevronUp,
} from 'react-icons/tb';
import { useAuth } from '../../context/AuthContext';
import styles from '../../app/page.module.css';

interface ApiKeyManagerProps {
  onKeysUpdated?: () => void;
}

export const ApiKeyManager: React.FC<ApiKeyManagerProps> = ({ onKeysUpdated }) => {
  const { session, userPlan } = useAuth();

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
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash');
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

      const data = await res.json();
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
        return <RiCpuLine size={size} color="#818cf8" />;
    }
  };

  const currentProviderMeta = quotaData?.supported_providers?.find(
    (p: any) => p.id === selectedProvider
  );

  const isFreeLimitReached = !!quotaData && !quotaData.is_paid && quotaData.count >= 3;

  return (
    <div
      id="ai-models-manager"
      style={{
        background: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '20px',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        boxShadow: '0 16px 40px rgba(0, 0, 0, 0.35)',
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.2))',
              border: '1px solid rgba(99, 102, 241, 0.35)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#818cf8',
              boxShadow: '0 0 15px rgba(99, 102, 241, 0.25)',
            }}
          >
            <RiCpuLine size={24} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h2
                style={{
                  fontSize: '1.15rem',
                  fontWeight: 800,
                  color: '#f8fafc',
                  letterSpacing: '-0.02em',
                  margin: 0,
                }}
              >
                Multi-Model &amp; Provider AI Integrations
              </h2>
              {/* Quota Badge */}
              <span
                style={{
                  fontSize: '0.72rem',
                  fontWeight: 800,
                  padding: '3px 10px',
                  borderRadius: '20px',
                  background: quotaData?.is_paid
                    ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.25), rgba(99, 102, 241, 0.25))'
                    : isFreeLimitReached
                    ? 'rgba(234, 179, 8, 0.2)'
                    : 'rgba(56, 189, 248, 0.15)',
                  color: quotaData?.is_paid
                    ? '#e9d5ff'
                    : isFreeLimitReached
                    ? '#facc15'
                    : '#38bdf8',
                  border: `1px solid ${
                    quotaData?.is_paid
                      ? 'rgba(168, 85, 247, 0.45)'
                      : isFreeLimitReached
                      ? 'rgba(234, 179, 8, 0.5)'
                      : 'rgba(56, 189, 248, 0.35)'
                  }`,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                }}
              >
                {quotaData?.is_paid ? (
                  <>
                    <RiVipCrownFill size={12} color="#c084fc" />
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
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '4px 0 0 0' }}>
              Scale autonomously across Google Gemini, OpenAI, Claude, DeepSeek, and Local LLM (Ollama). The default key is used to generate QA defect reports.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            onClick={() => {
              if (isFreeLimitReached && !showAddForm) {
                setShowUpgradeModal(true);
              } else {
                setShowAddForm(!showAddForm);
              }
            }}
            className="btn btn-primary"
            style={{
              padding: '8px 16px',
              fontSize: '0.84rem',
              borderRadius: '10px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: showAddForm
                ? 'rgba(255, 255, 255, 0.08)'
                : 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              fontWeight: 700,
            }}
          >
            {showAddForm ? (
              <>
                <TbChevronUp size={16} /> Hide Add Form
              </>
            ) : (
              <>
                <RiAddLine size={16} /> Add AI Key / Model
              </>
            )}
          </button>
        </div>
      </div>

      {/* Subscription Paywall Prompt if limit reached */}
      {(showUpgradeModal || (isFreeLimitReached && showAddForm)) && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.12), rgba(168, 85, 247, 0.14))',
            border: '1px solid rgba(234, 179, 8, 0.45)',
            borderRadius: '16px',
            padding: '18px 22px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            flexWrap: 'wrap',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', maxWidth: '650px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                background: 'rgba(234, 179, 8, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#facc15',
                flexShrink: 0,
              }}
            >
              <RiVipCrownFill size={22} />
            </div>
            <div>
              <div style={{ fontSize: '0.98rem', fontWeight: 800, color: '#facc15' }}>
                Free Tier Maximum Reached (3 of 3 Allowed Keys)
              </div>
              <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '3px', lineHeight: 1.4 }}>
                You have reached the maximum quota for the Free plan. To connect additional AI models, custom Ollama endpoints, and prevent rate limits, activate an official Pro or Enterprise subscription.
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <Link
              href="/pricing"
              className="btn btn-primary"
              style={{
                background: 'linear-gradient(135deg, #f59e0b 0%, #ec4899 50%, #8b5cf6 100%)',
                border: 'none',
                color: '#fff',
                fontWeight: 800,
                fontSize: '0.86rem',
                padding: '9px 18px',
                borderRadius: '10px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                textDecoration: 'none',
                boxShadow: '0 4px 18px rgba(245, 158, 11, 0.35)',
              }}
            >
              <TbSparkles size={16} /> Start Subscription Plan <TbArrowRight size={16} />
            </Link>
            <button
              type="button"
              onClick={() => setShowUpgradeModal(false)}
              className="btn btn-secondary"
              style={{ padding: '9px 14px', fontSize: '0.82rem', borderRadius: '10px' }}
            >
              Dismiss
            </button>
          </div>
        </motion.div>
      )}

      {/* Inline Add API Key Drawer Form */}
      <AnimatePresence>
        {showAddForm && (
          <motion.form
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            onSubmit={handleAddKey}
            style={{
              overflow: 'hidden',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '16px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f8fafc' }}>
                Connect New AI Provider &amp; Model
              </div>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                Stored encrypted · Zero shared telemetry
              </span>
            </div>

            {/* Provider Selector Tabs */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>
                Select AI Platform Provider:
              </label>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                  gap: '8px',
                }}
              >
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
                      style={{
                        padding: '10px 12px',
                        borderRadius: '10px',
                        background: isSelected
                          ? 'rgba(99, 102, 241, 0.2)'
                          : 'rgba(255, 255, 255, 0.03)',
                        border: `1px solid ${
                          isSelected ? '#6366f1' : 'rgba(255, 255, 255, 0.06)'
                        }`,
                        color: isSelected ? '#f8fafc' : '#94a3b8',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '0.82rem',
                        fontWeight: isSelected ? 700 : 500,
                        transition: 'all 0.2s ease',
                      }}
                    >
                      {renderProviderIcon(p.id, 16)}
                      <span style={{ whiteSpace: 'nowrap' }}>{p.name.split(' ')[0]}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Model & Label Selection Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '12px',
              }}
            >
              {/* Model Dropdown */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>
                  Model Target:
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  style={{
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontSize: '0.84rem',
                    outline: 'none',
                  }}
                >
                  {(currentProviderMeta?.models || [selectedModel]).map((m: string) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>

              {/* Friendly Label Name */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>
                  Key Label / Description (Optional):
                </label>
                <input
                  type="text"
                  placeholder={`e.g. My ${selectedProvider.toUpperCase()} Work Key`}
                  value={keyNameInput}
                  onChange={(e) => setKeyNameInput(e.target.value)}
                  style={{
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontSize: '0.84rem',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            {/* Secret API Key Input */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>
                {selectedProvider === 'local_llm'
                  ? 'Authorization Token (Optional for Ollama):'
                  : `API Secret Key for ${currentProviderMeta?.name || selectedProvider}:`}
              </label>
              <div style={{ position: 'relative' }}>
                <input
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
                  style={{
                    width: '100%',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '8px',
                    padding: '8px 40px 8px 12px',
                    color: '#f8fafc',
                    fontSize: '0.84rem',
                    outline: 'none',
                    fontFamily: 'monospace',
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
                    color: '#64748b',
                    cursor: 'pointer',
                  }}
                >
                  {showKeySecret ? <RiEyeOffLine size={16} /> : <RiEyeLine size={16} />}
                </button>
              </div>
            </div>

            {/* Custom Endpoint Input (if Ollama or custom proxy) */}
            {(selectedProvider === 'local_llm' || currentProviderMeta?.requires_endpoint) && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>
                  Custom Endpoint URL (Ollama or OpenAI-compatible gateway):
                </label>
                <input
                  type="url"
                  placeholder="http://localhost:11434/v1"
                  value={endpointInput}
                  onChange={(e) => setEndpointInput(e.target.value)}
                  style={{
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontSize: '0.84rem',
                    outline: 'none',
                    fontFamily: 'monospace',
                  }}
                />
              </div>
            )}

            {/* Set Default Checkbox */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="checkbox"
                id="dashboard-is-default-key"
                checked={isDefaultInput}
                onChange={(e) => setIsDefaultInput(e.target.checked)}
                style={{ cursor: 'pointer', accentColor: '#6366f1' }}
              />
              <label
                htmlFor="dashboard-is-default-key"
                style={{ fontSize: '0.82rem', color: '#e2e8f0', cursor: 'pointer' }}
              >
                Set this model as the active default engine for automated QA crawls
              </label>
            </div>

            {/* Feedback message */}
            {feedback && (
              <div
                style={{
                  fontSize: '0.82rem',
                  color: feedback.type === 'error' ? '#ef4444' : '#10b981',
                  background:
                    feedback.type === 'error'
                      ? 'rgba(239, 68, 68, 0.1)'
                      : 'rgba(16, 185, 129, 0.1)',
                  border: `1px solid ${
                    feedback.type === 'error'
                      ? 'rgba(239, 68, 68, 0.25)'
                      : 'rgba(16, 185, 129, 0.25)'
                  }`,
                  borderRadius: '8px',
                  padding: '8px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                {feedback.type === 'error' ? <TbAlertCircle size={16} /> : <TbCheck size={16} />}
                <span>{feedback.msg}</span>
              </div>
            )}

            {/* Submit button */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="btn btn-secondary"
                style={{ padding: '8px 16px', fontSize: '0.82rem', borderRadius: '8px' }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || (isFreeLimitReached && !quotaData?.is_paid)}
                className="btn btn-primary"
                style={{
                  padding: '8px 20px',
                  fontSize: '0.84rem',
                  borderRadius: '8px',
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  border: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontWeight: 700,
                  opacity: isFreeLimitReached && !quotaData?.is_paid ? 0.6 : 1,
                  cursor: isFreeLimitReached && !quotaData?.is_paid ? 'not-allowed' : 'pointer',
                }}
              >
                {isSubmitting ? (
                  <>
                    <TbLoader2 className="pulse" size={16} /> Storing Key...
                  </>
                ) : (
                  <>
                    <TbCheck size={16} /> Save &amp; Connect Key
                  </>
                )}
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      {/* List of Connected API Keys */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
            Active AI Keys ({apiKeys.length} {apiKeys.length === 1 ? 'Connected' : 'Connected'})
          </span>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Click star icon to switch default QA engine
          </span>
        </div>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', padding: '16px', fontSize: '0.84rem' }}>
            <TbLoader2 size={16} className="pulse" /> Loading connected API keys...
          </div>
        ) : apiKeys.length === 0 ? (
          <div
            style={{
              padding: '24px',
              borderRadius: '12px',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px dashed rgba(255, 255, 255, 0.1)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              textAlign: 'center',
            }}
          >
            <TbKey size={32} color="#64748b" />
            <div style={{ color: '#f8fafc', fontWeight: 600, fontSize: '0.9rem' }}>
              No AI Model Keys Connected Yet
            </div>
            <div style={{ color: '#94a3b8', fontSize: '0.8rem', maxWidth: '380px' }}>
              Connect your Google Gemini, OpenAI, Claude, or DeepSeek API key to enable autonomous QA defect analysis and report generation.
            </div>
            <button
              type="button"
              onClick={() => setShowAddForm(true)}
              className="btn btn-primary"
              style={{
                marginTop: '6px',
                padding: '6px 14px',
                fontSize: '0.8rem',
                borderRadius: '8px',
              }}
            >
              + Connect First API Key
            </button>
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '12px',
            }}
          >
            {apiKeys.map((key) => {
              const isDefault = !!key.is_default;
              const isRevealed = !!revealedKeyIds[key.id];

              return (
                <div
                  key={key.id}
                  style={{
                    padding: '14px 16px',
                    borderRadius: '14px',
                    background: isDefault
                      ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(16, 185, 129, 0.08))'
                      : 'rgba(255, 255, 255, 0.025)',
                    border: `1px solid ${
                      isDefault ? 'rgba(99, 102, 241, 0.4)' : 'rgba(255, 255, 255, 0.07)'
                    }`,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                    position: 'relative',
                    transition: 'all 0.2s ease',
                    boxShadow: isDefault ? '0 4px 20px rgba(99, 102, 241, 0.15)' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '8px',
                          background: 'rgba(255, 255, 255, 0.05)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        {renderProviderIcon(key.provider_id, 18)}
                      </div>
                      <div>
                        <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#f8fafc' }}>
                          {key.key_name || `${(key.provider_id || '').toUpperCase()} Engine`}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                          <span
                            style={{
                              fontSize: '0.72rem',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: 'rgba(255, 255, 255, 0.06)',
                              color: '#94a3b8',
                              fontFamily: 'monospace',
                            }}
                          >
                            {key.model || 'default-model'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Default Status Badge / Action */}
                    {isDefault ? (
                      <span
                        style={{
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          padding: '3px 8px',
                          borderRadius: '6px',
                          background: 'rgba(16, 185, 129, 0.18)',
                          color: '#34d399',
                          border: '1px solid rgba(16, 185, 129, 0.35)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <RiStarFill size={11} color="#34d399" /> Default Engine
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleSetDefaultKey(key.id)}
                        disabled={settingDefaultId === key.id}
                        title="Set as Default QA Model"
                        style={{
                          background: 'rgba(255, 255, 255, 0.04)',
                          border: '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: '6px',
                          padding: '3px 8px',
                          fontSize: '0.72rem',
                          color: '#94a3b8',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        <RiStarLine size={12} /> Set Default
                      </button>
                    )}
                  </div>

                  {/* Masked Key Display & Actions */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '6px 10px',
                      borderRadius: '8px',
                      background: 'rgba(0, 0, 0, 0.25)',
                      fontSize: '0.78rem',
                      fontFamily: 'monospace',
                      color: '#cbd5e1',
                    }}
                  >
                    <span>
                      {isRevealed
                        ? key.masked_key || '••••••••••••'
                        : (key.masked_key || '••••••••••••').replace(/^(AIzaSy|sk-proj-|sk-ant-).*(.{4})$/, '$1...$2')}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <button
                        type="button"
                        onClick={() =>
                          setRevealedKeyIds((prev) => ({ ...prev, [key.id]: !prev[key.id] }))
                        }
                        title={isRevealed ? 'Mask key' : 'Show masked snippet'}
                        style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
                      >
                        {isRevealed ? <RiEyeOffLine size={14} /> : <RiEyeLine size={14} />}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteKey(key.id)}
                        disabled={deletingId === key.id}
                        title="Disconnect API Key"
                        style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer' }}
                      >
                        <TbTrash size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
