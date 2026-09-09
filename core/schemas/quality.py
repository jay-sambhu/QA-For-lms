"""
Strongly typed Pydantic models for Quality Gates and Scoring.
"""
from typing import List
from enum import Enum
from pydantic import BaseModel, Field


class OverallQualityStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    BLOCKED = "BLOCKED"
    INCONCLUSIVE = "INCONCLUSIVE"
    FAILED = "FAILED"


class SubscoreBreakdownModel(BaseModel):
    functional_quality: int = 100
    reliability: int = 100
    security: int = 100
    accessibility: int = 100
    performance: int = 100
    regression: int = 100
    coverage: int = 100
    confidence: int = 100


class QualityGateResultModel(BaseModel):
    overall_status: OverallQualityStatus
    health_score: int
    grade: str
    is_deployable: bool
    blocking_reasons: List[str] = Field(default_factory=list)
    warning_reasons: List[str] = Field(default_factory=list)
    subscores: SubscoreBreakdownModel = Field(default_factory=SubscoreBreakdownModel)
