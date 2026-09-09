#!/usr/bin/env python3
"""
JASUSS End-to-End Autonomous Quality Engineering Pipeline (Nexus Engine V2).
Full integration of Pipeline State Machine, Application Knowledge Model, Resumable Discovery,
Risk Planning, Multi-Category Test Generation, Self-Healing Execution, SHA256 Defect Deduplication,
Regression Memory, API Testing, Accessibility/Performance Auditing, and Quality Gates.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime

from core.state_machine import PipelineStateMachine, PipelineStage
from core.agent.agent_orchestrator import AgentOrchestrator
from core.discovery.resumable_crawler import ResumableDiscoveryEngine
from core.application_model.manager import ApplicationKnowledgeManager
from core.planning.risk_planner import RiskPlannerEngine
from core.test_generator_v2 import AutonomousTestGenerator
from core.executor_v2 import SelfHealingExecutor
from core.defect_verification import DefectVerificationEngine
from core.regression_v2 import RegressionMemoryEngine
from core.api_testing.api_tester import ApiTestingEngine
from core.performance.perf_a11y_engine import PerfA11yEngine
from core.learning.pattern_extractor import HistoricalLearningEngine
from core.bug_detector import generate_qa_findings
from core.gemini_analyzer import generate_report
from core.qa_report_generator import QAReportGenerator
from core import ci_quality_gate

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


async def run_pipeline(url, max_pages=30, auth_token=None, run_id=None, output_dir=None,
                       login_url=None, username=None, password=None, **kwargs):
    """Executes the complete autonomous quality engineering pipeline end-to-end."""
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.abspath(output_dir) if output_dir else ROOT_DIR
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    print(f"Starting JASUSS Autonomous Quality Engineering Pipeline for: {url}")
    print(f"Run ID: {run_id}")
    print("=" * 70)

    # Initialize State Machine & Agent Orchestrator
    sm = PipelineStateMachine(run_id, results_dir)
    orchestrator = AgentOrchestrator(run_id, results_dir)

    # 1. DISCOVERING STAGE
    sm.transition_to(PipelineStage.DISCOVERING, "Starting resumable autonomous discovery engine...")
    orchestrator.log_decision("DiscoveryAgent", "DISCOVERING", f"Starting discovery on target {url}", {"target": url})

    discovery_engine = ResumableDiscoveryEngine(
        url,
        run_id=run_id,
        results_dir=results_dir,
        max_pages=max_pages,
        auth_token=auth_token,
        login_url=login_url,
        username=username,
        password=password,
    )
    discovery_result = await discovery_engine.execute_discovery()
    crawl_file = discovery_result.get("output_file")
    if not crawl_file or discovery_result.get("pages_crawled", 0) == 0:
        sm.transition_to(PipelineStage.FAILED, "Discovery failed to load target pages.")
        print("ERROR: Autonomous Discovery produced no pages.")
        return None

    # 2. MODELING STAGE
    sm.transition_to(PipelineStage.MODELING, "Building persistent Application Knowledge Model...")
    app_manager = ApplicationKnowledgeManager(url, results_dir)
    app_model = app_manager.update_from_discovery(discovery_result)
    orchestrator.log_decision("ModelingAgent", "MODELING", "Updated application knowledge graph", {"routes_count": len(app_model.routes)})

    # 3. PLANNING STAGE
    sm.transition_to(PipelineStage.PLANNING, "Generating risk-based test plan...")
    risk_planner = RiskPlannerEngine(app_model.model_dump(), results_dir, run_id)
    test_plan = risk_planner.generate_plan()
    orchestrator.log_decision("PlanningAgent", "PLANNING", f"Created risk-weighted test plan with {len(test_plan.suites)} suites", {"suites_count": len(test_plan.suites)})

    # 4. GENERATING STAGE
    sm.transition_to(PipelineStage.GENERATING, "Generating autonomous multi-category test cases...")
    generator = AutonomousTestGenerator(app_model.model_dump(), test_plan.model_dump(), results_dir, run_id)
    generated_test_cases = generator.generate_test_cases()
    orchestrator.log_decision("TestGenerationAgent", "GENERATING", f"Generated {len(generated_test_cases)} multi-category test cases", {"test_cases_count": len(generated_test_cases)})

    # 5. EXECUTING & ASSERTING STAGE
    sm.transition_to(PipelineStage.EXECUTING, "Executing test cases with self-healing executor...")
    executor = SelfHealingExecutor(generator.output_file, results_dir, run_id)
    execution_results = await executor.execute_suite()
    orchestrator.log_decision("ExecutionAgent", "EXECUTING", f"Executed {len(execution_results)} test cases", {"executed_count": len(execution_results)})

    # 6. VERIFYING & TRIAGING STAGE
    sm.transition_to(PipelineStage.VERIFYING, "Verifying assertions, API schemas, and performance/accessibility...")
    raw_findings_dict = generate_qa_findings(crawl_file=crawl_file, results_dir=results_dir, run_id=run_id)
    raw_findings = raw_findings_dict.get("findings", []) if raw_findings_dict else []

    # SHA256 Defect Verification & Deduplication
    defect_engine = DefectVerificationEngine(raw_findings, results_dir, run_id)
    deduplicated_defects = defect_engine.process_and_deduplicate()

    # API Testing & Perf/A11y Auditing
    api_engine = ApiTestingEngine(discovery_result.get("api_calls", []), results_dir, run_id)
    api_results = api_engine.run_api_tests()

    perf_a11y_engine = PerfA11yEngine(discovery_result.get("pages", []), results_dir, run_id)
    perf_a11y_report = perf_a11y_engine.audit_pages()

    # 7. TRIAGING & REGRESSION STAGE
    sm.transition_to(PipelineStage.TRIAGING, "Triaging deduplicated defect findings...")
    sm.transition_to(PipelineStage.REGRESSION, "Detecting regressions against historical memory...")
    baseline_file = kwargs.get("baseline_file")
    regression_engine = RegressionMemoryEngine([d.model_dump() for d in deduplicated_defects], baseline_file, results_dir, run_id)
    regression_analysis = regression_engine.analyze_regression()

    # Learning Engine Pattern Extraction
    learning_engine = HistoricalLearningEngine(app_manager.app_id, results_dir)
    learning_engine.record_run_outcomes([d.model_dump() for d in deduplicated_defects])

    # 8. SCORING STAGE
    sm.transition_to(PipelineStage.SCORING, "Computing quality gate & generating report...")
    findings_file = raw_findings_dict["output_file"] if raw_findings_dict else crawl_file
    gemini_result = await generate_report(findings_file=findings_file, results_dir=results_dir, run_id=run_id)
    if not gemini_result:
        sm.transition_to(PipelineStage.FAILED, "Gemini report generation failed.")
        return None

    # Report Generation
    report_gen = QAReportGenerator(results_dir=results_dir, base_dir=base_dir)
    report_gen.test_cases_file = generator.output_file
    report_gen.test_results_file = executor.output_file
    final_report = report_gen.generate(source_path=gemini_result["json_path"], run_id=run_id)

    sm.transition_to(PipelineStage.COMPLETED, "Scan pipeline completed successfully.")

    print("\nPipeline completed successfully!")
    print(f"Final JSON: {final_report['json_path']}")
    print(f"Final Markdown: {final_report['md_path']}")

    if kwargs.get("ci_mode"):
        exit_code = ci_quality_gate.evaluate_quality_gate(final_report["json_path"])
        if exit_code != 0:
            print(f"\nCI Quality Gate Failed with exit code {exit_code}")
            sys.exit(exit_code)
        else:
            print("\nCI Quality Gate Passed")

    return final_report


async def main():
    parser = argparse.ArgumentParser(description="JASUSS Autonomous Quality Engineering Pipeline")
    parser.add_argument("url", help="Target URL to analyze")
    parser.add_argument("--max-pages", type=int, default=30, help="Maximum pages to crawl")
    parser.add_argument("--auth-token", help="Optional Bearer token")
    parser.add_argument("--login-url", help="Optional Login URL")
    parser.add_argument("--username", help="Optional Username")
    parser.add_argument("--password", help="Optional Password")
    parser.add_argument("--run-id", help="Identifier for output files")
    parser.add_argument("--output-dir", help="Base directory for output")
    parser.add_argument("--ci", action="store_true", help="Run in CI mode with exit status")
    parser.add_argument("--baseline", help="Path to baseline report")

    args = parser.parse_args()
    if args.max_pages < 1:
        parser.error("--max-pages must be at least 1")

    password = args.password or os.environ.get("QA_AUTH_PASSWORD")
    try:
        result = await run_pipeline(
            args.url,
            max_pages=args.max_pages,
            auth_token=args.auth_token,
            run_id=args.run_id,
            output_dir=args.output_dir,
            login_url=args.login_url,
            username=args.username,
            password=password,
            ci_mode=args.ci,
            baseline_file=args.baseline,
        )
    except Exception as error:
        print(f"ERROR: Pipeline failed: {error}")
        return 1

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
