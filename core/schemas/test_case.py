"""
Strongly typed Pydantic models for Test Cases and Test Execution.
"""
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class TestPriority(str, Enum):
    __test__ = False
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TestCategory(str, Enum):
    __test__ = False
    FUNCTIONAL = "functional"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    FORM = "form"
    NAVIGATION = "navigation"
    API = "api"
    UI = "ui"
    RELIABILITY = "reliability"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"


class TestStepModel(BaseModel):
    step_index: int
    action: str  # click, fill, navigate, wait, assert, etc.
    target_selector: Optional[str] = None
    fallback_selectors: List[str] = Field(default_factory=list)
    value: Optional[str] = None
    expected_result: str


class TestCaseModel(BaseModel):
    id: str
    title: str
    objective: str
    category: TestCategory = TestCategory.FUNCTIONAL
    priority: TestPriority = TestPriority.P2
    risk_score: float = 0.5
    preconditions: List[str] = Field(default_factory=list)
    steps: List[TestStepModel] = Field(default_factory=list)
    expected_behavior: str
    evidence_requirements: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    cleanup_steps: List[str] = Field(default_factory=list)
