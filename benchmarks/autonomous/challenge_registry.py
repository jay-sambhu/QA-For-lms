"""
Challenge App Registry & Lifecycle Manager for Phase 19 Autonomous Benchmarks.
Manages dynamic Uvicorn server processes and port assignments.
"""
import time
import subprocess
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ChallengeAppConfig:
    key: str
    name: str
    description: str
    module_path: str  # e.g., "tests.challenge_apps.crud.main:app"
    port: int
    base_url: str


CHALLENGE_APPS: Dict[str, ChallengeAppConfig] = {
    "crud": ChallengeAppConfig(
        key="crud",
        name="Application A — CRUD Inventory",
        description="Inventory management with Auth, Dashboard, Create, Edit, Delete, Search, and Pagination",
        module_path="tests.challenge_apps.crud.main:app",
        port=8101,
        base_url="http://127.0.0.1:8101",
    ),
    "ecommerce": ChallengeAppConfig(
        key="ecommerce",
        name="Application B — E-Commerce ShopSphere",
        description="Product catalog, cart management, discount calculation, and checkout pipeline",
        module_path="tests.challenge_apps.ecommerce.main:app",
        port=8102,
        base_url="http://127.0.0.1:8102",
    ),
    "lms": ChallengeAppConfig(
        key="lms",
        name="Application C — LMS EduPortal",
        description="Course catalog, student lessons, quiz submission, and instructor portal",
        module_path="tests.challenge_apps.lms.main:app",
        port=8103,
        base_url="http://127.0.0.1:8103",
    ),
    "dashboard": ChallengeAppConfig(
        key="dashboard",
        name="Application D — Enterprise Admin Console",
        description="Multi-role administration console, user management, audit logs, and system logs API",
        module_path="tests.challenge_apps.dashboard.main:app",
        port=8104,
        base_url="http://127.0.0.1:8104",
    ),
    "spa": ChallengeAppConfig(
        key="spa",
        name="Application E — Single Page App (SPA)",
        description="Modern SPA with client-side tabs, activity feed API, lazy chunk loader, and settings",
        module_path="tests.challenge_apps.spa.main:app",
        port=8105,
        base_url="http://127.0.0.1:8105",
    ),
    "complex_forms": ChallengeAppConfig(
        key="complex_forms",
        name="Application F — Complex Form Wizard",
        description="Multi-step registration wizard with dependent dropdowns and boundary validation",
        module_path="tests.challenge_apps.complex_forms.main:app",
        port=8106,
        base_url="http://127.0.0.1:8106",
    ),
}


class ChallengeServerManager:
    """Manages spawning and tearing down challenge app Uvicorn instances."""

    def __init__(self, config: ChallengeAppConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None

    def start(self, timeout_sec: int = 10) -> bool:
        cmd = [
            "uvicorn",
            self.config.module_path,
            "--host",
            "127.0.0.1",
            "--port",
            str(self.config.port),
            "--log-level",
            "error",
        ]
        self.process = subprocess.Popen(cmd)
        
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            try:
                res = requests.get(self.config.base_url, timeout=1.0)
                if res.status_code < 500 or res.status_code == 404:
                    return True
            except Exception:
                time.sleep(0.3)
        return False

    def stop(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None


def get_all_challenge_configs() -> List[ChallengeAppConfig]:
    return list(CHALLENGE_APPS.values())
