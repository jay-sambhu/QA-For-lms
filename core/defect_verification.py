"""
Autonomous Defect Detection, Verification Loop, and Fingerprint Deduplication Engine (Phase 8).

Fingerprints are computed on the detector's device-agnostic root_cause_key,
so one defect seen on three viewports is one defect. Nothing here verifies a
defect by re-running it, so verification_status is UNVERIFIED and the
confidence is the detector's.
"""
import hashlib
import json
import os
import time
from typing import Dict, List, Any, Optional

from core.schemas.defect import DefectModel, DefectSeverity, DefectVerificationStatus

_CONFIDENCE_SCORE = {"high": 0.9, "medium": 0.6, "low": 0.3}


class DefectVerificationEngine:
    def __init__(self, raw_findings: List[Dict[str, Any]], results_dir: str, run_id: str, target: Optional[str] = None):
        self.raw_findings = raw_findings
        self.results_dir = results_dir
        self.run_id = run_id
        self.target = (target or "").strip().lower()
        self.output_file = os.path.join(results_dir, f"defects_{run_id}.json")
        self.fingerprints_by_id: Dict[str, str] = {}

    @staticmethod
    def compute_fingerprint(root_cause_key: str, title: str = "", description: str = "", target: str = "") -> str:
        """Deterministic SHA256 fingerprint for defect deduplication.

        `root_cause_key` already identifies the defect across pages and
        devices; title/description only enter when no key exists."""
        if root_cause_key:
            raw_key = f"{target.strip().lower()}|{root_cause_key.strip().lower()}"
        else:
            raw_key = f"{target.strip().lower()}|{title.strip().lower()}:{description[:50].strip().lower()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def _page_of(item: Dict[str, Any]) -> str:
        pages = item.get("affected_pages") or []
        if pages:
            return str(pages[0])
        page = item.get("actual_url") or item.get("page") or item.get("url") or "unknown"
        return str(page).rsplit(" [", 1)[0]

    def process_and_deduplicate(self) -> List[DefectModel]:
        defects_map: Dict[str, DefectModel] = {}
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for item in self.raw_findings:
            url = self._page_of(item)
            title = item.get("title", "Detected Bug")
            desc = item.get("description", "Automated bug detection finding")
            severity_str = str(item.get("severity", "medium") or "medium").lower()

            try:
                severity = DefectSeverity(severity_str)
            except ValueError:
                severity = DefectSeverity.MEDIUM

            fp = self.compute_fingerprint(item.get("root_cause_key") or "", title, desc, self.target)
            if item.get("id"):
                self.fingerprints_by_id[str(item["id"])] = fp

            occurrences = int(item.get("occurrences") or item.get("deduplicated_count") or 1)
            page_count = int(item.get("affected_page_count") or len(item.get("affected_pages") or []) or 1)
            devices = item.get("affected_devices") or []

            if fp in defects_map:
                # Deduplicate: increment occurrence count
                existing = defects_map[fp]
                existing.occurrence_count += occurrences
                existing.last_seen = now
            else:
                defect_id = f"DEF-{len(defects_map)+1:03d}"
                confidence = _CONFIDENCE_SCORE.get(str(item.get("confidence") or "").lower(), 0.5)
                defects_map[fp] = DefectModel(
                    defect_id=defect_id,
                    fingerprint=fp,
                    title=title,
                    description=desc,
                    severity=severity,
                    priority=item.get("priority", "P2"),
                    verification_status=DefectVerificationStatus.UNVERIFIED,
                    reproducibility=(
                        f"observed {occurrences} time(s) on {page_count} page(s)"
                        + (f" across {len(devices)} viewport(s)" if devices else "")
                    ),
                    occurrence_count=occurrences,
                    first_seen=now,
                    last_seen=now,
                    affected_url=url,
                    affected_endpoint=item.get("url") or None,
                    evidence={"raw": item},
                    confidence_score=confidence,
                )

        defects_list = list(defects_map.values())

        os.makedirs(self.results_dir, exist_ok=True)
        dump_data = [d.model_dump() for d in defects_list]
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)

        # Generate Evidence Manifest
        manifest_path = os.path.join(self.results_dir, f"evidence_manifest_{self.run_id}.json")
        manifest_entries = []
        for d in defects_list:
            raw = d.evidence.get("raw", {})
            evidence = raw.get("evidence", {}) or {}
            manifest_entries.append({
                "defect_id": d.defect_id,
                "fingerprint": d.fingerprint,
                "title": d.title,
                "affected_url": d.affected_url,
                "severity": d.severity.value if hasattr(d.severity, "value") else str(d.severity),
                "verification_status": d.verification_status.value if hasattr(d.verification_status, "value") else str(d.verification_status),
                "reproduction_count": d.occurrence_count,
                "confidence_score": d.confidence_score,
                "evidence_sources": [
                    source for source, present in (
                        ("screenshot", bool(raw.get("screenshots") or raw.get("screenshot"))),
                        ("console_error", bool(evidence.get("console_errors"))),
                        ("http_error", bool(evidence.get("http_errors"))),
                        ("network_failure", bool(evidence.get("network_failures"))),
                        ("responsive_check", bool(evidence.get("responsive_checks"))),
                    ) if present
                ],
            })
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"manifest": manifest_entries, "generated_at": now}, f, indent=2)

        return defects_list
