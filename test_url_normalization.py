#!/usr/bin/env python3
"""
Test suite for URL normalization in the crawler.
"""

import sys
import tempfile

from crawler.crawler import WebsiteCrawler


def make_crawler():
    """Build a crawler whose output dirs land in a temp dir, not the repo.

    WebsiteCrawler creates results/ and screenshots/<run_id>/ in its output
    directory at construction time, so instantiating it with the default
    (cwd) left a trail of empty directories in the repo on every test run.
    """
    return WebsiteCrawler(
        "https://dplms.com",
        max_pages=30,
        output_dir=tempfile.mkdtemp(prefix="qa_url_test_"),
    )


def test_url_normalization():
    """Test all URL normalization cases."""
    
    # Create a crawler instance to test normalize_url method
    crawler = make_crawler()
    
    test_cases = [
        # (input_url, expected_output, description)
        ("https://dplms.com", "https://dplms.com/", "Root URL without trailing slash"),
        ("https://dplms.com/", "https://dplms.com/", "Root URL with trailing slash"),
        ("https://DPLMS.COM/", "https://dplms.com/", "Uppercase hostname"),
        ("https://dplms.com/#pricing", "https://dplms.com/", "Root URL with fragment"),
        ("https://dplms.com/#anything", "https://dplms.com/", "Root URL with different fragment"),
        ("https://dplms.com/pricing#plans", "https://dplms.com/pricing", "Non-root URL with fragment"),
        ("https://dplms.com/pricing#faq", "https://dplms.com/pricing", "Non-root URL with different fragment"),
        ("https://DPLMS.COM/Product", "https://dplms.com/Product", "Mixed case path (preserves path case)"),
        ("https://dplms.com/product/", "https://dplms.com/product", "Non-root URL with trailing slash"),
        ("https://dplms.com/search?q=lms", "https://dplms.com/search?q=lms", "URL with query parameters"),
        ("https://DPLMS.COM/search?q=lms", "https://dplms.com/search?q=lms", "Uppercase with query parameters"),
        ("https://dplms.com/search?q=lms#results", "https://dplms.com/search?q=lms", "URL with query and fragment"),
        ("https://dplms.com/product/?id=1", "https://dplms.com/product?id=1", "Path with trailing slash and query"),
        ("https://dplms.com/dir/page", "https://dplms.com/dir/page", "Multi-level path without trailing slash"),
        ("https://dplms.com/dir/page/", "https://dplms.com/dir/page", "Multi-level path with trailing slash"),
    ]
    
    print("Running URL Normalization Tests")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for input_url, expected, description in test_cases:
        result = crawler.normalize_url(input_url)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"\n{status}: {description}")
        print(f"  Input:    {input_url}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0


def test_visited_set_deduplication():
    """Test that equivalent URLs are treated as the same in the visited set."""
    
    print("\n\nTesting Visited Set Deduplication")
    print("=" * 80)
    
    crawler = make_crawler()

    # Add equivalent URLs to the visited set
    url1 = crawler.normalize_url("https://dplms.com")
    url2 = crawler.normalize_url("https://dplms.com/")
    url3 = crawler.normalize_url("https://DPLMS.COM/")
    
    crawler.visited.add(url1)
    crawler.visited.add(url2)
    crawler.visited.add(url3)
    
    print("\nAdded 3 equivalent URLs to visited set:")
    print(f"  1. {url1}")
    print(f"  2. {url2}")
    print(f"  3. {url3}")
    
    print(f"\nVisited set size: {len(crawler.visited)}")
    print(f"Visited set contents: {crawler.visited}")
    
    if len(crawler.visited) == 1:
        print("\n✓ PASS: All equivalent URLs resulted in a single entry in visited set")
        return True
    else:
        print("\n✗ FAIL: Equivalent URLs were not deduplicated")
        return False


def test_queue_deduplication():
    """Test that equivalent URLs don't get added to queue twice."""
    
    print("\n\nTesting Queue Deduplication")
    print("=" * 80)
    
    crawler = make_crawler()

    # Clear the initial queue
    crawler.queue.clear()
    
    url1 = crawler.normalize_url("https://dplms.com/page")
    url2 = crawler.normalize_url("https://dplms.com/page/")
    
    print("\nTesting with equivalent URLs:")
    print(f"  URL 1: {url1}")
    print(f"  URL 2: {url2}")
    
    # Add first URL
    if url1 not in crawler.visited and url1 not in crawler.queue:
        crawler.queue.append(url1)
    
    # Try to add second (equivalent) URL
    if url2 not in crawler.visited and url2 not in crawler.queue:
        crawler.queue.append(url2)
    
    print(f"\nQueue size: {len(crawler.queue)}")
    print(f"Queue contents: {crawler.queue}")
    
    if len(crawler.queue) == 1:
        print("\n✓ PASS: Equivalent URLs were not added to queue twice")
        return True
    else:
        print("\n✗ FAIL: Equivalent URLs were added to queue multiple times")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("CRAWLER URL NORMALIZATION TEST SUITE")
    print("=" * 80)
    
    test1_pass = test_url_normalization()
    test2_pass = test_visited_set_deduplication()
    test3_pass = test_queue_deduplication()
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    all_pass = test1_pass and test2_pass and test3_pass
    
    if all_pass:
        print("✓ All tests PASSED!")
        sys.exit(0)
    else:
        print("✗ Some tests FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
