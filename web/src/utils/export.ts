import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';

export interface CanonicalExportData {
  target: string;
  scanId: string;
  generatedAt: string;
  status: string;
  pagesCrawled: number;
  pagesDiscovered: number;
  durationSeconds: number;
  qualityScore: {
    score: number;
    grade: string;
    summary: string;
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
    regression: { new: number; fixed: number; unchanged: number; worsened: number; improved: number };
  };
  findings: Array<any>;
  testCases: Array<any>;
  crossDevice: {
    devices_tested: number;
    responsive_findings: number;
    device_breakdown: { desktop: number; iphone: number; ipad: number };
  };
  isDegraded: boolean;
  degradedCount: number;
}

/**
 * Normalizes scan results from any API / report format into a strict canonical export model.
 */
export const extractCanonicalExportData = (results: any, scanId: string | null = ''): CanonicalExportData => {
  if (!results) {
    return {
      target: 'Unknown',
      scanId: scanId || 'N/A',
      generatedAt: new Date().toISOString(),
      status: 'completed',
      pagesCrawled: 0,
      pagesDiscovered: 0,
      durationSeconds: 0,
      qualityScore: { score: 100, grade: 'A', summary: 'Excellent' },
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
        devices_tested: 3,
        responsive_findings: 0,
        device_breakdown: { desktop: 0, iphone: 0, ipad: 0 },
      },
      isDegraded: false,
      degradedCount: 0,
    };
  }

  const qa = results.qa_metrics || {};
  const meta = results.report_metadata || {};
  const summary = results.summary || {};
  const severity = results.severity || {};
  const triage = results.triage_metrics || {};
  const tcm = results.test_case_metrics || qa.test_cases || {};
  const qs = qa.quality_score || meta.quality_score || { score: 100, grade: 'A', summary: 'Excellent' };
  const crawl = qa.crawl || meta.cross_device_metrics || {};
  const findingsMetrics = qa.findings || {};

  const target = qa.target || meta.target || results.target || 'Unknown';
  const resolvedScanId = scanId || results.id || results.scan_id || meta.scan_id || 'N/A';
  const generatedAt = qa.generated_at || meta.generated_at || new Date().toISOString();
  const status = results.status || 'completed';

  const pagesCrawled = crawl.pages_crawled ?? meta.pages_crawled ?? 0;
  const pagesDiscovered = crawl.pages_discovered ?? pagesCrawled;
  const durationSeconds = qa.duration_seconds ?? meta.duration_seconds ?? 0;

  // Test Case Metrics
  const tcTotal = tcm.total ?? 0;
  const tcPassed = tcm.passed ?? 0;
  const tcFailed = tcm.failed ?? 0;
  const tcSkipped = tcm.skipped ?? tcm.manual_review ?? 0;
  const tcBlocked = tcm.blocked ?? 0;
  const tcErrored = tcm.errored ?? 0;
  const tcExecuted = tcm.executed ?? (tcPassed + tcFailed + tcErrored);
  const tcPassRate = tcm.pass_rate ?? (tcTotal > 0 ? Number(((tcPassed / tcTotal) * 100).toFixed(2)) : 0.0);
  const tcFailRate = tcm.fail_rate ?? (tcTotal > 0 ? Number(((tcFailed / tcTotal) * 100).toFixed(2)) : 0.0);
  const tcSkipRate = tcm.skip_rate ?? (tcTotal > 0 ? Number(((tcSkipped / tcTotal) * 100).toFixed(2)) : 0.0);
  const tcBlockRate = tcm.block_rate ?? (tcTotal > 0 ? Number(((tcBlocked / tcTotal) * 100).toFixed(2)) : 0.0);
  const tcErroredRate = tcm.errored_rate ?? (tcTotal > 0 ? Number(((tcErrored / tcTotal) * 100).toFixed(2)) : 0.0);
  const tcDurationMs = tcm.duration_ms ?? 0;

  // Findings Metrics
  const bySev = findingsMetrics.by_severity || severity || {};
  const byPri = findingsMetrics.by_priority || triage.priority || {};
  const byClass = findingsMetrics.by_classification || {};
  const reg = findingsMetrics.by_regression || triage.regression_summary || summary.regression_summary || {};

  const totalFindings = findingsMetrics.total ?? summary.total_candidates ?? (results.findings?.length || 0);
  const criticalFindings = bySev.critical ?? 0;
  const highFindings = bySev.high ?? 0;
  const medFindings = bySev.medium ?? 0;
  const lowFindings = bySev.low ?? 0;
  const infoFindings = bySev.info ?? 0;

  const p0 = byPri.P0 ?? 0;
  const p1 = byPri.P1 ?? 0;
  const p2 = byPri.P2 ?? 0;
  const p3 = byPri.P3 ?? 0;
  const p4 = byPri.P4 ?? 0;

  const confirmedBugs = byClass.confirmed_bug ?? triage.confirmed_bug ?? summary.confirmed_bugs ?? 0;
  const highConf = byClass.high_confidence_candidate ?? triage.high_confidence_candidate ?? summary.potential_issues ?? 0;
  const manualReview = byClass.needs_manual_review ?? triage.needs_manual_review ?? summary.manual_review ?? 0;
  const informational = byClass.informational ?? triage.informational ?? summary.informational ?? 0;
  const duplicates = byClass.duplicate ?? triage.duplicate ?? 0;

  const isDegraded = Boolean(meta.ai_analysis_degraded || meta.ai_analysis_failures);
  const degradedCount = meta.ai_analysis_failures ?? 0;

  return {
    target,
    scanId: resolvedScanId,
    generatedAt,
    status,
    pagesCrawled,
    pagesDiscovered,
    durationSeconds,
    qualityScore: {
      score: typeof qs.score === 'number' ? qs.score : 100,
      grade: qs.grade || 'A',
      summary: qs.summary || 'Excellent',
    },
    testCasesSummary: {
      total: tcTotal,
      executed: tcExecuted,
      passed: tcPassed,
      failed: tcFailed,
      skipped: tcSkipped,
      blocked: tcBlocked,
      errored: tcErrored,
      pass_rate: tcPassRate,
      fail_rate: tcFailRate,
      skip_rate: tcSkipRate,
      block_rate: tcBlockRate,
      errored_rate: tcErroredRate,
      duration_ms: tcDurationMs,
    },
    findingsSummary: {
      total: totalFindings,
      critical: criticalFindings,
      high: highFindings,
      medium: medFindings,
      low: lowFindings,
      info: infoFindings,
      P0: p0,
      P1: p1,
      P2: p2,
      P3: p3,
      P4: p4,
      confirmed_bugs: confirmedBugs,
      high_confidence_candidates: highConf,
      needs_manual_review: manualReview,
      informational: informational,
      duplicates: duplicates,
      regression: {
        new: reg.new ?? 0,
        fixed: reg.fixed ?? 0,
        unchanged: reg.unchanged ?? 0,
        worsened: reg.worsened ?? 0,
        improved: reg.improved ?? 0,
      },
    },
    findings: results.findings || [],
    testCases: results.test_cases || [],
    crossDevice: {
      devices_tested: crawl.devices_tested ?? 3,
      responsive_findings: crawl.responsive_findings ?? 0,
      device_breakdown: crawl.device_breakdown || { desktop: 0, iphone: 0, ipad: 0 },
    },
    isDegraded,
    degradedCount,
  };
};

