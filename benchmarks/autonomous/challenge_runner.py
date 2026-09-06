"""
Master Challenge Runner for JASUSS Phase 19 Autonomous QA Reality Validation.
Executes JASUSS in UNKNOWN_DEFECT_MODE across all 6 challenge applications.

Usage:
    python benchmarks/autonomous/challenge_runner.py [--app APP_KEY] [--viewports VIEWPORT_COUNT]
"""
import os
import sys
import argparse
import json
import time
import asyncio

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from benchmarks.autonomous.challenge_registry import (
    get_all_challenge_configs,
    CHALLENGE_APPS,
    ChallengeServerManager,
)
from benchmarks.autonomous.scoring import evaluate_scan_against_ground_truth
from benchmarks.autonomous.report_generator import generate_challenge_suite_report
from run_qa import run_pipeline


def run_challenge_suite(app_filter: str = None, viewports: int = 1) -> str:
    print("==========================================================================")
    print("JASUSS PHASE 19 — AUTONOMOUS QA CHALLENGE RUNNER")
    print("Execution Mode: UNKNOWN_DEFECT_MODE=true (Zero Prior Defect Hints)")
    print("==========================================================================")

    os.environ["UNKNOWN_DEFECT_MODE"] = "true"
    output_base_dir = os.path.abspath("results/autonomous_validation")
    os.makedirs(output_base_dir, exist_ok=True)

    configs = get_all_challenge_configs()
    if app_filter and app_filter in CHALLENGE_APPS:
        configs = [CHALLENGE_APPS[app_filter]]

    scorecards = []

    for cfg in configs:
        print(f"\n--------------------------------------------------------------------------")
        print(f"STARTING CHALLENGE: {cfg.name} ({cfg.key})")
        print(f"Target URL: {cfg.base_url}")
        print(f"--------------------------------------------------------------------------")

        # Start App Server
        mgr = ChallengeServerManager(cfg)
        started = mgr.start()
        if not started:
            print(f"ERROR: Failed to start server for {cfg.name} on {cfg.base_url}")
            continue

        scan_id = f"challenge_{cfg.key}_{int(time.time())}"
        app_results_dir = os.path.join(output_base_dir, cfg.key)
        os.makedirs(app_results_dir, exist_ok=True)

        try:
            # Run JASUSS Pipeline
            pipeline_results = asyncio.run(run_pipeline(
                url=cfg.base_url,
                run_id=scan_id,
                output_dir=app_results_dir,
            ))

            results_subdir = os.path.join(app_results_dir, "results")
            target_folder = results_subdir if os.path.exists(results_subdir) else app_results_dir

            qa_findings_path = os.path.join(target_folder, f"qa_findings_{scan_id}.json")
            agent_decisions_path = os.path.join(target_folder, f"agent_decisions_{scan_id}.json")
            execution_results_path = os.path.join(target_folder, f"execution_results_{scan_id}.json")

            raw_findings = []
            if os.path.exists(qa_findings_path):
                data = json.load(open(qa_findings_path))
                raw_findings = data.get("page_level_findings", [])

            agent_decisions = []
            if os.path.exists(agent_decisions_path):
                agent_decisions = json.load(open(agent_decisions_path))

            executed_tests_count = 0
            if os.path.exists(execution_results_path):
                executed_tests_count = len(json.load(open(execution_results_path)))

            # Score against ground truth
            card = evaluate_scan_against_ground_truth(
                app_key=cfg.key,
                app_name=cfg.name,
                raw_findings=raw_findings,
                agent_decisions=agent_decisions,
                executed_tests_count=executed_tests_count,
            )
            scorecards.append(card)

            print(f"  True Positives:  {card.true_positives} / {card.ground_truth_count}")
            print(f"  False Positives: {card.false_positives}")
            print(f"  False Negatives: {card.false_negatives}")
            print(f"  Precision:       {card.precision}")
            print(f"  Recall:          {card.recall}")
            print(f"  F1 Score:        {card.f1_score}")
            print(f"  Autonomy Rate:   {card.autonomy_rate * 100:.1f}%")

        finally:
            mgr.stop()

    # Generate Suite Report
    paths = generate_challenge_suite_report(scorecards, output_base_dir)

    print("\n==========================================================================")
    print("CHALLENGE SUITE COMPLETED SUCCESSFULLY!")
    print(f"JSON Report:     {paths['json']}")
    print(f"Markdown Report: {paths['markdown']}")
    print("==========================================================================")
    return paths["markdown"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JASUSS Autonomous QA Challenge Runner")
    parser.add_argument("--app", type=str, help="Filter by app key (crud, ecommerce, lms, dashboard, spa, complex_forms)")
    parser.add_argument("--viewports", type=int, default=1, help="Number of viewports to simulate")
    args = parser.parse_args()

    run_challenge_suite(app_filter=args.app, viewports=args.viewports)
