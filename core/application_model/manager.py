"""
Persistent Application Knowledge Model Manager for JASUSS.
"""
import json
import os
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from core.schemas.application_model import ApplicationKnowledgeModel, WorkflowModel, StateTransitionModel
from core.schemas.discovery import DiscoveryResultModel, PageModel


class ApplicationKnowledgeManager:
    def __init__(self, target_url: str, output_dir: str):
        self.target_url = target_url
        self.output_dir = output_dir
        self.parsed = urlparse(target_url)
        self.app_id = f"app_{self.parsed.netloc.replace('.', '_').replace(':', '_')}"
        self.model_path = os.path.join(output_dir, "application_model.json")
        self.model = self.load_model()
        self.save_model()

    def load_model(self) -> ApplicationKnowledgeModel:
        """Loads model from disk or initializes a new model."""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return ApplicationKnowledgeModel(**data)
            except Exception:
                pass

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return ApplicationKnowledgeModel(
            application_id=self.app_id,
            target_url=self.target_url,
            environments=["production"],
            technology_hints=[],
            discovered_at=now,
            last_updated=now,
            routes={},
            roles=["anonymous", "authenticated"],
            workflows=[],
            state_transitions=[],
            business_critical_paths=["/login", "/auth", "/dashboard", "/checkout", "/billing", "/settings"],
            api_endpoints=[],
        )

    def save_model(self):
        """Persists model to disk."""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self.model.last_updated = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self.model_path, "w", encoding="utf-8") as f:
            json.dump(self.model.model_dump(), f, indent=2)

    def update_from_discovery(self, discovery_data: Dict[str, Any]):
        """Updates the application model with newly discovered pages, routes, elements, APIs, and technology hints."""
        pages = discovery_data.get("pages", [])
        for page_dict in pages:
            route = page_dict.get("route", "/")
            url = page_dict.get("url", "")
            title = page_dict.get("title")
            forms = page_dict.get("forms", [])
            elements = page_dict.get("elements", [])
            api_calls = page_dict.get("api_calls", [])

            # Categorize route authentication requirement
            requires_auth = page_dict.get("requires_auth", False)
            if any(term in route.lower() for term in ["dashboard", "admin", "settings", "profile", "billing"]):
                requires_auth = True

            # Register API dependencies
            api_deps = [f"{api.get('method', 'GET')} {api.get('url')}" for api in api_calls]

            self.model.routes[route] = {
                "url": url,
                "title": title,
                "requires_auth": requires_auth,
                "forms_count": len(forms),
                "interactive_elements_count": len(elements),
                "api_dependencies": api_deps[:10],
                "last_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

            # Identify state transitions from interactive navigation
            if len(self.model.routes) > 1:
                route_keys = list(self.model.routes.keys())
                for i in range(len(route_keys) - 1):
                    t_id = f"tr_{route_keys[i]}_to_{route_keys[i+1]}"
                    if not any(st.transition_id == t_id for st in self.model.state_transitions):
                        self.model.state_transitions.append(
                            StateTransitionModel(
                                transition_id=t_id,
                                from_route=route_keys[i],
                                to_route=route_keys[i+1],
                                trigger_action="navigate_click",
                                api_triggers=[],
                            )
                        )

            # Auto-infer workflows
            if "/login" in self.model.routes and "/dashboard" in self.model.routes:
                if not any(wf.workflow_id == "wf_login_to_dashboard" for wf in self.model.workflows):
                    self.model.workflows.append(
                        WorkflowModel(
                            workflow_id="wf_login_to_dashboard",
                            name="User Authentication & Dashboard Access",
                            description="Login workflow leading to authenticated dashboard",
                            is_business_critical=True,
                            requires_role="anonymous",
                        )
                    )

        self.save_model()
        return self.model
