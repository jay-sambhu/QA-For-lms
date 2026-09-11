"""
Unit tests for Pipeline State Machine and Transitions.
"""
import os
import tempfile
import pytest
from core.state_machine import PipelineStateMachine, PipelineStage


def test_pipeline_state_machine_valid_flow():
    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = PipelineStateMachine("test_scan_001", tmp_dir)
        assert sm.current_stage == PipelineStage.CREATED

        sm.transition_to(PipelineStage.DISCOVERING, "Started discovery")
        assert sm.current_stage == PipelineStage.DISCOVERING

        sm.transition_to(PipelineStage.MODELING, "Building model")
        assert sm.current_stage == PipelineStage.MODELING

        sm.transition_to(PipelineStage.PLANNING, "Planning tests")
        assert sm.current_stage == PipelineStage.PLANNING

        sm.transition_to(PipelineStage.GENERATING, "Generating test cases")
        assert sm.current_stage == PipelineStage.GENERATING

        sm.transition_to(PipelineStage.EXECUTING, "Executing test cases")
        assert sm.current_stage == PipelineStage.EXECUTING

        sm.transition_to(PipelineStage.VERIFYING, "Verifying assertions")
        assert sm.current_stage == PipelineStage.VERIFYING

        sm.transition_to(PipelineStage.TRIAGING, "Triaging defects")
        assert sm.current_stage == PipelineStage.TRIAGING

        sm.transition_to(PipelineStage.REGRESSION, "Detecting regressions")
        assert sm.current_stage == PipelineStage.REGRESSION

        sm.transition_to(PipelineStage.SCORING, "Computing quality gate")
        assert sm.current_stage == PipelineStage.SCORING

        sm.transition_to(PipelineStage.COMPLETED, "Scan completed")
        assert sm.current_stage == PipelineStage.COMPLETED


def test_pipeline_state_machine_invalid_transition():
    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = PipelineStateMachine("test_scan_002", tmp_dir)
        with pytest.raises(ValueError, match="Invalid stage transition"):
            sm.transition_to(PipelineStage.COMPLETED, "Direct completion invalid")


def test_pipeline_state_machine_checkpoint_creation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = PipelineStateMachine("test_scan_003", tmp_dir)
        sm.transition_to(PipelineStage.DISCOVERING, "Discovery started")
        checkpoint_path = os.path.join(tmp_dir, "checkpoint_test_scan_003.json")
        assert os.path.exists(checkpoint_path)


def test_pipeline_state_machine_update_progress():
    import json
    calls = []
    def callback(stage, percent, message):
        calls.append((stage, percent, message))

    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = PipelineStateMachine("test_scan_004", tmp_dir, progress_cb=callback)
        sm.transition_to(PipelineStage.DISCOVERING, "Discovery initial")
        sm.update_progress(15, "Crawling page 1/5 [Desktop]", active_device="Desktop")

        progress_path = os.path.join(tmp_dir, "progress_test_scan_004.json")
        assert os.path.exists(progress_path)
        with open(progress_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["percent"] == 15
        assert data["message"] == "Crawling page 1/5 [Desktop]"
        assert data["active_device"] == "Desktop"
        assert len(calls) == 3  # CREATED, DISCOVERING, update_progress

