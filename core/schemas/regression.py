"""
Strongly typed Pydantic models for Regression & Flakiness Memory.
"""
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class RegressionStatus(str, Enum):
    NEW_FAILURE = "NEW_FAILURE"
    FIXED = "FIXED"
    REGRESSION = "REGRESSION"
    FLAKY = "FLAKY"
    UNCHANGED = "UNCHANGED"
    IMPROVED = "IMPROVED"


class FlakyMetricModel(BaseModel):
    test_id: str
    pass_count: int = 0
    fail_count: int = 0
    total_runs: int = 0
    flakiness_score: float = 0.0  # 0.0 (stable) to 1.0 (highly flaky)
    is_flaky: bool = False


class RegressionAnalysisModel(BaseModel):
    scan_id: str
    baseline_scan_id: Optional[str] = None
    new_failures: List[str] = Field(default_factory=list)
    regressions: List[str] = Field(default_factory=list)
    fixed_defects: List[str] = Field(default_factory=list)
    flaky_tests: List[FlakyMetricModel] = Field(default_factory=list)
