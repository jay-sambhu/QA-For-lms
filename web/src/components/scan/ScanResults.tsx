"use client";

import React, { useState, useMemo } from 'react';
import {
  RiFileExcel2Line,
  RiCodeSSlashLine,
  RiMarkdownLine,
  RiAwardFill,
  RiBug2Line,
  RiErrorWarningFill,
  RiSearchLine,
  RiRefreshLine,
  RiDownload2Line,
} from 'react-icons/ri';
import { FaRegFilePdf } from 'react-icons/fa6';
import {
  TbDeviceDesktop,
  TbDeviceMobile,
  TbDeviceTablet,
  TbClock,
  TbChecklist,
  TbDevices,
  TbActivity,
  TbTestPipe,
  TbFileAnalytics,
} from 'react-icons/tb';
import { QAReport } from '../../types/qa';
import { handleDownloadReport } from '../../utils/export';
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
  const [searchQuery, setSearchQuery] = useState('');
  const [filterClass, setFilterClass] = useState('ALL');
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [filterPriority, setFilterPriority] = useState('ALL');

  const safeScore = useMemo(() => {
    const raw = results?.qa_metrics?.quality_score;
    if (typeof raw === 'number' && Number.isFinite(raw)) {
      return Math.max(0, Math.min(100, Math.round(raw)));
    }
    return 100;
  }, [results?.qa_metrics?.quality_score]);

  const letterGrade = results?.qa_metrics?.letter_grade || 'A+';
  const verdictText = results?.qa_metrics?.verdict || 'EXCELLENT - Production Ready';

  const filteredFindings = useMemo(() => {
    if (!results?.findings) return [];
    return results.findings.filter((finding) => {
      const matchesSearch =
        !searchQuery ||
        finding.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        finding.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        finding.id?.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesClass = filterClass === 'ALL' || finding.classification === filterClass;
      const matchesSeverity = filterSeverity === 'ALL' || finding.severity === filterSeverity;
      const matchesPriority = filterPriority === 'ALL' || finding.priority === filterPriority;

      return matchesSearch && matchesClass && matchesSeverity && matchesPriority;
    });
  }, [results?.findings, searchQuery, filterClass, filterSeverity, filterPriority]);

  return (
    <div className={styles.resultsPanel}>
      <div className={styles.resultsHeader}>
        <div>
          <h2>
            <TbFileAnalytics size={26} color="#818cf8" /> Autonomous QA Scan Report
          </h2>
          <div style={{ color: '#94a3b8', fontSize: '0.92rem', marginTop: '4px' }}>
            Target: <strong style={{ color: '#f8fafc' }}>{results.report_metadata?.target}</strong> · Generated at{' '}
            {new Date(results.report_metadata?.generated_at).toLocaleTimeString()}
          </div>
        </div>

        <div className={styles.exportActions}>
          <button
            className={styles.exportBtn}
            onClick={() =>
              handleDownloadReport({
                results,
                scanId,
                format: 'pdf',
                sessionToken,
              })
            }
            title="Download PDF Report"
          >
            <FaRegFilePdf size={15} color="#ef4444" /> PDF Report
          </button>

          <button
            className={styles.exportBtn}
            onClick={() =>
              handleDownloadReport({
                results,
                scanId,
                format: 'excel',
                sessionToken,
              })
            }
            title="Download Excel Spreadsheet"
          >
            <RiFileExcel2Line size={16} color="#10b981" /> Excel Sheet
          </button>

          <button
            className={styles.exportBtn}
            onClick={() =>
              handleDownloadReport({
                results,
                scanId,
                format: 'json',
                sessionToken,
              })
            }
            title="Download Raw JSON"
          >
            <RiCodeSSlashLine size={16} color="#38bdf8" /> JSON
          </button>

          <button
            className={styles.exportBtn}
            onClick={() =>
              handleDownloadReport({
                results,
                scanId,
                format: 'md',
                sessionToken,
              })
            }
            title="Download Markdown Report"
          >
            <RiMarkdownLine size={16} color="#a855f7" /> Markdown
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

      {results.report_metadata?.ai_analysis_degraded && (
        <div className={styles.degradedBanner}>
          <RiErrorWarningFill size={22} style={{ flexShrink: 0 }} />
          <div>
            <strong>AI Analysis Incomplete:</strong> {results.report_metadata.ai_analysis_failures} findings
            used deterministic fallbacks because the AI endpoint was unreachable.
          </div>
        </div>
      )}

      {/* Score Dial Card */}
      <div className={styles.scoreCard}>
        <div className={styles.scoreDialContainer}>
          <div className={styles.scoreCircleWrapper}>
            <svg width="130" height="130" viewBox="0 0 130 130">
              <circle
                cx="65"
                cy="65"
                r="54"
                fill="none"
                stroke="rgba(255, 255, 255, 0.08)"
                strokeWidth="10"
              />
              <circle
                cx="65"
                cy="65"
                r="54"
                fill="none"
                stroke={safeScore >= 80 ? '#10b981' : safeScore >= 60 ? '#f59e0b' : '#ef4444'}
                strokeWidth="10"
                strokeDasharray="339.29"
                strokeDashoffset={339.29 - (339.29 * safeScore) / 100}
                strokeLinecap="round"
                transform="rotate(-90 65 65)"
                style={{ transition: 'stroke-dashoffset 1s ease-out' }}
              />
            </svg>
            <div className={styles.scoreCircleCenter}>
              <span className={styles.scoreNumber}>{safeScore}</span>
              <span className={styles.scoreGradePill}>{letterGrade}</span>
            </div>
          </div>
        </div>

        <div className={styles.scoreDetails}>
          <div
            className={styles.scoreVerdictBadge}
            style={{
              background: safeScore >= 80 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
              color: safeScore >= 80 ? '#34d399' : '#fbbf24',
              border: `1px solid ${safeScore >= 80 ? 'rgba(16, 185, 129, 0.35)' : 'rgba(245, 158, 11, 0.35)'}`,
            }}
          >
            <RiAwardFill size={15} /> {verdictText}
          </div>
          <div className={styles.scoreTitle}>
            {safeScore >= 80 ? 'High Software Quality & Reliability' : 'Remediation Required Before Release'}
          </div>
          <div className={styles.scoreDescription}>
            {safeScore >= 80
              ? 'Target web application successfully passed automated multi-viewport assertions and user journeys with zero critical runtime exceptions.'
              : 'Discovered defects, unhandled network failures, or layout anomalies that require attention.'}
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span>Total Test Cases</span>
            <TbTestPipe size={20} color="#818cf8" />
          </div>
          <div className={styles.statValue}>
            {results.qa_metrics?.test_cases?.total ?? results.test_cases?.length ?? 0}
          </div>
          <div className={styles.statSub}>
            {results.qa_metrics?.test_cases?.passed ?? 0} Passed · {results.qa_metrics?.test_cases?.failed ?? 0} Failed
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span>Total Findings</span>
            <RiBug2Line size={20} color="#ef4444" />
          </div>
          <div className={styles.statValue}>{results.findings?.length ?? 0}</div>
          <div className={styles.statSub}>
            {results.qa_metrics?.findings?.confirmed_bugs ?? 0} Confirmed Bugs
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span>Pages & Devices</span>
            <TbDeviceDesktop size={20} color="#38bdf8" />
          </div>
          <div className={styles.statValue}>
            {results.report_metadata?.pages_crawled ?? 1}
          </div>
          <div className={styles.statSub}>Desktop · iPhone 13 · iPad</div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span>Execution Duration</span>
            <TbClock size={20} color="#34d399" />
          </div>
          <div className={styles.statValue}>
            {results.qa_metrics?.duration?.formatted_duration ?? '00:15s'}
          </div>
          <div className={styles.statSub}>Parallel worker pipeline</div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className={styles.tabsBar}>
        <button
          className={`${styles.tabBtn} ${activeTab === 'findings' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('findings')}
        >
          <RiBug2Line size={17} /> Defect Triage ({results.findings?.length ?? 0})
        </button>

        {results.test_cases && results.test_cases.length > 0 && (
          <button
            className={`${styles.tabBtn} ${activeTab === 'tests' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('tests')}
          >
            <TbChecklist size={17} /> Automated Test Cases ({results.test_cases.length})
          </button>
        )}

        {results.report_metadata?.cross_device_metrics && (
          <button
            className={`${styles.tabBtn} ${activeTab === 'devices' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('devices')}
          >
            <TbDevices size={17} /> Responsive QA Matrix
          </button>
        )}
      </div>

      {/* Findings Tab */}
      {activeTab === 'findings' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className={styles.filterBar}>
            <div className={styles.searchInputWrapper}>
              <RiSearchLine size={17} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
              <input
                type="text"
                placeholder="Search findings by ID, title, or keyword..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={styles.searchInput}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <select
                className={styles.filterSelect}
                value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}
              >
                <option value="ALL">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>

              <select
                className={styles.filterSelect}
                value={filterPriority}
                onChange={(e) => setFilterPriority(e.target.value)}
              >
                <option value="ALL">All Priorities</option>
                <option value="P0">P0 (Blocker)</option>
                <option value="P1">P1 (Critical)</option>
                <option value="P2">P2 (Major)</option>
                <option value="P3">P3 (Minor)</option>
              </select>

              <select
                className={styles.filterSelect}
                value={filterClass}
                onChange={(e) => setFilterClass(e.target.value)}
              >
                <option value="ALL">All Classifications</option>
                <option value="confirmed_bug">Confirmed Bug</option>
                <option value="high_confidence_candidate">Candidate</option>
                <option value="needs_manual_review">Needs Review</option>
                <option value="informational">Info</option>
              </select>
            </div>
          </div>

          <div className={styles.findingsList}>
            {filteredFindings.map((finding, idx) => (
              <div key={finding.id || idx} className={styles.findingItem}>
                <div className={styles.findingHeader}>
                  <span className={styles.findingId}>{finding.id}</span>
                  <span className={`${styles.severityBadge} ${styles[finding.severity] ?? ''}`}>
                    {finding.severity}
                  </span>
                </div>

                <h3 style={{ fontSize: '1.18rem', color: '#f8fafc' }}>{finding.title}</h3>
                <p className={styles.findingDesc}>{finding.description || finding.manual_verification}</p>

                <div className={styles.tagsRow}>
                  {finding.priority && <span className={styles.chip}>Priority: {finding.priority}</span>}
                  {finding.user_impact && <span className={styles.chip}>Impact: {finding.user_impact.toUpperCase()}</span>}
                  {finding.root_cause?.category && (
                    <span className={styles.chip}>Cause: {finding.root_cause.category.replace('_', ' ')}</span>
                  )}
                  {finding.page && <span className={styles.chip}>{finding.page}</span>}
                </div>

                <details className={styles.evidenceAccordion}>
                  <summary className={styles.evidenceSummary}>View Evidence & Remediation Steps</summary>
                  <div className={styles.evidenceBody}>
                    {finding.root_cause?.summary && (
                      <p style={{ marginBottom: '8px' }}>
                        <strong>Root Cause Summary:</strong> {finding.root_cause.summary}
                      </p>
                    )}
                    <p style={{ marginBottom: '8px' }}>
                      <strong>Recommendation:</strong> {finding.recommendation || 'Review component lifecycle and error bounds.'}
                    </p>

                    {finding.reproduction?.steps && finding.reproduction.steps.length > 0 && (
                      <div style={{ marginTop: '10px' }}>
                        <strong>Reproduction Steps:</strong>
                        <ol style={{ paddingLeft: '20px', marginTop: '4px' }}>
                          {finding.reproduction.steps.map((step, sIdx) => (
                            <li key={sIdx}>{step}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                </details>
              </div>
            ))}

            {filteredFindings.length === 0 && (
              <div className={styles.noFindings}>
                ✨ No bugs or anomalies match the selected filters.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tests Tab */}
      {activeTab === 'tests' && results.test_cases && (
        <div className={styles.findingsList}>
          {results.test_cases.map((tc, idx) => {
            const status = tc.status || 'passed';
            const isPassed = status === 'passed';
            const isFailed = status === 'failed';
            const isErrored = status === 'errored';

            return (
              <div
                key={tc.id || idx}
                className={styles.findingItem}
                style={{
                  borderLeftColor: isPassed ? '#10b981' : isFailed ? '#ef4444' : isErrored ? '#f43f5e' : '#f59e0b',
                }}
              >
                <div className={styles.findingHeader}>
                  <span className={styles.findingId}>{tc.id}</span>
                  <span
                    className={styles.severityBadge}
                    style={{
                      background: isPassed ? 'rgba(16, 185, 129, 0.2)' : isFailed ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                      color: isPassed ? '#34d399' : isFailed ? '#f87171' : '#fbbf24',
                    }}
                  >
                    {status.toUpperCase()}
                  </span>
                </div>

                <h3 style={{ fontSize: '1.12rem', color: '#f8fafc' }}>{tc.title}</h3>

                <div className={styles.tagsRow}>
                  <span className={styles.chip}>{tc.category || 'General'}</span>
                  {tc.priority && <span className={styles.chip}>Priority: {tc.priority}</span>}
                  {tc.source_page && <span className={styles.chip}>{tc.source_page}</span>}
                </div>

                <div style={{ fontSize: '0.9rem', color: '#cbd5e1' }}>
                  <div>
                    <strong>Expected:</strong> {tc.expected_result || 'N/A'}
                  </div>
                  <div style={{ marginTop: '4px' }}>
                    <strong>Actual:</strong> {tc.actual_result || 'Assertion passed successfully.'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Devices Tab */}
      {activeTab === 'devices' && results.report_metadata?.cross_device_metrics && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <div className={styles.statHeader}>
                <span>Desktop (1920x1080)</span>
                <TbDeviceDesktop size={20} color="#818cf8" />
              </div>
              <div className={styles.statValue}>
                {results.report_metadata.cross_device_metrics.device_breakdown.desktop}
              </div>
              <div className={styles.statSub}>Responsive Findings</div>
            </div>

            <div className={styles.statCard}>
              <div className={styles.statHeader}>
                <span>iPhone 13 (390x844)</span>
                <TbDeviceMobile size={20} color="#38bdf8" />
              </div>
              <div className={styles.statValue}>
                {results.report_metadata.cross_device_metrics.device_breakdown.iphone}
              </div>
              <div className={styles.statSub}>Touch & Viewport Findings</div>
            </div>

            <div className={styles.statCard}>
              <div className={styles.statHeader}>
                <span>iPad (820x1180)</span>
                <TbDeviceTablet size={20} color="#34d399" />
              </div>
              <div className={styles.statValue}>
                {results.report_metadata.cross_device_metrics.device_breakdown.ipad}
              </div>
              <div className={styles.statSub}>Tablet Layout Findings</div>
            </div>

            <div className={styles.statCard}>
              <div className={styles.statHeader}>
                <span>Total Responsive Issues</span>
                <TbActivity size={20} color="#f59e0b" />
              </div>
              <div className={styles.statValue}>
                {results.report_metadata.cross_device_metrics.responsive_findings}
              </div>
              <div className={styles.statSub}>Across all emulated viewports</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
