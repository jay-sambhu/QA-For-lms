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

export type QAFinding = Finding;
export type TestCase = NonNullable<QAReport['test_cases']>[number];
export type CrossDeviceMetrics = NonNullable<QAReport['report_metadata']['cross_device_metrics']>;

export interface QualityScore {
  score: number;
  grade: string;
  summary: string;
}

export interface DeviceBreakdown {
  desktop: number;
  iphone: number;
  ipad: number;
}

export interface RegressionSummary {
  new: number;
  fixed: number;
  unchanged: number;
  worsened: number;
  improved: number;
}

export interface QAReport {
  report_metadata: {
    generated_at: string;
    source_report?: string;
    target: string;
    pages_crawled: number;
    crawl_partial?: boolean;
    auth_wall_pages?: number;
    ai_analysis_failures?: number;
    ai_analysis_degraded?: boolean;
    interactive_metrics?: {
      elements_discovered: number;
      interactions_attempted: number;
      passed: number;
      failed: number;
      manual_review: number;
    } | null;
    cross_device_metrics?: {
      devices_tested: number;
      pages_tested?: number;
      pages_crawled?: number;
      pages_discovered?: number;
      pages_failed?: number;
      responsive_findings: number;
      device_breakdown: DeviceBreakdown;
    };
    quality_score?: QualityScore;
  };
  summary: {
    total_candidates: number;
    confirmed_bugs: number;
    potential_issues: number;
    manual_review: number;
    informational: number;
    ignored: number;
    analysis_failures?: number;
    regression_summary?: Partial<RegressionSummary>;
  };
  qa_metrics?: {
    target?: string;
    generated_at?: string;
    quality_score?: number | QualityScore;
    letter_grade?: string;
    verdict?: string;
    duration_seconds?: number;
    test_cases?: {
      total: number;
      passed: number;
      failed: number;
      skipped?: number;
      blocked?: number;
      errored?: number;
      executed?: number;
      pass_rate?: number;
      fail_rate?: number;
      skip_rate?: number;
      block_rate?: number;
      errored_rate?: number;
      duration_ms?: number;
    };
    findings?: {
      total?: number;
      confirmed_bugs?: number;
      critical?: number;
      high?: number;
      medium?: number;
      low?: number;
      info?: number;
      by_classification?: {
        confirmed_bug?: number;
        high_confidence_candidate?: number;
        needs_manual_review?: number;
        expected_behavior?: number;
        informational?: number;
        duplicate?: number;
        ignored?: number;
      };
      by_severity?: Record<string, number>;
      by_priority?: Record<string, number>;
      by_regression?: Record<string, number>;
      critical_high?: number;
      analysis_failures?: number;
    };
    crawl?: {
      pages_crawled: number;
      pages_attempted?: number;
      pages_discovered?: number;
      pages_failed?: number;
      max_pages?: number;
      http_errors?: number;
      network_failures?: number;
      console_errors?: number;
      devices_tested?: number;
      responsive_findings?: number;
      device_breakdown?: DeviceBreakdown;
    };
    duration?: {
      duration_seconds?: number;
      formatted_duration?: string;
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
    regression_summary: RegressionSummary;
  };
  severity: Record<Severity, number>;
  findings: Finding[];
  test_cases?: Array<{
    id: string;
    title?: string;
    description?: string;
    objective?: string;
    issue_level?: 'critical' | 'high' | 'medium' | 'low' | string;
    category?: string;
    priority?: string;
    source_page?: string;
    steps?: Array<string | { step_index?: number; action?: string; target_selector?: string; value?: string; expected_result?: string }>;
    execution_policy?: string;
    status?: string;
    expected_result?: string;
    actual_result?: string;
    exact_result?: string;
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
    skipped?: number;
    errored?: number;
    pass_rate?: number;
    fail_rate?: number;
    skip_rate?: number;
    block_rate?: number;
    errored_rate?: number;
    duration_ms?: number;
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

/** Body of GET /api/v1/scans/{id}. */
export interface ScanStatusResponse {
  id: string;
  user_id?: string;
  url?: string;
  status: ScanStatus;
  is_authenticated?: boolean;
  created_at?: string | null;
  completed_at?: string | null;
  progress?: ProgressPayload | null;
  results?: QAReport | null;
  has_cloud_report?: boolean;
}
