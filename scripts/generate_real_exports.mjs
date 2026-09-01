import * as fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import * as XLSX from '../web/node_modules/xlsx/xlsx.mjs';
import { jsPDF } from '../web/node_modules/jspdf/dist/jspdf.node.min.js';
import autoTable from '../web/node_modules/jspdf-autotable/dist/jspdf.plugin.autotable.js';

XLSX.set_fs(fs);
const applyAutoTable = autoTable.default || autoTable;

const scanJson = JSON.parse(fs.readFileSync('./results/real_scan_export/real_scan_result.json', 'utf-8'));
const results = scanJson.results;
const qa = results.qa_metrics;
const meta = results.report_metadata;
const tc = qa.test_cases;
const fs_metrics = qa.findings;

console.log('=== REAL SCAN EXPORT GENERATION ===');
console.log('Target:', qa.target);
console.log('Quality Score:', qa.quality_score.score, qa.quality_score.grade);
console.log('Test Cases:', tc.total, 'Passed:', tc.passed, 'Pass Rate:', tc.pass_rate + '%');
console.log('Findings:', fs_metrics.total);

// Generate Excel
const wb = XLSX.utils.book_new();
const summarySheetData = [
  ['AI QA AGENT — EXECUTIVE SCAN REPORT'],
  [],
  ['GENERAL INFORMATION', ''],
  ['Target URL', qa.target],
  ['Scan ID', scanJson.id || 'N/A'],
  ['Scan Status', scanJson.status.toUpperCase()],
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
];

const summaryWs = XLSX.utils.aoa_to_sheet(summarySheetData);
summaryWs['!cols'] = [{ wch: 30 }, { wch: 25 }, { wch: 25 }, { wch: 15 }];
XLSX.utils.book_append_sheet(wb, summaryWs, 'Executive Summary');

if (results.test_cases && results.test_cases.length > 0) {
  const tcHeaders = ['Test ID', 'Status', 'Title', 'Category', 'Priority', 'Duration (ms)', 'Source Page', 'Expected Result', 'Actual Result'];
  const tcRows = results.test_cases.map((t) => [
    t.id,
    (t.status || t.execution_policy || 'SKIPPED').toUpperCase(),
    t.title,
    t.category || 'Functional',
    t.priority || 'P3',
    typeof t.duration_ms === 'number' ? t.duration_ms : 0,
    t.source_page || '',
    t.expected_result || 'Expected pass',
    t.actual_result || 'N/A',
  ]);
  const tcWs = XLSX.utils.aoa_to_sheet([tcHeaders, ...tcRows]);
  XLSX.utils.book_append_sheet(wb, tcWs, 'Test Cases');
}

const excelPath = './results/real_scan_export/real_scan_report.xlsx';
XLSX.writeFile(wb, excelPath);
console.log('Saved Excel:', excelPath);

// Generate PDF
const doc = new jsPDF('p', 'mm', 'a4');
doc.setFillColor(30, 41, 59);
doc.rect(0, 0, 210, 28, 'F');
doc.setFontSize(16);
doc.setTextColor(255, 255, 255);
doc.text('AI QA AGENT — EXECUTIVE SCAN REPORT', 14, 14);

const overviewBody = [
  ['Target URL', qa.target, 'Site Health Score', qa.quality_score.score + ' / 100 (Grade ' + qa.quality_score.grade + ')'],
  ['Pages Crawled / Discovered', qa.crawl.pages_crawled + ' / ' + qa.crawl.pages_discovered, 'Scan Duration', qa.duration_seconds + 's'],
  ['Total Automated Test Cases', '' + tc.total, 'Test Pass Rate', tc.pass_rate + '%'],
  ['Total Defects / Findings', '' + fs_metrics.total, 'Critical / High Severity', fs_metrics.by_severity.critical + ' / ' + fs_metrics.by_severity.high],
];

applyAutoTable(doc, {
  startY: 35,
  head: [['Scan Attribute', 'Value', 'Quality Metric', 'Result']],
  body: overviewBody,
  theme: 'grid',
  headStyles: { fillColor: [30, 41, 59] },
});

const tcBody = [
  ['Total Test Cases', tc.total.toString(), tc.total > 0 ? '100.0%' : '0.0%'],
  ['Passed', tc.passed.toString(), tc.pass_rate + '%'],
  ['Failed', tc.failed.toString(), tc.fail_rate + '%'],
  ['Skipped', tc.skipped.toString(), tc.skip_rate + '%'],
  ['Blocked', tc.blocked.toString(), tc.block_rate + '%'],
  ['Errored', tc.errored.toString(), tc.errored_rate + '%'],
];

applyAutoTable(doc, {
  startY: doc.lastAutoTable.finalY + 8,
  head: [['Test Execution Metric', 'Count', 'Percentage Rate']],
  body: tcBody,
  theme: 'striped',
  headStyles: { fillColor: [79, 70, 229] },
});

if (results.test_cases && results.test_cases.length > 0) {
  const tcRows = results.test_cases.map((t) => [
    t.id,
    (t.status || t.execution_policy || 'SKIPPED').toUpperCase(),
    t.title,
    t.duration_ms ? t.duration_ms + 'ms' : '0ms',
    t.expected_result,
    t.actual_result || 'N/A',
  ]);
  applyAutoTable(doc, {
    startY: doc.lastAutoTable.finalY + 8,
    head: [['ID', 'Status', 'Test Case Title', 'Duration', 'Expected Result', 'Actual Result']],
    body: tcRows,
    theme: 'grid',
    headStyles: { fillColor: [16, 185, 129] },
  });
}

const totalPages = doc.internal.getNumberOfPages();
for (let i = 1; i <= totalPages; i++) {
  doc.setPage(i);
  doc.setFontSize(8);
  doc.setTextColor(150);
  doc.text('Page ' + i + ' of ' + totalPages, 196, 292, { align: 'right' });
}

const pdfPath = './results/real_scan_export/real_scan_report.pdf';
const pdfBytes = doc.output('arraybuffer');
fs.writeFileSync(pdfPath, Buffer.from(pdfBytes));
console.log('Saved PDF:', pdfPath, '(' + totalPages + ' pages)');
