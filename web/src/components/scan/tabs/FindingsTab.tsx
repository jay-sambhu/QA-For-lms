"use client";

import React, { useState, useMemo } from 'react';
import { RiSearchLine, RiBug2Line } from 'react-icons/ri';
import { QAFinding } from '../../../types/qa';
import { EmptyState3D, Surface3D, cx, type Tone } from '../../three';
import s from '../scan3d.module.css';

interface FindingsTabProps {
  findings: QAFinding[];
}

const ENTER_LIMIT = 8;
const enterDelay = (step: number) =>
  step < ENTER_LIMIT ? ({ ['--enter-delay' as string]: `${Math.min(step, 5) * 60}ms` } as React.CSSProperties) : undefined;

const severityTone = (severity?: string): Tone => {
  switch (severity?.toLowerCase()) {
    case 'critical':
    case 'high':
      return 'danger';
    case 'medium':
      return 'warning';
    case 'low':
      return 'info';
    default:
      return 'neutral';
  }
};

const severityChip = (severity?: string) => {
  const tone = severityTone(severity);
  const solid = severity?.toLowerCase() === 'critical';
  return cx('chip chip--sm', `chip--${tone}`, solid ? 'chip--solid' : 'chip--dot');
};

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
    <div className={s.stackTight}>
      <Surface3D pad="sm" aria-label="Finding filters">
        <div className={s.filterBar}>
          <div className={s.search}>
            <RiSearchLine size={17} className={s.searchIcon} aria-hidden="true" />
            <input
              type="text"
              placeholder="Search findings by ID, title, or keyword..."
              aria-label="Search findings"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={s.field}
            />
          </div>

          <div className={s.selects}>
            <select
              className={cx(s.field, s.select)}
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              title="Filter by Severity"
              aria-label="Filter by severity"
            >
              <option value="ALL">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>

            <select
              className={cx(s.field, s.select)}
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}
              title="Filter by Priority"
              aria-label="Filter by priority"
            >
              <option value="ALL">All Priorities</option>
              <option value="P0">P0 (Blocker)</option>
              <option value="P1">P1 (Critical)</option>
              <option value="P2">P2 (Major)</option>
              <option value="P3">P3 (Minor)</option>
            </select>

            <select
              className={cx(s.field, s.select)}
              value={filterClass}
              onChange={(e) => setFilterClass(e.target.value)}
              title="Filter by Classification"
              aria-label="Filter by classification"
            >
              <option value="ALL">All Classifications</option>
              <option value="confirmed_bug">Confirmed Bug</option>
              <option value="high_confidence_candidate">Candidate</option>
              <option value="needs_manual_review">Needs Review</option>
              <option value="informational">Info</option>
            </select>
          </div>
        </div>
      </Surface3D>

      <div className={s.cardList}>
        {filteredFindings.map((finding, idx) => (
          <Surface3D
            key={finding.id || idx}
            as="article"
            accent={severityTone(finding.severity)}
            className={cx(s.card, idx < ENTER_LIMIT && 'enter-3d')}
            style={enterDelay(idx)}
          >
            <div className={s.cardHead}>
              <span className={cx(s.cardId, s.mono)}>{finding.id}</span>
              <div className={s.cardChips}>
                {finding.priority && <span className="chip chip--sm chip--neutral">{finding.priority}</span>}
                <span className={severityChip(finding.severity)}>{finding.severity?.toUpperCase()}</span>
              </div>
            </div>

            <h3 className={s.cardTitle}>{finding.title}</h3>
            <p className={s.cardDesc}>
              {finding.description || finding.manual_verification || 'No description provided.'}
            </p>

            <div className={s.tagRow}>
              {finding.user_impact && (
                <span className="chip chip--sm chip--neutral">Impact: {finding.user_impact.toUpperCase()}</span>
              )}
              {finding.root_cause?.category && (
                <span className="chip chip--sm chip--neutral">
                  Cause: {finding.root_cause.category.replace('_', ' ')}
                </span>
              )}
              {finding.page && (
                <span className={cx('chip chip--sm chip--neutral', s.chipTruncate)} title={finding.page}>
                  {finding.page}
                </span>
              )}
            </div>

            <details className={cx('surface-inset', s.evidence)}>
              <summary className={s.evidenceSummary}>View Evidence & Remediation Steps</summary>
              <div className={s.evidenceBody}>
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
                    <ol>
                      {finding.reproduction.steps.map((step: string, sIdx: number) => (
                        <li key={sIdx}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            </details>
          </Surface3D>
        ))}

        {filteredFindings.length === 0 && (
          <Surface3D>
            <EmptyState3D
              compact
              accent="success"
              icon={<RiBug2Line size={16} />}
              title="No findings match the selected filters"
              description="No bugs or anomalies match the current search and filter combination."
            />
          </Surface3D>
        )}
      </div>
    </div>
  );
};
