"""
Supabase Storage Manager for Autonomous QA Agent (JASUSS.TECH).

Provides bucket storage for scan reports (JSON, Markdown, PDF, Excel),
enforcing a strict 20 MB storage limit per user and enabling direct,
instant downloads without re-generating report files.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger("ai_qa_agent.supabase_storage")

USER_STORAGE_LIMIT_BYTES = 20 * 1024 * 1024  # Strict 20 MB per user
BUCKET_NAME = "reports"

MIME_TYPES = {
    "json": "application/json",
    "md": "text/markdown; charset=utf-8",
    "markdown": "text/markdown; charset=utf-8",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def get_supabase_client():
    """Initialize and return a Supabase client using environment variables."""
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        logger.warning("Supabase credentials not found in environment (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).")
        return None

    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as error:
        logger.error("Failed to initialize Supabase client: %s", error)
        return None


def ensure_bucket_exists(client=None) -> bool:
    """Ensure the reports bucket exists in Supabase Storage."""
    sb = client or get_supabase_client()
    if not sb:
        return False

    try:
        buckets = sb.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        if BUCKET_NAME not in bucket_names:
            sb.storage.create_bucket(
                BUCKET_NAME,
                options={"public": False, "file_size_limit": USER_STORAGE_LIMIT_BYTES},
            )
            logger.info("Created Supabase storage bucket '%s'", BUCKET_NAME)
        return True
    except Exception as error:
        logger.warning("Error verifying/creating Supabase bucket '%s': %s", BUCKET_NAME, error)
        return False


def get_user_storage_usage(user_id: str, client=None) -> Dict[str, Any]:
    """
    Calculate the total storage (in bytes) used by the user in the reports bucket.
    Enforces the 20 MB limit.
    """
    sb = client or get_supabase_client()
    if not sb:
        return {
            "used_bytes": 0,
            "limit_bytes": USER_STORAGE_LIMIT_BYTES,
            "used_mb": 0.0,
            "limit_mb": 20.0,
            "used_percent": 0.0,
            "remaining_bytes": USER_STORAGE_LIMIT_BYTES,
            "file_count": 0,
        }

    total_bytes = 0
    file_count = 0
    safe_uid = str(user_id).strip()

    try:
        items = sb.storage.from_(BUCKET_NAME).list(safe_uid)
        for item in items:
            # If item is a folder (metadata is None or id is None)
            if item.get("id") is None or item.get("metadata") is None:
                folder_name = item.get("name")
                if folder_name:
                    sub_items = sb.storage.from_(BUCKET_NAME).list(f"{safe_uid}/{folder_name}")
                    for sit in sub_items:
                        size = sit.get("metadata", {}).get("size") if sit.get("metadata") else 0
                        if size:
                            total_bytes += int(size)
                            file_count += 1
            else:
                size = item.get("metadata", {}).get("size") if item.get("metadata") else 0
                if size:
                    total_bytes += int(size)
                    file_count += 1
    except Exception as error:
        logger.warning("Could not calculate storage usage for user %s: %s", safe_uid, error)

    used_mb = round(total_bytes / (1024 * 1024), 2)
    limit_mb = round(USER_STORAGE_LIMIT_BYTES / (1024 * 1024), 2)
    used_percent = min(100.0, round((total_bytes / USER_STORAGE_LIMIT_BYTES) * 100, 1))
    remaining_bytes = max(0, USER_STORAGE_LIMIT_BYTES - total_bytes)

    return {
        "used_bytes": total_bytes,
        "limit_bytes": USER_STORAGE_LIMIT_BYTES,
        "used_mb": used_mb,
        "limit_mb": limit_mb,
        "used_percent": used_percent,
        "remaining_bytes": remaining_bytes,
        "file_count": file_count,
        "is_quota_exceeded": total_bytes >= USER_STORAGE_LIMIT_BYTES,
    }


def upload_scan_reports(
    user_id: str,
    scan_id: str,
    local_files: Dict[str, str],
    client=None,
) -> Dict[str, Any]:
    """
    Upload generated reports to Supabase Storage under {user_id}/{scan_id}/report.{ext}.
    Verifies that the user will not exceed their 20 MB storage limit.
    """
    sb = client or get_supabase_client()
    if not sb:
        return {"success": False, "reason": "supabase_not_configured"}

    ensure_bucket_exists(sb)

    safe_uid = str(user_id).strip()
    safe_scan_id = str(scan_id).strip()

    # Calculate upload size
    upload_size = 0
    valid_files = {}
    for ext, path_str in local_files.items():
        if path_str and os.path.isfile(path_str):
            size = os.path.getsize(path_str)
            upload_size += size
            valid_files[ext] = path_str

    if not valid_files:
        return {"success": False, "reason": "no_files_found"}

    # Check 20 MB Quota
    usage = get_user_storage_usage(safe_uid, client=sb)
    if (usage["used_bytes"] + upload_size) > USER_STORAGE_LIMIT_BYTES:
        msg = (
            f"Storage quota exceeded for user {safe_uid}. "
            f"Current used: {usage['used_mb']} MB, Upload size: {round(upload_size / (1024 * 1024), 2)} MB, "
            f"Allocated limit: 20 MB."
        )
        logger.warning(msg)
        return {
            "success": False,
            "reason": "quota_exceeded",
            "message": "Bucket storage limit of 20 MB exceeded. Please delete older reports to upload new ones.",
            "usage": usage,
        }

    uploaded = {}
    signed_urls = {}

    for ext, local_path in valid_files.items():
        canonical_ext = "xlsx" if ext in ("excel", "xlsx") else ("md" if ext in ("markdown", "md") else ext)
        storage_path = f"{safe_uid}/{safe_scan_id}/report.{canonical_ext}"
        mime_type = MIME_TYPES.get(canonical_ext, "application/octet-stream")

        try:
            with open(local_path, "rb") as f:
                content = f.read()

            sb.storage.from_(BUCKET_NAME).upload(
                storage_path,
                content,
                file_options={"upsert": "true", "content-type": mime_type},
            )
            uploaded[canonical_ext] = storage_path

            # Generate 24-hour signed download URL for direct access
            signed_res = sb.storage.from_(BUCKET_NAME).create_signed_url(storage_path, 86400)
            if signed_res and isinstance(signed_res, dict):
                signed_urls[canonical_ext] = signed_res.get("signedURL") or signed_res.get("signedUrl")
            elif signed_res and hasattr(signed_res, "signed_url"):
                signed_urls[canonical_ext] = signed_res.signed_url

            logger.info("Uploaded report %s to Supabase storage (%s bytes)", storage_path, len(content))
        except Exception as error:
            logger.error("Failed to upload %s to Supabase storage: %s", storage_path, error)

    return {
        "success": True,
        "uploaded": uploaded,
        "signed_urls": signed_urls,
        "usage": get_user_storage_usage(safe_uid, client=sb),
    }


def get_scan_report_file(user_id: str, scan_id: str, file_type: str, client=None) -> Optional[bytes]:
    """Download stored report bytes directly from Supabase Storage without re-generating."""
    sb = client or get_supabase_client()
    if not sb:
        return None

    canonical_ext = "xlsx" if file_type in ("excel", "xlsx") else ("md" if file_type in ("markdown", "md") else file_type)
    storage_path = f"{str(user_id).strip()}/{str(scan_id).strip()}/report.{canonical_ext}"

    try:
        data = sb.storage.from_(BUCKET_NAME).download(storage_path)
        if data:
            return data
    except Exception as error:
        logger.debug("Report %s not found in Supabase Storage: %s", storage_path, error)

    return None


def get_scan_report_signed_url(user_id: str, scan_id: str, file_type: str, expires_in: int = 3600, client=None) -> Optional[str]:
    """Return a direct signed download URL from Supabase Storage."""
    sb = client or get_supabase_client()
    if not sb:
        return None

    canonical_ext = "xlsx" if file_type in ("excel", "xlsx") else ("md" if file_type in ("markdown", "md") else file_type)
    storage_path = f"{str(user_id).strip()}/{str(scan_id).strip()}/report.{canonical_ext}"

    try:
        res = sb.storage.from_(BUCKET_NAME).create_signed_url(storage_path, expires_in)
        if isinstance(res, dict):
            return res.get("signedURL") or res.get("signedUrl")
        elif hasattr(res, "signed_url"):
            return res.signed_url
    except Exception as error:
        logger.debug("Could not create signed URL for %s: %s", storage_path, error)

    return None


def delete_scan_reports(user_id: str, scan_id: str, client=None) -> bool:
    """Delete all report files for a given scan from Supabase Storage to free up user's 20 MB quota."""
    sb = client or get_supabase_client()
    if not sb:
        return False

    safe_uid = str(user_id).strip()
    safe_scan_id = str(scan_id).strip()
    folder_path = f"{safe_uid}/{safe_scan_id}"

    try:
        items = sb.storage.from_(BUCKET_NAME).list(folder_path)
        if items:
            paths_to_delete = [f"{folder_path}/{item['name']}" for item in items if item.get("name")]
            if paths_to_delete:
                sb.storage.from_(BUCKET_NAME).remove(paths_to_delete)
                logger.info("Deleted %d files from Supabase storage for scan %s", len(paths_to_delete), safe_scan_id)
        return True
    except Exception as error:
        logger.error("Failed to delete scan reports from Supabase storage for %s: %s", safe_scan_id, error)
        return False
