"use client";

import React, { useMemo } from 'react';
import { RiBug2Line } from 'react-icons/ri';
import { TbDeviceDesktop, TbClock, TbTestPipe } from 'react-icons/tb';
import { QAReport } from '../../types/qa';
import { StatTile3D } from '../three';

interface MetricsGridProps {
  results: QAReport;
  /** Stagger step of the first tile (each tile adds one 60ms step) */
  enterStep?: number;
}

const enterDelay = (step: number) => ({ ['--enter-delay' as string]: `${step * 60}ms` }) as React.CSSProperties;

export const MetricsGrid: React.FC<MetricsGridProps> = ({ results, enterStep = 1 }) => {
  const totalTestCases =
    results.qa_metrics?.test_cases?.total ?? results.test_cases?.length ?? 0;
  const passedTestCases = results.qa_metrics?.test_cases?.passed ?? 0;
  const failedTestCases = results.qa_metrics?.test_cases?.failed ?? 0;

  const totalFindings =
    results.findings?.length ?? results.qa_metrics?.findings?.total ?? 0;
  const confirmedBugs =
    results.qa_metrics?.findings?.by_classification?.confirmed_bug ??
    (results.summary as any)?.confirmed_bugs ??
    results.qa_metrics?.findings?.confirmed_bugs ??
    0;

  const pagesCrawled =
    results.report_metadata?.pages_crawled ??
    results.qa_metrics?.crawl?.pages_crawled ??
    1;

  const durationSec = results.qa_metrics?.duration_seconds;
  const formattedDuration = results.qa_metrics?.duration?.formatted_duration;
  const durationText = useMemo(() => {
    if (formattedDuration) return formattedDuration;
    if (typeof durationSec === 'number' && durationSec > 0) {
      const mins = Math.floor(durationSec / 60);
      const secs = Math.round(durationSec % 60);
      return `${mins}m ${secs}s`;
    }
    // Unknown duration (older reports): never show a made-up number.
    return '—';
  }, [durationSec, formattedDuration]);

  return (
    <>
      <div className="span-3 enter-3d" style={enterDelay(enterStep)}>
        <StatTile3D
          label="Total Test Cases"
          value={totalTestCases}
          accent="primary"
          icon={<TbTestPipe size={20} />}
          hint={`${passedTestCases} Passed · ${failedTestCases} Failed`}
        />
      </div>
      <div className="span-3 enter-3d" style={enterDelay(enterStep + 1)}>
        <StatTile3D
          label="Total Findings"
          value={totalFindings}
          accent={confirmedBugs > 0 ? 'danger' : totalFindings > 0 ? 'warning' : 'success'}
          icon={<RiBug2Line size={20} />}
          hint={`${confirmedBugs} Confirmed ${confirmedBugs === 1 ? 'Bug' : 'Bugs'}`}
        />
      </div>
      <div className="span-3 enter-3d" style={enterDelay(enterStep + 2)}>
        <StatTile3D
          label="Pages & Devices"
          value={pagesCrawled}
          accent="info"
          icon={<TbDeviceDesktop size={20} />}
          hint="Desktop · iPhone 13 · iPad"
        />
      </div>
      <div className="span-3 enter-3d" style={enterDelay(enterStep + 3)}>
        <StatTile3D
          label="Execution Duration"
          value={durationText}
          accent="neutral"
          icon={<TbClock size={20} />}
          hint="Parallel worker pipeline"
        />
      </div>
    </>
  );
};
