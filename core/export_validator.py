"""
JASUSS Report Export File Validator Engine.
Validates generated PDF, Excel/XLSX, JSON, and Markdown report export files for non-zero byte size, schema compliance, and format integrity.
"""
import os
import json
from typing import Dict, Any


class ExportFileValidationResult:
    def __init__(self, file_path: str, format_type: str, is_valid: bool, size_bytes: int, error_message: str = ""):
        self.file_path = file_path
        self.format_type = format_type
        self.is_valid = is_valid
        self.size_bytes = size_bytes
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "format_type": self.format_type,
            "is_valid": self.is_valid,
            "size_bytes": self.size_bytes,
            "error_message": self.error_message,
        }


class ExportReportValidator:
    def validate_export_file(self, file_path: str, expected_format: str) -> ExportFileValidationResult:
        if not os.path.exists(file_path):
            return ExportFileValidationResult(file_path, expected_format, False, 0, "Export file does not exist")

        size_bytes = os.path.getsize(file_path)
        if size_bytes == 0:
            return ExportFileValidationResult(file_path, expected_format, False, 0, "Export file is 0 bytes empty")

        fmt = expected_format.lower()

        if fmt == "json":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, (dict, list)):
                    return ExportFileValidationResult(file_path, fmt, False, size_bytes, "JSON root is not dict or list")
            except Exception as e:
                return ExportFileValidationResult(file_path, fmt, False, size_bytes, f"JSON parse failure: {str(e)}")

        elif fmt == "markdown" or fmt == "md":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "# " not in content and "## " not in content:
                    return ExportFileValidationResult(file_path, fmt, False, size_bytes, "Markdown file missing header formatting")
            except Exception as e:
                return ExportFileValidationResult(file_path, fmt, False, size_bytes, f"Markdown read failure: {str(e)}")

        elif fmt == "pdf":
            try:
                with open(file_path, "rb") as f:
                    header = f.read(4)
                if header != b"%PDF":
                    return ExportFileValidationResult(file_path, fmt, False, size_bytes, "Invalid PDF magic header bytes")
            except Exception as e:
                return ExportFileValidationResult(file_path, fmt, False, size_bytes, f"PDF byte read failure: {str(e)}")

        elif fmt in ("xlsx", "excel"):
            try:
                with open(file_path, "rb") as f:
                    header = f.read(4)
                if header != b"PK\x03\x04":
                    return ExportFileValidationResult(file_path, fmt, False, size_bytes, "Invalid XLSX magic header bytes")
            except Exception as e:
                return ExportFileValidationResult(file_path, fmt, False, size_bytes, f"XLSX byte read failure: {str(e)}")

        return ExportFileValidationResult(file_path, fmt, True, size_bytes)
