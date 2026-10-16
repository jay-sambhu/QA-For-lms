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
import { SegmentedTabs3D, Surface3D, cx } from '../three';
import s from './scan3d.module.css';

interface ScanResultsProps {
  results: QAReport;
  scanId: string | null;
  sessionToken?: string;
  onNewScan: () => void;
}

type ResultsTab = 'findings' | 'tests' | 'devices';

const enterDelay = (step: number) => ({ ['--enter-delay' as string]: `${step * 60}ms` }) as React.CSSProperties;

export const ScanResults: React.FC<ScanResultsProps> = ({
  results,
  scanId,
  sessionToken,
  onNewScan,
}) => {
  const [activeTab, setActiveTab] = useState<ResultsTab>('findings');

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

  const tabs = useMemo(() => {
    const list: { id: ResultsTab; label: string; icon: React.ReactNode; badge?: number }[] = [
      { id: 'findings', label: 'Defect Triage', icon: <RiBug2Line size={16} />, badge: findingsCount },
    ];
    if (testCasesCount > 0) {
      list.push({ id: 'tests', label: 'Automated Test Cases', icon: <TbChecklist size={16} />, badge: testCasesCount });
    }
    if (hasCrossDevice) {
      list.push({ id: 'devices', label: 'Responsive QA Matrix', icon: <TbDevices size={16} /> });
    }
    return list;
  }, [findingsCount, testCasesCount, hasCrossDevice]);

  return (
    <div className={s.stack}>
      <ReportHeader
        results={results}
        scanId={scanId}
        sessionToken={sessionToken}
        onNewScan={onNewScan}
        className="enter-3d"
        style={enterDelay(0)}
      />

      {results.report_metadata?.ai_analysis_degraded && (
        <Surface3D as="section" accent="warning" pad="sm" className="enter-3d" style={enterDelay(1)} role="status">
          <div className={s.degraded}>
            <span className="icon-well icon-well--sm" aria-hidden="true">
              <RiErrorWarningFill size={18} />
            </span>
            <div>
              <strong>AI Analysis Incomplete:</strong>{' '}
              {results.report_metadata.ai_analysis_failures} finding(s) kept the deterministic triage
              because the AI model did not return a valid analysis (overloaded or out of quota).
              Re-run the scan later to get the AI verdict.
            </div>
          </div>
        </Surface3D>
      )}

      <div className="bento">
        <QualityScoreCard
          score={safeScore}
          letterGrade={letterGrade}
          verdict={verdictText}
          className="span-6 row-2 enter-3d"
          style={enterDelay(1)}
        />
        <MetricsGrid results={results} enterStep={2} />
      </div>

      <div className="enter-3d" style={enterDelay(3)}>
        <SegmentedTabs3D
          ariaLabel="Report sections"
          idPrefix="report"
          tabs={tabs}
          active={activeTab}
          onChange={setActiveTab}
        />
      </div>

      <div
        key={activeTab}
        role="tabpanel"
        id={`report-panel-${activeTab}`}
        aria-labelledby={`report-tab-${activeTab}`}
        className={cx('enter-3d', s.stackTight)}
      >
        {activeTab === 'findings' && <FindingsTab findings={results.findings || []} />}
        {activeTab === 'tests' && <TestCasesTab testCases={results.test_cases || []} />}
        {activeTab === 'devices' && (
          <DevicesTab crossDeviceMetrics={results.report_metadata?.cross_device_metrics} />
        )}
      </div>
    </div>
  );
};
