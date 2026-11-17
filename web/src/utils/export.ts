// jspdf / jspdf-autotable / xlsx are heavy (~750 KB) and only needed for the client-side
// fallback when the server has no pre-generated report, so they are loaded on demand.
import type { jsPDF } from 'jspdf';
import { ApiError, downloadScanReport, saveBlob } from './download';
import type { DeviceBreakdown, Finding, QAReport, RegressionSummary, TestCase } from '../types/qa';

declare module 'jspdf' {
  interface jsPDF {
    lastAutoTable?: { finalY: number };
  }
}

export interface CanonicalExportData {
  target: string;
  scanId: string;
  generatedAt: string;
  status: string;
  pagesCrawled: number;
  pagesDiscovered: number;
  durationSeconds: number;
  /** null fields mean the report carried no score; exporters print "N/A" rather than a perfect grade */
  qualityScore: {
    score: number | null;
    grade: string | null;
    summary: string | null;
  };
  testCasesSummary: {
    total: number;
    executed: number;
    passed: number;
    failed: number;
    skipped: number;
    blocked: number;
    errored: number;
    pass_rate: number;
    fail_rate: number;
    skip_rate: number;
    block_rate: number;
    errored_rate: number;
    duration_ms: number;
  };
  findingsSummary: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
    P0: number;
    P1: number;
    P2: number;
    P3: number;
    P4: number;
    confirmed_bugs: number;
    high_confidence_candidates: number;
    needs_manual_review: number;
    informational: number;
    duplicates: number;
    regression: RegressionSummary;
  };
  findings: Finding[];
  testCases: TestCase[];
  crossDevice: {
    /** false when the report has no cross-device telemetry at all */
    measured: boolean;
    devices_tested: number;
    responsive_findings: number;
    device_breakdown: DeviceBreakdown;
  };
  isDegraded: boolean;
  degradedCount: number;
}

const EMPTY_BREAKDOWN: DeviceBreakdown = { desktop: 0, iphone: 0, ipad: 0 };

const rate = (count: number, total: number) => (total > 0 ? Number(((count / total) * 100).toFixed(2)) : 0.0);

const finiteOrNull = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value) ? value : null;

const scoreText = (qs: CanonicalExportData['qualityScore']) =>
  qs.score === null ? 'N/A' : `${qs.score} / 100`;

const gradeText = (qs: CanonicalExportData['qualityScore']) => qs.grade ?? 'N/A';

const summaryText = (qs: CanonicalExportData['qualityScore']) => qs.summary ?? 'N/A';

const safeFileStem = (scanId: string, target: string) =>
  (scanId && scanId !== 'N/A' ? scanId : target || 'scan').replace(/[^a-z0-9-]/gi, '_').toLowerCase();

/**
 * Normalizes scan results from any API / report format into a strict canonical export model.
 */
