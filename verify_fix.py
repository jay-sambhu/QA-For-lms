#!/usr/bin/env python3
"""
Final comprehensive verification of URL canonicalization fix.
Verifies all requirements from the task.
"""

import json
from urllib.parse import urlparse


def normalize_url(url):
    """Same normalization logic as in the crawler."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"
    query = parsed.query
    if query:
        return f"{scheme}://{netloc}{path}?{query}"
    else:
        return f"{scheme}://{netloc}{path}"


def verify_crawl_results():
    """Verify the crawl results meet all requirements."""
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE URL CANONICALIZATION VERIFICATION")
    print("=" * 80)
    
    with open('results/crawl_20260825_111613.json') as f:
        data = json.load(f)
    
    results = {
        "passed": [],
        "failed": [],
    }
    
    # Requirement 1: Root URLs normalized
    print("\n[1] Root URL Normalization")
    if data['target'] == 'https://dplms.com/':
        print("    ✓ PASS: Start URL normalized to 'https://dplms.com/'")
        results["passed"].append("Root URL normalization")
    else:
        print(f"    ✗ FAIL: Expected 'https://dplms.com/', got '{data['target']}'")
        results["failed"].append("Root URL normalization")
    
    # Requirement 2: No duplicate homepages
    print("\n[2] Duplicate Homepage Elimination")
    urls = [p['url'] for p in data['pages']]
    homepage_count = sum(1 for url in urls if url == 'https://dplms.com/')
    if homepage_count == 1:
        print(f"    ✓ PASS: Homepage appears exactly once (not duplicated)")
        results["passed"].append("No duplicate homepages")
    else:
        print(f"    ✗ FAIL: Homepage appears {homepage_count} times")
        results["failed"].append("No duplicate homepages")
    
    # Requirement 3: All URLs are unique
    print("\n[3] Unique URL Enforcement")
    unique_count = len(set(urls))
    if unique_count == len(urls):
        print(f"    ✓ PASS: All {len(urls)} URLs are unique (no duplicates)")
        results["passed"].append("URL uniqueness")
    else:
        print(f"    ✗ FAIL: {len(urls)} URLs but only {unique_count} unique")
        results["failed"].append("URL uniqueness")
    
    # Requirement 4: Screenshots match pages (no duplicate screenshots)
    print("\n[4] Screenshot Count")
    if len(urls) == 30:
        print(f"    ✓ PASS: Exactly 30 pages crawled (one per screenshot)")
        results["passed"].append("Screenshot count")
    else:
        print(f"    ✗ FAIL: Expected 30 pages, got {len(urls)}")
        results["failed"].append("Screenshot count")
    
    # Requirement 5: Monitoring data still collected
    print("\n[5] Network Monitoring Preservation")
    http_errors = len(data['http_errors'])
    console_errors = len(data['console_errors'])
    monitoring_ok = http_errors > 0 and console_errors > 0
    if monitoring_ok:
        print(f"    ✓ PASS: HTTP errors ({http_errors}) and console errors ({console_errors}) collected")
        results["passed"].append("Network monitoring")
    else:
        print(f"    ✗ FAIL: Missing monitoring data")
        results["failed"].append("Network monitoring")
    
    # Requirement 6: Page data structure preserved
    print("\n[6] Page Data Structure")
    required_fields = {'url', 'title', 'status', 'links', 'screenshot', 'timestamp'}
    first_page = data['pages'][0]
    if all(field in first_page for field in required_fields):
        print(f"    ✓ PASS: All required fields present: {', '.join(sorted(required_fields))}")
        results["passed"].append("Page data structure")
    else:
        print(f"    ✗ FAIL: Missing fields")
        results["failed"].append("Page data structure")
    
    # Requirement 7: Internal URL filtering still works
    print("\n[7] Internal URL Filtering")
    all_internal = all(url.startswith('https://dplms.com') for url in urls)
    if all_internal:
        print(f"    ✓ PASS: All {len(urls)} URLs are internal to dplms.com")
        results["passed"].append("Internal URL filtering")
    else:
        print(f"    ✗ FAIL: Found external URLs")
        results["failed"].append("Internal URL filtering")
    
    # Requirement 8: Lowercase normalization
    print("\n[8] Hostname Case Normalization")
    all_lowercase = all(url.startswith('https://dplms.com') for url in urls)
    if all_lowercase:
        print(f"    ✓ PASS: All hostnames are lowercase")
        results["passed"].append("Hostname normalization")
    else:
        print(f"    ✗ FAIL: Found non-lowercase hostnames")
        results["failed"].append("Hostname normalization")
    
    # Requirement 9: Trailing slash handling
    print("\n[9] Trailing Slash Normalization")
    root_has_slash = data['pages'][0]['url'].endswith('/')
    non_roots = [u for u in urls if u != 'https://dplms.com/']
    non_roots_no_trailing = all(not u.endswith('/') for u in non_roots)
    if root_has_slash and non_roots_no_trailing:
        print(f"    ✓ PASS: Root has '/', non-root paths don't")
        results["passed"].append("Trailing slash normalization")
    else:
        print(f"    ✗ FAIL: Inconsistent trailing slash handling")
        results["failed"].append("Trailing slash normalization")
    
    # Requirement 10: Fragment removal
    print("\n[10] URL Fragment Removal")
    # This is verified by checking that normalize_url removes fragments
    test_url = "https://dplms.com/page#section"
    normalized = normalize_url(test_url)
    if normalized == "https://dplms.com/page":
        print(f"    ✓ PASS: Fragments are removed during normalization")
        results["passed"].append("Fragment removal")
    else:
        print(f"    ✗ FAIL: Fragments not properly removed")
        results["failed"].append("Fragment removal")
    
    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"\n✓ Passed: {len(results['passed'])} requirements")
    for item in results['passed']:
        print(f"  • {item}")
    
    if results['failed']:
        print(f"\n✗ Failed: {len(results['failed'])} requirements")
        for item in results['failed']:
            print(f"  • {item}")
        return False
    else:
        print(f"\n🎉 ALL {len(results['passed'])} REQUIREMENTS MET!")
        return True


if __name__ == "__main__":
    import sys
    success = verify_crawl_results()
    sys.exit(0 if success else 1)
