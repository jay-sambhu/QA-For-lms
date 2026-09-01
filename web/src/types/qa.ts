export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface Finding {
  id: string;
  classification: string;
  severity: Severity;
  confidence: string;
  title: string;
  page: string;
  url: string;
  description: string;
  recommendation: string;
  expected_result?: string;
  actual_result?: string;
  manual_verification?: string;
  affected_pages_count?: number;
  occurrence_count?: number;
  priority?: string;
  root_cause?: { category?: string; summary?: string };
  user_impact?: string;
  regression_status?: string;
  screenshots?: string[];
  evidence?: {
    http_errors?: unknown[];
    console_errors?: unknown[];
    network_failures?: unknown[];
    screenshot?: string;
  };
  reproduction?: {
    url?: string;
    device?: string;
    viewport?: { width: number; height: number };
    steps?: string[];
  };
}

export interface QAReport {
  report_metadata: {
    generated_at: string;
    source_report?: string;
    target: string;
    pages_crawled: number;
    ai_analysis_failures?: number;
    ai_analysis_degraded?: boolean;
    interactive_metrics?: {
      elements_discovered: number;
      interactions_attempted: number;
      passed: number;
      failed: number;
      manual_review: number;
    };
    cross_device_metrics?: {
      devices_tested: number;
      pages_tested: number;
      responsive_findings: number;
      device_breakdown: {
        desktop: number;
        iphone: number;
        ipad: number;
      };
    };
  };
  summary: {
    total_candidates: number;
    confirmed_bugs: number;
    potential_issues: number;
    manual_review: number;
    informational: number;
    ignored: number;
    analysis_failures?: number;
  };
  qa_metrics?: {
    quality_score: number;
    letter_grade: string;
    verdict: string;
    test_cases: {
      total: number;
      passed: number;
      failed: number;
      skipped: number;
      blocked: number;
      errored: number;
      pass_rate: number;
      fail_rate: number;
    };
    findings: {
      total: number;
      confirmed_bugs: number;
      critical: number;
      high: number;
      medium: number;
      low: number;
      info: number;
    };
    crawl: {
      pages_crawled: number;
      pages_attempted: number;
      http_errors: number;
      network_failures: number;
      console_errors: number;
      devices_tested: number;
    };
    duration: {
      duration_seconds: number;
      formatted_duration: string;
    };
  };
  triage_metrics?: {
    confirmed_bug: number;
    high_confidence_candidate: number;
    needs_manual_review: number;
    expected_behavior: number;
    informational: number;
    duplicate: number;
    priority: { P0: number; P1: number; P2: number; P3: number; P4: number };
    regression_summary: { new: number; fixed: number; unchanged: number; worsened: number; improved: number };
  };
  severity: Record<Severity, number>;
  findings: Finding[];
  test_cases?: Array<{
    id: string;
    title?: string;
    description?: string;
    category?: string;
    priority?: string;
    source_page?: string;
    steps?: string[];
    execution_policy?: string;
    status?: string;
    expected_result?: string;
    actual_result?: string;
    evidence?: unknown;
    duration_ms?: number;
  }>;
  test_case_metrics?: {
    total: number;
    executed: number;
    passed: number;
    failed: number;
    blocked: number;
    manual_review: number;
  };
}

export interface ProgressPayload {
  percent: number;
  message: string;
  stage?: string;
  active_device?: string;
  active_url?: string;
  page_current?: number;
  page_total?: number;
}

export type ScanStatus = 'pending' | 'running' | 'completed' | 'failed' | 'error' | 'cancelled' | '';