export const extractCanonicalExportData = (results: QAReport | null | undefined, scanId: string | null = ''): CanonicalExportData => {
  if (!results) {
    return {
      target: 'Unknown',
      scanId: scanId || 'N/A',
      generatedAt: new Date().toISOString(),
      status: 'completed',
      pagesCrawled: 0,
      pagesDiscovered: 0,
      durationSeconds: 0,
      qualityScore: { score: null, grade: null, summary: null },
      testCasesSummary: {
        total: 0,
        executed: 0,
        passed: 0,
        failed: 0,
        skipped: 0,
        blocked: 0,
        errored: 0,
        pass_rate: 0.0,
        fail_rate: 0.0,
        skip_rate: 0.0,
        block_rate: 0.0,
        errored_rate: 0.0,
        duration_ms: 0,
      },
      findingsSummary: {
        total: 0,
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
        info: 0,
        P0: 0,
        P1: 0,
        P2: 0,
        P3: 0,
        P4: 0,
        confirmed_bugs: 0,
        high_confidence_candidates: 0,
        needs_manual_review: 0,
        informational: 0,
        duplicates: 0,
        regression: { new: 0, fixed: 0, unchanged: 0, worsened: 0, improved: 0 },
      },
      findings: [],
      testCases: [],
      crossDevice: {
        measured: false,
        devices_tested: 0,
        responsive_findings: 0,
        device_breakdown: { ...EMPTY_BREAKDOWN },
      },
      isDegraded: false,
      degradedCount: 0,
    };
  }

  const qa = results.qa_metrics ?? {};
  const meta = results.report_metadata;
  const summary = results.summary;
  const severity = results.severity ?? {};
  const triage = results.triage_metrics;
  const tcm = results.test_case_metrics ?? qa.test_cases;
  const crawl = qa.crawl;
  const crossDevice = meta?.cross_device_metrics ?? crawl;
  const findingsMetrics = qa.findings ?? {};

  const rawScore = qa.quality_score ?? meta?.quality_score;
  const scoreObject = rawScore && typeof rawScore === 'object' ? rawScore : undefined;
  const score = finiteOrNull(typeof rawScore === 'number' ? rawScore : scoreObject?.score);
  const grade = scoreObject?.grade || qa.letter_grade || null;
  const scoreSummary = scoreObject?.summary || qa.verdict || null;

  const target = qa.target || meta?.target || 'Unknown';
  const generatedAt = qa.generated_at || meta?.generated_at || new Date().toISOString();

  const pagesCrawled = crawl?.pages_crawled ?? meta?.pages_crawled ?? 0;
  const pagesDiscovered = crawl?.pages_discovered ?? crawl?.pages_attempted ?? pagesCrawled;
  const durationSeconds = qa.duration_seconds ?? qa.duration?.duration_seconds ?? 0;

  // Test Case Metrics
  const tcTotal: number = Number(tcm?.total ?? results.test_cases?.length ?? 0);
  const tcPassed: number = Number(tcm?.passed ?? 0);
  const tcFailed: number = Number(tcm?.failed ?? 0);
  const tcSkipped: number = Number(tcm?.skipped ?? (tcm as any)?.manual_review ?? 0);
  const tcBlocked: number = Number(tcm?.blocked ?? 0);
  const tcErrored: number = Number(tcm?.errored ?? 0);
  const tcExecuted: number = Number(tcm?.executed ?? tcPassed + tcFailed + tcErrored);

  // Findings Metrics
  const bySev: Record<string, number | undefined> = findingsMetrics.by_severity ?? severity;
  const byPri: Record<string, number | undefined> = findingsMetrics.by_priority ?? triage?.priority ?? {};
  const byClass = findingsMetrics.by_classification ?? {};
  const reg: Partial<RegressionSummary> =
    findingsMetrics.by_regression ?? triage?.regression_summary ?? summary?.regression_summary ?? {};

  const totalFindings = findingsMetrics.total ?? summary?.total_candidates ?? results.findings?.length ?? 0;

  const isDegraded = Boolean(meta?.ai_analysis_degraded || meta?.ai_analysis_failures);

  return {
    target,
    scanId: scanId || 'N/A',
    generatedAt,
    status: 'completed',
    pagesCrawled,
    pagesDiscovered,
    durationSeconds,
    qualityScore: { score, grade, summary: scoreSummary },
    testCasesSummary: {
      total: tcTotal,
      executed: tcExecuted,
      passed: tcPassed,
      failed: tcFailed,
      skipped: tcSkipped,
      blocked: tcBlocked,
      errored: tcErrored,
      pass_rate: tcm?.pass_rate ?? rate(tcPassed, tcTotal),
      fail_rate: tcm?.fail_rate ?? rate(tcFailed, tcTotal),
      skip_rate: tcm?.skip_rate ?? rate(tcSkipped, tcTotal),
      block_rate: tcm?.block_rate ?? rate(tcBlocked, tcTotal),
      errored_rate: tcm?.errored_rate ?? rate(tcErrored, tcTotal),
      duration_ms: tcm?.duration_ms ?? 0,
    },
    findingsSummary: {
      total: totalFindings,
      critical: bySev.critical ?? 0,
      high: bySev.high ?? 0,
      medium: bySev.medium ?? 0,
      low: bySev.low ?? 0,
      info: bySev.info ?? 0,
      P0: byPri.P0 ?? 0,
      P1: byPri.P1 ?? 0,
      P2: byPri.P2 ?? 0,
      P3: byPri.P3 ?? 0,
      P4: byPri.P4 ?? 0,
      confirmed_bugs: byClass.confirmed_bug ?? triage?.confirmed_bug ?? summary?.confirmed_bugs ?? 0,
      high_confidence_candidates:
        byClass.high_confidence_candidate ?? triage?.high_confidence_candidate ?? summary?.potential_issues ?? 0,
      needs_manual_review: byClass.needs_manual_review ?? triage?.needs_manual_review ?? summary?.manual_review ?? 0,
      informational: byClass.informational ?? triage?.informational ?? summary?.informational ?? 0,
      duplicates: byClass.duplicate ?? triage?.duplicate ?? 0,
      regression: {
        new: reg.new ?? 0,
        fixed: reg.fixed ?? 0,
        unchanged: reg.unchanged ?? 0,
        worsened: reg.worsened ?? 0,
        improved: reg.improved ?? 0,
      },
    },
    findings: results.findings ?? [],
    testCases: results.test_cases ?? [],
    crossDevice: {
      measured: Boolean(crossDevice && (crossDevice.devices_tested || crossDevice.device_breakdown)),
      devices_tested: crossDevice?.devices_tested ?? 0,
      responsive_findings: crossDevice?.responsive_findings ?? 0,
      device_breakdown: { ...EMPTY_BREAKDOWN, ...(crossDevice?.device_breakdown ?? {}) },
    },
    isDegraded,
    degradedCount: meta?.ai_analysis_failures ?? 0,
  };
};

