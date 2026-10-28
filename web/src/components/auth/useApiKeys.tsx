"use client";

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { RiCpuLine, RiGoogleFill, RiOpenaiFill } from 'react-icons/ri';
import { SiAnthropic } from 'react-icons/si';
import { TbBrain, TbServer2 } from 'react-icons/tb';
import { normalizeTrial, type TrialStatus } from '../dashboard/trial';

export type ApiKeyRecord = {
  id: string;
  provider_id: string;
  key_name?: string;
  model?: string;
  masked_key?: string;
  is_default?: boolean;
};

export type ProviderMeta = {
  id: string;
  name: string;
  default_model?: string;
  default_endpoint?: string;
  models?: string[];
  requires_endpoint?: boolean;
};

export type ApiKeyQuota = {
  count: number;
  max_allowed: number;
  plan_tier: string;
  is_paid: boolean;
  can_add_more: boolean;
  supported_providers: ProviderMeta[];
};

export type NewApiKeyInput = {
  provider_id: string;
  api_key: string;
  key_name?: string;
  model: string;
  endpoint?: string;
  is_default: boolean;
};

export type ApiKeyFeedback = { type: 'success' | 'error'; msg: string };

export const FREE_KEY_LIMIT = 3;

export const FALLBACK_PROVIDERS: ProviderMeta[] = [
  { id: 'gemini', name: 'Google Gemini', default_model: 'gemini-3.8-flash' },
  { id: 'openai', name: 'OpenAI' },
  { id: 'anthropic', name: 'Anthropic' },
  { id: 'deepseek', name: 'DeepSeek', requires_endpoint: true, default_endpoint: 'https://api.deepseek.com/v1' },
  { id: 'local_llm', name: 'Local LLM', requires_endpoint: true, default_endpoint: 'http://localhost:11434/v1' },
];

export const PROVIDER_LABELS: Record<string, string> = {
  gemini: 'Gemini',
  openai: 'OpenAI',
  anthropic: 'Claude',
  deepseek: 'DeepSeek',
  local_llm: 'Ollama / Local',
};

export const KEY_PLACEHOLDERS: Record<string, string> = {
  gemini: 'AIzaSy...',
  openai: 'sk-proj-...',
  anthropic: 'sk-ant-...',
  deepseek: 'sk-...',
  local_llm: 'Optional token for local cluster',
};

