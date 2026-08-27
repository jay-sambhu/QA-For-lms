#!/usr/bin/env python3
"""
QA Finding Classifier - Deterministic bug detection and classification.

Reads crawler results and produces structured QA findings with:
- Intelligent deduplication at page level
- Root-cause grouping across pages
- HTTP status classification
- Network failure analysis
- Console error categorization
- First-party vs third-party detection
"""

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict


def normalize_host(value):
    """
    Reduce a URL or bare host to a comparable hostname.

    Lowercases, strips a trailing dot, drops any port/userinfo, and removes a
    leading "www." so that apex and www hosts compare equal.
    """
    if not value:
        return ''

    text = str(value).strip()
    if not text:
        return ''

    # Accept both full URLs and bare hosts such as "example.com:8080".
    host = urlparse(text).hostname if '//' in text else None
    if host is None:
        # urlparse needs a scheme to populate `hostname`, so add one.
        host = urlparse(f'//{text}').hostname or ''

    host = host.lower().rstrip('.')
    return host[4:] if host.startswith('www.') else host


class QAFindingClassifier:
    """Classifies and deduplicates QA findings from crawler results."""

    # Third-party domains to deprioritize
    THIRD_PARTY_DOMAINS = {
        'google-analytics.com',
        'googletagmanager.com',
        'facebook.com',
        'connect.facebook.net',
        'analytics.google.com',
        'stats.g.doubleclick.net',
        'cdn.segment.com',
        'api.segment.io',
        'js.intercomcdn.com',
        'intercom.io',
        'widget.intercom.io',
        'api.intercom.io',
        'zendesk.com',
        'zdassets.com',
        'hotjar.com',
        'hj.hotjar.com',
        'static.hotjar.com',
    }

    # Network failure reasons to ignore
    IGNORABLE_FAILURES = {
        'net::ERR_ABORTED',  # Normal cancellation during navigation
        'net::ERR_BLOCKED_BY_RESPONSE',  # CORB (Cross-Origin Read Blocking)
    }

    def __init__(self, target_domain, crawl_result):
        """
        Initialize the classifier.

        Args:
            target_domain: The main domain being tested (e.g. 'dplms.com').
                A full URL is also accepted.
            crawl_result: The crawler result dictionary
        """
        self.target_domain = normalize_host(target_domain)
        self.crawl_result = crawl_result or {}
        self.findings = []
        self.root_cause_candidates = []
        self.finding_id_counter = 0
        self.candidate_id_counter = 0

    def is_first_party(self, url):
        """Check if a URL belongs to the first-party domain (or a subdomain)."""
        host = normalize_host(url)
        if not host or not self.target_domain:
            return False

        return host == self.target_domain or host.endswith('.' + self.target_domain)

    def is_third_party(self, url):
        """Check if a URL is from a known third-party analytics/support vendor."""
        host = normalize_host(url)
        if not host:
            return False

        # Match the host exactly or as a proper subdomain. A substring test
        # would wrongly classify hosts like "notfacebook.com.example.net".
        for third_party in self.THIRD_PARTY_DOMAINS:
            candidate = normalize_host(third_party)
            if host == candidate or host.endswith('.' + candidate):
                return True

        return False

    def classify_http_status(self, status):
        """Classify HTTP status code."""
        if not isinstance(status, int):
            return {
                'severity': 'info',
                'category': 'unknown',
                'description': 'Unknown HTTP status'
            }

        if status >= 500:
            return {
                'severity': 'high',
                'category': 'server_error',
                'description': f'{status} Server Error'
            }
        elif status == 404:
            return {
                'severity': 'high',
                'category': '404_not_found',
                'description': '404 Not Found'
            }
        elif status in (401, 403):
            return {
                'severity': 'medium',
                'category': 'auth_error',
                'description': f'{status} Requires Investigation'
            }
        elif status == 400:
            return {
                'severity': 'medium',
                'category': 'bad_request',
                'description': '400 Bad Request'
            }
        elif status == 429:
            return {
                'severity': 'low',
                'category': 'rate_limit',
                'description': '429 Rate Limit'
            }
        elif 300 <= status < 400:
            return {
                'severity': 'info',
                'category': 'redirect',
                'description': f'{status} Redirect'
            }
        elif 200 <= status < 300:
            return {
                'severity': 'info',
                'category': 'success',
                'description': f'{status} Success'
            }
        else:
            return {
                'severity': 'info',
                'category': 'other',
                'description': f'{status} Other'
            }

    def should_ignore_network_failure(self, failure):
        """
        Check if a network failure should be ignored.

        `failure` may be None: Playwright reports no reason string for some
        aborted requests, so coerce before comparing.
        """
        reason = (failure or '').strip()
        if not reason:
            # An empty reason carries no signal; treat it as ignorable rather
            # than emitting a finding with no diagnostic content.
            return True

        return any(
            reason == ignorable or reason.startswith(ignorable)
            for ignorable in self.IGNORABLE_FAILURES
        )

    def get_page_title(self, page_url):
        """Get the page title from crawl pages."""
        for page in self.crawl_result.get('pages', []):
            if page.get('url') == page_url:
                return page.get('title') or ''
        return ''

    def get_page_screenshot(self, page_url):
        """Get the page screenshot from crawl pages."""
        for page in self.crawl_result.get('pages', []):
            if page.get('url') == page_url:
                return page.get('screenshot') or ''
        return ''

    def find_matching_console_errors(self, http_error):
        """Find console errors on the same page that reference the same status."""
        matching = []
        status = http_error.get('status')
        page = http_error.get('page')

        if status is None:
            return matching

        # Only accept phrasings where the number is unambiguously an HTTP
        # status. A bare `str(status) in text` test produced false matches on
        # things like "500ms" or an unrelated id containing "404".
        status_patterns = [
            re.compile(rf'status\s+(?:code\s+)?of\s+{status}\b', re.I),
            re.compile(rf'status\s*(?:code)?\s*[:=]\s*{status}\b', re.I),
            re.compile(rf'\bhttp\s*{status}\b', re.I),
            re.compile(rf'\b{status}\s+\(?(?:not found|forbidden|unauthorized'
                       rf'|bad request|internal server error)\)?', re.I),
        ]

        for console_error in self.crawl_result.get('console_errors', []):
            if console_error.get('page') != page:
                continue

            error_text = console_error.get('text') or ''
            if any(pattern.search(error_text) for pattern in status_patterns):
                matching.append(console_error)

        return matching

    def generate_finding_id(self):
        """Generate a unique finding ID."""
        self.finding_id_counter += 1
        return f"BUG-{self.finding_id_counter:03d}"

    def generate_candidate_id(self):
        """Generate a unique root-cause candidate ID."""
        self.candidate_id_counter += 1
        return f"CANDIDATE-{self.candidate_id_counter:03d}"

    def generate_root_cause_key(self, url, status, method=''):
        """
        Generate a deterministic root-cause grouping key.

        The host is lowercased (hosts are case-insensitive) but the path and
        query are left as-is, because those *are* case-sensitive and folding
        them merges genuinely different endpoints such as /User and /user.
        """
        parsed = urlparse(url or '')
        host = normalize_host(url)
        tail = parsed.path or ''
        if parsed.query:
            tail = f'{tail}?{parsed.query}'

        scheme = (parsed.scheme or '').lower()
        return f'{scheme}://{host}{tail}|{status}|{(method or "").upper()}'

    def classify_http_errors(self):
        """Classify HTTP errors into findings."""
        # Group errors by page + url + status for deduplication
        error_groups = defaultdict(list)
        
        for http_error in self.crawl_result.get('http_errors', []):
            page = http_error.get('page', '')
            url = http_error.get('url', '')
            status = http_error.get('status')
            
            # Create a deduplication key
            key = (page, url, status)
            error_groups[key].append(http_error)
        
        # Process each unique error group
        for (page, url, status), errors in error_groups.items():
            classification = self.classify_http_status(status)

            # A non-int status (null in a hand-edited or older crawl file)
            # cannot be compared with < or >= below. classify_http_status
            # already tolerates it; the comparisons here did not.
            numeric_status = status if isinstance(status, int) else None

            # Determine confidence and severity based on first-party status
            is_first_party_request = self.is_first_party(url)
            is_third_party_request = self.is_third_party(url)

            # Adjust severity for third-party
            severity = classification['severity']
            if is_third_party_request:
                # Deprioritize third-party errors (except 5xx which are always high)
                if numeric_status is not None and numeric_status < 500:
                    severity = 'info'

            # Determine confidence
            if numeric_status is None:
                confidence = 'low'
            elif numeric_status >= 500:
                confidence = 'high'
            elif numeric_status == 404:
                confidence = 'high'
            elif numeric_status in (401, 403):
                confidence = 'medium'
            else:
                confidence = 'medium'
            
            # Find matching console errors
            matching_console = self.find_matching_console_errors(errors[0])
            
            # Get page title and screenshot
            page_title = self.get_page_title(page)
            screenshot = self.get_page_screenshot(page)
            
            # Generate description
            description = self._generate_http_description(
                status, url, is_first_party_request
            )
            
            # Generate root-cause key for grouping
            method = errors[0].get('method', '')
            root_cause_key = self.generate_root_cause_key(url, status, method)
            
            # Create finding
            finding = {
                'id': self.generate_finding_id(),
                'type': 'http_error',
                'severity': severity,
                'confidence': confidence,
                'page': page,
                'url': url,
                'status': status,
                'method': method,
                'resource_type': errors[0].get('resource_type', ''),
                'title': page_title,
                'description': description,
                'root_cause_key': root_cause_key,
                'evidence': {
                    'http_errors': errors,
                    'console_errors': matching_console,
                    'network_failures': [],
                },
                'screenshot': screenshot,
                'first_party': is_first_party_request,
                'deduplicated_count': len(errors),
            }
            
            self.findings.append(finding)

    def _generate_http_description(self, status, url, is_first_party):
        """Generate a descriptive message for an HTTP error."""
        parsed = urlparse(url or '')

        # Compare whole path segments. A substring test called /therapy and
        # /rapid "API" endpoints.
        segments = {segment.lower() for segment in parsed.path.split('/') if segment}
        is_api = bool(segments & {'api', 'apis', 'graphql', 'rest', 'v1', 'v2', 'v3'})
        resource_type = 'API' if is_api else 'Resource'
        
        if status >= 500:
            return f"{resource_type} returned {status} server error"
        elif status == 404:
            return f"{resource_type} not found"
        elif status == 401:
            return f"Potential authentication issue with {resource_type} (401)"
        elif status == 403:
            return f"Potential access control issue with {resource_type} (403)"
        elif status == 400:
            return f"Potential malformed request to {resource_type}"
        elif status == 429:
            return f"Rate limiting on {resource_type}"
        else:
            return f"{resource_type} returned HTTP {status}"

    def classify_console_errors(self):
        """Classify console errors into findings."""
        # Track which console errors are already covered by HTTP errors
        covered_console_errors = set()
        for finding in self.findings:
            for console_error in finding['evidence'].get('console_errors', []):
                error_text = console_error.get('text', '')
                page = console_error.get('page', '')
                covered_console_errors.add((page, error_text))
        
        # Group uncovered console errors by page + error pattern
        error_groups = defaultdict(list)
        
        for console_error in self.crawl_result.get('console_errors', []):
            page = console_error.get('page', '')
            text = console_error.get('text', '')
            
            # Skip if already covered by HTTP error
            if (page, text) in covered_console_errors:
                continue
            
            # Skip third-party tracking errors
            if self._is_tracking_error(text):
                continue
            
            # Skip expected authentication errors
            if self._is_expected_auth_error(text):
                continue
            
            # Create a deduplication key based on error pattern
            key = (page, self._error_pattern(text))
            error_groups[key].append(console_error)
        
        # Process each unique error group
        for (page, pattern), errors in error_groups.items():
            error_text = errors[0].get('text', '')

            classification = self._classify_console_error(error_text)

            if classification['ignore']:
                continue

            page_title = self.get_page_title(page)
            screenshot = self.get_page_screenshot(page)

            finding = {
                'id': self.generate_finding_id(),
                'type': 'console_error',
                'severity': classification['severity'],
                'confidence': classification['confidence'],
                'page': page,
                'url': '',
                'error_text': error_text,
                'error_category': classification['category'],
                'title': page_title,
                'description': classification['description'],
                # Keyed on the normalized message so the same console error is
                # grouped into one root cause across every page it appears on.
                'root_cause_key': f"console_error|{classification['category']}|{pattern}",
                'evidence': {
                    'http_errors': [],
                    'console_errors': errors,
                    'network_failures': [],
                },
                'screenshot': screenshot,
                'first_party': True,
                'deduplicated_count': len(errors),
            }

            self.findings.append(finding)

    def _error_pattern(self, error_text):
        """Extract a pattern from error text for deduplication."""
        # Remove specific values and timestamps
        pattern = (error_text or '').lower()
        # Remove URLs and IDs so the same error with different ids collapses.
        pattern = re.sub(r'https?://[^\s]+', '', pattern)
        pattern = re.sub(r'\d+', '', pattern)
        pattern = re.sub(r'\s+', ' ', pattern)
        return pattern.strip()

    def _is_tracking_error(self, text):
        """Check if an error is from tracking/analytics."""
        tracking_keywords = [
            'analytics',
            'google-analytics',
            'googletagmanager',
            'facebook pixel',
            'intercom',
            'hotjar',
            'segment',
            'mixpanel',
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in tracking_keywords)

    def _is_expected_auth_error(self, text):
        """Check if an error is an expected authentication rejection."""
        text_lower = text.lower()
        return 'status of 401' in text_lower

    def _classify_console_error(self, error_text):
        """Classify a console error message."""
        text_lower = error_text.lower()
        
        # Runtime errors
        if any(err in text_lower for err in ['typeerror', 'referenceerror', 'syntaxerror']):
            return {
                'ignore': False,
                'severity': 'high',
                'confidence': 'high',
                'category': 'javascript_exception',
                'description': 'JavaScript runtime error detected',
            }
        
        # Failed to load resource
        if 'failed to load resource' in text_lower:
            return {
                'ignore': False,
                'severity': 'medium',
                'confidence': 'medium',
                'category': 'resource_load_failure',
                'description': 'Failed to load application resource',
            }
        
        # Uncaught error
        if 'uncaught' in text_lower:
            return {
                'ignore': False,
                'severity': 'high',
                'confidence': 'high',
                'category': 'uncaught_exception',
                'description': 'Uncaught exception in application',
            }
        
        # CORS errors
        if 'cors' in text_lower or 'cross-origin' in text_lower:
            return {
                'ignore': False,
                'severity': 'medium',
                'confidence': 'high',
                'category': 'cors_error',
                'description': 'Cross-Origin Resource Sharing (CORS) error',
            }
        
        # Default: capture as info
        return {
            'ignore': False,
            'severity': 'info',
            'confidence': 'medium',
            'category': 'console_message',
            'description': 'Console message',
        }

    def classify_network_failures(self):
        """Classify network failures into findings."""
        # Deduplicate identical failures before creating findings; a single
        # broken asset referenced on many pages otherwise produces one finding
        # per request.
        failure_groups = defaultdict(list)

        for failure in self.crawl_result.get('network_failures', []):
            failure_reason = failure.get('failure') or ''

            # Skip ignorable failures
            if self.should_ignore_network_failure(failure_reason):
                continue

            # Skip third-party analytics
            url = failure.get('url', '')
            if self.is_third_party(url):
                continue

            page = failure.get('page', '')
            key = (page, url, failure.get('method', ''), failure_reason)
            failure_groups[key].append(failure)

        for (page, url, method, failure_reason), failures in failure_groups.items():
            description = f"Network failure: {failure_reason}"
            is_first_party_request = self.is_first_party(url)

            finding = {
                'id': self.generate_finding_id(),
                'type': 'network_failure',
                # A first-party request that never completed is more likely to
                # break the page than a failed request to an unknown host.
                'severity': 'medium' if is_first_party_request else 'low',
                'confidence': 'high',
                'page': page,
                'url': url,
                'method': method,
                'resource_type': failures[0].get('resource_type', ''),
                'title': self.get_page_title(page),
                'description': description,
                'root_cause_key': f'network_failure|{url}|{method}|{failure_reason}',
                'evidence': {
                    'http_errors': [],
                    'console_errors': [],
                    'network_failures': failures,
                },
                'screenshot': self.get_page_screenshot(page),
                'first_party': is_first_party_request,
                'deduplicated_count': len(failures),
            }

            self.findings.append(finding)

    def group_findings_by_root_cause(self):
        """
        Group findings by root-cause key to identify repeated issues.

        Every finding type participates. HTTP errors group on
        url + status + method, console errors on the normalized message, and
        network failures on url + method + failure reason. Previously only
        `http_error` findings were grouped, which meant console and network
        findings never became candidates and were therefore invisible to both
        the Gemini stage and the final report.

        All page-level evidence is preserved.
        """
        root_cause_groups = defaultdict(list)

        for finding in self.findings:
            root_cause_key = finding.get('root_cause_key')
            if not root_cause_key:
                # Fall back to a per-finding key so nothing is silently lost.
                root_cause_key = f"{finding.get('type', 'unknown')}|{finding['id']}"

            root_cause_groups[root_cause_key].append(finding)

        # defaultdict preserves insertion order, so candidate IDs are stable
        # across runs for identical input.
        for root_cause_key, findings_in_group in root_cause_groups.items():
            if not findings_in_group:
                continue

            self.root_cause_candidates.append(
                self._build_candidate(root_cause_key, findings_in_group)
            )

    def _build_candidate(self, root_cause_key, findings_in_group):
        """Build one root-cause candidate from a group of page-level findings."""
        template = findings_in_group[0]
        finding_type = template.get('type', 'unknown')

        # Keep pages and screenshots index-aligned. Collecting them into two
        # independently de-duplicated lists let them drift out of sync, so a
        # consumer zipping the two lists paired the wrong screenshot with the
        # wrong page.
        page_screenshots = {}
        all_http_errors = []
        all_console_errors = []
        all_network_failures = []
        occurrences = 0

        for finding in findings_in_group:
            page = finding.get('page') or ''
            if page and page not in page_screenshots:
                page_screenshots[page] = finding.get('screenshot') or ''

            evidence = finding.get('evidence', {})
            all_http_errors.extend(evidence.get('http_errors', []))
            all_console_errors.extend(evidence.get('console_errors', []))
            all_network_failures.extend(evidence.get('network_failures', []))

            # Count raw events, not pages: the same endpoint failing 30 times
            # on one page is 30 occurrences, not 1.
            occurrences += finding.get('deduplicated_count', 1)

        affected_pages = list(page_screenshots.keys())
        page_count = len(affected_pages)

        title, description = self._candidate_narrative(
            finding_type, template, occurrences, page_count
        )

        return {
            'id': self.generate_candidate_id(),
            'type': finding_type,
            'severity': template.get('severity'),
            'confidence': template.get('confidence'),
            'root_cause_key': root_cause_key,
            'url': template.get('url'),
            'status': template.get('status'),
            'method': template.get('method'),
            'resource_type': template.get('resource_type'),
            'error_text': template.get('error_text'),
            'error_category': template.get('error_category'),
            'title': title,
            'description': description,
            'occurrences': occurrences,
            'affected_pages': affected_pages,
            'affected_page_count': page_count,
            # Paths only, for consumers that just want to attach images.
            'screenshots': [path for path in page_screenshots.values() if path],
            # Explicit page->screenshot pairing for consumers that need both.
            'page_screenshots': [
                {'page': page, 'screenshot': path}
                for page, path in page_screenshots.items()
            ],
            'evidence': {
                'http_errors': all_http_errors,
                'console_errors': all_console_errors,
                'network_failures': all_network_failures,
            },
            'first_party': template.get('first_party'),
        }

    def _candidate_narrative(self, finding_type, template, occurrences, page_count):
        """Return a (title, description) pair for a root-cause candidate."""
        parts = []

        if finding_type == 'http_error':
            endpoint = (template.get('url') or '').split('?')[0]
            status = template.get('status')

            if page_count > 1:
                title = f'Repeated HTTP {status} response from {endpoint}'
                parts.append(
                    f"The {(template.get('resource_type') or 'API').lower()} returned "
                    f"HTTP {status} across {page_count} crawled pages "
                    f"({occurrences} requests)."
                )
            else:
                title = template.get('description') or f'HTTP {status} error'
                parts.append(template.get('description') or '')

            if status == 401:
                parts.append(
                    'This may be expected for unauthenticated users but should be verified.'
                )
            elif status == 403:
                parts.append(
                    'This may indicate intentional access control but should be verified.'
                )

        elif finding_type == 'console_error':
            snippet = (template.get('error_text') or '').strip()
            if len(snippet) > 120:
                snippet = f'{snippet[:117]}...'

            base = template.get('description') or 'Console error'
            title = f'{base} on {page_count} page(s)' if page_count > 1 else base
            parts.append(base + '.')
            if snippet:
                parts.append(f'Message: {snippet}')
            if page_count > 1:
                parts.append(
                    f'Observed on {page_count} crawled pages ({occurrences} occurrences).'
                )

        elif finding_type == 'network_failure':
            endpoint = (template.get('url') or '').split('?')[0]
            title = f'Request to {endpoint} failed to complete'
            parts.append(template.get('description') or 'Network failure.')
            if page_count > 1:
                parts.append(
                    f'Observed on {page_count} crawled pages ({occurrences} occurrences).'
                )

        else:
            title = template.get('description') or 'Finding'
            parts.append(template.get('description') or '')

        description = ' '.join(part for part in parts if part).strip()
        return title, description

    def classify(self):
        """Perform full classification."""
        self.classify_http_errors()
        self.classify_console_errors()
        self.classify_network_failures()
        self.group_findings_by_root_cause()
        return self.findings

    def get_findings_summary(self):
        """Get summary statistics of findings and candidates."""
        # Raw event counts from crawler
        raw_http_errors = len(self.crawl_result.get('http_errors', []))
        raw_console_errors = len(self.crawl_result.get('console_errors', []))
        raw_network_failures = len(self.crawl_result.get('network_failures', []))
        raw_events = raw_http_errors + raw_console_errors + raw_network_failures
        
        # Page-level findings counts
        total_page_findings = len(self.findings)
        http_page_findings = sum(1 for f in self.findings if f.get('type') == 'http_error')
        console_page_findings = sum(1 for f in self.findings if f.get('type') == 'console_error')
        network_page_findings = sum(1 for f in self.findings if f.get('type') == 'network_failure')

        # Root-cause candidate counts
        total_candidates = len(self.root_cause_candidates)

        # Severity distribution (for candidates)
        high = sum(1 for c in self.root_cause_candidates if c.get('severity') == 'high')
        medium = sum(1 for c in self.root_cause_candidates if c.get('severity') == 'medium')
        low = sum(1 for c in self.root_cause_candidates if c.get('severity') == 'low')
        info = sum(1 for c in self.root_cause_candidates if c.get('severity') == 'info')
        
        return {
            'raw_events': raw_events,
            'raw_http_errors': raw_http_errors,
            'raw_console_errors': raw_console_errors,
            'raw_network_failures': raw_network_failures,
            'deduplicated_page_findings': total_page_findings,
            'page_findings_by_type': {
                'http_error': http_page_findings,
                'console_error': console_page_findings,
                'network_failure': network_page_findings,
            },
            'root_cause_candidates': total_candidates,
            'severity_distribution': {
                'high': high,
                'medium': medium,
                'low': low,
                'info': info,
            }
        }