const DEVICE_ROWS: ReadonlyArray<{ label: string; key: keyof DeviceBreakdown }> = [
  { label: 'Desktop (1920x1080)', key: 'desktop' },
  { label: 'Mobile (iPhone 13, 390x844)', key: 'iphone' },
  { label: 'Tablet (iPad, 820x1180)', key: 'ipad' },
];

const deviceStatus = (data: CanonicalExportData) => (data.crossDevice.measured ? 'Tested' : 'Not recorded');

const testCaseStatus = (t: TestCase) => (t.status || t.execution_policy || 'skipped').toUpperCase();

/**
 * Generates and triggers a PDF download for the QA scan.
 */
const downloadPDF = async (results: QAReport, scanId: string | null = '') => {
  const [jspdfModule, autotableModule] = await Promise.all([
    import('jspdf'),
    import('jspdf-autotable'),
  ]);

  const data = extractCanonicalExportData(results, scanId);
  const JsPdfConstructor = (jspdfModule as any).jsPDF || (jspdfModule as any).default;
  const autoTable = (autotableModule as any).default || (autotableModule as any).autoTable;
  const doc: jsPDF = new JsPdfConstructor('p', 'mm', 'a4'); // A4 Portrait (210 x 297 mm)

  const formattedDate = new Date(data.generatedAt).toLocaleString();
  const tableEnd = (fallback: number) => (doc.lastAutoTable ? doc.lastAutoTable.finalY + 8 : fallback);

  // 1. Header Banner
  doc.setFillColor(30, 41, 59); // Slate 800
  doc.rect(0, 0, 210, 28, 'F');

  doc.setFontSize(15);
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.text('JASUSS QA PLATFORM — EXECUTIVE REPORT', 14, 12);

  doc.setFontSize(8.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(203, 213, 225); // Slate 300
  doc.text(`Target: ${data.target}  |  Scan ID: ${data.scanId}  |  Date: ${formattedDate}`, 14, 20);

  let currentY = 34;

  // 2. Degradation Warning Banner
  if (data.isDegraded) {
    doc.setFillColor(254, 242, 242); // Red 50
    doc.setDrawColor(239, 68, 68); // Red 500
    doc.rect(14, currentY, 182, 12, 'FD');

    doc.setFontSize(9);
    doc.setTextColor(185, 28, 28); // Red 700
    doc.setFont('helvetica', 'bold');
    doc.text(
      `Warning: AI analysis was incomplete. ${data.degradedCount} finding(s) could not be analysed by the model.`,
      18,
      currentY + 7
    );
    currentY += 16;
  }

  // 3. Executive Overview Summary Table
  const qs = data.qualityScore;
  const healthText =
    qs.score === null ? 'N/A (no score recorded)' : `${scoreText(qs)} (Grade ${gradeText(qs)} - ${summaryText(qs)})`;
  const overviewBody = [
    ['Target URL', data.target, 'Site Health Score', healthText],
    ['Pages Crawled / Discovered', `${data.pagesCrawled} / ${data.pagesDiscovered}`, 'Scan Duration', `${data.durationSeconds}s`],
    ['Total Automated Test Cases', `${data.testCasesSummary.total}`, 'Test Pass Rate', `${data.testCasesSummary.pass_rate}%`],
    ['Total Defects / Findings', `${data.findingsSummary.total}`, 'Critical / High Severity', `${data.findingsSummary.critical} / ${data.findingsSummary.high}`],
  ];

  autoTable(doc, {
    startY: currentY,
    head: [['Scan Attribute', 'Value', 'Quality Metric', 'Result']],
    body: overviewBody,
    theme: 'grid',
    headStyles: { fillColor: [30, 41, 59], textColor: 255, fontStyle: 'bold', fontSize: 9 },
    bodyStyles: { fontSize: 8.5, textColor: [30, 41, 59] },
    margin: { left: 14, right: 14 },
  });

  currentY = tableEnd(currentY + 36);

  // 4. Test Execution Summary Table
  const tc = data.testCasesSummary;
  const testSummaryBody = [
    ['Total Test Cases', tc.total.toString(), tc.total > 0 ? '100.0%' : '0.0%'],
    ['Passed', tc.passed.toString(), `${tc.pass_rate}%`],
    ['Failed', tc.failed.toString(), `${tc.fail_rate}%`],
    ['Skipped / Manual Review', tc.skipped.toString(), `${tc.skip_rate}%`],
    ['Blocked', tc.blocked.toString(), `${tc.block_rate}%`],
    ['Errored', tc.errored.toString(), `${tc.errored_rate}%`],
  ];

  // 5. Findings Breakdown Table
  const fs = data.findingsSummary;
  const findingSummaryBody = [
    ['Total Unique Findings', fs.total.toString(), 'P0 (Blocker)', fs.P0.toString()],
    ['Critical Severity', fs.critical.toString(), 'P1 (High Priority)', fs.P1.toString()],
    ['High Severity', fs.high.toString(), 'P2 (Medium Priority)', fs.P2.toString()],
    ['Medium Severity', fs.medium.toString(), 'P3 (Low Priority)', fs.P3.toString()],
    ['Low Severity', fs.low.toString(), 'P4 (Trivial)', fs.P4.toString()],
    ['Informational', fs.info.toString(), 'Duplicates Filtered', fs.duplicates.toString()],
  ];

  if (currentY > 230) {
    doc.addPage();
    currentY = 20;
  }

  autoTable(doc, {
    startY: currentY,
    head: [['Test Execution Metric', 'Count', 'Percentage Rate']],
    body: testSummaryBody,
    theme: 'striped',
    headStyles: { fillColor: [79, 70, 229], textColor: 255, fontStyle: 'bold', fontSize: 9 },
    bodyStyles: { fontSize: 8.5 },
    margin: { left: 14, right: 14 },
  });

  currentY = tableEnd(currentY + 40);

  if (currentY > 230) {
    doc.addPage();
    currentY = 20;
  }

  autoTable(doc, {
    startY: currentY,
    head: [['Severity Classification', 'Count', 'Priority Level', 'Count']],
    body: findingSummaryBody,
    theme: 'striped',
    headStyles: { fillColor: [139, 92, 246], textColor: 255, fontStyle: 'bold', fontSize: 9 },
    bodyStyles: { fontSize: 8.5 },
    margin: { left: 14, right: 14 },
  });

  currentY = tableEnd(currentY + 40);

  // 6. Cross-device matrix (only when the pipeline recorded one)
  if (data.crossDevice.measured) {
    if (currentY > 240) {
      doc.addPage();
      currentY = 20;
    }

    autoTable(doc, {
      startY: currentY,
      head: [['Device / Viewport', 'Status', 'Responsive Findings']],
      body: DEVICE_ROWS.map((row) => [row.label, deviceStatus(data), data.crossDevice.device_breakdown[row.key].toString()]),
      theme: 'striped',
      headStyles: { fillColor: [14, 165, 233], textColor: 255, fontStyle: 'bold', fontSize: 9 },
      bodyStyles: { fontSize: 8.5 },
      margin: { left: 14, right: 14 },
    });

    currentY = tableEnd(currentY + 30);
  }

  // 7. Test Case Details Table (if any)
  if (data.testCases.length > 0) {
    if (currentY > 220) {
      doc.addPage();
      currentY = 20;
    }

    const testCasesRows = data.testCases.map((t) => [
      t.id || 'TC',
      testCaseStatus(t),
      t.title || 'Untitled Test',
      t.duration_ms ? `${t.duration_ms}ms` : '0ms',
      t.expected_result || 'Expected pass',
      t.actual_result || 'N/A',
    ]);

    autoTable(doc, {
      startY: currentY,
      head: [['ID', 'Status', 'Test Case Title', 'Duration', 'Expected Result', 'Actual Result']],
      body: testCasesRows,
      theme: 'grid',
      headStyles: { fillColor: [16, 185, 129], textColor: 255, fontStyle: 'bold', fontSize: 8.5 },
      bodyStyles: { fontSize: 7.5, cellPadding: 2 },
      columnStyles: {
        0: { cellWidth: 20 },
        1: { cellWidth: 20 },
        2: { cellWidth: 45 },
        3: { cellWidth: 18 },
        4: { cellWidth: 40 },
        5: { cellWidth: 39 },
      },
      margin: { left: 14, right: 14 },
    });

    currentY = tableEnd(currentY + 40);
  }

  // 8. Findings Details Table (if any)
  if (data.findings.length > 0) {
    if (currentY > 220) {
      doc.addPage();
      currentY = 20;
    }

    const findingsRows = data.findings.map((f) => {
      const sev = (f.severity || 'info').toUpperCase();
      const pri = (f.priority || 'P3').toUpperCase();
      const desc = `${f.title || 'Issue'}\n${(f.description || f.manual_verification || '').substring(0, 200)}`;
      return [
        f.id || 'BUG',
        `${sev}\n(${pri})`,
        desc,
        f.recommendation || 'Review and remediate.',
        f.affected_pages_count?.toString() || '1',
        f.page || f.url || 'N/A',
      ];
    });

    autoTable(doc, {
      startY: currentY,
      head: [['ID', 'Severity', 'Issue Description', 'Recommendation', 'Pages', 'Location']],
      body: findingsRows,
      theme: 'grid',
      headStyles: { fillColor: [225, 29, 72], textColor: 255, fontStyle: 'bold', fontSize: 8.5 },
      bodyStyles: { fontSize: 7.5, cellPadding: 2.5 },
      columnStyles: {
        0: { cellWidth: 18 },
        1: { cellWidth: 20 },
        2: { cellWidth: 60 },
        3: { cellWidth: 45 },
        4: { cellWidth: 15 },
        5: { cellWidth: 24 },
      },
      margin: { left: 14, right: 14 },
    });
  } else {
    if (currentY > 250) {
      doc.addPage();
      currentY = 20;
    }
    // Clean zero-findings banner
    doc.setFillColor(240, 253, 244); // Green 50
    doc.setDrawColor(34, 197, 94); // Green 500
    doc.rect(14, currentY, 182, 14, 'FD');

    doc.setFontSize(10);
    doc.setTextColor(21, 128, 61); // Green 700
    doc.setFont('helvetica', 'bold');
    doc.text('Zero Defects Detected — Your site passed all automated QA checks cleanly.', 18, currentY + 9);
  }

  // 9. Running Header & Footer with Pagination
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);

    // Running Header (Pages 2+)
    if (i > 1) {
      doc.setFontSize(8);
      doc.setTextColor(148, 163, 184);
      doc.text(`JASUSS QA Platform — ${data.target}`, 14, 8);
      doc.setDrawColor(226, 232, 240);
      doc.line(14, 10, 196, 10);
    }

    // Running Footer
    doc.setFontSize(8);
    doc.setTextColor(148, 163, 184); // Slate 400
    doc.setDrawColor(226, 232, 240);
    doc.line(14, 287, 196, 287);
    doc.text(`Confidential — JASUSS QA Platform (Powered by Nexus)`, 14, 292);
    doc.text(`Page ${i} of ${totalPages}`, 196, 292, { align: 'right' });
  }

  doc.save(`qa-report-${safeFileStem(data.scanId, data.target)}.pdf`);
};

