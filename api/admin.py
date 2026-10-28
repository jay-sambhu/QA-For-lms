"""
Admin Dashboard & Platform Telemetry API Endpoints for JASUSS Suite (Powered by Nexus)
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict

import psutil
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func

from db import SessionLocal
from models import User, Scan, Subscription, PaymentTransaction, ApiKey, BlogPost
from core.ai_config import (
    get_ai_providers_state,
    update_ai_provider_config,
    AI_PROVIDERS_REGISTRY,
)
from api.deps import require_admin
from api.rate_limiter import make_rate_limiter
from api.secrets import decrypt_secret, encrypt_secret, mask_secret
from api.utils import celery_workers, iso_utc, redis_reachable, slugify, validate_provider_endpoint

logger = logging.getLogger("ai_qa_agent.admin")

rate_limit_admin = make_rate_limiter(240, "user", "admin")

admin_router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin & System Telemetry"],
    dependencies=[Depends(require_admin), Depends(rate_limit_admin)],
)

_PAGE = Query(50, ge=1, le=500)
_OFFSET = Query(0, ge=0)


@admin_router.get("/metrics")
def get_admin_metrics() -> Dict[str, Any]:
    """Platform-wide KPIs: MRR, users, subscription distribution, scan success rate."""
    from billing.gateways import PLANS
    with SessionLocal() as db:
        total_users = db.query(func.count(User.id)).scalar() or 0
        scan_counts = dict(db.query(Scan.status, func.count(Scan.id)).group_by(Scan.status).all())
        total_scans = sum(scan_counts.values())
        completed_scans = scan_counts.get("completed", 0)
        failed_scans = scan_counts.get("failed", 0)
        running_scans = scan_counts.get("running", 0) + scan_counts.get("pending", 0)

        active_plan_counts = dict(
            db.query(Subscription.plan_id, func.count(Subscription.id))
            .filter(Subscription.status == "active")
            .group_by(Subscription.plan_id)
            .all()
        )
        gateway_counts = dict(
            db.query(Subscription.gateway, func.count(Subscription.id))
            .filter(Subscription.status == "active")
            .group_by(Subscription.gateway)
            .all()
        )
        total_transactions = db.query(func.count(PaymentTransaction.id)).scalar() or 0

    pro_count = active_plan_counts.get("pro", 0)
    enterprise_count = active_plan_counts.get("enterprise", 0)
    paid_count = sum(c for plan, c in active_plan_counts.items() if plan != "free")
    free_count = max(0, total_users - paid_count)
    mrr_cents = sum(PLANS.get(plan, {}).get("price_cents", 0) * c for plan, c in active_plan_counts.items())
    success_rate = round((completed_scans / total_scans * 100), 1) if total_scans > 0 else 100.0

    return {
        "platform_overview": {
            "total_users": total_users,
            "total_scans": total_scans,
            "completed_scans": completed_scans,
            "failed_scans": failed_scans,
            "active_running_scans": running_scans,
            "scan_success_rate": success_rate,
        },
        "financial_metrics": {
            "mrr_usd": round(mrr_cents / 100, 2),
            "total_paid_subscriptions": paid_count,
            "plan_distribution": {
                "free": free_count,
                "pro": pro_count,
                "enterprise": enterprise_count,
            },
            "total_transactions": total_transactions,
        },
        "gateway_distribution": {
            g: gateway_counts.get(g, 0) for g in ("stripe", "lemonsqueezy", "razorpay", "paypal")
        },
    }


@admin_router.get("/users")
def list_admin_users(limit: int = _PAGE, offset: int = _OFFSET) -> Dict[str, Any]:
    """Registered users with plan tier, scan usage and role (paged)."""
    with SessionLocal() as db:
        scan_counts = (
            db.query(Scan.user_id.label("user_id"), func.count(Scan.id).label("scans_count"))
            .group_by(Scan.user_id)
            .subquery()
        )
        rows = (
            db.query(User, func.coalesce(scan_counts.c.scans_count, 0))
            .outerjoin(scan_counts, scan_counts.c.user_id == User.id)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        total = db.query(func.count(User.id)).scalar() or 0
        return {
            "users": [
                {
                    "id": u.id,
                    "email": u.email,
                    "role": u.role,
                    "plan_tier": u.plan_tier or "free",
                    "scans_count": int(count or 0),
                    "created_at": iso_utc(u.created_at),
                }
                for u, count in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@admin_router.patch("/users/{user_id}/role")
def update_user_role(user_id: str, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Elevate or demote user role between 'user' and 'admin'."""
    new_role = payload.get("role")
    if new_role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'user' or 'admin'.")
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        user.role = new_role
        db.commit()
        return {"status": "success", "user_id": user_id, "role": user.role}


