"""
Public & Dynamic Blog Engine API Endpoints for JASUSS Suite
Handles dynamic blog post retrieval, categorization, and automatic database seeding.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import re

from db import SessionLocal
from models import BlogPost

blogs_router = APIRouter(
    prefix="/api/v1/blogs",
    tags=["Public Blogs"],
)

INITIAL_SEED_POSTS = [
    {
        "slug": "autonomous-web-qa-revolution",
        "title": "The Autonomous Web QA Revolution: Replacing Scripted Test Suites with AI Multi-Viewport Agents",
        "excerpt": "How AI-driven crawlers and synthetic user agents are eliminating brittle Selenium/Cypress test scripts and detecting silent visual & functional regressions.",
        "category": "AI & Automation",
        "reading_time": "5 min read",
        "author_name": "Nexus Core Engineering",
        "author_role": "Platform Architecture Team",
        "author_avatar": "/logo.png",
        "tags": json.dumps(["Autonomous QA", "Regression Testing", "Playwright", "Nexus Engine"]),
        "status": "published",
        "published_at": datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc),
        "content": json.dumps([
            "Traditional end-to-end testing has reached a critical breaking point in modern continuous delivery pipelines. For years, development teams have poured thousands of engineering hours into writing and maintaining fragile Selenium, Cypress, and Playwright scripts. When a CSS selector changes by a single class name, or an asynchronous animation delays by 200 milliseconds, automated builds turn red with false positives.",
            "The fundamental flaw of scripted QA is that scripts are deterministic assertions over non-deterministic, dynamic web user interfaces. A script only tests what the engineer thought to assert yesterday, leaving zero-day edge cases, responsive layout collisions, and asynchronous state corruptions completely unmonitored.",
            "### The Emergence of Autonomous Quality Assurance",
            "Autonomous Web QA reimagines the verification lifecycle from the ground up. Instead of hardcoded element selectors (`#submit-btn`), an autonomous agent utilizes multi-modal computer vision and accessibility tree synthesis to comprehend web applications as actual human users experience them.",
            "By combining headless browser clusters with intelligent heuristics, autonomous agents can:",
            "- Navigate complex interactive flows (authentication, multi-step forms, shopping carts) without pre-scripted locators.",
            "- Execute synthetic interaction testing across simultaneous viewports (Desktop 4K, Tablet, Mobile portrait/landscape) to surface responsive breakpoints.",
            "- Automatically catalog DOM mutations, unhandled promise rejections, network payload anomalies, and layout shifts.",
            "### Beyond Assertions: Deterministic Defect Triage",
            "When a regression is discovered, traditional CI runners merely dump cryptic stack traces. Autonomous QA agents perform automated root-cause triage: capturing high-definition video evidence, generating precise console exception logs, calculating WCAG accessibility compliance scores, and estimating severity based on user journey impact.",
            "The future of software testing is not writing more scripts—it is deploying autonomous systems that verify your digital experiences continuously."
        ]),
    },
    {
        "slug": "mastering-multi-viewport-testing",
        "title": "Mastering Multi-Viewport Testing: Preventing UI Breakages on Mobile, Tablet & Foldable Screens",
        "excerpt": "A deep dive into responsive web testing: container queries, fluid typography, touch target compliance, and detecting viewport-specific layout shifts.",
        "category": "Responsive Design",
        "reading_time": "7 min read",
        "author_name": "Aira Sharma",
        "author_role": "Principal Frontend Architect",
        "author_avatar": "/logo.png",
        "tags": json.dumps(["Mobile UX", "Tablet Testing", "CSS Breakpoints", "Core Web Vitals"]),
        "status": "published",
        "published_at": datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc),
        "content": json.dumps([
            "More than 58% of global web traffic originates from mobile devices and tablets, yet the vast majority of QA suites continue to test exclusively on a 1920x1080 desktop browser. This creates an enormous quality gap where critical user-facing bugs slip into production unnoticed.",
            "Responsive bugs rarely manifest as total page crashes. Instead, they are subtle and insidious: sticky navigation menus overflowing modal dialogs, buttons slipping below the virtual keyboard viewport, text overlapping due to rigid line-height declarations, or tap targets shrinking below accessibility thresholds.",
            "### The Three Pillars of Multi-Viewport Verification",
            "To ensure seamless rendering across modern hardware, modern automated quality assurance must audit three distinct viewport dimensions simultaneously:",
            "1. **Mobile Viewports (360px – 430px)**: Validating touch target compliance (minimum 48x48px per WCAG 2.2 guidelines), preventing horizontal micro-scrolling, and ensuring navigation drawers transition smoothly without body scroll leaks.",
            "2. **Tablet Viewports (768px – 1024px)**: Auditing dual-column flex grids, sticky sidebar behavior, and responsive media transitions where desktop and mobile CSS rules frequently conflict.",
            "3. **Desktop & Ultra-wide (1280px – 3840px)**: Verifying maximum container boundaries, typography scaling, and high-DPI asset rendering.",
            "### Automated Layout Shift Detection (CLS)",
            "Multi-viewport auditing also measures Cumulative Layout Shift (CLS) on dynamic screen sizes. When responsive images lack explicit aspect-ratio attributes or dynamic ad banners pop into view without reserved DOM spacing, mobile users experience jarring content jumps.",
            "With JASUSS.TECH's automated multi-viewport synthesis, every page is rendered and stress-tested simultaneously across desktop, tablet, and mobile configurations before shipping to end users."
        ]),
    },
    {
        "slug": "synthetic-user-simulation-vs-rum",
        "title": "Synthetic User Simulation vs Real User Monitoring: Finding Zero-Day Defects Before Users Do",
        "excerpt": "Why waiting for real user error telemetry in production costs 10x more than preemptive synthetic exploration and automated defect triage.",
        "category": "Quality Engineering",
        "reading_time": "6 min read",
        "author_name": "Karan Adhikari",
        "author_role": "Lead Reliability Engineer",
        "author_avatar": "/logo.png",
        "tags": json.dumps(["Synthetic Testing", "RUM", "Error Monitoring", "DevOps"]),
        "status": "published",
        "published_at": datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc),
        "content": json.dumps([
            "In the modern telemetry landscape, engineering organizations frequently rely on Real User Monitoring (RUM) tools like Sentry, Datadog, or LogRocket. While RUM is invaluable for tracking production exceptions, relying solely on RUM for quality assurance means treating your paying customers as your QA team.",
            "When a customer discovers a broken checkout button or a broken authentication token flow, the damage is already done: cart abandonment, brand degradation, and lost revenue.",
            "### The Proactive Power of Synthetic Exploration",
            "Synthetic user simulation simulates realistic user behaviors in staging and production environments around the clock. Unlike passive error monitoring, synthetic simulation proactively exercises critical application pathways:",
            "- Executing complex session lifecycles including cookie rotation and JWT hydration.",
            "- Testing slow 3G network throttling and high-latency edge conditions.",
            "- Simulating edge user actions such as rapid double-clicking, browser back-forward cache navigation, and autofill interaction.",
            "### Cost Comparison: Catching Defects Early",
            "Studies consistently demonstrate that repairing a defect caught during automated synthetic pre-flight checks costs roughly 1/10th of resolving an issue reported by a high-value customer.",
            "By integrating synthetic agents into your continuous deployment lifecycle, teams achieve 99.9% release confidence without sacrificing deployment velocity."
        ]),
    },
    {
        "slug": "automated-defect-triage-executive-compliance",
        "title": "Automated Defect Triage & Executive Compliance: The New Enterprise Standard",
        "excerpt": "Translating technical DOM exceptions, console errors, and performance regressions into actionable executive reports with automated severity grading.",
        "category": "Compliance & Security",
        "reading_time": "8 min read",
        "author_name": "Nexus Core Engineering",
        "author_role": "Platform Architecture Team",
        "author_avatar": "/logo.png",
        "tags": json.dumps(["Executive Reports", "Defect Triage", "Compliance", "WCAG"]),
        "status": "published",
        "published_at": datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc),
        "content": json.dumps([
            "One of the biggest communication breakdowns in software development happens between engineering teams and executive leadership. Engineers speak in terms of `TypeError: Cannot read property of undefined` or `LCP: 3800ms`. Leadership cares about user retention, conversion rates, and regulatory compliance.",
            "The role of modern QA platforms is to bridge this gap through automated defect synthesis and standardized compliance grading.",
            "### Executive Quality Scoring",
            "JASUSS.TECH aggregates thousands of low-level signals into clear, actionable executive metrics:",
            "- **Overall Quality Score (0–100%)**: Weighted composite index reflecting stability, visual integrity, and execution reliability.",
            "- **Severity Classification**: Categorizing defects into Blocker, Major, Minor, and Cosmetic based on business impact.",
            "- **Regulatory Compliance**: Automated checks for accessibility standards (WCAG 2.1 AA), privacy requirements, and Core Web Vitals thresholds.",
            "### Seamless Handoff to Engineering",
            "Each executive finding is paired with deep technical telemetry for immediate developer remediation: HAR network archives, console logs, Playwright trace logs, and exact viewport screenshots.",
            "This dual-layer approach empowers engineering leads to fix bugs in minutes while providing stakeholders with transparent, audit-ready quality reports."
        ]),
    },
]


def seed_default_blogs_if_empty():
    """Seeds default blog posts into PostgreSQL if the blog_posts table is currently empty."""
    try:
        with SessionLocal() as db:
            count = db.query(BlogPost).count()
            if count == 0:
                for item in INITIAL_SEED_POSTS:
                    post = BlogPost(
                        slug=item["slug"],
                        title=item["title"],
                        excerpt=item["excerpt"],
                        category=item["category"],
                        reading_time=item["reading_time"],
                        author_name=item["author_name"],
                        author_role=item["author_role"],
                        author_avatar=item["author_avatar"],
                        tags=item["tags"],
                        status=item["status"],
                        published_at=item["published_at"],
                        content=item["content"],
                    )
                    db.add(post)
                db.commit()
    except Exception as exc:
        print(f"[BLOG SEED ERROR] Failed to seed initial blog posts: {exc}")


@blogs_router.get("")
async def get_published_blogs(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title, excerpt, or tags"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Retrieve all published blog posts ordered chronologically."""
    with SessionLocal() as db:
        query = db.query(BlogPost).filter(BlogPost.status == "published")

        if category:
            query = query.filter(BlogPost.category.ilike(f"%{category.strip()}%"))

        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                (BlogPost.title.ilike(s)) |
                (BlogPost.excerpt.ilike(s)) |
                (BlogPost.tags.ilike(s))
            )

        total = query.count()
        posts = (
            query.order_by(BlogPost.published_at.desc(), BlogPost.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "posts": [p.to_dict() for p in posts],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@blogs_router.get("/categories")
async def get_blog_categories() -> Dict[str, Any]:
    """Retrieve distinct categories and count of published posts per category."""
    with SessionLocal() as db:
        posts = db.query(BlogPost).filter(BlogPost.status == "published").all()
        counts: Dict[str, int] = {}
        for p in posts:
            c = p.category or "General"
            counts[c] = counts.get(c, 0) + 1

        category_list = [{"name": cat, "count": cnt} for cat, cnt in sorted(counts.items())]
        return {"categories": category_list, "total": len(category_list)}


@blogs_router.get("/{slug}")
async def get_blog_by_slug(slug: str) -> Dict[str, Any]:
    """Retrieve a single published blog post by unique slug."""
    clean_slug = slug.strip().lower()
    with SessionLocal() as db:
        post = (
            db.query(BlogPost)
            .filter(BlogPost.slug == clean_slug, BlogPost.status == "published")
            .first()
        )
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found")
        return {"post": post.to_dict()}