def find_latest_crawl_result(results_dir='results'):
    """Find the latest crawl result file."""
    results_path = Path(results_dir)
    if not results_path.exists():
        return None

    # Sort by modification time, not filename. Run ids are no longer always
    # timestamps -- the API passes a scan UUID -- so lexicographic ordering
    # would pick whichever id happens to sort highest, not the newest file.
    # The name is the tiebreak because mtime granularity is coarse enough that
    # two files written in the same tick would otherwise order arbitrarily.
    crawl_files = sorted(
        results_path.glob('crawl_*.json'),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )


    if not crawl_files:
        return None

    return str(crawl_files[0])


def generate_qa_findings(crawl_file=None, results_dir='results', run_id=None):
    """
    Generate QA findings from a crawler result.

    Args:
        crawl_file: Explicit path to a crawl_*.json file. When omitted the most
            recent file in `results_dir` is used, which is only safe for
            single-run/CLI usage — concurrent runs must pass this explicitly.
        results_dir: Directory to read from and write to.
        run_id: Suffix for the output filename. Defaults to a timestamp.
    """
    if crawl_file is None:
        crawl_file = find_latest_crawl_result(results_dir)
        if crawl_file is None:
            print(f"No crawl results found in {results_dir}/")
            return None

    print(f"Loading crawl results from: {crawl_file}")

    with open(crawl_file, encoding='utf-8') as f:
        crawl_result = json.load(f)

    # Extract target domain
    target_url = crawl_result.get('target', '')
    target_domain = normalize_host(target_url)

    # Classify findings
    classifier = QAFindingClassifier(target_domain, crawl_result)
    findings = classifier.classify()

    # Generate output file
    results_path = Path(results_dir)
    results_path.mkdir(parents=True, exist_ok=True)

    suffix = run_id or datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = str(results_path / f'qa_findings_{suffix}.json')

    output_data = {
        'target': target_url,
        'target_domain': target_domain,
        'crawl_source': str(crawl_file),
        'generated_at': datetime.now().isoformat(),
        'summary': classifier.get_findings_summary(),
        'page_level_findings': findings,
        'root_cause_candidates': classifier.root_cause_candidates,
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"QA findings saved to: {output_file}")

    # Print summary
    print_findings_summary(classifier, findings, classifier.root_cause_candidates, output_file)

    output_data['output_file'] = output_file

    return output_data


