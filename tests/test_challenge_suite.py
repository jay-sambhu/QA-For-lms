"""
Unit and Integration Tests for Phase 19 Autonomous QA Challenge Suite & Scoring Engine.
"""
import os
import tempfile
import pytest

from benchmarks.autonomous.defect_registry import get_ground_truth_defects, HIDDEN_DEFECT_REGISTRY
from benchmarks.autonomous.challenge_registry import get_all_challenge_configs, CHALLENGE_APPS
from benchmarks.autonomous.scoring import evaluate_scan_against_ground_truth
from benchmarks.autonomous.report_generator import generate_challenge_suite_report


def test_defect_registry_integrity():
    apps = ["crud", "ecommerce", "lms", "dashboard", "spa", "complex_forms"]
    for app_key in apps:
        defects = get_ground_truth_defects(app_key)
        assert len(defects) >= 3, f"Expected at least 3 hidden defects for {app_key}"
        for d in defects:
            assert d.defect_id.startswith(app_key.upper()[:4]) or len(d.defect_id) > 0
            assert d.category in ["functional", "ui", "security", "api", "navigation", "javascript", "validation"]


def test_challenge_registry_configs():
    configs = get_all_challenge_configs()
    assert len(configs) == 6
    ports = [c.port for c in configs]
    assert len(ports) == len(set(ports)), "Challenge app ports must be unique"


def test_scoring_engine_calculation():
    raw_findings = [
        {
            "page": "http://127.0.0.1:8101/items/999/delete",
            "url": "http://127.0.0.1:8101/items/999/delete",
            "status": 500,
            "title": "Delete on item 999 raises HTTP 500",
            "description": "Database Constraint Failure",
            "severity": "high",
            "screenshot": "screenshot.png",
        },
        {
            "page": "http://127.0.0.1:8101/items/search",
            "url": "http://127.0.0.1:8101/items/search",
            "title": "Search page horizontal layout overflow",
            "description": "Horizontal overflow",
            "severity": "medium",
            "screenshot": "overflow.png",
        },
        {
            "page": "http://127.0.0.1:8101/items/create",
            "url": "http://127.0.0.1:8101/items/create",
            "title": "Item creation allows negative price input -100",
            "description": "Negative price input",
            "severity": "medium",
            "screenshot": "negative.png",
        },
    ]

    scorecard = evaluate_scan_against_ground_truth(
        app_key="crud",
        app_name="Application A — CRUD",
        raw_findings=raw_findings,
        agent_decisions=[{"action": "crawl"}],
        executed_tests_count=10,
    )

    assert scorecard.ground_truth_count == 3
    assert scorecard.true_positives == 3
    assert scorecard.false_positives == 0
    assert scorecard.false_negatives == 0
    assert scorecard.precision == 1.0
    assert scorecard.recall == 1.0
    assert scorecard.f1_score == 1.0
    assert scorecard.release_decision == "FAIL"  # Ground truth defects confirmed -> Release blocked (FAIL)


def test_report_generator():
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_findings = [
            {
                "page": "http://127.0.0.1:8101/items/999/delete",
                "url": "http://127.0.0.1:8101/items/999/delete",
                "status": 500,
                "title": "Delete on item 999 raises HTTP 500",
                "description": "Database Constraint Failure",
                "severity": "high",
            }
        ]
        card = evaluate_scan_against_ground_truth("crud", "CRUD App", raw_findings, [], 5)
        paths = generate_challenge_suite_report([card], tmp_dir)

        assert os.path.exists(paths["json"])
        assert os.path.exists(paths["markdown"])
