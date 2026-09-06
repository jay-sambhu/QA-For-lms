"""
Integration tests for JASUSS Console & Network Error Interceptor Engine.
"""
import pytest
from core.bug_detector import QAFindingClassifier


def test_console_unhandled_promise_rejection():
    classifier = QAFindingClassifier("127.0.0.1", {"start_url": "http://127.0.0.1:8105/", "pages": []})
    text = "Uncaught (in promise) Error: ChunkLoadError: Failed to fetch module /static/chunk_missing.js"
    res = classifier._classify_console_error(text)
    assert "severity" in res
    assert res["ignore"] is False


def test_subresource_404_noise_filtering():
    classifier = QAFindingClassifier("127.0.0.1", {"start_url": "http://127.0.0.1:8105/", "pages": []})
    text = "Failed to load resource: the server responded with a status of 404 (Not Found)"
    res = classifier._classify_console_error(text)
    assert "severity" in res