@admin_router.get("/scans")
def list_admin_scans(limit: int = _PAGE, offset: int = _OFFSET) -> Dict[str, Any]:
    """Scans across all tenants, newest first (paged)."""
    with SessionLocal() as db:
        scans = db.query(Scan).order_by(Scan.created_at.desc()).offset(offset).limit(limit).all()
        total = db.query(func.count(Scan.id)).scalar() or 0
        return {
            "scans": [
                {
                    "id": s.id,
                    "user_id": s.user_id,
                    "url": s.url,
                    "status": s.status,
                    "is_authenticated": bool(s.is_authenticated),
                    "created_at": iso_utc(s.created_at),
                    "completed_at": iso_utc(s.completed_at),
                }
                for s in scans
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@admin_router.get("/system")
def get_system_telemetry() -> Dict[str, Any]:
    """Host telemetry and real worker health (Celery ping, cached)."""
    cpu_pct = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    workers = celery_workers()
    broker_up = redis_reachable(1.0)
    if workers:
        worker_status = "online"
    elif broker_up:
        worker_status = "no_workers"
    else:
        worker_status = "offline"

    return {
        "cluster_health": "operational" if workers else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "platform": "JASUSS Engine (Powered by Nexus)",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "cpu_utilization_percent": cpu_pct,
            "memory_used_mb": round(ram.used / (1024 * 1024), 1),
            "memory_total_mb": round(ram.total / (1024 * 1024), 1),
            "memory_percent": ram.percent,
        },
        "crawler_workers": {
            "status": worker_status,
            "active_nodes": len(workers or []),
            "nodes": workers or [],
            "broker": "Redis Queue (qa_queue)" if broker_up else "Redis unavailable",
            "concurrency": f"{os.getenv('WORKER_CONCURRENCY', '1')} scan(s) per worker",
        },
    }


@admin_router.get("/ai-providers")
def get_ai_providers() -> Dict[str, Any]:
    """Get all supported AI providers, active provider, model selections, and configuration state."""
    return get_ai_providers_state()


@admin_router.post("/ai-providers")
def update_ai_provider(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Update the active AI reasoning provider, API keys, custom endpoints, and models."""
    provider_id = payload.get("provider_id")
    if not provider_id:
        raise HTTPException(status_code=400, detail="provider_id is required")

    try:
        endpoint = validate_provider_endpoint(payload.get("endpoint"))
        updated = update_ai_provider_config(
            provider_id=provider_id,
            model=payload.get("model"),
            api_key=payload.get("api_key"),
            endpoint=endpoint,
            temperature=payload.get("temperature"),
            max_tokens=payload.get("max_tokens"),
        )
        return {
            "message": f"Successfully updated AI provider to {provider_id.upper()}",
            "config": updated,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _probe_provider(provider_id: str, api_key: str, model: str, endpoint: str) -> Dict[str, Any]:
    """One tiny real completion request through the same client the pipeline uses."""
    from core.gemini_analyzer import GeminiQAAnalyzer
    analyzer = GeminiQAAnalyzer(
        api_key=api_key,
        model_name=model,
        provider_id=provider_id,
        endpoint=endpoint,
    )
    started = time.monotonic()
    text = asyncio.run(analyzer._call_model("Reply with the single word: pong"))
    latency_ms = int((time.monotonic() - started) * 1000)
    return {"latency_ms": latency_ms, "model": analyzer.model_name, "sample": str(text or "")[:40]}


@admin_router.post("/ai-providers/test")
def test_ai_provider(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Verify a provider key by making a minimal real request."""
    provider_id = str(payload.get("provider_id", "gemini")).lower()
    if provider_id not in AI_PROVIDERS_REGISTRY:
        raise HTTPException(status_code=400, detail="Unsupported AI provider")

    meta = AI_PROVIDERS_REGISTRY[provider_id]
    key = (payload.get("api_key") or os.environ.get(meta.env_key_name) or "").strip()
    if not key and provider_id != "local_llm":
        return {
            "status": "warning",
            "message": f"No API key provided for {meta.name}. Please enter your secret key.",
            "provider": provider_id,
        }
    try:
        endpoint = validate_provider_endpoint(payload.get("endpoint") or meta.default_endpoint)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    model = (payload.get("model") or meta.default_model or "").strip()

    try:
        probe = _probe_provider(provider_id, key or "local", model, endpoint)
    except Exception as error:
        message = str(error).replace(key, "[REDACTED]") if key else str(error)
        logger.warning("Provider test failed for %s: %s", provider_id, message[:300])
        return {
            "status": "error",
            "message": f"{meta.name} rejected the request: {message[:200]}",
            "provider": provider_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": "success",
        "message": f"Connection to {meta.name} verified ({probe['model']}). Latency: {probe['latency_ms']}ms.",
        "provider": provider_id,
        "latency_ms": probe["latency_ms"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@admin_router.get("/api-keys")
def list_api_keys() -> Dict[str, Any]:
    """List the server-side key pool (masked)."""
    with SessionLocal() as db:
        keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
        return {
            "api_keys": [
                {
                    "id": k.id,
                    "key_value": mask_secret(k.key_value),
                    "status": k.status,
                    "service": k.service,
                    "rate_limit_reset_at": iso_utc(k.rate_limit_reset_at),
                    "created_at": iso_utc(k.created_at),
                }
                for k in keys
            ]
        }


@admin_router.post("/api-keys")
def add_api_key(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Add a key to the server-side pool (encrypted at rest)."""
    key_value = str(payload.get("key_value") or "").strip()
    service = str(payload.get("service") or "gemini").strip().lower()
    if not key_value:
        raise HTTPException(status_code=400, detail="key_value is required")
    if len(key_value) > 512:
        raise HTTPException(status_code=400, detail="key_value is too long")

    with SessionLocal() as db:
        for existing in db.query(ApiKey).all():
            if decrypt_secret(existing.key_value) == key_value:
                raise HTTPException(status_code=400, detail="API Key already exists")
        new_key = ApiKey(key_value=encrypt_secret(key_value), service=service, status="active")
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        return {"message": "API key added successfully", "id": new_key.id}


@admin_router.delete("/api-keys/{key_id}")
def delete_api_key(key_id: str) -> Dict[str, Any]:
    """Delete an API key."""
    with SessionLocal() as db:
        key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if not key:
            raise HTTPException(status_code=404, detail="API Key not found")
        db.delete(key)
        db.commit()
        return {"message": "API key deleted successfully"}


# ---------------------------------------------------------------------------
# Dynamic Admin Blog Management Endpoints
# ---------------------------------------------------------------------------

def _content_to_str(value) -> str:
    return json.dumps(value) if isinstance(value, list) else str(value)


def _tags_to_str(value) -> str:
    if isinstance(value, list):
        return json.dumps([str(t).strip() for t in value if str(t).strip()])
    return str(value or "")


@admin_router.get("/blogs")
def list_admin_blogs() -> Dict[str, Any]:
    """List all blog posts (published & drafts) with status counts."""
    with SessionLocal() as db:
        posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
        status_counts = dict(db.query(BlogPost.status, func.count(BlogPost.id)).group_by(BlogPost.status).all())
        return {
            "blogs": [p.to_dict() for p in posts],
            "stats": {
                "total": sum(status_counts.values()),
                "published": status_counts.get("published", 0),
                "drafts": status_counts.get("draft", 0),
            },
        }


@admin_router.post("/blogs")
def create_blog_post(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Admin creates a new dynamic blog post."""
    author = payload.get("author") if isinstance(payload.get("author"), dict) else {}
    title = (payload.get("title") or "").strip()
    excerpt = (payload.get("excerpt") or "").strip()
    raw_content = payload.get("content") or ""
    category = (payload.get("category") or "AI & Automation").strip()
    reading_time = (payload.get("reading_time") or payload.get("readingTime") or "5 min read").strip()
    author_name = (payload.get("author_name") or author.get("name") or "Nexus Core Engineering").strip()
    author_role = (payload.get("author_role") or author.get("role") or "Platform Architecture Team").strip()
    author_avatar = (payload.get("author_avatar") or author.get("avatar") or "/logo.png").strip()
    status = payload.get("status") if payload.get("status") in ["published", "draft"] else "published"

    if not title:
        raise HTTPException(status_code=400, detail="Article title is required.")
    if not excerpt:
        raise HTTPException(status_code=400, detail="Article excerpt is required.")
    if not raw_content:
        raise HTTPException(status_code=400, detail="Article content is required.")

    with SessionLocal() as db:
        candidate_slug = (payload.get("slug") or "").strip().lower() or slugify(title)
        final_slug = candidate_slug
        suffix = 2
        while db.query(BlogPost.id).filter(BlogPost.slug == final_slug).first():
            final_slug = f"{candidate_slug}-{suffix}"
            suffix += 1

        new_post = BlogPost(
            slug=final_slug,
            title=title,
            excerpt=excerpt,
            content=_content_to_str(raw_content),
            category=category,
            tags=_tags_to_str(payload.get("tags") or []),
            author_name=author_name,
            author_role=author_role,
            author_avatar=author_avatar,
            reading_time=reading_time,
            status=status,
            published_at=datetime.now(timezone.utc) if status == "published" else None,
        )
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return {"message": "Blog post created successfully", "blog": new_post.to_dict()}


@admin_router.put("/blogs/{blog_id}")
def update_blog_post(blog_id: str, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Admin updates an existing blog post."""
    with SessionLocal() as db:
        post = db.query(BlogPost).filter(BlogPost.id == blog_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found.")

        if payload.get("title"):
            post.title = str(payload["title"]).strip()

        if payload.get("slug"):
            new_slug = slugify(str(payload["slug"]))
            if new_slug != post.slug:
                conflict = db.query(BlogPost.id).filter(BlogPost.slug == new_slug, BlogPost.id != blog_id).first()
                if conflict:
                    raise HTTPException(status_code=400, detail="Slug already in use by another article.")
                post.slug = new_slug

        if "excerpt" in payload:
            post.excerpt = str(payload["excerpt"]).strip()
        if "content" in payload:
            post.content = _content_to_str(payload["content"])
        if "category" in payload:
            post.category = str(payload["category"]).strip()
        if "tags" in payload:
            post.tags = _tags_to_str(payload["tags"])
        if payload.get("reading_time") or payload.get("readingTime"):
            post.reading_time = str(payload.get("reading_time") or payload.get("readingTime")).strip()

        author = payload.get("author") if isinstance(payload.get("author"), dict) else {}
        author_name = payload.get("author_name") or author.get("name")
        author_role = payload.get("author_role") or author.get("role")
        author_avatar = payload.get("author_avatar") or author.get("avatar")
        if author_name is not None:
            post.author_name = str(author_name).strip()
        if author_role is not None:
            post.author_role = str(author_role).strip()
        if author_avatar is not None:
            post.author_avatar = str(author_avatar).strip()

        new_status = payload.get("status")
        if new_status in ["published", "draft"]:
            if new_status == "published" and post.status != "published" and not post.published_at:
                post.published_at = datetime.now(timezone.utc)
            post.status = new_status

        db.commit()
        db.refresh(post)
        return {"message": "Blog post updated successfully", "blog": post.to_dict()}


@admin_router.patch("/blogs/{blog_id}/status")
def toggle_blog_status(blog_id: str, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Toggle or set blog post status ('published' or 'draft')."""
    target_status = payload.get("status")
    with SessionLocal() as db:
        post = db.query(BlogPost).filter(BlogPost.id == blog_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found.")

        if target_status in ["published", "draft"]:
            post.status = target_status
        else:
            post.status = "draft" if post.status == "published" else "published"

        if post.status == "published" and not post.published_at:
            post.published_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(post)
        return {
            "message": f"Article status set to {post.status}",
            "status": post.status,
            "blog": post.to_dict(),
        }


@admin_router.delete("/blogs/{blog_id}")
def delete_blog_post(blog_id: str) -> Dict[str, Any]:
    """Admin permanently deletes a blog post."""
    with SessionLocal() as db:
        post = db.query(BlogPost).filter(BlogPost.id == blog_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found.")
        db.delete(post)
        db.commit()
        return {"message": "Blog post deleted successfully", "id": blog_id}