def print_findings_summary(classifier, findings, candidates, output_file):
    """Print a human-readable summary of findings and root-cause candidates."""
    summary = classifier.get_findings_summary()
    
    print("\n" + "=" * 80)
    print("QA FINDINGS SUMMARY")
    print("=" * 80)
    
    print("\nRAW EVENTS:")
    print(f"  HTTP errors:      {summary['raw_http_errors']}")
    print(f"  Console errors:   {summary['raw_console_errors']}")
    print(f"  Network failures: {summary['raw_network_failures']}")
    print(f"  Total:            {summary['raw_events']}")
    
    print("\nPAGE-LEVEL FINDINGS (deduplicated by page+url+status):")
    print(f"  Total:            {summary['deduplicated_page_findings']}")
    print(f"  HTTP errors:      {summary['page_findings_by_type']['http_error']}")
    print(f"  Console errors:   {summary['page_findings_by_type']['console_error']}")
    print(f"  Network failures: {summary['page_findings_by_type']['network_failure']}")
    
    print("\nROOT-CAUSE CANDIDATES (grouped by url+status+method):")
    print(f"  Total:            {summary['root_cause_candidates']}")
    severity = summary['severity_distribution']
    print(f"  HIGH:             {severity['high']}")
    print(f"  MEDIUM:           {severity['medium']}")
    print(f"  LOW:              {severity['low']}")
    print(f"  INFO:             {severity['info']}")
    
    if candidates:
        print("\n" + "-" * 80)
        print("ROOT-CAUSE CANDIDATE DETAILS")
        print("-" * 80)
        
        for candidate in candidates:
            print(f"\n{candidate['id']}")
            print(f"  Type:         {candidate.get('type', 'N/A')}")
            print(f"  Severity:     {(candidate.get('severity') or 'n/a').upper()}")
            print(f"  Confidence:   {candidate.get('confidence', 'N/A')}")
            print(f"  Title:        {candidate.get('title', 'N/A')}")
            print(f"  URL:          {candidate.get('url') or 'N/A'}")
            print(f"  Status:       {candidate.get('status') or 'N/A'}")
            print(f"  Method:       {candidate.get('method') or 'N/A'}")
            print(f"  Occurrences:  {candidate.get('occurrences', 0)}")
            print(f"  Description:  {candidate.get('description', '')}")
            
            affected = candidate.get('affected_pages', [])
            if affected:
                print(f"  Affected Pages ({len(affected)}):")
                for page in affected[:3]:
                    print(f"    - {page}")
                if len(affected) > 3:
                    print(f"    ... and {len(affected) - 3} more")
    
    if findings:
        print("\n" + "-" * 80)
        print("PAGE-LEVEL FINDINGS DETAIL (sample, first 5)")
        print("-" * 80)
        
        for finding in findings[:5]:
            print(f"\n{finding['id']}")
            print(f"  Type:      {finding.get('type', 'N/A')}")
            print(f"  Severity:  {(finding.get('severity') or 'n/a').upper()}")
            print(f"  Page:      {finding.get('page') or 'N/A'}")

            if finding.get('type') == 'http_error':
                print(f"  URL:       {finding.get('url') or 'N/A'}")
                print(f"  Status:    {finding.get('status') or 'N/A'}")
            elif finding.get('type') == 'console_error':
                print(f"  Error:     {(finding.get('error_text') or 'N/A')[:60]}...")
            elif finding.get('type') == 'network_failure':
                print(f"  URL:       {finding.get('url') or 'N/A'}")
                print(f"  Failure:   {finding.get('description') or 'N/A'}")
    
    print("\n" + "=" * 80)
    print(f"Results saved to: {output_file}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    generate_qa_findings()
