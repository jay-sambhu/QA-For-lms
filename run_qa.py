#!/usr/bin/env python3
import argparse
import asyncio
import os

from crawler.crawler import WebsiteCrawler
from bug_detector import generate_qa_findings
from gemini_analyzer import generate_report
from qa_report_generator import QAReportGenerator

async def main():
    parser = argparse.ArgumentParser(description="End-to-end AI QA Agent Pipeline")
    parser.add_argument("url", help="Target URL to crawl and analyze")
    parser.add_argument("--max-pages", type=int, default=30, help="Maximum pages to crawl")
    parser.add_argument("--auth-token", help="Optional Bearer token for authentication")
    
    args = parser.parse_args()
    
    print(f"Starting AI QA Pipeline for: {args.url}")
    print("=" * 60)
    
    print("\n[Stage 1] Crawling website...")
    crawler = WebsiteCrawler(args.url, max_pages=args.max_pages, auth_token=args.auth_token)
    await crawler.crawl()
    
    print("\n[Stage 2] Running deterministic bug detector...")
    generate_qa_findings()
    
    print("\n[Stage 3] Running Gemini AI analysis...")
    await generate_report()
    
    print("\n[Stage 4] Generating final QA report...")
    generator = QAReportGenerator()
    result = generator.generate()
    
    print("\nPipeline completed successfully!")
    if result:
        print(f"Final JSON: {result['json_path']}")
        print(f"Final Markdown: {result['md_path']}")

if __name__ == "__main__":
    asyncio.run(main())
