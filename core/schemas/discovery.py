"""
Strongly typed Pydantic models for Discovery Engine artifacts.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ElementModel(BaseModel):
    element_id: str
    tag_name: str
    role: Optional[str] = None
    text: Optional[str] = None
    attributes: Dict[str, str] = Field(default_factory=dict)
    is_visible: bool = True
    is_enabled: bool = True
    location: Optional[Dict[str, float]] = None
    selector_hierarchy: List[str] = Field(default_factory=list)


class FormModel(BaseModel):
    form_id: str
    action: Optional[str] = None
    method: str = "GET"
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    has_submit_button: bool = False


class ApiEndpointModel(BaseModel):
    url: str
    method: str
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    latency_ms: Optional[float] = None
    request_headers: Dict[str, str] = Field(default_factory=dict)
    response_headers: Dict[str, str] = Field(default_factory=dict)
    is_xhr_or_fetch: bool = True


class PageModel(BaseModel):
    page_id: str
    url: str
    route: str
    title: Optional[str] = None
    viewport: str = "desktop"
    requires_auth: bool = False
    status_code: int = 200
    elements: List[ElementModel] = Field(default_factory=list)
    forms: List[FormModel] = Field(default_factory=list)
    api_calls: List[ApiEndpointModel] = Field(default_factory=list)
    console_errors: List[str] = Field(default_factory=list)
    network_errors: List[str] = Field(default_factory=list)
    screenshot_path: Optional[str] = None


class DiscoveryResultModel(BaseModel):
    scan_id: str
    target_url: str
    start_time: str
    end_time: Optional[str] = None
    pages_attempted: int = 0
    pages_crawled: int = 0
    pages_failed: int = 0
    pages: List[PageModel] = Field(default_factory=list)
    routes_discovered: List[str] = Field(default_factory=list)
    viewports_tested: List[str] = Field(default_factory=list)
