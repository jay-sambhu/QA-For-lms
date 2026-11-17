"use client";

import React from 'react';
import { TbChecklist } from 'react-icons/tb';
import { TestCase } from '../../../types/qa';
import { EmptyState3D, Surface3D, cx, type Tone } from '../../three';
import s from '../scan3d.module.css';

interface TestCasesTabProps {
  testCases: TestCase[];
}

const ENTER_LIMIT = 8;
const enterDelay = (step: number) =>
  step < ENTER_LIMIT ? ({ ['--enter-delay' as string]: `${Math.min(step, 5) * 60}ms` } as React.CSSProperties) : undefined;

const statusTone = (status: string): Tone => {
  if (status === 'passed') return 'success';
  if (status === 'failed' || status === 'errored') return 'danger';
  return 'warning';
};

const issueLevelTone = (level?: string): Tone => {
  const l = (level || '').toLowerCase();
  if (l === 'critical') return 'danger';
  if (l === 'high') return 'warning';
  if (l === 'medium') return 'info';
  return 'neutral';
};

const resolveIssueLevel = (tc: TestCase): string => {
  if (tc.issue_level) return tc.issue_level.toLowerCase();
  const priority = (tc.priority || '').toUpperCase();
  if (priority === 'P0' || priority === 'CRITICAL') return 'critical';
  if (priority === 'P1' || priority === 'HIGH') return 'high';
  if (priority === 'P2' || priority === 'MEDIUM') return 'medium';
  if (priority === 'P3' || priority === 'LOW') return 'low';
  return 'medium';
};

export const TestCasesTab: React.FC<TestCasesTabProps> = ({ testCases }) => {
  if (!testCases || testCases.length === 0) {
    return (
      <Surface3D>
        <EmptyState3D
          icon={<TbChecklist size={16} />}
          title="No automated test cases"
          description="No automated test cases were recorded for this scan."
        />
      </Surface3D>
    );
  }

  return (
    <div className={s.cardList}>
      {testCases.map((tc, idx) => {
        const status = tc.status || 'passed';
        const tone = statusTone(status);
        const issueLevel = resolveIssueLevel(tc);
        const levelTone = issueLevelTone(issueLevel);

        return (
          <Surface3D
            key={tc.id || idx}
            as="article"
            accent={tone}
            className={cx(s.card, idx < ENTER_LIMIT && 'enter-3d')}
            style={enterDelay(idx)}
          >
            <div className={s.cardHead}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span className={cx(s.cardId, s.mono)}>{tc.id}</span>
                <span className={cx('chip chip--sm chip--dot', `chip--${levelTone}`)}>
                  {issueLevel.toUpperCase()}
                </span>
              </div>
              <span className={cx('chip chip--sm chip--dot', `chip--${tone}`)}>{status.toUpperCase()}</span>
            </div>

            <h3 className={s.cardTitle}>{tc.title}</h3>

            {(tc.description || tc.objective) && (
              <p className={s.cardDesc}>{tc.description || tc.objective}</p>
            )}

            <div className={s.tagRow}>
              <span className="chip chip--sm chip--neutral">{tc.category || 'General Assertion'}</span>
              {tc.priority && <span className="chip chip--sm chip--neutral">Priority: {tc.priority}</span>}
              {tc.duration_ms !== undefined && (
                <span className={cx('chip chip--sm chip--neutral', s.mono)}>{tc.duration_ms}ms</span>
              )}
              {tc.source_page && (
                <span className={cx('chip chip--sm chip--neutral', s.chipTruncate)} title={tc.source_page}>
                  {tc.source_page}
                </span>
              )}
            </div>

            <div className={cx('surface-inset', s.resultPair)}>
              <div>
                <strong>Expected Result</strong>
                <span>{tc.expected_result || 'Expected behavior to succeed without errors.'}</span>
              </div>
              <div>
                <strong>Exact Result</strong>
                <span>{tc.exact_result || tc.actual_result || 'Assertion passed successfully.'}</span>
              </div>
            </div>
          </Surface3D>
        );
      })}
    </div>
  );
};
