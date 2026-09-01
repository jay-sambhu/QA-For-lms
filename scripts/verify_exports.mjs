import * as fs from 'fs';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import * as XLSX from '../web/node_modules/xlsx/xlsx.mjs';
import { jsPDF } from '../web/node_modules/jspdf/dist/jspdf.node.min.js';
import autoTable from '../web/node_modules/jspdf-autotable/dist/jspdf.plugin.autotable.js';

XLSX.set_fs(fs);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const outputDir = path.join(__dirname, '../results/export_verification');

if (!existsSync(outputDir)) {
  mkdirSync(outputDir, { recursive: true });
}

console.log('=== RUNNING PHASE 4B EXPORT VERIFICATION SCRIPT ===\n');

// 1. Test Data Fixtures
const zeroDataFixture = {
  target: 'https://zero-findings.example.com',
  status: 'completed',
  report_metadata: {
    target: 'https://zero-findings.example.com',
    scan_id: 'SCAN-ZERO-001',
    generated_at: '2026-09-01T10:00:00Z',
    pages_crawled: 3,
    pages_discovered: 3,
    duration_seconds: 12.5,
  },
  qa_metrics: {
    target: 'https://zero-findings.example.com',
    duration_seconds: 12.5,
    crawl: { pages_crawled: 3, pages_discovered: 3, pages_failed: 0, max_pages: 5 },
    test_cases: {
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
    findings: {
      total: 0,
      by_severity: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
      by_priority: { P0: 0, P1: 0, P2: 0, P3: 0, P4: 0 },
      by_classification: { confirmed_bug: 0, high_confidence_candidate: 0, needs_manual_review: 0, informational: 0, duplicate: 0 },
      by_regression: { new: 0, fixed: 0, unchanged: 0, worsened: 0, improved: 0 },
    },
    quality_score: { score: 100, grade: 'A', summary: 'Excellent' },
  },
  findings: [],
  test_cases: [],
};

const multiDataFixture = {
  target: 'https://production-app.example.com',
  status: 'completed',
  report_metadata: {
    target: 'https://production-app.example.com',
    scan_id: 'SCAN-MULTI-002',
    generated_at: '2026-09-01T10:30:00Z',
    pages_crawled: 12,
    pages_discovered: 15,
    duration_seconds: 48.75,
  },
  qa_metrics: {
    target: 'https://production-app.example.com',
    duration_seconds: 48.75,
    crawl: {
      pages_crawled: 12,
      pages_discovered: 15,
      pages_failed: 1,
      max_pages: 20,
      responsive_findings: 2,
      device_breakdown: { desktop: 0, iphone: 1, ipad: 1 },
    },
    test_cases: {
      total: 10,
      executed: 8,
      passed: 5,
      failed: 2,
      skipped: 1,
      blocked: 1,
      errored: 1,
      pass_rate: 50.0,
      fail_rate: 20.0,
      skip_rate: 10.0,
      block_rate: 10.0,
      errored_rate: 10.0,
      duration_ms: 12450,
    },
    findings: {
      total: 5,
      by_severity: { critical: 1, high: 1, medium: 2, low: 1, info: 0 },
      by_priority: { P0: 1, P1: 1, P2: 2, P3: 1, P4: 0 },
      by_classification: { confirmed_bug: 2, high_confidence_candidate: 1, needs_manual_review: 2, informational: 0, duplicate: 0 },
      by_regression: { new: 3, fixed: 1, unchanged: 1, worsened: 0, improved: 0 },
    },
    quality_score: { score: 44, grade: 'F', summary: 'Critical Issues Detected' },
  },
  findings: [
    {
      id: 'BUG-101',
      severity: 'critical',
      priority: 'P0',
      title: 'Checkout Payment Button Unclickable',
      classification: 'confirmed_bug',
      confidence: 'high',
      page: 'https://production-app.example.com/checkout',
      description: 'Z-index overlay blocks payment submission button.',
      expected_result: 'Clicking submit triggers payment gateway.',
      actual_result: 'Click event intercepted by invisible modal.',
      recommendation: 'Fix z-index hierarchy on overlay component.',
      affected_pages_count: 1,
    },
    {
      id: 'BUG-102',
      severity: 'high',
      priority: 'P1',
      title: 'XSS Vulnerability in Search Bar',
      classification: 'confirmed_bug',
      confidence: 'high',
      page: 'https://production-app.example.com/search',
      description: 'Unescaped user input reflected in DOM.',
      expected_result: 'Input sanitized and escaped.',
      actual_result: 'Alert script executed.',
      recommendation: 'Sanitize query params with DOMPurify.',
      affected_pages_count: 2,
    },
  ],
  test_cases: [
    {
      id: 'TC-001',
      title: 'Verify User Login with Valid Credentials',
      category: 'Authentication',
      priority: 'P0',
      status: 'passed',
      duration_ms: 1540,
      source_page: 'https://production-app.example.com/login',
      expected_result: 'User redirected to dashboard',
      actual_result: 'Redirected to dashboard successfully',
    },
    {
      id: 'TC-002',
      title: 'Verify Payment Checkout Submission',
      category: 'Checkout',
      priority: 'P0',
      status: 'failed',
      duration_ms: 2200,
      source_page: 'https://production-app.example.com/checkout',
      expected_result: 'Payment completed',
      actual_result: 'Button blocked by overlay',
    },
  ],
};

// 2. Test Excel Workbook Creation
console.log('Testing Excel (.xlsx) generation...');
function generateExcel(results, filename) {
  const qa = results.qa_metrics;
  const meta = results.report_metadata;
  const tc = qa.test_cases;
  const fs = qa.findings;

  const wb = XLSX.utils.book_new();

  const summarySheetData = [
    ['AI QA AGENT — EXECUTIVE SCAN REPORT'],
    [],
    ['GENERAL INFORMATION', ''],
    ['Target URL', qa.target],
    ['Scan ID', meta.scan_id || 'N/A'],
    ['Scan Status', results.status.toUpperCase()],
    ['Generated At', meta.generated_at],
    ['Scan Duration (seconds)', qa.duration_seconds],
    ['Pages Crawled', qa.crawl.pages_crawled],
    ['Pages Discovered', qa.crawl.pages_discovered],
    [],
    ['QUALITY & HEALTH', ''],
    ['Site Health Score', qa.quality_score.score],
    ['Health Grade', qa.quality_score.grade],
    ['Health Summary', qa.quality_score.summary],
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
    ['Total Unique Findings', fs.total, 'P0 (Blocker)', fs.by_priority.P0],
    ['Critical Severity', fs.by_severity.critical, 'P1 (High)', fs.by_priority.P1],
    ['High Severity', fs.by_severity.high, 'P2 (Medium)', fs.by_priority.P2],
    ['Medium Severity', fs.by_severity.medium, 'P3 (Low)', fs.by_priority.P3],
    ['Low Severity', fs.by_severity.low, 'P4 (Trivial)', fs.by_priority.P4],
  ];

  const summaryWs = XLSX.utils.aoa_to_sheet(summarySheetData);
  summaryWs['!cols'] = [{ wch: 30 }, { wch: 25 }, { wch: 25 }, { wch: 15 }];
  XLSX.utils.book_append_sheet(wb, summaryWs, 'Executive Summary');

  if (results.test_cases && results.test_cases.length > 0) {
    const tcHeaders = ['Test ID', 'Status', 'Title', 'Category', 'Priority', 'Duration (ms)', 'Source Page', 'Expected Result', 'Actual Result'];
    const tcRows = results.test_cases.map((t) => [
      t.id,
      t.status.toUpperCase(),
      t.title,
      t.category,
      t.priority,
      t.duration_ms,
      t.source_page,
      t.expected_result,
      t.actual_result,
    ]);
    const tcWs = XLSX.utils.aoa_to_sheet([tcHeaders, ...tcRows]);
    XLSX.utils.book_append_sheet(wb, tcWs, 'Test Cases');
  }

  if (results.findings && results.findings.length > 0) {
    const fHeaders = ['Finding ID', 'Severity', 'Priority', 'Classification', 'Title', 'Page Location', 'Description', 'Recommendation', 'Affected Pages'];
    const fRows = results.findings.map((f) => [
      f.id,
      f.severity.toUpperCase(),
      f.priority.toUpperCase(),
      f.classification,
      f.title,
      f.page,
      f.description,
      f.recommendation,
      f.affected_pages_count,
    ]);
    const fWs = XLSX.utils.aoa_to_sheet([fHeaders, ...fRows]);
    XLSX.utils.book_append_sheet(wb, fWs, 'Defect Findings');
  }

  const filePath = path.join(outputDir, filename);
  XLSX.writeFile(wb, filePath);
  console.log(`Saved Excel workbook: ${filePath}`);

  // Inspect generated workbook
  const readWb = XLSX.readFile(filePath);
  console.log(`  Sheets in ${filename}:`, readWb.SheetNames);
  const summarySheet = readWb.Sheets['Executive Summary'];
  const summaryJson = XLSX.utils.sheet_to_json(summarySheet, { header: 1 });
  console.log(`  Summary Rows Count: ${summaryJson.length}`);

  return readWb;
}

// 3. Test PDF Document Creation
console.log('\nTesting PDF generation...');
function generatePDF(results, filename) {
  const qa = results.qa_metrics;
  const meta = results.report_metadata;
  const tc = qa.test_cases;
  const fs = qa.findings;

  const doc = new jsPDF('p', 'mm', 'a4');

  // Header Banner
  doc.setFillColor(30, 41, 59);
  doc.rect(0, 0, 210, 28, 'F');
  doc.setFontSize(16);
  doc.setTextColor(255, 255, 255);
  doc.text('AI QA AGENT — EXECUTIVE SCAN REPORT', 14, 14);

  // Summary Table
  const overviewBody = [
    ['Target URL', qa.target, 'Site Health Score', `${qa.quality_score.score} / 100 (Grade ${qa.quality_score.grade})`],
    ['Pages Crawled / Discovered', `${qa.crawl.pages_crawled} / ${qa.crawl.pages_discovered}`, 'Scan Duration', `${qa.duration_seconds}s`],
    ['Total Automated Test Cases', `${tc.total}`, 'Test Pass Rate', `${tc.pass_rate}%`],
    ['Total Defects / Findings', `${fs.total}`, 'Critical / High Severity', `${fs.by_severity.critical} / ${fs.by_severity.high}`],
  ];

  const applyAutoTable = autoTable.default || autoTable;
  applyAutoTable(doc, {
    startY: 35,
    head: [['Scan Attribute', 'Value', 'Quality Metric', 'Result']],
    body: overviewBody,
    theme: 'grid',
    headStyles: { fillColor: [30, 41, 59] },
  });

  const tcBody = [
    ['Total Test Cases', tc.total.toString(), tc.total > 0 ? '100.0%' : '0.0%'],
    ['Passed', tc.passed.toString(), `${tc.pass_rate}%`],
    ['Failed', tc.failed.toString(), `${tc.fail_rate}%`],
    ['Skipped', tc.skipped.toString(), `${tc.skip_rate}%`],
    ['Blocked', tc.blocked.toString(), `${tc.block_rate}%`],
    ['Errored', tc.errored.toString(), `${tc.errored_rate}%`],
  ];

  applyAutoTable(doc, {
    startY: doc.lastAutoTable.finalY + 8,
    head: [['Test Execution Metric', 'Count', 'Percentage Rate']],
    body: tcBody,
    theme: 'striped',
    headStyles: { fillColor: [79, 70, 229] },
  });

  if (results.findings && results.findings.length > 0) {
    const fRows = results.findings.map((f) => [
      f.id,
      `${f.severity.toUpperCase()} (${f.priority.toUpperCase()})`,
      `${f.title}\n${f.description}`,
      f.recommendation,
    ]);
    applyAutoTable(doc, {
      startY: doc.lastAutoTable.finalY + 8,
      head: [['ID', 'Severity', 'Issue Description', 'Recommendation']],
      body: fRows,
      theme: 'grid',
      headStyles: { fillColor: [225, 29, 72] },
    });
  }

  const totalPages = doc.internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(150);
    doc.text(`Page ${i} of ${totalPages}`, 196, 292, { align: 'right' });
  }

  const filePath = path.join(outputDir, filename);
  const pdfBytes = doc.output('arraybuffer');
  writeFileSync(filePath, Buffer.from(pdfBytes));
  console.log(`Saved PDF document: ${filePath} (${totalPages} pages)`);
  return { totalPages, filePath };
}

const zeroWb = generateExcel(zeroDataFixture, 'zero_findings_report.xlsx');
const zeroPdf = generatePDF(zeroDataFixture, 'zero_findings_report.pdf');

const multiWb = generateExcel(multiDataFixture, 'multi_findings_report.xlsx');
const multiPdf = generatePDF(multiDataFixture, 'multi_findings_report.pdf');

console.log('\n=== ALL EXPORT GENERATIONS COMPLETED SUCCESSFULLY ===');
