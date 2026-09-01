#!/usr/bin/env python3
"""
Tests for the QA Finding Classifier.
"""

import unittest
from bug_detector import QAFindingClassifier


class TestQAFindingClassifier(unittest.TestCase):
    """Test suite for QA finding classification."""

    def setUp(self):
        """Set up test fixtures."""
        self.target_domain = 'dplms.com'
        
        # Minimal crawl result structure
        self.base_crawl_result = {
            'target': 'https://dplms.com/',
            'pages_crawled': 1,
            'pages': [
                {
                    'url': 'https://dplms.com/',
                    'title': 'Home Page',
                    'status': 200,
                    'links': 10,
                    'screenshot': 'screenshots/001_page.png',
                    'timestamp': '2026-08-25T10:00:00',
                }
            ],
            'http_errors': [],
            'network_failures': [],
            'console_errors': [],
        }

    def test_401_classification_medium_severity(self):
        """Test that 401 errors are classified as medium severity."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['status'], 401)
        self.assertEqual(finding['severity'], 'medium')
        self.assertIn('authentication', finding['description'].lower())

    def test_404_classification_high_severity(self):
        """Test that 404 errors are classified as high severity."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/product',
                'url': 'https://dplms.com/api/missing-endpoint',
                'status': 404,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['status'], 404)
        self.assertEqual(finding['severity'], 'high')

    def test_500_classification_high_severity(self):
        """Test that 500+ errors are classified as high severity."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/product',
                'url': 'https://api.dplms.com/api/broken',
                'status': 500,
                'method': 'POST',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['status'], 500)
        self.assertEqual(finding['severity'], 'high')

    def test_err_aborted_ignored(self):
        """Test that ERR_ABORTED network failures are ignored."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['network_failures'] = [
            {
                'url': 'https://some-url.com/page',
                'method': 'GET',
                'resource_type': 'document',
                'failure': 'net::ERR_ABORTED',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # Should be ignored
        self.assertEqual(len(findings), 0)

    def test_third_party_analytics_ignored(self):
        """Test that third-party analytics errors are ignored or deprioritized."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://google-analytics.com/analytics.js',
                'status': 404,
                'method': 'GET',
                'resource_type': 'script',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        # Should be deprioritized to 'info' even though it's a 404
        self.assertEqual(finding['severity'], 'info')

    def test_http_and_console_error_deduplication(self):
        """Test that HTTP errors and matching console errors are deduplicated."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        crawl_result['console_errors'] = [
            {
                'page': 'https://dplms.com/',
                'text': 'Failed to load resource: the server responded with a status of 401 ()',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # Should create only 1 finding (the HTTP error with matching console error)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['type'], 'http_error')
        # Console error should be attached to the HTTP error finding
        self.assertEqual(len(finding['evidence']['console_errors']), 1)

    def test_first_party_subdomain_detection(self):
        """Test that subdomains of target domain are detected as first-party."""
        crawler = QAFindingClassifier(self.target_domain, self.base_crawl_result)
        
        # Test subdomain
        self.assertTrue(crawler.is_first_party('https://api.dplms.com/endpoint'))
        self.assertTrue(crawler.is_first_party('https://cdn.dplms.com/file'))
        self.assertTrue(crawler.is_first_party('https://app.dplms.com/dashboard'))
        
        # Test main domain
        self.assertTrue(crawler.is_first_party('https://dplms.com/page'))
        
        # Test third-party
        self.assertFalse(crawler.is_first_party('https://google.com/analytics'))
        self.assertFalse(crawler.is_first_party('https://cdn.example.com/lib'))

    def test_unique_bug_ids(self):
        """Test that each finding gets a unique ID."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart',
                'status': 404,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/product',
                'url': 'https://api.dplms.com/api/product',
                'status': 500,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        self.assertEqual(len(findings), 2)
        ids = [f['id'] for f in findings]
        # Check IDs are unique
        self.assertEqual(len(ids), len(set(ids)))
        # Check ID format
        self.assertRegex(ids[0], r'BUG-\d{3}')
        self.assertRegex(ids[1], r'BUG-\d{3}')

    def test_duplicate_http_errors_deduplicated(self):
        """Test that duplicate HTTP errors (same page, url, status) are deduplicated."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # Should create only 1 finding
        self.assertEqual(len(findings), 1)
        # But the finding should note it was deduplicated
        self.assertEqual(findings[0]['deduplicated_count'], 3)

    def test_first_party_flag(self):
        """Test that first_party flag is set correctly."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart',  # First-party
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/',
                'url': 'https://google-analytics.com/collect',  # Third-party
                'status': 404,
                'method': 'GET',
                'resource_type': 'image',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # First finding should be first-party
        first_party_finding = next(f for f in findings if 'api.dplms.com' in f['url'])
        self.assertTrue(first_party_finding['first_party'])
        
        # Second finding should be third-party
        third_party_finding = next(f for f in findings if 'google-analytics' in f['url'])
        self.assertFalse(third_party_finding['first_party'])

    def test_javascript_exception_classification(self):
        """Test that JavaScript exceptions are properly classified."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['console_errors'] = [
            {
                'page': 'https://dplms.com/',
                'text': 'TypeError: Cannot read property "x" of undefined',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['type'], 'console_error')
        self.assertEqual(finding['error_category'], 'javascript_exception')
        self.assertEqual(finding['severity'], 'high')

    def test_expected_auth_errors_not_duplicated_as_console(self):
        """Test that console 401 errors matching HTTP errors are not duplicated."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        crawl_result['console_errors'] = [
            {
                'page': 'https://dplms.com/',
                'text': 'Failed to load resource: the server responded with a status of 401 ()',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # Should only have 1 finding (the HTTP error)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['type'], 'http_error')

    def test_confidence_levels(self):
        """Test that confidence levels are properly assigned."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/broken',
                'status': 500,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/missing',
                'status': 404,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/auth',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # 500 should be high confidence
        finding_500 = next(f for f in findings if f['status'] == 500)
        self.assertEqual(finding_500['confidence'], 'high')
        
        # 404 should be high confidence
        finding_404 = next(f for f in findings if f['status'] == 404)
        self.assertEqual(finding_404['confidence'], 'high')
        
        # 401 should be medium confidence
        finding_401 = next(f for f in findings if f['status'] == 401)
        self.assertEqual(finding_401['confidence'], 'medium')

    def test_same_endpoint_multiple_pages_grouped(self):
        """Test that same endpoint across multiple pages creates one root-cause candidate."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['pages'] = [
            {'url': 'https://dplms.com/', 'title': 'Home', 'status': 200, 'links': 10, 'screenshot': 'screenshots/001_page.png', 'timestamp': '2026-08-25T10:00:00'},
            {'url': 'https://dplms.com/product', 'title': 'Product', 'status': 200, 'links': 10, 'screenshot': 'screenshots/002_page.png', 'timestamp': '2026-08-25T10:00:00'},
            {'url': 'https://dplms.com/about', 'title': 'About', 'status': 200, 'links': 10, 'screenshot': 'screenshots/003_page.png', 'timestamp': '2026-08-25T10:00:00'},
        ]
        # Same endpoint fails on 3 different pages
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart?tenant=default',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/product',
                'url': 'https://api.dplms.com/api/cart?tenant=default',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/about',
                'url': 'https://api.dplms.com/api/cart?tenant=default',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # Should create 3 page-level findings
        self.assertEqual(len(findings), 3)
        
        # But only 1 root-cause candidate
        self.assertEqual(len(classifier.root_cause_candidates), 1)
        candidate = classifier.root_cause_candidates[0]
        
        # Candidate should have all 3 affected pages
        self.assertEqual(candidate['occurrences'], 3)
        self.assertEqual(len(candidate['affected_pages']), 3)
        self.assertIn('https://dplms.com/', candidate['affected_pages'])
        self.assertIn('https://dplms.com/product', candidate['affected_pages'])
        self.assertIn('https://dplms.com/about', candidate['affected_pages'])

    def test_different_endpoints_401_grouped(self):
        """Test that different endpoints with 401 are grouped into a single candidate."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['pages'] = [
            {'url': 'https://dplms.com/', 'title': 'Home', 'status': 200, 'links': 10, 'screenshot': 'screenshots/001_page.png', 'timestamp': '2026-08-25T10:00:00'},
            {'url': 'https://dplms.com/product', 'title': 'Product', 'status': 200, 'links': 10, 'screenshot': 'screenshots/002_page.png', 'timestamp': '2026-08-25T10:00:00'},
        ]
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart?tenant=default',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/product',
                'url': 'https://api.dplms.com/api/auth/me?tenant=default',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # Should create 2 page-level findings
        self.assertEqual(len(findings), 2)
        
        # Should create 1 separate root-cause candidate because 401s on same host are grouped
        self.assertEqual(len(classifier.root_cause_candidates), 1)
        
        # The URL in the candidate should be one of the original URLs
        candidate_url = classifier.root_cause_candidates[0].get('url', '')
        self.assertTrue(candidate_url.startswith('https://api.dplms.com'))

    def test_different_endpoints_non_auth_separate_candidates(self):
        """Test that different endpoints with non-auth errors create separate root-cause candidates."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['pages'] = [
            {'url': 'https://dplms.com/', 'title': 'Home', 'status': 200, 'links': 10, 'screenshot': 'screenshots/001_page.png', 'timestamp': '2026-08-25T10:00:00'},
            {'url': 'https://dplms.com/product', 'title': 'Product', 'status': 200, 'links': 10, 'screenshot': 'screenshots/002_page.png', 'timestamp': '2026-08-25T10:00:00'},
        ]
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart?tenant=default',
                'status': 500,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/product',
                'url': 'https://api.dplms.com/api/auth/me?tenant=default',
                'status': 500,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # Should create 2 page-level findings
        self.assertEqual(len(findings), 2)
        
        # Should create 2 separate root-cause candidates (different URLs)
        self.assertEqual(len(classifier.root_cause_candidates), 2)
        
        urls = {c['url'] for c in classifier.root_cause_candidates}
        self.assertEqual(len(urls), 2)
        self.assertIn('https://api.dplms.com/api/cart?tenant=default', urls)
        self.assertIn('https://api.dplms.com/api/auth/me?tenant=default', urls)

    def test_same_endpoint_different_status_separate_candidates(self):
        """Test that same endpoint with different status codes create separate candidates."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['pages'] = [
            {'url': 'https://dplms.com/', 'title': 'Home', 'status': 200, 'links': 10, 'screenshot': 'screenshots/001_page.png', 'timestamp': '2026-08-25T10:00:00'},
            {'url': 'https://dplms.com/product', 'title': 'Product', 'status': 200, 'links': 10, 'screenshot': 'screenshots/002_page.png', 'timestamp': '2026-08-25T10:00:00'},
        ]
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart',
                'status': 401,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/product',
                'url': 'https://api.dplms.com/api/cart',
                'status': 500,
                'method': 'GET',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # Should create 2 page-level findings
        self.assertEqual(len(findings), 2)
        
        # Should create 2 separate root-cause candidates (different statuses)
        self.assertEqual(len(classifier.root_cause_candidates), 2)
        
        statuses = {c['status'] for c in classifier.root_cause_candidates}
        self.assertEqual(statuses, {401, 500})

    def test_same_endpoint_different_method_separate_candidates(self):
        """Test that same endpoint with different methods create separate candidates."""
        crawl_result = self.base_crawl_result.copy()
        crawl_result['pages'] = [
            {'url': 'https://dplms.com/', 'title': 'Home', 'status': 200, 'links': 10, 'screenshot': 'screenshots/001_page.png', 'timestamp': '2026-08-25T10:00:00'},
            {'url': 'https://dplms.com/product', 'title': 'Product', 'status': 200, 'links': 10, 'screenshot': 'screenshots/002_page.png', 'timestamp': '2026-08-25T10:00:00'},
        ]
        crawl_result['http_errors'] = [
            {
                'page': 'https://dplms.com/',
                'url': 'https://api.dplms.com/api/cart',
                'status': 500,
                'method': 'GET',
                'resource_type': 'xhr',
            },
            {
                'page': 'https://dplms.com/product',
                'url': 'https://api.dplms.com/api/cart',
                'status': 500,
                'method': 'POST',
                'resource_type': 'xhr',
            }
        ]
        
        classifier = QAFindingClassifier(self.target_domain, crawl_result)
        findings = classifier.classify()
        
        # Should create 2 page-level findings
        self.assertEqual(len(findings), 2)
        
        # Should create 2 separate root-cause candidates (different methods)
        self.assertEqual(len(classifier.root_cause_candidates), 2)
        
        methods = {c['method'] for c in classifier.root_cause_candidates}
        self.assertEqual(methods, {'GET', 'POST'})

    def test_root_cause_key_deterministic(self):
        """Test that root-cause keys are deterministic."""
        classifier = QAFindingClassifier(self.target_domain, self.base_crawl_result)
        
        # Same input should produce same key
        key1 = classifier.generate_root_cause_key(
            'https://api.dplms.com/api/cart?tenant=default', 401, 'GET'
        )
        key2 = classifier.generate_root_cause_key(
            'https://api.dplms.com/api/cart?tenant=default', 401, 'GET'
        )
        self.assertEqual(key1, key2)
        
        # Different inputs should produce different keys for non-auth
        key3 = classifier.generate_root_cause_key(
            'https://api.dplms.com/api/auth/me?tenant=default', 500, 'GET'
        )
        self.assertNotEqual(key1, key3)
        
        # For auth errors, different paths on the same host should produce the same key
        key4 = classifier.generate_root_cause_key(
            'https://api.dplms.com/api/cart?tenant=default', 401, 'GET'
        )
        key5 = classifier.generate_root_cause_key(
            'https://api.dplms.com/api/auth/me?tenant=default', 401, 'GET'
        )
        self.assertEqual(key4, key5)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestQAFindingClassifier)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
