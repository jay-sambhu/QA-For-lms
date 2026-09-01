"use client";

import React, { useState, useEffect } from 'react';
import {
  RiGoogleFill,
  RiOpenaiFill,
  RiCheckDoubleFill,
  RiErrorWarningFill,
  RiKey2Line,
  RiCpuLine,
  RiSave3Line,
  RiEyeLine,
  RiEyeOffLine,
} from 'react-icons/ri';
import {
  SiAnthropic,
} from 'react-icons/si';
import {
  TbBrain,
  TbServer2,
  TbPlugConnected,
  TbLoader2,
  TbAdjustments,
} from 'react-icons/tb';
import styles from '../../app/page.module.css';

export const AIProviderConfig: React.FC = () => {
  const [providersData, setProvidersData] = useState<any>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>('gemini');
  const [selectedModel, setSelectedModel] = useState<string>('gemini-2.5-flash');
  const [apiKeyInput, setApiKeyInput] = useState<string>('');
  const [customEndpoint, setCustomEndpoint] = useState<string>('');
  const [temperature, setTemperature] = useState<number>(0.2);
  const [showKey, setShowKey] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [testing, setTesting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  const fetchProviders = async () => {
    try {
      const res = await fetch('/api/v1/admin/ai-providers');
      if (res.ok) {
        const data = await res.json();
        setProvidersData(data);
        setSelectedProvider(data.active_provider || 'gemini');
        setSelectedModel(data.active_model || 'gemini-2.5-flash');
        setTemperature(data.temperature ?? 0.2);

        const currentP = data.providers?.find((p: any) => p.id === data.active_provider);
        if (currentP?.current_endpoint) {
          setCustomEndpoint(currentP.current_endpoint);
        }
      }
    } catch (e) {
      console.error('Failed to load AI providers:', e);
    }
  };

  useEffect(() => {
    fetchProviders();
  }, []);

  const handleProviderSelect = (pId: string) => {
    setSelectedProvider(pId);
    setApiKeyInput('');
    setFeedback(null);
    const pMeta = providersData?.providers?.find((p: any) => p.id === pId);
    if (pMeta) {
      setSelectedModel(pMeta.default_model);
      setCustomEndpoint(pMeta.current_endpoint || pMeta.default_endpoint || '');
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/v1/admin/ai-providers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: selectedProvider,
          model: selectedModel,
          api_key: apiKeyInput || undefined,
          endpoint: customEndpoint || undefined,
          temperature: temperature,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to save AI configuration');

      setFeedback({ type: 'success', text: `Active AI Engine updated to ${selectedProvider.toUpperCase()} (${selectedModel})` });
      await fetchProviders();
      setApiKeyInput('');
    } catch (err) {
      setFeedback({ type: 'error', text: err instanceof Error ? err.message : 'Save failed' });
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/v1/admin/ai-providers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: selectedProvider,
          api_key: apiKeyInput || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Test connection failed');

      if (data.status === 'warning') {
        setFeedback({ type: 'warning', text: data.message });
      } else {
        setFeedback({ type: 'success', text: data.message });
      }
    } catch (err) {
      setFeedback({ type: 'error', text: err instanceof Error ? err.message : 'Connection test failed' });
    } finally {
      setTesting(false);
    }
  };

  const currentProviderMeta = providersData?.providers?.find((p: any) => p.id === selectedProvider);

  const getProviderIcon = (id: string) => {
    switch (id) {
      case 'gemini': return <RiGoogleFill size={20} color="#4285f4" />;
      case 'openai': return <RiOpenaiFill size={20} color="#10a37f" />;
      case 'anthropic': return <SiAnthropic size={18} color="#d97706" />;
      case 'deepseek': return <TbBrain size={20} color="#3b82f6" />;
      case 'local_llm': return <TbServer2 size={20} color="#10b981" />;
      default: return <RiCpuLine size={20} />;
    }
  };

  return (
    <div className={styles.adminTableCard}>
      <div className={styles.adminTableCardTitle}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
          <RiCpuLine size={20} color="#818cf8" /> Multi-AI Provider & Engine Setup
        </span>
        <span style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 600 }}>
          ACTIVE: {providersData?.active_provider?.toUpperCase()} ({providersData?.active_model})
        </span>
      </div>

      <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {feedback && (
          <div className={`${styles.authBanner} ${feedback.type === 'success' ? styles.authBannerSuccess : styles.authBannerError}`}>
            {feedback.type === 'success' ? <RiCheckDoubleFill size={18} /> : <RiErrorWarningFill size={18} />}
            <span>{feedback.text}</span>
          </div>
        )}

        {/* AI Provider Switcher Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '12px' }}>
          {providersData?.providers?.map((p: any) => {
            const isSelected = selectedProvider === p.id;
            const isActive = providersData?.active_provider === p.id;

            return (
              <button
                key={p.id}
                type="button"
                onClick={() => handleProviderSelect(p.id)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  padding: '14px',
                  background: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${isSelected ? '#6366f1' : 'rgba(255, 255, 255, 0.08)'}`,
                  borderRadius: '14px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  {getProviderIcon(p.id)}
                  {isActive && (
                    <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 6px', background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', borderRadius: '4px' }}>
                      IN USE
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f8fafc' }}>{p.name}</div>
                <div style={{ fontSize: '0.75rem', color: p.is_configured ? '#34d399' : '#94a3b8' }}>
                  {p.is_configured ? `● Configured (${p.masked_key || 'Active'})` : '○ Key Required'}
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Provider Form */}
        {currentProviderMeta && (
          <form onSubmit={handleSaveConfig} style={{ display: 'flex', flexDirection: 'column', gap: '18px', background: 'rgba(0, 0, 0, 0.25)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
            <div style={{ fontSize: '0.88rem', color: '#94a3b8' }}>
              {currentProviderMeta.description}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
              {/* Model Selector */}
              <div className={styles.modalFormGroup}>
                <label className={styles.modalFormLabel}>
                  <RiCpuLine size={14} style={{ display: 'inline', marginRight: '4px' }} /> Reasoning Model Selection
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className={styles.modalInput}
                >
                  {currentProviderMeta.models?.map((m: string) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              {/* API Key Input */}
              <div className={styles.modalFormGroup}>
                <label className={styles.modalFormLabel}>
                  <RiKey2Line size={14} style={{ display: 'inline', marginRight: '4px' }} /> Secret API Key ({currentProviderMeta.env_key_name})
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showKey ? 'text' : 'password'}
                    placeholder={currentProviderMeta.is_configured ? `Configured (${currentProviderMeta.masked_key}) — enter to update` : 'sk-... or AI API Key'}
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                    className={styles.modalInput}
                    style={{ paddingRight: '40px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }}
                  >
                    {showKey ? <RiEyeOffLine size={16} /> : <RiEyeLine size={16} />}
                  </button>
                </div>
              </div>
            </div>

            {/* Custom Endpoint Input (for DeepSeek / Local LLM) */}
            {currentProviderMeta.requires_endpoint && (
              <div className={styles.modalFormGroup}>
                <label className={styles.modalFormLabel}>
                  Custom Base URL / Inference Endpoint
                </label>
                <input
                  type="url"
                  placeholder={currentProviderMeta.default_endpoint || 'http://localhost:11434/v1'}
                  value={customEndpoint}
                  onChange={(e) => setCustomEndpoint(e.target.value)}
                  className={styles.modalInput}
                />
              </div>
            )}

            {/* Temperature Slider */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: '#cbd5e1' }}>
                <TbAdjustments size={16} color="#818cf8" /> Inference Temperature: <strong style={{ color: '#ffffff' }}>{temperature}</strong>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                style={{ width: '180px', accentColor: '#6366f1' }}
              />
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '6px' }}>
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={testing}
                className="btn btn-secondary"
                style={{ padding: '9px 16px', fontSize: '0.85rem' }}
              >
                {testing ? <TbLoader2 size={16} className="pulse" /> : <TbPlugConnected size={16} />}
                <span>Test Connection</span>
              </button>

              <button
                type="submit"
                disabled={saving}
                className="btn btn-primary"
                style={{ padding: '9px 20px', fontSize: '0.85rem' }}
              >
                {saving ? <TbLoader2 size={16} className="pulse" /> : <RiSave3Line size={16} />}
                <span>Save & Activate Provider</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
