/** The only statuses the backend emits for a scan (api/main.py, worker/tasks.py). */
export type ScanRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export const SCAN_RUN_STATUSES: readonly ScanRunStatus[] = ['pending', 'running', 'completed', 'failed', 'cancelled'];

export const isScanRunStatus = (value: unknown): value is ScanRunStatus =>
  typeof value === 'string' && (SCAN_RUN_STATUSES as readonly string[]).includes(value);

/** Queued or crawling: the row is still changing and the report is not ready. */
export const isActiveScan = (status: unknown): boolean => status === 'pending' || status === 'running';

const CHIP_BY_STATUS: Record<ScanRunStatus, string> = {
  pending: 'chip--info chip--live',
  running: 'chip--info chip--live',
  completed: 'chip--success chip--dot',
  failed: 'chip--danger chip--dot',
  cancelled: 'chip--neutral',
};

const LABEL_BY_STATUS: Record<ScanRunStatus, string> = {
  pending: 'Queued',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

/** Chip classes for a scan status; unknown values fall back to a neutral chip. */
export const scanStatusChip = (status: unknown, size?: 'sm'): string => {
  const tone = isScanRunStatus(status) ? CHIP_BY_STATUS[status] : 'chip--neutral';
  return size === 'sm' ? `chip chip--sm ${tone}` : `chip ${tone}`;
};

export const scanStatusLabel = (status: unknown): string =>
  isScanRunStatus(status) ? LABEL_BY_STATUS[status] : String(status || 'Unknown');
