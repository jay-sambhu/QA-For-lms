export type TrialStatus = {
  enabled: boolean;
  total: number;
  used: number;
  remaining: number;
  has_own_key: boolean;
  daily_available: boolean;
};

export type TrialState = {
  /** No own key, trial enabled and scans still left */
  trialActive: boolean;
  /** No own key, trial enabled but every free scan is spent */
  trialExhausted: boolean;
  /** No own key and no trial available: the user cannot scan at all */
  keyMissing: boolean;
};

export const normalizeTrial = (data: unknown): TrialStatus | null => {
  if (!data || typeof data !== 'object') return null;
  const raw = data as Record<string, unknown>;
  if (typeof raw.remaining !== 'number') return null;
  return {
    enabled: !!raw.enabled,
    total: Number(raw.total) || 0,
    used: Number(raw.used) || 0,
    remaining: Math.max(0, Number(raw.remaining) || 0),
    has_own_key: !!raw.has_own_key,
    daily_available: raw.daily_available !== false,
  };
};

/** Derives the three mutually exclusive trial flags once; null hasApiKey means "still checking". */
export const deriveTrialState = (
  trial: TrialStatus | null | undefined,
  hasApiKey: boolean | null | undefined
): TrialState => {
  const noKey = hasApiKey === false;
  const enabled = !!trial?.enabled;
  return {
    trialActive: noKey && enabled && (trial?.remaining ?? 0) > 0,
    trialExhausted: noKey && enabled && (trial?.remaining ?? 0) <= 0,
    keyMissing: noKey && !enabled,
  };
};
