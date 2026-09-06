"""
Unit tests for JASUSS ExportReportValidator.
"""
import os
import tempfile
import pytest
from core.export_validator import ExportReportValidator


def test_validate_json_export():
    validator = ExportReportValidator()
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write('{"scan_id": "scan_123", "status": "completed"}')
        path = f.name

    try:
        res = validator.validate_export_file(path, "json")
        assert res.is_valid is True
        assert res.size_bytes > 0
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_validate_empty_export():
    validator = ExportReportValidator()
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        path = f.name

    try:
        res = validator.validate_export_file(path, "markdown")
        assert res.is_valid is False
        assert "0 bytes" in res.error_message
    finally:
        if os.path.exists(path):
            os.remove(path)
