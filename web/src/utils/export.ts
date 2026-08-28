import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';

// Use any to avoid strict type dependencies in this utility file,
// we assume it matches QAReport from page.tsx
export const downloadPDF = (results: any) => {
  if (!results) return;

  const doc = new jsPDF('landscape');
  const target = results.report_metadata?.target || 'Unknown Target';
  const generatedAt = results.report_metadata?.generated_at
    ? new Date(results.report_metadata.generated_at).toLocaleString()
    : new Date().toLocaleString();

  // Title & Header
  doc.setFontSize(22);
  doc.setTextColor(33, 37, 41);
  doc.text('QA Scan Report', 14, 22);

  doc.setFontSize(12);
  doc.setTextColor(108, 117, 125);
  doc.text(`Target: ${target}`, 14, 32);
  doc.text(`Generated: ${generatedAt}`, 14, 38);
  doc.text(`Pages Crawled: ${results.report_metadata?.pages_crawled || 0}`, 14, 44);

  let startY = 55;

  // AI Analysis Degraded Warning
  if (results.report_metadata?.ai_analysis_degraded) {
    doc.setFontSize(11);
    doc.setTextColor(220, 53, 69); // Red
    doc.text(
      `Warning: AI analysis was incomplete. ${
        results.report_metadata.ai_analysis_failures || 0
      } findings could not be analysed by the model.`,
      14,
      startY
    );
    startY += 10;
  }

  // Summary Table
  const summary = results.summary || {};
  const severity = results.severity || {};
  const tcm = results.test_case_metrics;
  
  const summaryBody = [
    ['Total Findings', summary.total_candidates?.toString() || '0'],
    ['Needs Review', summary.manual_review?.toString() || '0'],
    ['Critical / High Severity', `${severity.critical || 0} / ${severity.high || 0}`],
    ['Medium / Low / Info', `${severity.medium || 0} / ${severity.low || 0} / ${severity.info || 0}`],
  ];
  if (tcm) {
    summaryBody.push(['Test Cases Executed / Total', `${tcm.executed} / ${tcm.total}`]);
    summaryBody.push(['Test Cases Passed / Failed', `${tcm.passed} / ${tcm.failed}`]);
  }
  
  autoTable(doc, {
    startY,
    head: [['Metric', 'Value']],
    body: summaryBody,
    theme: 'grid',
    headStyles: { fillColor: [79, 70, 229] }, // Indigo
    styles: { fontSize: 11 },
  });

  // Bug Triage Summary Table
  const triage = results.triage_metrics || {};
  if (Object.keys(triage).length > 0) {
    const triageBody = [
      ['Confirmed Bugs', triage.confirmed_bug?.toString() || '0'],
      ['High Confidence Candidates', triage.high_confidence_candidate?.toString() || '0'],
      ['Needs Manual Review', triage.needs_manual_review?.toString() || '0'],
      ['Duplicates', triage.duplicate?.toString() || '0'],
      ['Priority (P0/P1/P2/P3/P4)', `${triage.priority?.P0||0} / ${triage.priority?.P1||0} / ${triage.priority?.P2||0} / ${triage.priority?.P3||0} / ${triage.priority?.P4||0}`],
    ];
    
    if (triage.regression_summary) {
      const rs = triage.regression_summary;
      triageBody.push(['Regression (New/Fixed/Unchanged/Worsened/Improved)', `${rs.new||0} / ${rs.fixed||0} / ${rs.unchanged||0} / ${rs.worsened||0} / ${rs.improved||0}`]);
    }
    
    autoTable(doc, {
      startY: (doc as any).lastAutoTable.finalY + 15,
      head: [['AI Bug Triage Metrics', 'Value']],
      body: triageBody,
      theme: 'grid',
      headStyles: { fillColor: [139, 92, 246] }, // Violet
      styles: { fontSize: 11 },
    });
  }

  // Findings Table
  const findings = results.findings || [];
  if (findings.length > 0) {
    const tableData = findings.map((f: any) => [
      f.id,
      f.severity.toUpperCase(),
      f.title,
      `${(f.description || f.manual_verification || '').substring(0, 150)}...
      
Expected: ${f.expected_result || 'Not specified.'}
Actual: ${f.actual_result || 'Not specified.'}
Reproduction: ${f.reproduction?.steps ? f.reproduction.steps.join(' -> ') : 'None'}`,
      f.affected_pages_count?.toString() || '1',
      f.page || 'N/A'
    ]);

    autoTable(doc, {
      startY: (doc as any).lastAutoTable.finalY + 15,
      head: [['ID', 'Severity', 'Issue', 'Description', 'Affected Pages', 'Example Page']],
      body: tableData,
      theme: 'striped',
      headStyles: { fillColor: [16, 185, 129] }, // Emerald
      styles: { fontSize: 9, cellPadding: 3 },
      columnStyles: {
        0: { cellWidth: 20 },
        1: { cellWidth: 25 },
        2: { cellWidth: 50 },
        3: { cellWidth: 120 },
        4: { cellWidth: 20 },
      },
      didDrawPage: (data) => {
        // Add Header to subsequent pages
        if (data.pageNumber > 1) {
          doc.setFontSize(10);
          doc.setTextColor(150);
          doc.text(`QA Scan Report - ${target}`, data.settings.margin.left, 10);
        }
      }
    });
  } else {
    doc.setFontSize(12);
    doc.setTextColor(40, 167, 69);
    doc.text('No deterministic bugs or AI candidates found! Your site looks healthy.', 14, (doc as any).lastAutoTable.finalY + 20);
  }

  // Footer with Page Numbers
  const pageCount = (doc as any).internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(10);
    doc.setTextColor(150);
    doc.text(
      `Page ${i} of ${pageCount}`,
      doc.internal.pageSize.width / 2,
      doc.internal.pageSize.height - 10,
      { align: 'center' }
    );
  }

  doc.save(`QA_Report_${target.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.pdf`);
};

