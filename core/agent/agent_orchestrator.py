"""
Modular Agent Orchestrator & Safety Layer for JASUSS (Phase 12).
"""
import json
import os
import re
from typing import Dict, List, Any
from pydantic import BaseModel, Field


class AgentDecisionModel(BaseModel):
    agent_name: str
    stage: str
    confidence: float
    reasoning: str
    output: Dict[str, Any] = Field(default_factory=dict)
    sanitized: bool = True


class AgentOrchestrator:
    """Orchestrates autonomous sub-agents with prompt-injection defense and schema validation."""

    def __init__(self, run_id: str, results_dir: str):
        self.run_id = run_id
        self.results_dir = results_dir
        self.decisions_log = os.path.join(results_dir, f"agent_decisions_{run_id}.json")
        self.history: List[AgentDecisionModel] = []

    @staticmethod
    def sanitize_untrusted_web_input(input_text: str) -> str:
        """Strips potential prompt-injection payloads from target webpage DOM/text."""
        if not input_text:
            return ""
        # Remove common prompt injection phrases
        sanitized = re.sub(r"(?i)(ignore previous instructions|system prompt|override safety)", "[REDACTED_PROMPT_INJECTION]", str(input_text))
        return sanitized

    def log_decision(self, agent_name: str, stage: str, reasoning: str, output: Dict[str, Any], confidence: float = 0.95):
        decision = AgentDecisionModel(
            agent_name=agent_name,
            stage=stage,
            confidence=confidence,
            reasoning=reasoning,
            output=output,
            sanitized=True,
        )
        self.history.append(decision)

        os.makedirs(self.results_dir, exist_ok=True)
        dump_data = [d.model_dump() for d in self.history]
        with open(self.decisions_log, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)

        return decision