/**
 * Generates and triggers an Excel (.xlsx) workbook download for the QA scan.
 */
const downloadExcel = async (results: QAReport, scanId: string | null = '') => {
  const xlsxModule = await import('xlsx');
  const XLSX = (xlsxModule as any).default || xlsxModule;

  const data = extractCanonicalExportData(results, scanId);
  const tc = data.testCasesSummary;
  const fs = data.findingsSummary;
  const qs = data.qualityScore;

  const wb = XLSX.utils.book_new();

  // 1. Executive Summary Sheet
  const summarySheetData: Array<Array<string | number>> = [
    ['JASUSS QA PLATFORM — EXECUTIVE SCAN REPORT'],
    ['Powered by Nexus Autonomous QA Intelligence'],
    [],
    ['GENERAL INFORMATION', ''],
    ['Target URL', data.target],
    ['Scan ID', data.scanId],
    ['Scan Status', data.status.toUpperCase()],
    ['Generated At', data.generatedAt],
    ['Scan Duration (seconds)', data.durationSeconds],
    ['Pages Crawled', data.pagesCrawled],
    ['Pages Discovered', data.pagesDiscovered],
    [],
    ['QUALITY & HEALTH', ''],
    ['Site Health Score', qs.score ?? 'N/A'],
    ['Health Grade', gradeText(qs)],
    ['Health Summary', summaryText(qs)],
    [],
    ['TEST EXECUTION METRICS', 'COUNT', 'RATE (%)'],
    ['Total Test Cases', tc.total, tc.total > 0 ? 100.0 : 0.0],
    ['Executed Test Cases', tc.executed, rate(tc.executed, tc.total)],
    ['Passed', tc.passed, tc.pass_rate],
    ['Failed', tc.failed, tc.fail_rate],
    ['Skipped / Manual Review', tc.skipped, tc.skip_rate],
    ['Blocked', tc.blocked, tc.block_rate],
    ['Errored', tc.errored, tc.errored_rate],
    ['Total Test Duration (ms)', tc.duration_ms, ''],
    [],
    ['FINDINGS BY SEVERITY', 'COUNT', 'PRIORITY BREAKDOWN', 'COUNT'],
    ['Total Unique Findings', fs.total, 'P0 (Blocker)', fs.P0],
    ['Critical Severity', fs.critical, 'P1 (High)', fs.P1],
    ['High Severity', fs.high, 'P2 (Medium)', fs.P2],
    ['Medium Severity', fs.medium, 'P3 (Low)', fs.P3],
    ['Low Severity', fs.low, 'P4 (Trivial)', fs.P4],
    ['Informational', fs.info, 'Duplicates Filtered', fs.duplicates],
    [],
    ['REGRESSION VS PREVIOUS RUN', 'COUNT'],
    ['New', fs.regression.new],
    ['Fixed', fs.regression.fixed],
    ['Unchanged', fs.regression.unchanged],
    ['Worsened', fs.regression.worsened],
    ['Improved', fs.regression.improved],
    [],
  ];

  const summaryWs = XLSX.utils.aoa_to_sheet(summarySheetData);
  summaryWs['!cols'] = [{ wch: 35 }, { wch: 25 }, { wch: 30 }, { wch: 15 }];
  XLSX.utils.book_append_sheet(wb, summaryWs, 'Executive Summary');

  // 2. Test Cases Sheet
  if (data.testCases.length > 0) {
    const tcHeaders = ['Test Case ID', 'Status', 'Title', 'Category', 'Priority', 'Source Page', 'Duration (ms)', 'Expected Result', 'Actual Result'];
    const tcRows = data.testCases.map((t) => [
      t.id || '',
      testCaseStatus(t),
      t.title || '',
      t.category || '',
      t.priority || '',
      t.source_page || '',
      t.duration_ms || 0,
      t.expected_result || '',
      t.actual_result || '',
    ]);

    const tcWs = XLSX.utils.aoa_to_sheet([tcHeaders, ...tcRows]);
    tcWs['!cols'] = [{ wch: 15 }, { wch: 12 }, { wch: 40 }, { wch: 15 }, { wch: 10 }, { wch: 30 }, { wch: 14 }, { wch: 30 }, { wch: 30 }];
    XLSX.utils.book_append_sheet(wb, tcWs, 'Test Cases');
  }

  // 3. Defect Findings Sheet
  if (data.findings.length > 0) {
    const findingHeaders = [
      'Finding ID',
      'Severity',
      'Priority',
      'Classification',
      'Regression',
      'Title',
      'Location / URL',
      'Description',
      'Expected',
      'Actual',
      'Recommended Action',
      'Affected Pages',
    ];

    const findingRows = data.findings.map((f) => [
      f.id || '',
      (f.severity || 'info').toUpperCase(),
      (f.priority || 'P3').toUpperCase(),
      f.classification || '',
      f.regression_status || '',
      f.title || '',
      f.page || f.url || '',
      f.description || '',
      f.expected_result || '',
      f.actual_result || '',
      f.recommendation || '',
      f.affected_pages_count ?? 1,
    ]);

    const findingsWs = XLSX.utils.aoa_to_sheet([findingHeaders, ...findingRows]);
    findingsWs['!cols'] = [
      { wch: 15 }, { wch: 10 }, { wch: 10 }, { wch: 18 }, { wch: 12 }, { wch: 35 },
      { wch: 30 }, { wch: 40 }, { wch: 30 }, { wch: 30 }, { wch: 40 }, { wch: 14 },
    ];
    XLSX.utils.book_append_sheet(wb, findingsWs, 'Defect Findings');
  }

  // 4. Cross-Device Matrix: real counts only, no invented performance figures
  const cdHeaders = ['Device / Viewport', 'Status', 'Responsive Findings'];
  const cdRows = DEVICE_ROWS.map((row) => [row.label, deviceStatus(data), data.crossDevice.device_breakdown[row.key]]);
  cdRows.push([]);
  cdRows.push(['Viewports tested', data.crossDevice.measured ? data.crossDevice.devices_tested : 'N/A', '']);
  cdRows.push(['Total responsive findings', data.crossDevice.measured ? data.crossDevice.responsive_findings : 'N/A', '']);

  const cdWs = XLSX.utils.aoa_to_sheet([cdHeaders, ...cdRows]);
  cdWs['!cols'] = [{ wch: 30 }, { wch: 15 }, { wch: 22 }];
  XLSX.utils.book_append_sheet(wb, cdWs, 'Device Responsiveness');

  XLSX.writeFile(wb, `qa-report-${safeFileStem(data.scanId, data.target)}.xlsx`);
};

