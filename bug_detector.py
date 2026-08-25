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
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict


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
            target_domain: The main domain being tested (e.g., 'dplms.com')
            crawl_result: The crawler result dictionary
        """
        self.target_domain = target_domain.lower()
        self.crawl_result = crawl_result
        self.findings = []
        self.root_cause_candidates = []
        self.finding_id_counter = 0
        self.candidate_id_counter = 0

    def is_first_party(self, url):
        """Check if a URL belongs to first-party domain."""
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        
        # Direct match
        if netloc == self.target_domain:
            return True
        
        # Subdomain match (*.dplms.com)
        if netloc.endswith('.' + self.target_domain):
            return True
        
        return False

    def is_third_party(self, url):
        """Check if a URL is from a known third-party."""
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        
        for third_party in self.THIRD_PARTY_DOMAINS:
            if third_party in netloc:
                return True
        
        return False

    def classify_http_status(self, status):
        """Classify HTTP status code."""
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
        """Check if a network failure should be ignored."""
        for ignorable in self.IGNORABLE_FAILURES:
            if ignorable in failure:
                return True
        return False

    def get_page_title(self, page_url):
        """Get the page title from crawl pages."""
        for page in self.crawl_result.get('pages', []):
            if page['url'] == page_url:
                return page.get('title', '')
        return ''

    def get_page_screenshot(self, page_url):
        """Get the page screenshot from crawl pages."""
        for page in self.crawl_result.get('pages', []):
            if page['url'] == page_url:
                return page.get('screenshot', '')
        return ''

    def find_matching_console_errors(self, http_error):
        """Find console errors that match an HTTP error."""
        matching = []
        status = http_error.get('status')
        page = http_error.get('page')
        
        # Look for console errors on the same page mentioning the same status
        for console_error in self.crawl_result.get('console_errors', []):
            if console_error.get('page') == page:
                error_text = console_error.get('text', '').lower()
                # Match error messages like "Failed to load resource: the server responded with a status of 401"
                if f'status of {status}' in error_text or f'{status}' in error_text:
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
        """Generate a deterministic root-cause grouping key."""
        # Primary key: normalized URL + status + method
        return f"{url}|{status}|{method}".lower()

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
            
            # Determine confidence and severity based on first-party status
            is_first_party_request = self.is_first_party(url)
            is_third_party_request = self.is_third_party(url)
            
            # Adjust severity for third-party
            severity = classification['severity']
            if is_third_party_request:
                # Deprioritize third-party errors (except 5xx which are always high)
                if status < 500:
                    severity = 'info'
            
            # Determine confidence
            if status >= 500:
                confidence = 'high'
            elif status == 404:
                confidence = 'high'
            elif status in (401, 403):
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
        parsed = urlparse(url)
        resource_type = 'API' if 'api' in parsed.path else 'Resource'
        
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
        pattern = error_text.lower()
        # Remove URLs and IDs
        import re
        pattern = re.sub(r'https?://[^\s]+', '', pattern)
        pattern = re.sub(r'\d+', '', pattern)
        pattern = pattern.strip()
        return pattern

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
        for failure in self.crawl_result.get('network_failures', []):
            failure_reason = failure.get('failure', '')
            
            # Skip ignorable failures
            if self.should_ignore_network_failure(failure_reason):
                continue
            
            # Skip third-party analytics
            url = failure.get('url', '')
            if self.is_third_party(url):
                continue
            
            description = f"Network failure: {failure_reason}"
            
            finding = {
                'id': self.generate_finding_id(),
                'type': 'network_failure',
                'severity': 'medium',
                'confidence': 'high',
                'url': url,
                'method': failure.get('method', ''),
                'resource_type': failure.get('resource_type', ''),
                'description': description,
                'evidence': {
                    'http_errors': [],
                    'console_errors': [],
                    'network_failures': [failure],
                },
                'first_party': self.is_first_party(url),
            }
            
            self.findings.append(finding)

    def group_findings_by_root_cause(self):
        """
        Group findings by root-cause key to identify repeated issues.
        
        Creates root-cause candidates by grouping findings with the same:
        - URL
        - HTTP status
        - HTTP method
        
        Preserves all page-level evidence.
        """
        # Group HTTP findings by root-cause key
        root_cause_groups = defaultdict(list)
        
        for finding in self.findings:
            # Only group HTTP errors (not console or network)
            if finding.get('type') != 'http_error':
                continue
            
            root_cause_key = finding.get('root_cause_key')
            if root_cause_key:
                root_cause_groups[root_cause_key].append(finding)
        
        # Create root-cause candidates
        for root_cause_key, findings_in_group in root_cause_groups.items():
            if not findings_in_group:
                continue
            
            # Use first finding as template
            template = findings_in_group[0]
            
            # Collect all affected pages and screenshots
            affected_pages = []
            screenshots = []
            all_http_errors = []
            all_console_errors = []
            
            for finding in findings_in_group:
                page = finding.get('page')
                if page and page not in affected_pages:
                    affected_pages.append(page)
                
                screenshot = finding.get('screenshot')
                if screenshot and screenshot not in screenshots:
                    screenshots.append(screenshot)
                
                # Collect all evidence
                evidence = finding.get('evidence', {})
                all_http_errors.extend(evidence.get('http_errors', []))
                all_console_errors.extend(evidence.get('console_errors', []))
            
            # Build candidate title
            endpoint = template.get('url', '').split('?')[0]  # Remove query params
            status = template.get('status')
            occurrences = len(affected_pages)
            
            if occurrences > 1:
                title = f"Repeated HTTP {status} response from {endpoint}"
            else:
                title = template.get('description', f'HTTP {status} error')
            
            # Build description
            description_parts = []
            if occurrences > 1:
                description_parts.append(
                    f"The {template.get('resource_type', 'API').lower()} returned HTTP {status} "
                    f"across {occurrences} crawled pages."
                )
            else:
                description_parts.append(template.get('description', ''))
            
            if template.get('status') == 401:
                description_parts.append(
                    "This may be expected for unauthenticated users but should be verified."
                )
            elif template.get('status') == 403:
                description_parts.append(
                    "This may indicate intentional access control but should be verified."
                )
            
            description = ' '.join(description_parts)
            
            # Create root-cause candidate
            candidate = {
                'id': self.generate_candidate_id(),
                'type': 'http_error',
                'severity': template.get('severity'),
                'confidence': template.get('confidence'),
                'root_cause_key': root_cause_key,
                'url': template.get('url'),
                'status': template.get('status'),
                'method': template.get('method'),
                'resource_type': template.get('resource_type'),
                'title': title,
                'description': description,
                'occurrences': occurrences,
                'affected_pages': affected_pages,
                'screenshots': screenshots,
                'evidence': {
                    'http_errors': all_http_errors,
                    'console_errors': all_console_errors,
                    'network_failures': [],
                },
                'first_party': template.get('first_party'),
            }
            
            self.root_cause_candidates.append(candidate)

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
        http_page_findings = sum(1 for f in self.findings if f['type'] == 'http_error')
        console_page_findings = sum(1 for f in self.findings if f['type'] == 'console_error')
        network_page_findings = sum(1 for f in self.findings if f['type'] == 'network_failure')
        
        # Root-cause candidate counts
        total_candidates = len(self.root_cause_candidates)
        
        # Severity distribution (for candidates)
        high = sum(1 for c in self.root_cause_candidates if c['severity'] == 'high')
        medium = sum(1 for c in self.root_cause_candidates if c['severity'] == 'medium')
        low = sum(1 for c in self.root_cause_candidates if c['severity'] == 'low')
        info = sum(1 for c in self.root_cause_candidates if c['severity'] == 'info')
        
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
    crawl_files = sorted(results_path.glob('crawl_*.json'), reverse=True)
    
    if not crawl_files:
        return None
    
    return str(crawl_files[0])


def generate_qa_findings(crawl_file=None):
    """Generate QA findings from a crawler result."""
    if crawl_file is None:
        crawl_file = find_latest_crawl_result()
        if crawl_file is None:
            print("No crawl results found")
            return None
    
    print(f"Loading crawl results from: {crawl_file}")
    
    with open(crawl_file) as f:
        crawl_result = json.load(f)
    
    # Extract target domain
    target_url = crawl_result.get('target', '')
    from urllib.parse import urlparse
    target_domain = urlparse(target_url).netloc
    
    # Classify findings
    classifier = QAFindingClassifier(target_domain, crawl_result)
    findings = classifier.classify()
    
    # Generate output file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'results/qa_findings_{timestamp}.json'
    
    output_data = {
        'target': target_url,
        'crawl_source': crawl_file,
        'generated_at': datetime.now().isoformat(),
        'summary': classifier.get_findings_summary(),
        'page_level_findings': findings,
        'root_cause_candidates': classifier.root_cause_candidates,
    }
    
    os.makedirs('results', exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"QA findings saved to: {output_file}")
    
    # Print summary
    print_findings_summary(classifier, findings, classifier.root_cause_candidates, output_file)
    
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
            print(f"  Severity:     {candidate['severity'].upper()}")
            print(f"  Confidence:   {candidate['confidence']}")
            print(f"  Title:        {candidate['title']}")
            print(f"  URL:          {candidate.get('url', 'N/A')}")
            print(f"  Status:       {candidate.get('status', 'N/A')}")
            print(f"  Method:       {candidate.get('method', 'N/A')}")
            print(f"  Occurrences:  {candidate['occurrences']}")
            print(f"  Description:  {candidate['description']}")
            
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
            print(f"  Type:      {finding['type']}")
            print(f"  Severity:  {finding['severity'].upper()}")
            print(f"  Page:      {finding.get('page', 'N/A')}")
            
            if finding['type'] == 'http_error':
                print(f"  URL:       {finding.get('url', 'N/A')}")
                print(f"  Status:    {finding.get('status', 'N/A')}")
            elif finding['type'] == 'console_error':
                print(f"  Error:     {finding.get('error_text', 'N/A')[:60]}...")
    
    print("\n" + "=" * 80)
    print(f"Results saved to: {output_file}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    generate_qa_findings()
