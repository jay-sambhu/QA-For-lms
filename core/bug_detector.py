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


DEVICE_SUFFIX_RE = re.compile(r'\s\[([^\[\]]+)\]$')

# Console text produced by a React/Next.js server-client markup mismatch.
# These are real defects but they are not crashes, and the minified text
# tells the reader nothing without the decoded message.
HYDRATION_ERROR_RE = re.compile(
    r'Minified React error #(418|419|421|422|423|424|425)\b'
    r'|Hydration failed'
    r'|did not match.*server'
    r'|Text content does not match'
    r'|There was an error while hydrating',
    re.I,
)

# Low-value assets whose absence is cosmetic (browser-requested icons and
# manifests), used to soften 404 severity.
LOW_VALUE_PATH_RE = re.compile(r'/(favicon[^/]*\.(ico|png|svg)|apple-touch-icon[^/]*|site\.webmanifest|manifest\.json|browserconfig\.xml|robots\.txt)$', re.I)

ASSET_RESOURCE_TYPES = {'image', 'font', 'stylesheet', 'script', 'media', 'texttrack', 'manifest'}
DOCUMENT_RESOURCE_TYPES = {'document', 'xhr', 'fetch', 'websocket', 'eventsource', 'other', ''}

# Viewport widths at or above this are desktop layouts, where a visible
# element poking past the right edge is almost always an intentional
# off-canvas control rather than a responsive defect.
DESKTOP_MIN_WIDTH = 1280


def strip_device_suffix(page_id):
    """'https://site/path [iPhone 13]' -> 'https://site/path'."""
    return DEVICE_SUFFIX_RE.sub('', page_id or '')