const mdCell = (value: string | undefined, fallback: string) => (value || fallback).replace(/\|/g, '\\|');

/**
 * Generates formatted Markdown report string from canonical data.
 */
export const generateMarkdownReport = (data: CanonicalExportData): string => {
  const formattedDate = new Date(data.generatedAt).toLocaleString();
  const tc = data.testCasesSummary;
  const fs = data.findingsSummary;
  const qs = data.qualityScore;

  const lines: string[] = [];

  lines.push('# JASUSS QA Report (Powered by Nexus)\n');

  if (data.isDegraded) {
    lines.push(
      `> ⚠️ **Warning — AI analysis was incomplete.** ${data.degradedCount} candidate(s) could not be analysed by the model. Deterministic fallbacks are used.\n`
    );
  }

  lines.push('## 1. Executive Summary\n');
  lines.push(`- **Target URL:** ${data.target}`);
  lines.push(`- **Scan ID:** \`${data.scanId}\``);
  lines.push(`- **Generated At:** ${formattedDate}`);
  lines.push(
    qs.score === null
      ? '- **Overall Health Score:** N/A (no score was recorded for this run)'
      : `- **Overall Health Score:** **${scoreText(qs)}** (Grade **${gradeText(qs)}** - *${summaryText(qs)}*)`
  );
  lines.push(`- **Pages Crawled / Discovered:** ${data.pagesCrawled} / ${data.pagesDiscovered}`);
  lines.push(`- **Scan Duration:** ${data.durationSeconds}s`);
  lines.push(`- **Total Automated Test Cases:** ${tc.total} (Pass Rate: **${tc.pass_rate}%**)`);
  lines.push(`- **Total Defects Identified:** ${fs.total} (Critical: ${fs.critical}, High: ${fs.high}, Medium: ${fs.medium}, Low: ${fs.low})\n`);

  lines.push('## 2. Automated Test Execution Summary\n');
  lines.push('| Metric | Count | Percentage |');
  lines.push('| :--- | :--- | :--- |');
  lines.push(`| Total Test Cases | ${tc.total} | ${tc.total > 0 ? '100.0%' : '0.0%'} |`);
  lines.push(`| Passed | ${tc.passed} | ${tc.pass_rate}% |`);
  lines.push(`| Failed | ${tc.failed} | ${tc.fail_rate}% |`);
  lines.push(`| Skipped / Manual Review | ${tc.skipped} | ${tc.skip_rate}% |`);
  lines.push(`| Blocked | ${tc.blocked} | ${tc.block_rate}% |`);
  lines.push(`| Errored | ${tc.errored} | ${tc.errored_rate}% |`);
  lines.push(`| Execution Duration | ${tc.duration_ms}ms | - |\n`);

  lines.push('## 3. Defect & Finding Metrics\n');
  lines.push('### Severity Breakdown\n');
  lines.push('| Severity | Count | Priority Level | Count |');
  lines.push('| :--- | :--- | :--- | :--- |');
  lines.push(`| Critical | ${fs.critical} | P0 (Blocker) | ${fs.P0} |`);
  lines.push(`| High | ${fs.high} | P1 (High) | ${fs.P1} |`);
  lines.push(`| Medium | ${fs.medium} | P2 (Medium) | ${fs.P2} |`);
  lines.push(`| Low | ${fs.low} | P3 (Low) | ${fs.P3} |`);
  lines.push(`| Informational | ${fs.info} | P4 (Trivial) | ${fs.P4} |`);
  lines.push(`| **Total Unique** | **${fs.total}** | Duplicates Filtered | ${fs.duplicates} |\n`);

  lines.push('## 4. Cross-Device Responsiveness\n');
  if (data.crossDevice.measured) {
    const cd = data.crossDevice;
    lines.push(`Viewports tested: **${cd.devices_tested}** · Responsive findings: **${cd.responsive_findings}**\n`);
    lines.push('| Device Viewport | Status | Responsive Findings |');
    lines.push('| :--- | :--- | :--- |');
    DEVICE_ROWS.forEach((row) => {
      lines.push(`| ${row.label} | ${deviceStatus(data)} | ${cd.device_breakdown[row.key]} |`);
    });
    lines.push('');
  } else {
    lines.push('No cross-device telemetry was recorded for this run.\n');
  }

  if (data.testCases.length > 0) {
    lines.push('## 5. Automated Test Cases Detail\n');
    lines.push('| ID | Status | Title | Duration | Expected Result | Actual Result |');
    lines.push('| :--- | :--- | :--- | :--- | :--- | :--- |');
    data.testCases.forEach((t) => {
      const dur = t.duration_ms ? `${t.duration_ms}ms` : '0ms';
      lines.push(
        `| \`${t.id || 'TC'}\` | **${testCaseStatus(t)}** | ${mdCell(t.title, 'Untitled')} | ${dur} | ${mdCell(t.expected_result, 'Pass')} | ${mdCell(t.actual_result, 'N/A')} |`
      );
    });
    lines.push('');
  }

  if (data.findings.length > 0) {
    lines.push('## 6. Detailed Defect Findings\n');
    data.findings.forEach((f, idx) => {
      const sev = (f.severity || 'info').toUpperCase();
      const pri = (f.priority || 'P3').toUpperCase();
      lines.push(`### ${idx + 1}. [${f.id || 'BUG'}] ${f.title || 'Untitled Defect'}\n`);
      lines.push(`- **Severity:** \`${sev}\` | **Priority:** \`${pri}\` | **Classification:** \`${f.classification || 'N/A'}\``);
      if (f.page || f.url) lines.push(`- **Location:** ${f.page || f.url}`);
      if (f.description) lines.push(`- **Description:** ${f.description}`);
      if (f.expected_result) lines.push(`- **Expected Result:** ${f.expected_result}`);
      if (f.actual_result) lines.push(`- **Actual Result:** ${f.actual_result}`);
      if (f.recommendation) lines.push(`- **Recommendation:** ${f.recommendation}`);
      if (f.reproduction?.steps && f.reproduction.steps.length > 0) {
        lines.push('- **Reproduction Steps:**');
        f.reproduction.steps.forEach((step, sIdx) => {
          lines.push(`  ${sIdx + 1}. ${step}`);
        });
      }
      lines.push('');
    });
  } else {
    lines.push('## 6. Defect Findings\n');
    lines.push('✨ **Zero defects detected.** The target web application passed all automated QA checks cleanly.\n');
  }

  lines.push('---\n*Confidential report generated autonomously by JASUSS QA Platform (Powered by Nexus).*');

  return lines.join('\n');
};

