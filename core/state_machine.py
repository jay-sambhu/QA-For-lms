"""
Deterministic Pipeline State Machine for JASUSS Scan Orchestration.
"""
import json
import os
import time
from enum import Enum
from typing import Dict, Any, Optional, Set, Callable


class PipelineStage(str, Enum):
    CREATED = "CREATED"
    DISCOVERING = "DISCOVERING"
    MODELING = "MODELING"
    PLANNING = "PLANNING"
    GENERATING = "GENERATING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    TRIAGING = "TRIAGING"
    REGRESSION = "REGRESSION"
    SCORING = "SCORING"
    COMPLETED = "COMPLETED"

    # Terminal / Non-success states
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"
    NEEDS_REVIEW = "NEEDS_REVIEW"


STAGE_PROGRESS_MAP: Dict[PipelineStage, int] = {
    PipelineStage.CREATED: 0,
    PipelineStage.DISCOVERING: 10,
    PipelineStage.MODELING: 25,
    PipelineStage.PLANNING: 35,
    PipelineStage.GENERATING: 45,
    PipelineStage.EXECUTING: 60,
    PipelineStage.VERIFYING: 75,
    PipelineStage.TRIAGING: 85,
    PipelineStage.REGRESSION: 90,
    PipelineStage.SCORING: 95,
    PipelineStage.COMPLETED: 100,
    PipelineStage.FAILED: 100,
    PipelineStage.CANCELLED: 100,
    PipelineStage.PARTIAL: 100,
    PipelineStage.NEEDS_REVIEW: 100,
}


ALLOWED_TRANSITIONS: Dict[PipelineStage, Set[PipelineStage]] = {
    PipelineStage.CREATED: {PipelineStage.DISCOVERING, PipelineStage.FAILED, PipelineStage.CANCELLED},
    PipelineStage.DISCOVERING: {PipelineStage.MODELING, PipelineStage.FAILED, PipelineStage.CANCELLED, PipelineStage.PARTIAL},
    PipelineStage.MODELING: {PipelineStage.PLANNING, PipelineStage.FAILED, PipelineStage.CANCELLED, PipelineStage.PARTIAL},
    PipelineStage.PLANNING: {PipelineStage.GENERATING, PipelineStage.FAILED, PipelineStage.CANCELLED, PipelineStage.PARTIAL},
    PipelineStage.GENERATING: {PipelineStage.EXECUTING, PipelineStage.FAILED, PipelineStage.CANCELLED, PipelineStage.PARTIAL},
    PipelineStage.EXECUTING: {PipelineStage.VERIFYING, PipelineStage.FAILED, PipelineStage.CANCELLED, PipelineStage.PARTIAL},
    PipelineStage.VERIFYING: {PipelineStage.TRIAGING, PipelineStage.FAILED, PipelineStage.CANCELLED, PipelineStage.PARTIAL, PipelineStage.NEEDS_REVIEW},
    PipelineStage.TRIAGING: {PipelineStage.REGRESSION, PipelineStage.FAILED, PipelineStage.CANCELLED, PipelineStage.PARTIAL, PipelineStage.NEEDS_REVIEW},
    PipelineStage.REGRESSION: {PipelineStage.SCORING, PipelineStage.FAILED, PipelineStage.CANCELLED, PipelineStage.PARTIAL},
    PipelineStage.SCORING: {PipelineStage.COMPLETED, PipelineStage.FAILED, PipelineStage.CANCELLED, PipelineStage.NEEDS_REVIEW},
    PipelineStage.COMPLETED: set(),
    PipelineStage.FAILED: set(),
    PipelineStage.CANCELLED: set(),
    PipelineStage.PARTIAL: set(),
    PipelineStage.NEEDS_REVIEW: set(),
}


class PipelineStateMachine:
    def __init__(self, scan_id: str, results_dir: str, progress_cb: Optional[Callable[[str, int, str], None]] = None):
        self.scan_id = scan_id
        self.results_dir = results_dir
        self.progress_cb = progress_cb
        self.current_stage = PipelineStage.CREATED
        self.history = []
        self.checkpoint_file = os.path.join(results_dir, f"checkpoint_{scan_id}.json")
        self.progress_file = os.path.join(results_dir, f"progress_{scan_id}.json")
        os.makedirs(results_dir, exist_ok=True)
        self._record_state(PipelineStage.CREATED, "Pipeline state machine initialized.")

    def transition_to(self, next_stage: PipelineStage, message: str = "", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Transitions pipeline to next_stage if allowed."""
        if next_stage not in ALLOWED_TRANSITIONS[self.current_stage]:
            raise ValueError(
                f"Invalid stage transition from {self.current_stage.value} to {next_stage.value} "
                f"for scan {self.scan_id}."
            )

        self.current_stage = next_stage
        self._record_state(next_stage, message, metadata)
        return True

    def _record_state(self, stage: PipelineStage, message: str, metadata: Optional[Dict[str, Any]] = None):
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        percent = STAGE_PROGRESS_MAP.get(stage, 0)
        entry = {
            "stage": stage.value,
            "percent": percent,
            "message": message,
            "timestamp": timestamp,
            "metadata": metadata or {},
        }
        self.history.append(entry)

        # Write progress JSON for live polling API
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump({
                    "scan_id": self.scan_id,
                    "stage": stage.value,
                    "percent": percent,
                    "message": message,
                    "timestamp": timestamp,
                }, f)
        except Exception:
            pass

        # Write checkpoint file
        try:
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump({
                    "scan_id": self.scan_id,
                    "current_stage": stage.value,
                    "history": self.history,
                }, f, indent=2)
        except Exception:
            pass

        if self.progress_cb:
            try:
                self.progress_cb(stage.value, percent, message)
            except Exception:
                pass

    def update_progress(self, percent: int, message: str, **metadata):
        """Updates live progress percent and message without transitioning stage."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump({
                    "scan_id": self.scan_id,
                    "stage": self.current_stage.value,
                    "percent": percent,
                    "message": message,
                    "timestamp": timestamp,
                    **metadata,
                }, f)
        except Exception:
            pass

        if self.progress_cb:
            try:
                self.progress_cb(self.current_stage.value, percent, message)
            except Exception:
                pass