def device_of(page_id):
    """'https://site/path [iPhone 13]' -> 'iPhone 13' (or '')."""
    match = DEVICE_SUFFIX_RE.search(page_id or '')
    return match.group(1) if match else ''


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

    def __init__(self, target_domain, crawl_result, interactive_result=None):
        """
        Initialize the classifier.

        Args:
            target_domain: The main domain being tested (e.g. 'dplms.com').
                A full URL is also accepted.
            crawl_result: The crawler result dictionary
            interactive_result: Optional interactive tester result dictionary
        """
        self.target_domain = normalize_host(target_domain)
        self.crawl_result = crawl_result or {}
        self.interactive_result = interactive_result or {}
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

    def _find_page(self, page_url):
        """Locate a crawl page record by page id ('url [Device]') or by bare URL.

        A bare URL matches the first successful render of that URL (desktop
        first, since the crawler visits it first)."""
        pages = self.crawl_result.get('pages', [])
        for page in pages:
            if page.get('url') == page_url:
                return page
        bare = strip_device_suffix(page_url)
        for page in pages:
            if page.get('error'):
                continue
            if page.get('actual_url') == bare or strip_device_suffix(page.get('url', '')) == bare:
                return page
        return None

    def get_page_title(self, page_url):
        """Get the page title from crawl pages."""
        page = self._find_page(page_url)
        return (page.get('title') or '') if page else ''

    def get_page_screenshot(self, page_url):
        """Get the page screenshot from crawl pages."""
        page = self._find_page(page_url)
        return (page.get('screenshot') or '') if page else ''

    def _devices_for(self, page_url):
        device = device_of(page_url)
        return [device] if device else []

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

        The host is lowercased (hosts are case-insensitive).
        Query parameters are stripped to group identical endpoints that vary only
        by query string (e.g. tracking tokens or tenant IDs). Trailing slashes are stripped.
        """
        parsed = urlparse(url or '')
        host = normalize_host(url)
        tail = parsed.path or ''
        
        # Strip trailing slashes to unify /api/cart/ and /api/cart
        tail = tail.rstrip('/')
        
        if status in (401, 403):
            # Group all auth errors on a host together, ignoring the path
            tail = ''
            method = 'ALL'

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
            resource_type = (errors[0].get('resource_type') or '').lower()

            severity = self._http_severity(
                classification['severity'], numeric_status, url,
                resource_type, is_first_party_request,
            )

            # Only a first-party failure can be verified against the site
            # under test; an unknown host returning 4xx is circumstantial.
            if numeric_status is None:
                confidence = 'low'
            elif not is_first_party_request:
                confidence = 'medium' if numeric_status >= 500 else 'low'
            elif numeric_status >= 500 or numeric_status == 404:
                confidence = 'high'
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
                'actual_url': strip_device_suffix(page),
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
                'affected_devices': self._devices_for(page),
            }

            self.findings.append(finding)

    @staticmethod
    def _http_severity(base_severity, status, url, resource_type, is_first_party):
        """Severity of an HTTP error from who served it and what it was.

        A first-party page or API failing is the site's bug; a missing icon
        or a broken request to an unknown third-party host is noise that
        should not cost score points."""
        if status is None:
            return 'info'
        if not is_first_party:
            return 'low' if status >= 500 else 'info'

        is_asset = resource_type in ASSET_RESOURCE_TYPES
        if status >= 500:
            return 'medium' if is_asset else 'high'
        if status == 404:
            if LOW_VALUE_PATH_RE.search(urlparse(url or '').path or ''):
                return 'low'
            return 'medium' if is_asset else 'high'
        if is_asset and base_severity in ('high', 'medium'):
            return 'low'
        return base_severity

    def _generate_http_description(self, status, url, is_first_party):
        """Generate a descriptive message for an HTTP error."""
        parsed = urlparse(url or '')

        # Compare whole path segments. A substring test called /therapy and
        # /rapid "API" endpoints.
        segments = {segment.lower() for segment in parsed.path.split('/') if segment}
        is_api = bool(segments & {'api', 'apis', 'graphql', 'rest', 'v1', 'v2', 'v3'})
        resource_type = 'API' if is_api else 'Resource'
        if not is_first_party:
            resource_type = f'Third-party {resource_type.lower()}'

        if not isinstance(status, int):
            return f"{resource_type} returned an unknown HTTP status"
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
            
            # One group per URL + message: the same error on three device
            # renders is one defect observed on three devices, not three
            # pages.
            key = (strip_device_suffix(page), self._error_pattern(text))
            error_groups[key].append(console_error)

        # Process each unique error group
        for (bare_page, pattern), errors in error_groups.items():
            error_text = errors[0].get('text', '')
            page = errors[0].get('page', '')

            classification = self._classify_console_error(error_text)

            if classification['ignore']:
                continue

            page_title = self.get_page_title(page)
            screenshot = self.get_page_screenshot(page)

            devices = []
            for err in errors:
                dev = device_of(err.get('page', ''))
                if dev and dev not in devices:
                    devices.append(dev)

            finding = {
                'id': self.generate_finding_id(),
                'type': 'console_error',
                'severity': classification['severity'],
                'confidence': classification['confidence'],
                'page': page,
                'actual_url': bare_page,
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
                'affected_devices': devices,
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
        # Distinctive tracker names/domains only. Bare words like "analytics" or
        # "segment" also matched first-party bugs such as
        # "initAnalytics is not defined" or "reading 'segments'", hiding them.
        tracking_keywords = [
            'google-analytics',
            'googletagmanager',
            'gtag(',
            'facebook pixel',
            'connect.facebook.net',
            'fbq(',
            'intercom',
            'hotjar',
            'cdn.segment.com',
            'api.segment.io',
            'mixpanel',
        ]
        text_lower = (text or '').lower()
        return any(keyword in text_lower for keyword in tracking_keywords)

    def _is_expected_auth_error(self, text):
        """Check if an error is an expected authentication rejection."""
        text_lower = text.lower()
        return 'status of 401' in text_lower

    def _classify_console_error(self, error_text):
        """Classify a console error message."""
        text_lower = error_text.lower()

        # React hydration mismatch: a real defect, but not a crash, and the
        # minified text needs decoding for the reader.
        hydration = HYDRATION_ERROR_RE.search(error_text or '')
        if hydration:
            code = hydration.group(1)
            link = f'https://react.dev/errors/{code}' if code else 'https://react.dev/link/hydration-mismatch'
            return {
                'ignore': False,
                'severity': 'medium',
                'confidence': 'high',
                'category': 'hydration_mismatch',
                'description': (
                    'Server/client markup mismatch (React hydration error). The HTML rendered on the server '
                    f'differs from what React rendered in the browser, so React re-renders the page client-side. See {link}'
                ),
            }

        # Runtime errors
        if any(err in text_lower for err in ['typeerror', 'referenceerror', 'syntaxerror']):
            return {
                'ignore': False,
                'severity': 'high',
                'confidence': 'high',
                'category': 'javascript_exception',
                'description': 'JavaScript runtime error detected',
            }
        
        # Failed to load resource (sub-resource 404 noise filtering)
        if 'failed to load resource' in text_lower:
            # Only elevate if it's a critical API endpoint error
            if any(api_kwd in text_lower for api_kwd in ['/api/', 'graphql', 'backend']):
                return {
                    'ignore': False,
                    'severity': 'high',
                    'confidence': 'high',
                    'category': 'application_api_error',
                    'description': 'Failed to load critical application API resource',
                }
            # Otherwise ignore non-critical sub-resource load warnings (favicon, assets, static)
            return {
                'ignore': True,
                'severity': 'low',
                'confidence': 'low',
                'category': 'resource_error',
                'description': 'Non-critical sub-resource load failure',
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
                'confidence': 'high' if is_first_party_request else 'medium',
                'page': page,
                'actual_url': strip_device_suffix(page),
                'affected_devices': self._devices_for(page),
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

    def classify_interaction_errors(self):
        """Classify interaction failures into findings."""
        for interaction in self.interactive_result.get('interactions', []):
            if interaction.get('result') != 'failed':
                continue
                
            page = interaction.get('page', '')
            action = interaction.get('action', '')
            element_text = interaction.get('element_text', '')
            
            evidence = interaction.get('evidence', {})
            
            finding = {
                'id': self.generate_finding_id(),
                'type': 'interaction_error',
                'severity': interaction.get('severity', 'high'),
                'confidence': interaction.get('confidence', 'high'),
                'page': page,
                'url': interaction.get('after_url', page),
                'method': 'INTERACT',
                'error_text': f"Interaction '{action}' on '{element_text}' failed.",
                'error_category': 'interaction_failure',
                'title': self.get_page_title(page),
                'description': interaction.get('description', 'Interaction failed.'),
                'root_cause_key': f"interaction_error|{page}|{action}|{element_text}",
                'evidence': {
                    'http_errors': evidence.get('http_errors', []),
                    'console_errors': evidence.get('console_errors', []),
                    'network_failures': evidence.get('network_failures', []),
                },
                'screenshot': evidence.get('screenshot') or self.get_page_screenshot(page),
                'first_party': True,
                'deduplicated_count': 1,
                'interactive_metadata': {
                    'element_type': interaction.get('element_type'),
                    'action': action,
                    'element_text': element_text,
                    'before_url': interaction.get('before_url'),
                }
            }
            
            self.findings.append(finding)

    def classify_responsive_issues(self):
        """Classify responsive and layout issues across devices.

        Only a real horizontal overflow (the document is wider than the
        viewport by more than 15px) is a medium/high defect. Visible
        controls poking past the edge without overflow are low, and on a
        desktop-width viewport they are ignored: at 1280px+ such elements
        are off-canvas drawers, carousels or sticky menus, not layout bugs.
        """
        for page_data in self.crawl_result.get('pages', []):
            if page_data.get('error') or page_data.get('auth_wall'):
                continue

            responsive = page_data.get('responsive_checks') or {}
            if not responsive or responsive.get('checked') is False:
                continue

            has_overflow = bool(responsive.get('horizontal_overflow', False))
            elements_outside = responsive.get('elements_outside_viewport', 0) or 0
            forms_outside = responsive.get('forms_outside_viewport', 0) or 0
            clipped_buttons = responsive.get('clipped_buttons', 0) or 0
            overflow_pixels = responsive.get('overflow_pixels', 0) or 0
            viewport_width = responsive.get('viewport_width', 0) or 0

            real_overflow = has_overflow and overflow_pixels > 15
            clipped_controls = forms_outside > 0 or clipped_buttons > 0

            if not real_overflow and elements_outside == 0 and not clipped_controls:
                continue
            if not real_overflow and viewport_width >= DESKTOP_MIN_WIDTH:
                continue

            dev_name = page_data.get('device', 'Unknown Device')

            if real_overflow and clipped_controls:
                severity = 'high'
                desc = (
                    f"Page is {overflow_pixels}px wider than the {viewport_width}px viewport on {dev_name}, "
                    f"and {forms_outside} form field(s) / {clipped_buttons} button(s) sit outside it."
                )
            elif real_overflow:
                severity = 'medium'
                desc = (
                    f"Page is {overflow_pixels}px wider than the {viewport_width}px viewport on {dev_name} "
                    f"({elements_outside} element(s) extend past the edge), so users must scroll sideways."
                )
            else:
                severity = 'low'
                desc = (
                    f"{elements_outside} visible element(s) ({clipped_buttons} button(s), {forms_outside} field(s)) "
                    f"extend past the {viewport_width}px viewport on {dev_name} without causing page overflow."
                )

            samples = responsive.get('samples') or []
            if samples:
                desc += ' Examples: ' + '; '.join(str(s) for s in samples[:3]) + '.'

            actual_url = page_data.get('actual_url') or strip_device_suffix(page_data.get('url', ''))
            page_id = page_data.get('url', actual_url)

            issue_type = 'overflow' if real_overflow else 'clipped_element'

            finding = {
                'id': self.generate_finding_id(),
                'type': 'responsive_issue',
                'severity': severity,
                'confidence': 'high' if real_overflow else 'medium',
                'page': page_id,
                'actual_url': actual_url,
                'device': dev_name,
                'url': actual_url,
                'title': f"Responsive layout issue on {dev_name}",
                'description': desc,
                'issue_type': issue_type,
                # One layout pattern across the site is one finding; pages and
                # devices are collected on the candidate.
                'root_cause_key': f"responsive_issue|{self.target_domain}|{issue_type}",
                'evidence': {
                    'http_errors': [],
                    'console_errors': [],
                    'network_failures': [],
                    'responsive_checks': responsive,
                },
                'screenshot': page_data.get('screenshot') or self.get_page_screenshot(page_id),
                'first_party': True,
                'deduplicated_count': 1,
                'affected_devices': [dev_name]
            }

            self.findings.append(finding)

    def classify_auth_walls(self):
        """One finding for every requested page that redirected to a login
        page or off-site. Informational without credentials (expected),
        medium when credentials were supplied and still did not grant access."""
        walled = {}
        for page_data in self.crawl_result.get('pages', []):
            if page_data.get('error') or not page_data.get('auth_wall'):
                continue
            actual_url = page_data.get('actual_url') or strip_device_suffix(page_data.get('url', ''))
            entry = walled.setdefault(actual_url, {
                'page': page_data.get('url', actual_url),
                'final_url': page_data.get('final_url', ''),
                'screenshot': page_data.get('screenshot') or '',
                'devices': [],
            })
            dev = page_data.get('device')
            if dev and dev not in entry['devices']:
                entry['devices'].append(dev)

        if not walled:
            return

        credentials = bool(self.crawl_result.get('auth_credentials_supplied'))
        severity = 'medium' if credentials else 'info'
        count = len(walled)
        first_url, first = next(iter(walled.items()))
        destination = first.get('final_url') or ''
        devices = sorted({d for entry in walled.values() for d in entry['devices']})

        if credentials:
            description = (
                f"{count} page(s) redirected to a login page even though login credentials were supplied, "
                f"so they were not tested. Example: {first_url} -> {destination}. Check that the credentials "
                "are valid for these areas and that the session cookie is accepted on every route."
            )
        else:
            description = (
                f"{count} page(s) require authentication and redirected to a login page "
                f"(example: {first_url} -> {destination}). Supply login credentials to include them in the scan."
            )

        self.findings.append({
            'id': self.generate_finding_id(),
            'type': 'auth_wall',
            'severity': severity,
            'confidence': 'high',
            'page': first['page'],
            'actual_url': first_url,
            'url': first_url,
            'final_url': destination,
            'title': 'Pages behind a login wall',
            'description': description,
            'root_cause_key': f"auth_wall|{self.target_domain}",
            'evidence': {
                'http_errors': [],
                'console_errors': [],
                'network_failures': [],
                'auth_walls': [
                    {'page': url, 'redirected_to': entry['final_url'], 'devices': entry['devices']}
                    for url, entry in walled.items()
                ],
            },
            'screenshot': first.get('screenshot') or '',
            'first_party': True,
            'deduplicated_count': count,
            'affected_devices': devices,
            'affected_urls': list(walled.keys()),
        })

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

        affected_devices = []
        page_views = set()
        for finding in findings_in_group:
            page_id = finding.get('page') or ''
            # Pages are URLs, not device renders: the same URL seen on three
            # viewports is one affected page observed on three devices.
            page = finding.get('actual_url') or strip_device_suffix(page_id)
            if page and page not in page_screenshots:
                page_screenshots[page] = finding.get('screenshot') or ''
            elif page and not page_screenshots.get(page) and finding.get('screenshot'):
                page_screenshots[page] = finding.get('screenshot')
            for extra in finding.get('affected_urls', []) or []:
                page_screenshots.setdefault(extra, '')
            if page_id:
                page_views.add(page_id)

            for d in [finding.get('device')] + list(finding.get('affected_devices', []) or []) + self._devices_for(page_id):
                if d and d not in affected_devices:
                    affected_devices.append(d)

            evidence = finding.get('evidence', {})
            all_http_errors.extend(evidence.get('http_errors', []))
            all_console_errors.extend(evidence.get('console_errors', []))
            all_network_failures.extend(evidence.get('network_failures', []))

            # Count raw events, not pages: the same endpoint failing 30 times
            # on one page is 30 occurrences, not 1.
            occurrences += finding.get('deduplicated_count', 1)

        affected_pages = list(page_screenshots.keys())
        page_count = len(affected_pages)
        affected_devices = sorted(affected_devices)

        severity = template.get('severity')
        if finding_type == 'responsive_issue':
            # The group spans pages and devices; its severity is the worst seen.
            rank = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'info': 0}
            severity = max((f.get('severity') or 'info' for f in findings_in_group), key=lambda s: rank.get(s, 0))

        title, description = self._candidate_narrative(
            finding_type, template, occurrences, page_count, affected_devices, findings_in_group
        )

        return {
            'id': self.generate_candidate_id(),
            'type': finding_type,
            'severity': severity,
            'confidence': template.get('confidence'),
            'root_cause_key': root_cause_key,
            'url': template.get('url'),
            'status': template.get('status'),
            'method': template.get('method'),
            'resource_type': template.get('resource_type'),
            'error_text': template.get('error_text'),
            'error_category': template.get('error_category'),
            'issue_type': template.get('issue_type'),
            'title': title,
            'description': description,
            'occurrences': occurrences,
            'affected_pages': affected_pages,
            'affected_page_count': page_count,
            'affected_page_views': len(page_views),
            'affected_devices': affected_devices,
            'page_titles': [t for t in {self.get_page_title(p) for p in affected_pages} if t][:5],
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

    @staticmethod
    def _scope_suffix(page_count, devices):
        """' (2 pages, 3 devices)' style suffix for titles; URLs never go in
        titles, they live in the url/affected_pages fields."""
        bits = []
        if page_count:
            bits.append(f"{page_count} page{'s' if page_count != 1 else ''}")
        if devices:
            bits.append(f"{len(devices)} device{'s' if len(devices) != 1 else ''}")
        return f" ({', '.join(bits)})" if bits else ''

    @staticmethod
    def _console_title(category, error_text):
        titles = {
            'hydration_mismatch': 'React hydration mismatch',
            'javascript_exception': 'JavaScript runtime error',
            'uncaught_exception': 'Uncaught JavaScript exception',
            'application_api_error': 'Application API request failed',
            'cors_error': 'Cross-origin (CORS) request blocked',
            'console_message': 'Console error message',
        }
        base = titles.get(category)
        if base:
            return base
        snippet = (error_text or '').strip().split('\n')[0]
        return snippet[:60] if snippet else 'Console error'

    def _candidate_narrative(self, finding_type, template, occurrences, page_count,
                             devices=None, findings_in_group=None):
        """Return a (title, description) pair for a root-cause candidate."""
        parts = []
        devices = devices or []
        findings_in_group = findings_in_group or [template]
        scope = self._scope_suffix(page_count, devices)
        device_list = ', '.join(devices)

        if finding_type == 'http_error':
            endpoint = (template.get('url') or '').split('?')[0]
            status = template.get('status')
            path = urlparse(endpoint).path or '/'
            kind = 'API' if (template.get('resource_type') or '') in ('xhr', 'fetch') else (
                'page' if (template.get('resource_type') or '') == 'document' else
                (template.get('resource_type') or 'resource')
            )
            party = '' if template.get('first_party') else 'Third-party '

            if status is None:
                title = f'{party}{kind} request failed{scope}'.strip()
            elif status >= 500:
                title = f'{party}{kind} returns HTTP {status}{scope}'.strip()
            elif status == 404:
                title = f'{party}{kind} not found (404){scope}'.strip()
            else:
                title = f'{party}{kind} returns HTTP {status}{scope}'.strip()
            title = title[0].upper() + title[1:]

            parts.append(f"{template.get('description') or f'HTTP {status} error'} at {path}.")
            if page_count > 1:
                parts.append(
                    f"Observed on {page_count} crawled pages ({occurrences} requests)."
                )
            elif occurrences > 1:
                parts.append(f"{occurrences} requests failed on this page.")
            if device_list:
                parts.append(f"Devices: {device_list}.")
            if not template.get('first_party'):
                parts.append('The failing host is not part of the site under test, so this is usually outside your control.')

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
            if len(snippet) > 160:
                snippet = f'{snippet[:157]}...'

            base = template.get('description') or 'Console error'
            title = self._console_title(template.get('error_category'), template.get('error_text')) + scope
            parts.append(base.rstrip('.') + '.')
            if snippet:
                parts.append(f'Message: {snippet}')
            if page_count > 1:
                parts.append(
                    f'Observed on {page_count} crawled pages ({occurrences} occurrences).'
                )
            elif len(devices) > 1:
                parts.append(f'Reproduced on every viewport tested ({device_list}).')

        elif finding_type == 'network_failure':
            endpoint = (template.get('url') or '').split('?')[0]
            path = urlparse(endpoint).path or '/'
            reason = (template.get('description') or 'Network failure.').replace('Network failure: ', '')
            party = '' if template.get('first_party') else 'Third-party '
            title = f"{party}request failed to complete ({reason}){scope}"
            title = title[0].upper() + title[1:]
            parts.append(f"The request to {path} did not complete: {reason}.")
            if page_count > 1:
                parts.append(
                    f'Observed on {page_count} crawled pages ({occurrences} occurrences).'
                )

        elif finding_type == 'interaction_error':
            action = template.get('interactive_metadata', {}).get('action', 'interaction')
            element_text = template.get('interactive_metadata', {}).get('element_text', 'element')
            title = f"Failed {action} on '{element_text}'"
            parts.append(template.get('description') or 'Interaction failed.')

            if page_count > 1:
                parts.append(f'Observed on {page_count} pages ({occurrences} occurrences).')

        elif finding_type == 'responsive_issue':
            issue_type = template.get('issue_type') or 'overflow'
            if issue_type == 'overflow':
                title = f"Horizontal overflow on {device_list or 'small screens'} ({page_count} page{'s' if page_count != 1 else ''})"
                parts.append('The page is wider than the viewport, so users must scroll sideways to see all content.')
            else:
                title = f"Interactive elements clipped outside viewport ({page_count} page{'s' if page_count != 1 else ''})"
                parts.append('Visible buttons or fields extend past the edge of the screen without causing page overflow.')
            worst = max(findings_in_group, key=lambda f: ((f.get('evidence') or {}).get('responsive_checks') or {}).get('overflow_pixels', 0) or 0)
            parts.append(worst.get('description') or template.get('description') or '')
            if page_count > 1:
                parts.append(f'Observed on {page_count} pages.')

        elif finding_type == 'auth_wall':
            title = template.get('title') or 'Pages behind a login wall'
            parts.append(template.get('description') or '')

        else:
            title = template.get('title') or template.get('description') or 'Finding'
            parts.append(template.get('description') or '')

        description = ' '.join(part for part in parts if part).strip()
        return title, description

    def classify(self):
        """Perform full classification."""
        self.classify_http_errors()
        self.classify_console_errors()
        self.classify_network_failures()
        self.classify_interaction_errors()
        self.classify_responsive_issues()
        self.classify_auth_walls()
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
        responsive_page_findings = sum(1 for f in self.findings if f.get('type') == 'responsive_issue')
        auth_wall_findings = sum(1 for f in self.findings if f.get('type') == 'auth_wall')

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
                'responsive_issue': responsive_page_findings,
                'auth_wall': auth_wall_findings,
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


def generate_qa_findings(crawl_file=None, results_dir='results', run_id=None, interactive_file=None):
    """
    Generate QA findings from a crawler result.

    Args:
        crawl_file: Explicit path to a crawl_*.json file. When omitted the most
            recent file in `results_dir` is used, which is only safe for
            single-run/CLI usage — concurrent runs must pass this explicitly.
        results_dir: Directory to read from and write to.
        run_id: Suffix for the output filename. Defaults to a timestamp.
        interactive_file: Optional path to an interactive_qa_*.json file.
    """
    if crawl_file is None:
        crawl_file = find_latest_crawl_result(results_dir)
        if crawl_file is None:
            print(f"No crawl results found in {results_dir}/")
            return None

    print(f"Loading crawl results from: {crawl_file}")

    with open(crawl_file, encoding='utf-8') as f:
        crawl_result = json.load(f)

    interactive_result = None
    if interactive_file and Path(interactive_file).exists():
        with open(interactive_file, 'r', encoding='utf-8') as f:
            interactive_result = json.load(f)

    # Extract target domain
    target_url = crawl_result.get('target', '')
    target_domain = normalize_host(target_url)

    # Classify findings
    classifier = QAFindingClassifier(target_domain, crawl_result, interactive_result=interactive_result)
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