/**
 * Generates and triggers a PDF download for the QA scan.
 */
export const downloadPDF = (results: any, scanId: string | null = '') => {
  if (!results) return;

  const data = extractCanonicalExportData(results, scanId);
  const doc = new jsPDF('p', 'mm', 'a4'); // A4 Portrait (210 x 297 mm)

  const formattedDate = new Date(data.generatedAt).toLocaleString();

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
  const overviewBody = [
    ['Target URL', data.target, 'Site Health Score', `${data.qualityScore.score} / 100 (Grade ${data.qualityScore.grade} - ${data.qualityScore.summary})`],
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

  currentY = (doc as any).lastAutoTable ? (doc as any).lastAutoTable.finalY + 8 : currentY + 36;

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

  currentY = (doc as any).lastAutoTable ? (doc as any).lastAutoTable.finalY + 8 : currentY + 40;

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

  currentY = (doc as any).lastAutoTable ? (doc as any).lastAutoTable.finalY + 8 : currentY + 40;

  // 6. Test Case Details Table (if any)
  if (data.testCases && data.testCases.length > 0) {
    if (currentY > 220) {
      doc.addPage();
      currentY = 20;
    }

    const testCasesRows = data.testCases.map((t: any) => {
      const rawStatus = (t.status || t.execution_policy || 'skipped').toUpperCase();
      const durationStr = t.duration_ms ? `${t.duration_ms}ms` : '0ms';
      return [
        t.id || 'TC',
        rawStatus,
        t.title || 'Untitled Test',
        durationStr,
        t.expected_result || 'Expected pass',
        t.actual_result || 'N/A',
      ];
    });

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

    currentY = (doc as any).lastAutoTable ? (doc as any).lastAutoTable.finalY + 8 : currentY + 40;
  }

  // 7. Findings Details Table (if any)
  if (data.findings && data.findings.length > 0) {
    if (currentY > 220) {
      doc.addPage();
      currentY = 20;
    }

    const findingsRows = data.findings.map((f: any) => {
      const sev = (f.severity || 'info').toUpperCase();
      const pri = (f.priority || 'P3').toUpperCase();
      const desc = `${f.title || 'Issue'}\n${(f.description || f.manual_verification || '').substring(0, 200)}`;
      const rec = f.recommendation || f.recommended_action || 'Review and remediate.';
      const pageLoc = f.page || f.url || 'N/A';

      return [
        f.id || 'BUG',
        `${sev}\n(${pri})`,
        desc,
        rec,
        f.affected_pages_count?.toString() || '1',
        pageLoc,
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

  // 8. Running Header & Footer with Pagination
  const totalPages = (doc as any).internal.getNumberOfPages();
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

  const safeScanId = scanId && scanId !== 'N/A' ? scanId : (data.target || 'scan').replace(/[^a-z0-9]/gi, '_').toLowerCase();
  const safeFilename = `qa-report-${safeScanId}.pdf`;
  doc.save(safeFilename);
};

/**
 * Generates and triggers an Excel (.xlsx) workbook download for the QA scan.
 */
export const downloadExcel = (results: any, scanId: string | null = '') => {
  if (!results) return;

  const data = extractCanonicalExportData(results, scanId);
  const tc = data.testCasesSummary;
  const fs = data.findingsSummary;

  const wb = XLSX.utils.book_new();

  // 1. Executive Summary Sheet
  const summarySheetData: Array<Array<any>> = [
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
    ['Site Health Score', data.qualityScore.score],
    ['Health Grade', data.qualityScore.grade],
    ['Health Summary', data.qualityScore.summary],
    [],
    ['TEST EXECUTION METRICS', 'COUNT', 'RATE (%)'],
    ['Total Test Cases', tc.total, tc.total > 0 ? 100.0 : 0.0],
    ['Executed Test Cases', tc.executed, tc.total > 0 ? Number(((tc.executed / tc.total) * 100).toFixed(2)) : 0.0],
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
    ['REGRESSION ANALYSIS', 'COUNT'],
    ['New Defects', fs.regression.new],
    ['Fixed Defects', fs.regression.fixed],
    ['Unchanged Defects', fs.regression.unchanged],
    ['Worsened Defects', fs.regression.worsened],
    ['Improved Defects', fs.regression.improved],
  ];

  const summaryWs = XLSX.utils.aoa_to_sheet(summarySheetData);
  summaryWs['!cols'] = [{ wch: 30 }, { wch: 25 }, { wch: 25 }, { wch: 15 }];
  XLSX.utils.book_append_sheet(wb, summaryWs, 'Executive Summary');

  // 2. Test Cases Sheet (if any)
  if (data.testCases && data.testCases.length > 0) {
    const tcHeaders = [
      'Test ID',
      'Status',
      'Title',
      'Category',
      'Priority',
      'Duration (ms)',
      'Source Page',
      'Expected Result',
      'Actual Result',
      'Evidence / Screenshot',
    ];

    const tcRows = data.testCases.map((t: any) => [
      t.id || 'TC',
      (t.status || t.execution_policy || 'SKIPPED').toUpperCase(),
      t.title || 'Untitled Test Case',
      t.category || 'Functional',
      t.priority || 'P3',
      typeof t.duration_ms === 'number' ? t.duration_ms : 0,
      t.source_page || '',
      t.expected_result || 'Expected pass',
      t.actual_result || 'N/A',
      t.evidence?.screenshot || (t.screenshots && t.screenshots[0]) || '',
    ]);

    const tcWs = XLSX.utils.aoa_to_sheet([tcHeaders, ...tcRows]);
    tcWs['!cols'] = [
      { wch: 15 },
      { wch: 12 },
      { wch: 35 },
      { wch: 15 },
      { wch: 10 },
      { wch: 15 },
      { wch: 30 },
      { wch: 35 },
      { wch: 35 },
      { wch: 30 },
    ];
    XLSX.utils.book_append_sheet(wb, tcWs, 'Test Cases');
  }

  // 3. Findings Sheet (if any)
  if (data.findings && data.findings.length > 0) {
    const findingHeaders = [
      'Finding ID',
      'Severity',
      'Priority',
      'Classification',
      'Confidence',
      'Title',
      'Page Location',
      'URL',
      'Description',
      'Expected Result',
      'Actual Result',
      'Reproduction Steps',
      'Recommendation',
      'Affected Pages Count',
      'Regression Status',
    ];

    const findingRows = data.findings.map((f: any) => [
      f.id || 'BUG',
      (f.severity || 'INFO').toUpperCase(),
      (f.priority || 'P3').toUpperCase(),
      f.classification || 'N/A',
      f.confidence || 'low',
      f.title || 'Untitled Issue',
      f.page || 'N/A',
      f.url || '',
      f.description || f.manual_verification || '',
      f.expected_result || 'Not specified.',
      f.actual_result || 'Not specified.',
      f.reproduction?.steps ? f.reproduction.steps.join(' -> ') : '',
      f.recommendation || f.recommended_action || '',
      typeof f.affected_pages_count === 'number' ? f.affected_pages_count : 1,
      f.regression_status || 'NEW',
    ]);

    const findingsWs = XLSX.utils.aoa_to_sheet([findingHeaders, ...findingRows]);
    findingsWs['!cols'] = [
      { wch: 15 },
      { wch: 12 },
      { wch: 10 },
      { wch: 22 },
      { wch: 12 },
      { wch: 35 },
      { wch: 30 },
      { wch: 35 },
      { wch: 45 },
      { wch: 30 },
      { wch: 30 },
      { wch: 35 },
      { wch: 40 },
      { wch: 20 },
      { wch: 15 },
    ];
    XLSX.utils.book_append_sheet(wb, findingsWs, 'Defect Findings');
  }

  // 4. Bug Triage Sheet (if findings exist)
  if (data.findings && data.findings.length > 0) {
    const triageHeaders = [
      'Finding ID',
      'Classification',
      'Severity',
      'Priority',
      'Confidence',
      'Root Cause Category',
      'User Impact',
      'Total Occurrences',
      'Affected Pages',
      'Regression Status',
      'Recommendation',
    ];

    const triageRows = data.findings.map((f: any) => [
      f.id || 'BUG',
      f.classification || 'N/A',
      (f.severity || 'INFO').toUpperCase(),
      (f.priority || 'P3').toUpperCase(),
      f.confidence || 'low',
      f.root_cause?.category?.replace('_', ' ') || 'unknown',
      f.user_impact || 'unknown',
      typeof f.occurrence_count === 'number' ? f.occurrence_count : 1,
      typeof f.affected_pages_count === 'number' ? f.affected_pages_count : 1,
      f.regression_status || 'NEW',
      f.recommendation || f.recommended_action || '',
    ]);

    const triageWs = XLSX.utils.aoa_to_sheet([triageHeaders, ...triageRows]);
    triageWs['!cols'] = [
      { wch: 15 },
      { wch: 22 },
      { wch: 12 },
      { wch: 10 },
      { wch: 12 },
      { wch: 22 },
      { wch: 18 },
      { wch: 18 },
      { wch: 16 },
      { wch: 16 },
      { wch: 40 },
    ];
    XLSX.utils.book_append_sheet(wb, triageWs, 'Bug Triage');
  }

  // 5. Cross Device Responsiveness Sheet
  if (data.crossDevice) {
    const cdHeaders = ['Device Platform', 'Tested Status', 'Responsive Issues Identified'];
    const cd = data.crossDevice;
    const cdRows = [
      ['Desktop (1920x1080)', 'Tested', cd.device_breakdown.desktop],
      ['iPhone (Mobile Viewport)', 'Tested', cd.device_breakdown.iphone],
      ['iPad (Tablet Viewport)', 'Tested', cd.device_breakdown.ipad],
    ];

    const cdWs = XLSX.utils.aoa_to_sheet([cdHeaders, ...cdRows]);
    cdWs['!cols'] = [{ wch: 28 }, { wch: 16 }, { wch: 30 }];
    XLSX.utils.book_append_sheet(wb, cdWs, 'Device Responsiveness');
  }

  const safeScanId = scanId && scanId !== 'N/A' ? scanId : (data.target || 'scan').replace(/[^a-z0-9]/gi, '_').toLowerCase();
  const safeFilename = `qa-report-${safeScanId}.xlsx`;

  try {
    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([wbout], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=UTF-8',
    });
    const downloadUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = downloadUrl;
    anchor.download = safeFilename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    setTimeout(() => {
      window.URL.revokeObjectURL(downloadUrl);
    }, 1000);
  } catch {
    XLSX.writeFile(wb, safeFilename);
  }
};

/**
 * Generates formatted Markdown report string from canonical data.
 */
export const generateMarkdownReport = (data: CanonicalExportData): string => {
  const formattedDate = new Date(data.generatedAt).toLocaleString();
  const tc = data.testCasesSummary;
  const fs = data.findingsSummary;

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
  lines.push(`- **Overall Health Score:** **${data.qualityScore.score} / 100** (Grade **${data.qualityScore.grade}** - *${data.qualityScore.summary}*)`);
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

  if (data.crossDevice) {
    const cd = data.crossDevice;
    lines.push('## 4. Cross-Device Responsiveness\n');
    lines.push('| Device Viewport | Status | Responsive Findings |');
    lines.push('| :--- | :--- | :--- |');
    lines.push(`| Desktop (1920x1080) | Tested | ${cd.device_breakdown.desktop} |`);
    lines.push(`| Mobile (iPhone Viewport) | Tested | ${cd.device_breakdown.iphone} |`);
    lines.push(`| Tablet (iPad Viewport) | Tested | ${cd.device_breakdown.ipad} |\n`);
  }

  if (data.testCases && data.testCases.length > 0) {
    lines.push('## 5. Automated Test Cases Detail\n');
    lines.push('| ID | Status | Title | Duration | Expected Result | Actual Result |');
    lines.push('| :--- | :--- | :--- | :--- | :--- | :--- |');
    data.testCases.forEach((t: any) => {
      const status = (t.status || t.execution_policy || 'SKIPPED').toUpperCase();
      const dur = t.duration_ms ? `${t.duration_ms}ms` : '0ms';
      const cleanTitle = (t.title || 'Untitled').replace(/\|/g, '\\|');
      const cleanExpected = (t.expected_result || 'Pass').replace(/\|/g, '\\|');
      const cleanActual = (t.actual_result || 'N/A').replace(/\|/g, '\\|');
      lines.push(`| \`${t.id || 'TC'}\` | **${status}** | ${cleanTitle} | ${dur} | ${cleanExpected} | ${cleanActual} |`);
    });
    lines.push('');
  }

  if (data.findings && data.findings.length > 0) {
    lines.push('## 6. Detailed Defect Findings\n');
    data.findings.forEach((f: any, idx: number) => {
      const sev = (f.severity || 'INFO').toUpperCase();
      const pri = (f.priority || 'P3').toUpperCase();
      lines.push(`### ${idx + 1}. [${f.id || 'BUG'}] ${f.title || 'Untitled Defect'}\n`);
      lines.push(`- **Severity:** \`${sev}\` | **Priority:** \`${pri}\` | **Classification:** \`${f.classification || 'N/A'}\``);
      if (f.page || f.url) lines.push(`- **Location:** ${f.page || f.url}`);
      if (f.description) lines.push(`- **Description:** ${f.description}`);
      if (f.expected_result) lines.push(`- **Expected Result:** ${f.expected_result}`);
      if (f.actual_result) lines.push(`- **Actual Result:** ${f.actual_result}`);
      if (f.recommendation || f.recommended_action) lines.push(`- **Recommendation:** ${f.recommendation || f.recommended_action}`);
      if (f.reproduction?.steps && f.reproduction.steps.length > 0) {
        lines.push('- **Reproduction Steps:**');
        f.reproduction.steps.forEach((step: string, sIdx: number) => {
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
export const downloadMarkdown = (results: any, scanId: string | null = '') => {
  if (!results) return;
  const data = extractCanonicalExportData(results, scanId);
  const mdContent = generateMarkdownReport(data);

  const safeScanId = scanId && scanId !== 'N/A' ? scanId : (data.target || 'scan').replace(/[^a-z0-9]/gi, '_').toLowerCase();
  const filename = `qa-report-${safeScanId}.md`;

  const blob = new Blob([mdContent], { type: 'text/markdown; charset=utf-8' });
  const downloadUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = downloadUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);
};

/**
 * Downloads raw JSON report file directly via Blob.
 */
export const downloadJSON = (results: any, scanId: string | null = '') => {
  if (!results) return;
  const data = extractCanonicalExportData(results, scanId);
  const jsonContent = JSON.stringify(results, null, 2);

  const safeScanId = scanId && scanId !== 'N/A' ? scanId : (data.target || 'scan').replace(/[^a-z0-9]/gi, '_').toLowerCase();
  const filename = `qa-report-${safeScanId}.json`;

  const blob = new Blob([jsonContent], { type: 'application/json; charset=utf-8' });
  const downloadUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = downloadUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);
};

export type ExportFormat = 'pdf' | 'excel' | 'xlsx' | 'json' | 'md' | 'markdown';

export interface DownloadReportOptions {
  results: any;
  scanId?: string | null;
  format: ExportFormat;
  sessionToken?: string | null;
}

/**
 * Parses filename from Content-Disposition header with fallback.
 */
export const extractFilenameFromDisposition = (disposition: string | null, fallbackFilename: string): string => {
  if (!disposition) return fallbackFilename;

  // Check for RFC 5987 / RFC 6266 utf-8 filename
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }

  // Check for standard filename="name" or filename=name
  const standardMatch = disposition.match(/filename="?([^";]+)"?/i);
  if (standardMatch && standardMatch[1]) {
    return standardMatch[1].trim();
  }

  return fallbackFilename;
};

/**
 * Unified download handler for all report formats (PDF, Excel, JSON, Markdown).
 * Automatically resolves Content-Disposition headers, MIME types, and fallback filenames.
 */
export const handleDownloadReport = async ({
  results,
  scanId,
  format,
  sessionToken,
}: DownloadReportOptions): Promise<void> => {
  const normFormat = format.toLowerCase() as ExportFormat;
  const safeScanId = scanId || results?.report_metadata?.scan_id || results?.id || 'unknown';

  if (normFormat === 'pdf') {
    downloadPDF(results, safeScanId);
    return;
  }

  if (normFormat === 'excel' || normFormat === 'xlsx') {
    downloadExcel(results, safeScanId);
    return;
  }

  if (normFormat === 'json') {
    // If we have local results, download directly or try backend
    try {
      if (sessionToken && safeScanId !== 'unknown') {
        const headers: Record<string, string> = { Authorization: `Bearer ${sessionToken}` };
        const response = await fetch(`/api/v1/scans/${safeScanId}/download/json`, { headers });
        if (response.ok) {
          const disposition = response.headers.get('content-disposition');
          const filename = extractFilenameFromDisposition(disposition, `qa-report-${safeScanId}.json`);
          const blob = await response.blob();
          const typedBlob = new Blob([blob], { type: 'application/json' });
          const downloadUrl = window.URL.createObjectURL(typedBlob);
          const anchor = document.createElement('a');
          anchor.href = downloadUrl;
          anchor.download = filename;
          document.body.appendChild(anchor);
          anchor.click();
          document.body.removeChild(anchor);
          setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);
          return;
        }
      }
    } catch {
      // Fallback below
    }
    downloadJSON(results, safeScanId);
    return;
  }

  if (normFormat === 'md' || normFormat === 'markdown') {
    // If we have local results, download directly or try backend
    try {
      if (sessionToken && safeScanId !== 'unknown') {
        const headers: Record<string, string> = { Authorization: `Bearer ${sessionToken}` };
        const response = await fetch(`/api/v1/scans/${safeScanId}/download/md`, { headers });
        if (response.ok) {
          const disposition = response.headers.get('content-disposition');
          const filename = extractFilenameFromDisposition(disposition, `qa-report-${safeScanId}.md`);
          const blob = await response.blob();
          const typedBlob = new Blob([blob], { type: 'text/markdown; charset=utf-8' });
          const downloadUrl = window.URL.createObjectURL(typedBlob);
          const anchor = document.createElement('a');
          anchor.href = downloadUrl;
          anchor.download = filename;
          document.body.appendChild(anchor);
          anchor.click();
          document.body.removeChild(anchor);
          setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);
          return;
        }
      }
    } catch {
      // Fallback below
    }
    downloadMarkdown(results, safeScanId);
    return;
  }
};
