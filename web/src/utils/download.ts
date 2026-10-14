// Lightweight helpers for downloading server-generated scan reports.
// Kept separate from utils/export.ts so pages that only need direct downloads
// don't pull in the client-side PDF/XLSX generators.

export type ServerReportFormat = 'pdf' | 'xlsx' | 'json' | 'md';

const MIME_TYPES: Record<ServerReportFormat, string> = {
  pdf: 'application/pdf',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  json: 'application/json',
  md: 'text/markdown; charset=utf-8',
};

/** Parses filename from a Content-Disposition header (RFC 5987 filename* first). */
export const extractFilenameFromDisposition = (disposition: string | null, fallbackFilename: string): string => {
  if (!disposition) return fallbackFilename;

  const utf8Match = disposition.match(/filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/i);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1].trim());
    } catch {
      return utf8Match[1].trim();
    }
  }

  const standardMatch = disposition.match(/filename\s*=\s*"?([^";]+)"?/i);
  if (standardMatch && standardMatch[1]) {
    return standardMatch[1].trim();
  }

  return fallbackFilename;
};

/** Triggers a browser download for a Blob and releases the object URL afterwards. */
export const saveBlob = (blob: Blob, filename: string) => {
  const downloadUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = downloadUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);
};

/**
 * Downloads a pre-generated report via GET /api/v1/scans/{id}/download/{format}.
 * Throws an Error (with the backend's `detail` when available) if the request fails,
 * so callers never save an error payload as a report file.
 */
export const downloadScanReport = async (
  scanId: string,
  format: ServerReportFormat,
  accessToken: string
): Promise<void> => {
  const res = await fetch(`/api/v1/scans/${encodeURIComponent(scanId)}/download/${format}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = typeof body?.detail === 'string' ? body.detail : '';
    } catch {
      // Non-JSON error body (e.g. proxy error page)
    }
    throw new Error(detail || `Download failed (HTTP ${res.status})`);
  }
  const filename = extractFilenameFromDisposition(
    res.headers.get('content-disposition'),
    `qa-report-${scanId}.${format}`
  );
  const blob = await res.blob();
  saveBlob(new Blob([blob], { type: MIME_TYPES[format] }), filename);
};
