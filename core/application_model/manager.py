"""
Persistent Application Knowledge Model Manager for JASUSS.
"""
import json
import os
import re
import time
from typing import Dict, Any
from urllib.parse import urlparse

from core.schemas.application_model import ApplicationKnowledgeModel, WorkflowModel, StateTransitionModel


def _comparable_host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


class ApplicationKnowledgeManager:
    def __init__(self, target_url: str, output_dir: str):
        self.target_url = target_url
        self.output_dir = output_dir
        self.parsed = urlparse(target_url)
        self.app_id = f"app_{re.sub(r'[^A-Za-z0-9_.-]', '_', self.parsed.netloc).replace('.', '_').replace(':', '_')}"
        # One model per application: a user who scans site A and then site B
        # must not get A's routes (and test cases) inside B's report.
        self.model_path = os.path.join(output_dir, f"application_model_{self.app_id}.json")
        self.model = self.load_model()
        self.save_model()

    def _new_model(self) -> ApplicationKnowledgeModel:
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

    def load_model(self) -> ApplicationKnowledgeModel:
        """Loads model from disk or initializes a new model."""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                model = ApplicationKnowledgeModel(**data)
                # A stale or copied file for another host is not this
                # application's knowledge.
                if _comparable_host(model.target_url) != _comparable_host(self.target_url):
                    return self._new_model()
                model.application_id = self.app_id
                model.target_url = self.target_url
                return model
            except Exception:
                pass

        return self._new_model()

    def save_model(self):
        """Persists model to disk."""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self.model.last_updated = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self.model_path, "w", encoding="utf-8") as f:
            json.dump(self.model.model_dump(), f, indent=2)

    def update_from_discovery(self, discovery_data: Dict[str, Any]):
        """Rebuild routes, transitions and workflows from this run's
        discovery, so test generation only targets what the current crawl
        reached. Routes seen in earlier runs but not this one are listed in a
        `stale_routes:` technology hint; per-route first_seen/seen_runs carry
        the history forward."""
        pages = discovery_data.get("pages", [])
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        previous_routes = dict(self.model.routes)
        current_routes: Dict[str, Dict[str, Any]] = {}

        for page_dict in pages:
            if page_dict.get("error"):
                continue
            route = page_dict.get("route", "/")
            url = page_dict.get("url", "")
            title = page_dict.get("title")
            forms = page_dict.get("forms", [])
            elements = page_dict.get("elements", [])
            api_calls = page_dict.get("api_calls", [])

            # Categorize route authentication requirement
            requires_auth = bool(page_dict.get("requires_auth", False) or page_dict.get("auth_wall"))
            if any(term in route.lower() for term in ["dashboard", "admin", "settings", "profile", "billing"]):
                requires_auth = True

            # Register API dependencies
            api_deps = []
            for api in api_calls:
                dep = f"{api.get('method', 'GET')} {api.get('url')}"
                if dep not in api_deps:
                    api_deps.append(dep)

            previous = previous_routes.get(route) or {}
            current_routes[route] = {
                "url": url,
                "title": title,
                "status": page_dict.get("status"),
                "requires_auth": requires_auth,
                "auth_wall": bool(page_dict.get("auth_wall")),
                "viewports": page_dict.get("viewports", []),
                "forms_count": len(forms),
                "interactive_elements_count": len(elements),
                "api_dependencies": api_deps[:10],
                "first_seen": previous.get("first_seen") or now,
                "last_seen": now,
                "seen_runs": int(previous.get("seen_runs") or 0) + 1,
            }

        stale = sorted(set(previous_routes) - set(current_routes))
        self.model.routes = current_routes

        # State transitions between consecutively discovered routes
        route_keys = list(current_routes.keys())
        self.model.state_transitions = [
            StateTransitionModel(
                transition_id=f"tr_{route_keys[i]}_to_{route_keys[i+1]}",
                from_route=route_keys[i],
                to_route=route_keys[i+1],
                trigger_action="navigate_click",
                api_triggers=[],
            )
            for i in range(len(route_keys) - 1)
        ]

        # Auto-infer workflows
        workflows = []
        if "/login" in current_routes and "/dashboard" in current_routes:
            workflows.append(
                WorkflowModel(
                    workflow_id="wf_login_to_dashboard",
                    name="User Authentication & Dashboard Access",
                    description="Login workflow leading to authenticated dashboard",
                    is_business_critical=True,
                    requires_role="anonymous",
                )
            )
        self.model.workflows = workflows

        hints = [h for h in self.model.technology_hints if not h.startswith("stale_routes:")]
        if stale:
            hints.append("stale_routes:" + ",".join(stale[:50]))
        self.model.technology_hints = hints

        self.save_model()
        return self.model