/**
 * Downloads Markdown report file directly via Blob.
 */
const downloadMarkdown = (results: QAReport, scanId: string | null = '') => {
  const data = extractCanonicalExportData(results, scanId);
  const mdContent = generateMarkdownReport(data);
  saveBlob(
    new Blob([mdContent], { type: 'text/markdown; charset=utf-8' }),
    `qa-report-${safeFileStem(data.scanId, data.target)}.md`
  );
};

/**
 * Downloads raw JSON report file directly via Blob.
 */
const downloadJSON = (results: QAReport, scanId: string | null = '') => {
  const data = extractCanonicalExportData(results, scanId);
  saveBlob(
    new Blob([JSON.stringify(results, null, 2)], { type: 'application/json; charset=utf-8' }),
    `qa-report-${safeFileStem(data.scanId, data.target)}.json`
  );
};

export type ExportFormat = 'pdf' | 'excel' | 'xlsx' | 'json' | 'md' | 'markdown';

export interface DownloadReportOptions {
  results: QAReport;
  scanId?: string | null;
  format: ExportFormat;
  sessionToken?: string | null;
}

/**
 * Unified download handler for all report formats (PDF, Excel, JSON, Markdown).
 * Prefers the server's pre-generated file and only builds one in the browser when
 * the server has none (404). Auth, quota and server errors are thrown to the caller
 * so the UI can tell the user what went wrong instead of silently handing over a
 * different, client-rendered file.
 */
export const handleDownloadReport = async ({
  results,
  scanId,
  format,
  sessionToken,
}: DownloadReportOptions): Promise<void> => {
  const normFormat = format.toLowerCase() as ExportFormat;
  const safeScanId = scanId || '';
  const serverFormat =
    normFormat === 'excel' || normFormat === 'xlsx'
      ? 'xlsx'
      : normFormat === 'markdown' || normFormat === 'md'
      ? 'md'
      : normFormat === 'json'
      ? 'json'
      : 'pdf';

  if (sessionToken && safeScanId) {
    try {
      await downloadScanReport(safeScanId, serverFormat, sessionToken);
      return;
    } catch (e) {
      if (!(e instanceof ApiError) || e.status !== 404) throw e;
    }
  }

  if (serverFormat === 'pdf') return downloadPDF(results, safeScanId);
  if (serverFormat === 'xlsx') return downloadExcel(results, safeScanId);
  if (serverFormat === 'json') return downloadJSON(results, safeScanId);
  return downloadMarkdown(results, safeScanId);
};
