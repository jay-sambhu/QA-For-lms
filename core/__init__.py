"""
JASUSS Core QA Pipeline & Defect Analysis Modules (Powered by Nexus)

Re-exports are resolved lazily (PEP 562). Importing a light submodule such as
``core.ai_config`` or ``core.supabase_storage`` from the API process must not
drag Playwright or the LLM SDKs into memory; those are only
needed by the worker that actually runs the pipeline.
"""

import importlib

_LAZY_EXPORTS = {
    "QAFindingClassifier": ".bug_detector",
    "generate_qa_findings": ".bug_detector",
    "CalculationEngine": ".calculation_engine",
    "CanonicalQAMetrics": ".calculation_engine",
    "QualityScore": ".calculation_engine",
    "FindingMetrics": ".calculation_engine",
    "TestCaseMetrics": ".calculation_engine",
    "GeminiQAAnalyzer": ".gemini_analyzer",
    "generate_report": ".gemini_analyzer",
    "QAReportGenerator": ".qa_report_generator",
    "RegressionDetector": ".regression_detector",
    "evaluate_quality_gate": ".ci_quality_gate",
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name):
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
