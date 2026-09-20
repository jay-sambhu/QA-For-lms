"use client";

import React, { useState } from 'react';
import {
  RiFileExcel2Line,
  RiCodeSSlashLine,
  RiMarkdownLine,
  RiRefreshLine,
} from 'react-icons/ri';
import { FaRegFilePdf } from 'react-icons/fa6';
import { TbFileAnalytics, TbLoader2 } from 'react-icons/tb';
import { QAReport } from '../../types/qa';
import { handleDownloadReport } from '../../utils/export';
import styles from '../../app/page.module.css';

interface ReportHeaderProps {
  results: QAReport;
  scanId: string | null;
  sessionToken?: string;
  onNewScan: () => void;
}

export const ReportHeader: React.FC<ReportHeaderProps> = ({
  results,
  scanId,
  sessionToken,
  onNewScan,
}) => {
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  const onDownload = async (format: 'pdf' | 'excel' | 'json' | 'md') => {
    try {
      setDownloadingFormat(format);
      await handleDownloadReport({
        results,
        scanId,
        format,
        sessionToken,
      });
    } finally {
      setDownloadingFormat(null);
    }
  };

  const targetUrl = results.report_metadata?.target || 'Web Application';
  const generatedAt = results.report_metadata?.generated_at
    ? new Date(results.report_metadata.generated_at).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : 'Just now';

  return (
    <div className={styles.resultsHeader}>
      <div>
        <h2>
          <TbFileAnalytics size={26} color="#818cf8" /> Autonomous QA Scan Report
        </h2>
        <div style={{ color: '#94a3b8', fontSize: '0.92rem', marginTop: '4px' }}>
          Target: <strong style={{ color: '#f8fafc' }}>{targetUrl}</strong> · Generated at {generatedAt}
        </div>
      </div>

      <div className={styles.exportActions}>
        <button
          className={styles.exportBtn}
          onClick={() => onDownload('pdf')}
          disabled={downloadingFormat !== null}
          title="Download Executive PDF Report"
        >
          {downloadingFormat === 'pdf' ? (
            <TbLoader2 size={15} className="pulse" />
          ) : (
            <FaRegFilePdf size={15} color="#ef4444" />
          )}
          <span>PDF Report</span>
        </button>

        <button
          className={styles.exportBtn}
          onClick={() => onDownload('excel')}
          disabled={downloadingFormat !== null}
          title="Download Multi-Tab Excel Workbook"
        >
          {downloadingFormat === 'excel' ? (
            <TbLoader2 size={16} className="pulse" />
          ) : (
            <RiFileExcel2Line size={16} color="#10b981" />
          )}
          <span>Excel Sheet</span>
        </button>

        <button
          className={styles.exportBtn}
          onClick={() => onDownload('json')}
          disabled={downloadingFormat !== null}
          title="Download Machine-Readable JSON"
        >
          {downloadingFormat === 'json' ? (
            <TbLoader2 size={16} className="pulse" />
          ) : (
            <RiCodeSSlashLine size={16} color="#38bdf8" />
          )}
          <span>JSON</span>
        </button>

        <button
          className={styles.exportBtn}
          onClick={() => onDownload('md')}
          disabled={downloadingFormat !== null}
          title="Download Markdown Summary"
        >
          {downloadingFormat === 'md' ? (
            <TbLoader2 size={16} className="pulse" />
          ) : (
            <RiMarkdownLine size={16} color="#a855f7" />
          )}
          <span>Markdown</span>
        </button>

        <button
          className="btn btn-primary"
          onClick={onNewScan}
          style={{ padding: '9px 18px', fontSize: '0.88rem' }}
        >
          <RiRefreshLine size={16} /> New Scan
        </button>
      </div>
    </div>
  );
};
