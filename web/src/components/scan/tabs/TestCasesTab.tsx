"use client";

import React from 'react';
import { TestCase } from '../../../types/qa';
import styles from '../../../app/page.module.css';

interface TestCasesTabProps {
  testCases: TestCase[];
}

export const TestCasesTab: React.FC<TestCasesTabProps> = ({ testCases }) => {
  if (!testCases || testCases.length === 0) {
    return (
      <div className={styles.noFindings}>
        No automated test cases were recorded for this scan.
      </div>
    );
  }

  return (
    <div className={styles.findingsList}>
      {testCases.map((tc, idx) => {
        const status = tc.status || 'passed';
        const isPassed = status === 'passed';
        const isFailed = status === 'failed';
        const isErrored = status === 'errored';

        const borderColor = isPassed
          ? '#10b981'
          : isFailed
          ? '#ef4444'
          : isErrored
          ? '#f43f5e'
          : '#f59e0b';
        const badgeBg = isPassed
          ? 'rgba(16, 185, 129, 0.2)'
          : isFailed
          ? 'rgba(239, 68, 68, 0.2)'
          : 'rgba(245, 158, 11, 0.2)';
        const badgeColor = isPassed ? '#34d399' : isFailed ? '#f87171' : '#fbbf24';

        return (
          <div
            key={tc.id || idx}
            className={styles.findingItem}
            style={{
              borderLeftColor: borderColor,
            }}
          >
            <div className={styles.findingHeader}>
              <span className={styles.findingId}>{tc.id}</span>
              <span
                className={styles.severityBadge}
                style={{
                  background: badgeBg,
                  color: badgeColor,
                }}
              >
                {status.toUpperCase()}
              </span>
            </div>

            <h3 style={{ fontSize: '1.12rem', color: '#f8fafc', margin: '4px 0 8px' }}>
              {tc.title}
            </h3>

            <div className={styles.tagsRow}>
              <span className={styles.chip}>{tc.category || 'General Assertion'}</span>
              {tc.priority && <span className={styles.chip}>Priority: {tc.priority}</span>}
              {tc.duration_ms !== undefined && (
                <span className={styles.chip}>{tc.duration_ms}ms</span>
              )}
              {tc.source_page && <span className={styles.chip}>{tc.source_page}</span>}
            </div>

            <div style={{ fontSize: '0.9rem', color: '#cbd5e1', marginTop: '8px' }}>
              <div>
                <strong style={{ color: '#94a3b8' }}>Expected:</strong>{' '}
                {tc.expected_result || 'N/A'}
              </div>
              <div style={{ marginTop: '4px' }}>
                <strong style={{ color: '#94a3b8' }}>Actual:</strong>{' '}
                {tc.actual_result || 'Assertion passed successfully.'}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
