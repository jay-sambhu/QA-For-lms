"use client";

import React, { useState, useMemo } from 'react';
import { RiSearchLine } from 'react-icons/ri';
import { QAFinding } from '../../../types/qa';
import styles from '../../../app/page.module.css';

interface FindingsTabProps {
  findings: QAFinding[];
}

export const FindingsTab: React.FC<FindingsTabProps> = ({ findings }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterClass, setFilterClass] = useState('ALL');
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [filterPriority, setFilterPriority] = useState('ALL');

  const filteredFindings = useMemo(() => {
    if (!findings) return [];
    return findings.filter((finding) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        finding.title?.toLowerCase().includes(q) ||
        finding.description?.toLowerCase().includes(q) ||
        finding.id?.toLowerCase().includes(q) ||
        finding.page?.toLowerCase().includes(q);

      const matchesClass = filterClass === 'ALL' || finding.classification === filterClass;
      const matchesSeverity = filterSeverity === 'ALL' || finding.severity === filterSeverity;
      const matchesPriority = filterPriority === 'ALL' || finding.priority === filterPriority;

      return matchesSearch && matchesClass && matchesSeverity && matchesPriority;
    });
  }, [findings, searchQuery, filterClass, filterSeverity, filterPriority]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className={styles.filterBar}>
        <div className={styles.searchInputWrapper}>
          <RiSearchLine
            size={17}
            style={{
              position: 'absolute',
              left: '14px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#64748b',
            }}
          />
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
            title="Filter by Severity"
          >
            <option value="ALL">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>

          <select
            className={styles.filterSelect}
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
            title="Filter by Priority"
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
            title="Filter by Classification"
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
              <span
                className={`${styles.severityBadge} ${
                  styles[finding.severity?.toLowerCase()] ?? ''
                }`}
              >
                {finding.severity?.toUpperCase()}
              </span>
            </div>

            <h3 style={{ fontSize: '1.18rem', color: '#f8fafc', margin: '4px 0 8px' }}>
              {finding.title}
            </h3>
            <p className={styles.findingDesc}>
              {finding.description || finding.manual_verification || 'No description provided.'}
            </p>

            <div className={styles.tagsRow}>
              {finding.priority && <span className={styles.chip}>Priority: {finding.priority}</span>}
              {finding.user_impact && (
                <span className={styles.chip}>Impact: {finding.user_impact.toUpperCase()}</span>
              )}
              {finding.root_cause?.category && (
                <span className={styles.chip}>
                  Cause: {finding.root_cause.category.replace('_', ' ')}
                </span>
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
                  <strong>Recommendation:</strong>{' '}
                  {finding.recommendation || 'Review component lifecycle and error bounds.'}
                </p>

                {finding.reproduction?.steps && finding.reproduction.steps.length > 0 && (
                  <div style={{ marginTop: '10px' }}>
                    <strong>Reproduction Steps:</strong>
                    <ol style={{ paddingLeft: '20px', marginTop: '4px' }}>
                      {finding.reproduction.steps.map((step: string, sIdx: number) => (
                        <li key={sIdx} style={{ marginBottom: '4px' }}>
                          {step}
                        </li>
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
  );
};
