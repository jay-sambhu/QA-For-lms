"""
Strongly typed Pydantic models for Defects & Deduplication.
"""
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class DefectSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DefectVerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    REPRODUCED = "reproduced"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    NEEDS_REVIEW = "needs_review"


class DefectModel(BaseModel):
    defect_id: str
    fingerprint: str
    title: str
    description: str
    severity: DefectSeverity
    priority: str = "P2"
    verification_status: DefectVerificationStatus = DefectVerificationStatus.UNVERIFIED
    reproducibility: str = "100%"
    occurrence_count: int = 1
    first_seen: str
    last_seen: str
    affected_url: str
    affected_endpoint: Optional[str] = None
    reproduction_steps: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    root_cause_hypothesis: Optional[str] = None
    confidence_score: float = 1.0
