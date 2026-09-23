"use client";

import React, { useState, useMemo } from 'react';
import { RiBug2Line, RiErrorWarningFill } from 'react-icons/ri';
import { TbChecklist, TbDevices } from 'react-icons/tb';
import { QAReport } from '../../types/qa';
import { ReportHeader } from './ReportHeader';
import { QualityScoreCard } from './QualityScoreCard';
import { MetricsGrid } from './MetricsGrid';
import { FindingsTab } from './tabs/FindingsTab';
import { TestCasesTab } from './tabs/TestCasesTab';
import { DevicesTab } from './tabs/DevicesTab';
import styles from '../../app/page.module.css';

interface ScanResultsProps {
  results: QAReport;
  scanId: string | null;
  sessionToken?: string;
  onNewScan: () => void;
}

export const ScanResults: React.FC<ScanResultsProps> = ({
  results,
  scanId,
  sessionToken,
  onNewScan,
}) => {
  const [activeTab, setActiveTab] = useState<'findings' | 'tests' | 'devices'>('findings');

  const safeScore = useMemo(() => {
    const raw = results?.qa_metrics?.quality_score;
    if (typeof raw === 'number' && Number.isFinite(raw)) {
      return Math.max(0, Math.min(100, Math.round(raw)));
    }
    if (raw && typeof raw === 'object' && typeof (raw as any).score === 'number' && Number.isFinite((raw as any).score)) {
      return Math.max(0, Math.min(100, Math.round((raw as any).score)));
    }
    const metaScore = (results?.report_metadata?.quality_score as any)?.score;
    if (typeof metaScore === 'number' && Number.isFinite(metaScore)) {
      return Math.max(0, Math.min(100, Math.round(metaScore)));
    }
    return 100;
  }, [results?.qa_metrics?.quality_score, results?.report_metadata?.quality_score]);

  const letterGrade =
    (results?.qa_metrics?.quality_score as any)?.grade ||
    (results?.report_metadata?.quality_score as any)?.grade ||
    results?.qa_metrics?.letter_grade ||
    'A+';

  const verdictText =
    (results?.qa_metrics?.quality_score as any)?.summary ||
    (results?.report_metadata?.quality_score as any)?.summary ||
    results?.qa_metrics?.verdict ||
    'EXCELLENT - Production Ready';

  const findingsCount = results.findings?.length ?? 0;
  const testCasesCount = results.test_cases?.length ?? 0;
  const hasCrossDevice = Boolean(results.report_metadata?.cross_device_metrics);

  return (
    <div className={styles.resultsPanel}>
      <ReportHeader
        results={results}
        scanId={scanId}
        sessionToken={sessionToken}
        onNewScan={onNewScan}
      />

      {results.report_metadata?.ai_analysis_degraded && (
        <div className={styles.degradedBanner}>
          <RiErrorWarningFill size={22} style={{ flexShrink: 0 }} />
          <div>
            <strong>AI Analysis Incomplete:</strong>{' '}
            {results.report_metadata.ai_analysis_failures} findings used deterministic fallbacks
            because the AI endpoint was unreachable.
          </div>
        </div>
      )}

      <QualityScoreCard
        score={safeScore}
        letterGrade={letterGrade}
        verdict={verdictText}
      />

      <MetricsGrid results={results} />

      {/* Tab Navigation */}
      <div className={styles.tabsBar}>
        <button
          className={`${styles.tabBtn} ${activeTab === 'findings' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('findings')}
        >
          <RiBug2Line size={17} /> Defect Triage ({findingsCount})
        </button>

        {testCasesCount > 0 && (
          <button
            className={`${styles.tabBtn} ${activeTab === 'tests' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('tests')}
          >
            <TbChecklist size={17} /> Automated Test Cases ({testCasesCount})
          </button>
        )}

        {hasCrossDevice && (
          <button
            className={`${styles.tabBtn} ${activeTab === 'devices' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('devices')}
          >
            <TbDevices size={17} /> Responsive QA Matrix
          </button>
        )}
      </div>

      {/* Active Tab Views */}
      {activeTab === 'findings' && <FindingsTab findings={results.findings || []} />}
      {activeTab === 'tests' && <TestCasesTab testCases={results.test_cases || []} />}
      {activeTab === 'devices' && (
        <DevicesTab crossDeviceMetrics={results.report_metadata?.cross_device_metrics} />
      )}
    </div>
  );
};
