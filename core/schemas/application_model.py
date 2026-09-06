"""
Strongly typed Pydantic models for Persistent Application Intelligence Model.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class WorkflowStepModel(BaseModel):
    step_number: int
    action: str
    target_selector: str
    target_page_url: str
    input_value: Optional[str] = None
    expected_state: Optional[str] = None


class WorkflowModel(BaseModel):
    workflow_id: str
    name: str
    description: str
    is_business_critical: bool = False
    requires_role: Optional[str] = None
    steps: List[WorkflowStepModel] = Field(default_factory=list)


class StateTransitionModel(BaseModel):
    transition_id: str
    from_route: str
    to_route: str
    trigger_action: str
    api_triggers: List[str] = Field(default_factory=list)


class ApplicationKnowledgeModel(BaseModel):
    application_id: str
    target_url: str
    environments: List[str] = Field(default_factory=lambda: ["production"])
    technology_hints: List[str] = Field(default_factory=list)
    discovered_at: str
    last_updated: str
    routes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    roles: List[str] = Field(default_factory=lambda: ["anonymous", "authenticated"])
    workflows: List[WorkflowModel] = Field(default_factory=list)
    state_transitions: List[StateTransitionModel] = Field(default_factory=list)
    business_critical_paths: List[str] = Field(default_factory=list)
    api_endpoints: List[Dict[str, Any]] = Field(default_factory=list)