export const ProviderIcon: React.FC<{ id: string; size?: number }> = ({ id, size = 18 }) => {
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

const authHeaders = (token: string, json = false): HeadersInit =>
  json ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` } : { Authorization: `Bearer ${token}` };

/**
 * Single source of truth for the user's AI provider keys, quota and free-trial state.
 * Pass `auto: false` to defer the first load (e.g. until a dialog opens) and call `refresh()` yourself.
 */
export function useApiKeys(token?: string, options: { auto?: boolean } = {}) {
  const { auto = true } = options;
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [quota, setQuota] = useState<ApiKeyQuota | null>(null);
  const [trial, setTrial] = useState<TrialStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [feedback, setFeedbackState] = useState<ApiKeyFeedback | null>(null);
  const feedbackTimer = useRef<number | null>(null);

  const setFeedback = useCallback((next: ApiKeyFeedback | null, clearAfterMs?: number) => {
    if (feedbackTimer.current) window.clearTimeout(feedbackTimer.current);
    feedbackTimer.current = null;
    setFeedbackState(next);
    if (next && clearAfterMs) {
      feedbackTimer.current = window.setTimeout(() => setFeedbackState(null), clearAfterMs);
    }
  }, []);

  useEffect(() => () => {
    if (feedbackTimer.current) window.clearTimeout(feedbackTimer.current);
  }, []);

  const fetchTrial = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch('/api/v1/user/trial', { headers: authHeaders(token) });
      if (res.ok) setTrial(normalizeTrial(await res.json()));
    } catch {
      // Older backends have no trial endpoint; the UI simply hides the trial card.
    }
  }, [token]);

  const refresh = useCallback(async (): Promise<ApiKeyRecord[] | null> => {
    if (!token) return null;
    setLoading(true);
    try {
      const res = await fetch('/api/v1/user/api-keys', { headers: authHeaders(token) });
      if (!res.ok) return null;
      const data = await res.json();
      const nextKeys: ApiKeyRecord[] = data.keys || [];
      setKeys(nextKeys);
      setQuota({
        count: data.count,
        max_allowed: data.max_allowed,
        plan_tier: data.plan_tier,
        is_paid: data.is_paid,
        can_add_more: data.can_add_more,
        supported_providers: data.supported_providers || [],
      });
      if (data.trial && typeof data.trial === 'object') {
        setTrial(normalizeTrial(data.trial));
      } else {
        void fetchTrial();
      }
      return nextKeys;
    } catch (e) {
      console.error('Failed to load user API keys:', e);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token, fetchTrial]);

  useEffect(() => {
    if (auto) void refresh();
  }, [auto, refresh]);

  const atFreeLimit = !!quota && !quota.is_paid && keys.length >= FREE_KEY_LIMIT;
  const providers = quota?.supported_providers?.length ? quota.supported_providers : FALLBACK_PROVIDERS;

  const addKey = useCallback(
    async (input: NewApiKeyInput): Promise<{ ok: boolean; limitReached: boolean }> => {
      if (!token) return { ok: false, limitReached: false };
      if (!input.api_key.trim() && input.provider_id !== 'local_llm') {
        setFeedback({ type: 'error', msg: 'Please provide a valid API key token.' });
        return { ok: false, limitReached: false };
      }
      if (atFreeLimit) {
        setFeedback({
          type: 'error',
          msg: `Free tier limit reached (${FREE_KEY_LIMIT}/${FREE_KEY_LIMIT} keys). Upgrade to Pro to connect more models.`,
        });
        return { ok: false, limitReached: true };
      }
      setFeedback(null);
      try {
        const res = await fetch('/api/v1/user/api-keys', {
          method: 'POST',
          headers: authHeaders(token, true),
          body: JSON.stringify({
            provider_id: input.provider_id,
            api_key: input.api_key.trim(),
            key_name: input.key_name?.trim() || undefined,
            model: input.model,
            endpoint: input.endpoint?.trim() || undefined,
            is_default: input.is_default,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          setFeedback({ type: 'error', msg: data.detail || 'Failed to save API key' });
          return { ok: false, limitReached: res.status === 403 };
        }
        await refresh();
        setFeedback({ type: 'success', msg: data.message || 'API key connected successfully!' }, 4000);
        return { ok: true, limitReached: false };
      } catch (err) {
        setFeedback({ type: 'error', msg: err instanceof Error ? err.message : 'Error saving API key' });
        return { ok: false, limitReached: false };
      }
    },
    [token, atFreeLimit, refresh, setFeedback],
  );

  const setDefault = useCallback(
    async (keyId: string): Promise<boolean> => {
      if (!token) return false;
      setBusyId(keyId);
      try {
        const res = await fetch(`/api/v1/user/api-keys/${keyId}/default`, { method: 'PUT', headers: authHeaders(token) });
        if (!res.ok) {
          setFeedback({ type: 'error', msg: `Failed to update default key (HTTP ${res.status})` });
          return false;
        }
        await refresh();
        setFeedback({ type: 'success', msg: 'Default AI model updated for upcoming scans.' }, 3000);
        return true;
      } catch {
        setFeedback({ type: 'error', msg: 'Failed to update default key' });
        return false;
      } finally {
        setBusyId(null);
      }
    },
    [token, refresh, setFeedback],
  );

  const deleteKey = useCallback(
    async (keyId: string): Promise<boolean> => {
      if (!token) return false;
      setBusyId(keyId);
      try {
        const res = await fetch(`/api/v1/user/api-keys/${keyId}`, { method: 'DELETE', headers: authHeaders(token) });
        if (!res.ok) {
          setFeedback({ type: 'error', msg: `Failed to remove API key (HTTP ${res.status})` });
          return false;
        }
        await refresh();
        setFeedback({ type: 'success', msg: 'API key removed.' }, 3000);
        return true;
      } catch {
        setFeedback({ type: 'error', msg: 'Failed to remove API key' });
        return false;
      } finally {
        setBusyId(null);
      }
    },
    [token, refresh, setFeedback],
  );

  return {
    keys,
    quota,
    trial,
    providers,
    loading,
    busyId,
    feedback,
    setFeedback,
    atFreeLimit,
    refresh,
    addKey,
    setDefault,
    deleteKey,
  };
}
