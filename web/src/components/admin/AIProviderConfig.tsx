"use client";

import React, { useState, useEffect, useCallback } from 'react';
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
  TbLink,
} from 'react-icons/tb';
import { useAuth } from '../../context/AuthContext';
import { Surface3D } from '../three';
import a from './admin3d.module.css';

export const AIProviderConfig: React.FC = () => {
  const { session } = useAuth();
  const [providersData, setProvidersData] = useState<any>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>('gemini');
  const [selectedModel, setSelectedModel] = useState<string>('gemini-3.8-flash');
  const [apiKeyInput, setApiKeyInput] = useState<string>('');
  const [customEndpoint, setCustomEndpoint] = useState<string>('');
  const [temperature, setTemperature] = useState<number>(0.2);
  const [showKey, setShowKey] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [testing, setTesting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  const fetchProviders = useCallback(async () => {
    if (!session?.access_token) return;
    try {
      const headers: Record<string, string> = {};
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
      const res = await fetch('/api/v1/admin/ai-providers', { headers });
      if (res.ok) {
        const data = await res.json();
        setProvidersData(data);
        setSelectedProvider(data.active_provider || 'gemini');
        setSelectedModel(data.active_model || 'gemini-3.8-flash');
        setTemperature(data.temperature ?? 0.2);

        const currentP = data.providers?.find((p: any) => p.id === data.active_provider);
        if (currentP?.current_endpoint) {
          setCustomEndpoint(currentP.current_endpoint);
        }
      }
    } catch (e) {
      console.error('Failed to load AI providers:', e);
    }
  }, [session?.access_token]);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

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
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
      const res = await fetch('/api/v1/admin/ai-providers', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          provider_id: selectedProvider,
          model: selectedModel,
          api_key: apiKeyInput || undefined,
          endpoint: customEndpoint || undefined,
          temperature: temperature,
        }),
      });
      const data = await res.json().catch(() => ({}));
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
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
      const res = await fetch('/api/v1/admin/ai-providers/test', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          provider_id: selectedProvider,
          api_key: apiKeyInput || undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
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

  const noticeClass =
    feedback?.type === 'success' ? a.noticeSuccess : feedback?.type === 'warning' ? a.noticeWarning : a.noticeDanger;

  return (
    <Surface3D as="section" aria-labelledby="ai-provider-title">
      <div className={a.panelHead}>
        <div className={a.panelTitleBlock}>
          <span className="icon-well" aria-hidden="true">
            <RiCpuLine size={20} />
          </span>
          <div>
            <span className="section-eyebrow">AI engine</span>
            <div className={a.panelTitleRow}>
              <h2 id="ai-provider-title" className={a.panelTitle}>Multi-AI Provider & Engine Setup</h2>
            </div>
            <p className={a.panelSub}>Choose the reasoning provider, model and credentials used by every scan.</p>
          </div>
        </div>
        {providersData?.active_provider && (
          <span className="chip chip--success chip--live">
            Active: {providersData.active_provider.toUpperCase()} ({providersData.active_model})
          </span>
        )}
      </div>

      <div className={a.panelBody}>
        {feedback && (
          <div className={`${a.notice} ${noticeClass}`} role="status">
            {feedback.type === 'success' ? <RiCheckDoubleFill size={18} /> : <RiErrorWarningFill size={18} />}
            <span>{feedback.text}</span>
          </div>
        )}

        {/* AI Provider Switcher Grid */}
        <div className={a.providerGrid} role="group" aria-label="AI providers">
          {providersData?.providers?.map((p: any) => {
            const isSelected = selectedProvider === p.id;
            const isActive = providersData?.active_provider === p.id;

            return (
              <button
                key={p.id}
                type="button"
                onClick={() => handleProviderSelect(p.id)}
                aria-pressed={isSelected}
                className={a.providerCard}
              >
                <div className={a.providerTop}>
                  <span className="icon-well icon-well--sm" aria-hidden="true">
                    {getProviderIcon(p.id)}
                  </span>
                  {isActive && <span className="chip chip--sm chip--success chip--solid">In use</span>}
                </div>
                <div className={a.providerName}>{p.name}</div>
                <div className={`${a.providerState} ${p.is_configured ? a.providerStateOn : ''}`}>
                  <span className={a.providerDot} aria-hidden="true" />
                  {p.is_configured ? `Configured (${p.masked_key || 'Active'})` : 'Key required'}
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Provider Form */}
        {currentProviderMeta && (
          <form onSubmit={handleSaveConfig} className={`surface-inset ${a.inset}`}>
            <p className={a.providerDesc}>{currentProviderMeta.description}</p>

            <div className={a.fieldGrid}>
              {/* Model Selector */}
              <div className={a.fieldGroup}>
                <label htmlFor="ai-model-select" className={a.fieldLabel}>
                  <RiCpuLine size={14} /> Reasoning Model Selection
                </label>
                <select
                  id="ai-model-select"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className={a.field}
                >
                  {currentProviderMeta.models?.map((m: string) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              {/* API Key Input */}
              <div className={a.fieldGroup}>
                <label htmlFor="ai-api-key" className={a.fieldLabel}>
                  <RiKey2Line size={14} /> Secret API Key ({currentProviderMeta.env_key_name})
                </label>
                <div className={a.passwordWrap}>
                  <input
                    id="ai-api-key"
                    type={showKey ? 'text' : 'password'}
                    placeholder={currentProviderMeta.is_configured ? `Configured (${currentProviderMeta.masked_key}) — enter to update` : 'sk-... or AI API Key'}
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                    autoComplete="off"
                    className={a.field}
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    className={`${a.iconBtn} ${a.passwordToggle}`}
                    aria-label={showKey ? 'Hide API key' : 'Show API key'}
                  >
                    {showKey ? <RiEyeOffLine size={16} /> : <RiEyeLine size={16} />}
                  </button>
                </div>
              </div>
            </div>

            {/* Custom Endpoint Input (for DeepSeek / Local LLM) */}
            {currentProviderMeta.requires_endpoint && (
              <div className={a.fieldGroup}>
                <label htmlFor="ai-endpoint" className={a.fieldLabel}>
                  <TbLink size={14} /> Custom Base URL / Inference Endpoint
                </label>
                <input
                  id="ai-endpoint"
                  type="url"
                  placeholder={currentProviderMeta.default_endpoint || 'http://localhost:11434/v1'}
                  value={customEndpoint}
                  onChange={(e) => setCustomEndpoint(e.target.value)}
                  className={`${a.field} ${a.mono}`}
                />
              </div>
            )}

            {/* Temperature Slider */}
            <div className={a.rangeRow}>
              <label htmlFor="ai-temperature" className={a.rangeLabel}>
                <TbAdjustments size={16} /> Inference Temperature: <strong>{temperature}</strong>
              </label>
              <input
                id="ai-temperature"
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className={a.range}
              />
            </div>

            {/* Actions */}
            <div className={a.formActions}>
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={testing}
                className="btn btn-secondary"
              >
                {testing ? <TbLoader2 size={16} className="pulse" /> : <TbPlugConnected size={16} />}
                <span>Test Connection</span>
              </button>

              <button
                type="submit"
                disabled={saving}
                className="btn btn-primary"
              >
                {saving ? <TbLoader2 size={16} className="pulse" /> : <RiSave3Line size={16} />}
                <span>Save & Activate Provider</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </Surface3D>
  );
};