export const downloadExcel = (results: any) => {
  if (!results) return;

  const target = results.report_metadata?.target || 'Unknown Target';
  const findings = results.findings || [];
  
  const summaryData = [
    { Metric: 'Target', Value: target },
    { Metric: 'Generated At', Value: results.report_metadata?.generated_at || new Date().toISOString() },
    { Metric: 'Pages Crawled', Value: results.report_metadata?.pages_crawled || 0 },
    { Metric: 'Total Findings', Value: results.summary?.total_candidates || 0 },
    { Metric: 'Needs Review', Value: results.summary?.manual_review || 0 },
    { Metric: 'Critical Severity', Value: results.severity?.critical || 0 },
    { Metric: 'High Severity', Value: results.severity?.high || 0 },
    { Metric: 'Medium Severity', Value: results.severity?.medium || 0 },
    { Metric: 'Low Severity', Value: results.severity?.low || 0 },
    { Metric: 'Info Severity', Value: results.severity?.info || 0 },
  ];
  
  if (results.triage_metrics) {
    const tm = results.triage_metrics;
    summaryData.push({ Metric: 'Triage - Confirmed Bugs', Value: tm.confirmed_bug || 0 });
    summaryData.push({ Metric: 'Triage - Candidates', Value: tm.high_confidence_candidate || 0 });
    summaryData.push({ Metric: 'Triage - Manual Review', Value: tm.needs_manual_review || 0 });
    summaryData.push({ Metric: 'Triage - P0', Value: tm.priority?.P0 || 0 });
    summaryData.push({ Metric: 'Triage - P1', Value: tm.priority?.P1 || 0 });
    summaryData.push({ Metric: 'Triage - P2', Value: tm.priority?.P2 || 0 });
    summaryData.push({ Metric: 'Triage - P3', Value: tm.priority?.P3 || 0 });
  }

  if (results.report_metadata?.ai_analysis_degraded) {
    summaryData.push({ Metric: 'Warning', Value: `AI analysis was incomplete. ${results.report_metadata.ai_analysis_failures || 0} findings could not be analysed.` });
  }

  // Prepare Findings Data
  const findingsData = findings.map((f: any) => ({
    'ID': f.id,
    'Severity': f.severity.toUpperCase(),
    'Title': f.title,
    'Classification': f.classification || 'N/A',
    'Confidence': f.confidence || 'N/A',
    'Description': f.description || f.manual_verification || '',
    'Expected Result': f.expected_result || 'Not specified.',
    'Actual Result': f.actual_result || 'Not specified.',
    'Reproduction Steps': f.reproduction?.steps ? f.reproduction.steps.join('\n') : '',
    'Device': f.reproduction?.device || '',
    'Viewport': f.reproduction?.viewport ? `${f.reproduction.viewport.width}x${f.reproduction.viewport.height}` : '',
    'Screenshot': f.evidence?.screenshot || (f.screenshots && f.screenshots.length > 0 ? f.screenshots[0] : ''),
    'Recommendation': f.recommendation || '',
    'Affected Pages Count': f.affected_pages_count || 1,
    'Example Page Crawled': f.page || 'N/A'
  }));

  // Create Workbooks & Sheets
  const wb = XLSX.utils.book_new();
  
  const summaryWs = XLSX.utils.json_to_sheet(summaryData);
  XLSX.utils.book_append_sheet(wb, summaryWs, 'Summary');
  
  if (results.triage_metrics) {
    const triageData = findings.map((f: any) => ({
      'ID': f.id,
      'Classification': f.classification || 'N/A',
      'Severity': f.severity.toUpperCase(),
      'Confidence': f.confidence || 'N/A',
      'Priority': f.priority || 'P3',
      'Root Cause Category': f.root_cause?.category?.replace('_', ' ') || 'N/A',
      'User Impact': f.user_impact || 'unknown',
      'Total Occurrences': f.occurrence_count || 1,
      'Affected Pages': f.affected_pages_count || 1,
      'Recommendation': f.recommendation || '',
      'Regression Status': f.regression_status || 'NEW'
    }));
    const triageWs = XLSX.utils.json_to_sheet(triageData);
    XLSX.utils.book_append_sheet(wb, triageWs, 'Bug Triage');
  }

  if (findingsData.length > 0) {
    const findingsWs = XLSX.utils.json_to_sheet(findingsData);
    XLSX.utils.book_append_sheet(wb, findingsWs, 'Findings');
  }

  if (results.test_cases && results.test_cases.length > 0) {
    const testCasesData = results.test_cases.map((tc: any) => ({
      'ID': tc.id,
      'Title': tc.title,
      'Category': tc.category,
      'Priority': tc.priority,
      'Status': (tc.status || tc.execution_policy || 'manual_review').toUpperCase(),
      'Source Page': tc.source_page || '',
      'Expected Result': tc.expected_result || '',
      'Actual Result': tc.actual_result || '',
      'Screenshot': tc.evidence?.screenshot || ''
    }));
    const testCasesWs = XLSX.utils.json_to_sheet(testCasesData);
    XLSX.utils.book_append_sheet(wb, testCasesWs, 'Test Cases');
  }

  // Save the file
  XLSX.writeFile(wb, `QA_Report_${target.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.xlsx`);
};
