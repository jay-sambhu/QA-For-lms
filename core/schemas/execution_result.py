"""
Strongly typed Pydantic models for Test Execution Results.
"""
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class TestResultStatus(str, Enum):
    __test__ = False
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"
    INCONCLUSIVE = "INCONCLUSIVE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class HealingRecordModel(BaseModel):
    step_index: int
    original_locator: str
    recovered_locator: str
    reason: str
    confidence: float
    behavior_equivalent: bool = True


class AssertionResultModel(BaseModel):
    assertion_type: str
    expected: Any
    actual: Any
    passed: bool
    message: str


class TestExecutionResultModel(BaseModel):
    test_id: str
    status: TestResultStatus
    duration_ms: int = 0
    executed_at: str
    error_message: Optional[str] = None
    step_results: List[Dict[str, Any]] = Field(default_factory=list)
    assertions: List[AssertionResultModel] = Field(default_factory=list)
    healing_events: List[HealingRecordModel] = Field(default_factory=list)
    screenshots: List[str] = Field(default_factory=list)
    network_har_path: Optional[str] = None
    console_logs: List[str] = Field(default_factory=list)
