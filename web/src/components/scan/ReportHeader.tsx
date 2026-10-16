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
import { Surface3D, cx } from '../three';
import s from './scan3d.module.css';

interface ReportHeaderProps {
  results: QAReport;
  scanId: string | null;
  sessionToken?: string;
  onNewScan: () => void;
  className?: string;
  style?: React.CSSProperties;
}

export const ReportHeader: React.FC<ReportHeaderProps> = ({
  results,
  scanId,
  sessionToken,
  onNewScan,
  className,
  style,
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
    } catch (e) {
      console.error('Report export failed:', e);
      alert('Could not export the report. Please try again.');
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
    <Surface3D as="section" pad="sm" accent className={className} style={style} aria-label="Report exports">
      <div className={s.toolbar}>
        <div className={s.toolbarCopy}>
          <span className="icon-well" aria-hidden="true">
            <TbFileAnalytics size={20} />
          </span>
          <div className={s.toolbarText}>
            <h2 className={s.toolbarTitle}>Autonomous QA Scan Report</h2>
            <span className={cx(s.toolbarMeta, s.truncate)} title={targetUrl}>
              Target: <strong>{targetUrl}</strong> · Generated at {generatedAt}
            </span>
          </div>
        </div>

        <div className={s.toolbarActions}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onDownload('pdf')}
            disabled={downloadingFormat !== null}
            title="Download Executive PDF Report"
          >
            {downloadingFormat === 'pdf' ? (
              <TbLoader2 size={15} className="pulse" />
            ) : (
              <FaRegFilePdf size={15} color="var(--tone-danger)" />
            )}
            <span>PDF Report</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onDownload('excel')}
            disabled={downloadingFormat !== null}
            title="Download Multi-Tab Excel Workbook"
          >
            {downloadingFormat === 'excel' ? (
              <TbLoader2 size={16} className="pulse" />
            ) : (
              <RiFileExcel2Line size={16} color="var(--tone-success)" />
            )}
            <span>Excel Sheet</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onDownload('json')}
            disabled={downloadingFormat !== null}
            title="Download Machine-Readable JSON"
          >
            {downloadingFormat === 'json' ? (
              <TbLoader2 size={16} className="pulse" />
            ) : (
              <RiCodeSSlashLine size={16} color="var(--tone-info)" />
            )}
            <span>JSON</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onDownload('md')}
            disabled={downloadingFormat !== null}
            title="Download Markdown Summary"
          >
            {downloadingFormat === 'md' ? (
              <TbLoader2 size={16} className="pulse" />
            ) : (
              <RiMarkdownLine size={16} color="var(--tone-violet)" />
            )}
            <span>Markdown</span>
          </button>

          <button type="button" className="btn btn-primary btn-sm" onClick={onNewScan}>
            <RiRefreshLine size={16} /> New Scan
          </button>
        </div>
      </div>
    </Surface3D>
  );
};
